'use strict';

// Run in a disposable VS Code Extension Development Host.
const vscode = require('vscode');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

async function until(condition, message) {
  for (let i = 0; i < 160; i++) {
    if (await condition()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(message);
}

async function run() {
  const folder = vscode.workspace.workspaceFolders[0].uri;
  const file = path.join(folder.fsPath, 'results.tex');
  const initial = '月面で測った。\r\n\r\n結果 A。\r\n';
  await fs.writeFile(file, '\uFEFF' + initial);
  const source = await vscode.workspace.openTextDocument(vscode.Uri.file(file));
  await vscode.window.showTextDocument(source);
  await vscode.commands.executeCommand('paperops.openReview');
  const editor = vscode.window.activeTextEditor;
  const review = editor.document;
  assert.equal(review.uri.scheme, 'paperops-review');
  const text = () => review.getText().replace(/\r\n/g, '\n');
  const disk = async () => (await fs.readFile(file, 'utf8')).replace(/\r\n/g, '\n');
  await editor.edit(edit => edit.insert(new vscode.Position(0, 0), '%> 出典は？\n'));
  await fs.writeFile(file, '\uFEFF' + initial.replace('結果 A', '結果 B'));
  await until(() => text().includes('結果 B'), '編集中の原稿の更新');
  assert.match(text(), /%> 出典は？/);
  assert.doesNotMatch(await disk(), /%>/);
  assert.ok(await review.save(), '添削タブの保存');
  assert.equal(await fs.readFile(file, 'utf8'), '\uFEFF' + text().replace(/\n/g, '\r\n'));

  // The second disk update arrives before the poll or the save sees it.
  const line = review.lineAt(3);
  assert.ok(await editor.edit(edit => edit.replace(line.range, '結果 C。')));
  await fs.writeFile(file, (await fs.readFile(file, 'utf8')).replace('結果 B', '結果 D'));
  await until(() => text().includes('<<<<<<< Paperops:'), '重なった変更の表示');
  assert.match(text(), /結果 C。/);
  assert.match(text(), /結果 D。/);
  assert.equal(await review.save(), false, '未解決のまま保存');
  assert.match(await disk(), /結果 D。/);
  assert.doesNotMatch(await disk(), /<<<|結果 C/);
  const start = text().indexOf('<<<<<<<');
  const end = text().indexOf('\n', text().indexOf('>>>>>>>')) + 1;
  // The virtual review uses the editor's own line endings.
  const positions = offset => new vscode.Position(text().slice(0, offset).split('\n').length - 1,
    text().slice(0, offset).split('\n').pop().length);
  assert.ok(await editor.edit(edit => edit.replace(new vscode.Range(positions(start), positions(end)), '結果 CD。\n')));
  assert.ok(await review.save(), '解決後の保存');
  assert.match(await disk(), /結果 CD。/);
  assert.doesNotMatch(await disk(), /<<<|>>>/);

  assert.ok(await editor.edit(edit => edit.insert(new vscode.Position(1, 0), '%> 単位は？\n')));
  await fs.writeFile(file, (await fs.readFile(file, 'utf8')).replace('結果 CD', '結果 EF'));
  assert.ok(await review.save(), '外部の更新直後に別箇所の編集を保存');
  assert.match(await disk(), /%> 単位は？/);
  assert.match(await disk(), /結果 EF。/);
  await until(() => text().includes('結果 EF。'), '保存と重なった変更も添削タブに反映');

  const last = review.lineAt(review.lineCount - 2);
  assert.ok(await editor.edit(edit => edit.replace(last.range, 'こちらの結果。')));
  await fs.writeFile(file, (await fs.readFile(file, 'utf8')).replace('結果 EF', '原稿の結果'));
  assert.equal(await review.save(), false, '外部の更新直後に同じ箇所を保存');
  await until(() => text().includes('<<<<<<< Paperops:'), '保存時の競合を表示');
  assert.match(await disk(), /原稿の結果。/);
  assert.doesNotMatch(await disk(), /こちらの結果|<<<<</);
  console.log('PAPEROPS_REVIEW_HOST_PASS');
}
module.exports = { run };
