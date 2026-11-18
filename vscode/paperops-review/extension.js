'use strict';

const vscode = require('vscode');
const { createHash } = require('node:crypto');
const { merge, hasMarkers, replacements } = require('./merge');

const scheme = 'paperops-review';
const normalize = text => text.replace(/\r\n/g, '\n');
const digest = text => createHash('sha256').update(text).digest('hex');
const fail = message => vscode.FileSystemError.Unavailable(message);

async function diskText(uri) {
  const bytes = await vscode.workspace.fs.readFile(uri);
  return normalize(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}

// No await between the version check and applyEdit. VS Code also carries the
// open document's version on the bulk edit sent to the editor process.
function applyText(doc, version, text) {
  if (doc.isClosed || doc.version !== version) return Promise.resolve(false);
  const before = doc.getText();
  const after = doc.eol === vscode.EndOfLine.CRLF ? text.replace(/\n/g, '\r\n') : text;
  const edit = new vscode.WorkspaceEdit();
  for (const part of replacements(before, after)) {
    edit.replace(doc.uri, new vscode.Range(doc.positionAt(part.start), doc.positionAt(part.end)), part.text);
  }
  return vscode.workspace.applyEdit(edit);
}

class Reviews {
  constructor(context) {
    this.storage = context.workspaceState;
    this.running = new Map();
    this.events = new vscode.EventEmitter();
    this.onDidChangeFile = this.events.event;
    this.warnings = new Map();
  }

  key(uri) { return uri.toString(); }

  state(uri) {
    const state = this.storage.get(this.key(uri));
    if (!state) throw vscode.FileSystemError.FileNotFound(uri);
    return state;
  }

  document(uri) {
    return vscode.workspace.textDocuments.find(doc => this.key(doc.uri) === this.key(uri));
  }

  async open(source) {
    if (!source || !['file', 'vscode-remote'].includes(source.scheme) || !/\.tex$/i.test(source.path)) {
      throw fail('原稿の .tex タブで実行してください。');
    }
    const name = source.path.split('/').pop().replace(/\.tex$/i, '（添削）.tex');
    const existing = vscode.workspace.textDocuments.find(doc =>
      doc.uri.scheme === scheme && this.storage.get(this.key(doc.uri))?.source === source.toString());
    const id = digest(vscode.env.sessionId + '\n' + source.toString());
    const uri = existing?.uri || vscode.Uri.from({ scheme, path: '/' + id + '/' + name });
    if (!this.document(uri)) {
      const original = this.document(source);
      if (original?.isDirty) throw fail('元のタブの未保存の編集を保存してから添削用タブを開いてください。');
      // If VS Code still has a hot-exit backup it can restore it on open.
      // Keep the associated baseline for that backup across window reloads.
      if (!this.storage.get(this.key(uri))) {
        await this.storage.update(this.key(uri), { source: source.toString(), base: await diskText(source) });
      }
    }
    const doc = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(doc, { preview: false });
    this.poll(doc);
  }

  async locked(uri, action) {
    const key = this.key(uri);
    const previous = this.running.get(key) || Promise.resolve();
    const next = previous.catch(() => {}).then(action);
    this.running.set(key, next);
    try { return await next; }
    finally { if (this.running.get(key) === next) this.running.delete(key); }
  }

  // A window can close between a versioned buffer edit and recording its new
  // merge base. Only adopt a pending baseline when we can identify the buffer.
  async recover(doc, state) {
    if (!state.pending) return state;
    const current = digest(normalize(doc.getText()));
    const { before, after, nextBase } = state.pending;
    if (doc.isDirty && current !== before && current !== after) {
      throw fail('中断前の編集を確認できません。添削用タブを別名で保存し、原稿と比較してください。');
    }
    const base = current === after ? nextBase : state.base;
    const restored = { source: state.source, base };
    await this.storage.update(this.key(doc.uri), restored);
    return restored;
  }

  async refresh(doc) {
    if (doc.isClosed) return;
    const uri = doc.uri;
    const state = await this.recover(doc, this.state(uri));
    const incoming = await diskText(vscode.Uri.parse(state.source));
    const version = doc.version;
    const before = normalize(doc.getText());
    if (doc.isClosed || hasMarkers(before)) return;
    const after = doc.isDirty ? merge(state.base, before, incoming) : incoming;
    if (before === after && state.base === incoming) return;
    const updated = { source: state.source, base: incoming };
    if (before !== after) {
      const pending = { before: digest(before), after: digest(after), nextBase: incoming };
      await this.storage.update(this.key(uri), { ...state, pending });
      if (!await applyText(doc, version, after)) {
        await this.storage.update(this.key(uri), state);
        return;
      }
    }
    await this.storage.update(this.key(uri), updated);
    if (hasMarkers(after)) this.warn(uri, '同じ箇所に変更があります。添削用タブで残す内容を選んで保存してください。');
  }

  warn(uri, message) {
    const key = this.key(uri);
    if (this.warnings.get(key) !== message) {
      this.warnings.set(key, message);
      void vscode.window.showWarningMessage('Paperops: ' + message);
    }
  }

  poll(doc) {
    if (doc.uri.scheme !== scheme || this.running.has(this.key(doc.uri))) return;
    void this.locked(doc.uri, () => this.refresh(doc)).catch(err => this.warn(doc.uri, err.message));
  }

  async writeFile(uri, bytes) {
    await this.locked(uri, async () => {
      const doc = this.document(uri);
      const local = normalize(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (!doc || normalize(doc.getText()) !== local) throw fail('入力が続いています。もう一度保存してください。');
      if (hasMarkers(local)) throw fail('添削用タブの競合箇所を解決してから保存してください。');
      const state = await this.recover(doc, this.state(uri));
      const target = vscode.Uri.parse(state.source);
      const incoming = await diskText(target);
      const result = merge(state.base, local, incoming);
      if (hasMarkers(result)) {
        await this.refresh(doc);
        throw fail('同じ箇所に変更があります。添削用タブで競合を解決してください。');
      }
      if (result !== incoming) await this.saveOriginal(target, incoming, result);
      // The editor just saved "local". Any intervening disk edits not already
      // in that snapshot are incoming changes on the next refresh.
      await this.storage.update(this.key(uri), { source: state.source, base: local });
      this.warnings.delete(this.key(uri));
    });
  }

  async saveOriginal(uri, expected, result) {
    const original = await vscode.workspace.openTextDocument(uri);
    const stale = () => fail('原稿が再度変更されました。元のタブの未保存の編集を確認して、もう一度保存してください。');
    // The normal file editor may receive its file-watcher event slightly
    // later than our read at save time, especially over Remote SSH.
    for (let i = 0; i < 12 && !original.isDirty && normalize(original.getText()) !== expected; i++) {
      if (await diskText(uri) !== expected) throw stale();
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const version = original.version;
    if (original.isDirty || normalize(original.getText()) !== expected || await diskText(uri) !== expected) throw stale();
    if (!await applyText(original, version, result)) throw stale();
    const latest = await diskText(uri);
    if (latest !== expected && latest !== result) {
      // Only withdraw the edit we just staged. Leave any concurrent typing
      // alone and keep the author's complete working copy in the review tab.
      if (!original.isClosed && normalize(original.getText()) === result) {
        await applyText(original, original.version, latest);
      }
      throw stale();
    }
    if (original.isClosed || normalize(original.getText()) !== result || !await original.save()) throw stale();
  }

  // The virtual file has its own save validation above. Its synthetic mtime
  // stays stable while live changes are applied to the in-memory editor.
  watch() { return new vscode.Disposable(() => {}); }
  stat(uri) {
    const size = Buffer.byteLength(this.state(uri).base);
    return { type: vscode.FileType.File, ctime: 1, mtime: 1, size };
  }
  readFile(uri) { return Buffer.from(this.state(uri).base); }
  readDirectory() { return []; }
  createDirectory() { throw vscode.FileSystemError.NoPermissions(); }
  delete() { throw vscode.FileSystemError.NoPermissions(); }
  rename() { throw vscode.FileSystemError.NoPermissions(); }
}

function activate(context) {
  const reviews = new Reviews(context);
  const visible = () => {
    for (const editor of vscode.window.visibleTextEditors) reviews.poll(editor.document);
  };
  // Poll only visible review tabs. Remote SSH and symlinked paper directories
  // can miss file-watcher notifications from another HPC login node.
  const timer = setInterval(visible, 1500);
  context.subscriptions.push(reviews.events,
    vscode.workspace.registerFileSystemProvider(scheme, reviews, { isCaseSensitive: true }),
    vscode.commands.registerCommand('paperops.openReview', async uri => {
      try { await reviews.open(uri || vscode.window.activeTextEditor?.document.uri); }
      catch (err) { void vscode.window.showErrorMessage('Paperops: ' + err.message); }
    }),
    vscode.window.onDidChangeVisibleTextEditors(visible),
    new vscode.Disposable(() => clearInterval(timer)));
  visible();
}

module.exports = { activate, Reviews };
