'use strict';

const { diff3Merge, diffIndices } = require('node-diff3');

// Keep line endings in the tokens so a missing final newline survives a merge.
function lines(text) {
  return text.match(/[^\n]*\n|[^\n]+$/g) || [];
}

// Trim unchanged ends of a replacement, including within a TeX source line.
function change(before, after) {
  let start = 0;
  let end = before.length;
  let tail = after.length;
  while (start < end && start < tail && before[start] === after[start]) start++;
  while (end > start && tail > start && before[end - 1] === after[tail - 1]) {
    end--;
    tail--;
  }
  return { start, end, text: after.slice(start, tail) };
}

const hasMarkers = text => /^(?:<<<<<<< Paperops: 添削|\|\|\|\|\|\|\| Paperops: 編集開始時|=======|>>>>>>> Paperops: 原稿)\r?$/m.test(text);

function merge(base, local, incoming) {
  if (local === base || local === incoming) return incoming;
  if (incoming === base) return local;
  const parts = diff3Merge(lines(local), lines(base), lines(incoming));
  const result = [];
  for (const part of parts) {
    if (part.ok) {
      result.push(part.ok.join(''));
      continue;
    }
    const original = part.conflict.o.join('');
    const ours = part.conflict.a.join('');
    const theirs = part.conflict.b.join('');
    const edits = [change(original, ours), change(original, theirs)]
      .sort((a, b) => a.start - b.start || a.end - b.end);
    const [first, second] = edits;
    const sameInsertion = first.start === first.end && second.start === second.end && first.start === second.start;
    const deletedAnchor = first.end === second.start && (
      (first.start === first.end && !second.text) || (!first.text && second.start === second.end)
    );
    if (first.end <= second.start && !sameInsertion && !deletedAnchor) {
      result.push(original.slice(0, first.start), first.text, original.slice(first.end, second.start),
        second.text, original.slice(second.end));
    } else {
      const block = text => text && !text.endsWith('\n') ? text + '\n' : text;
      result.push('<<<<<<< Paperops: 添削\n', block(ours), '||||||| Paperops: 編集開始時\n',
        block(original), '=======\n', block(theirs), '>>>>>>> Paperops: 原稿\n');
    }
  }
  return result.join('');
}

// Apply separate ranges so that the cursor stays with the paragraph being edited.
function replacements(before, after) {
  const a = lines(before);
  const b = lines(after);
  const offsets = [0];
  for (const line of a) offsets.push(offsets[offsets.length - 1] + line.length);
  return diffIndices(a, b).map(({ buffer1: [i, n], buffer2: [j, m] }) => {
    const edit = change(a.slice(i, i + n).join(''), b.slice(j, j + m).join(''));
    return { start: offsets[i] + edit.start, end: offsets[i] + edit.end, text: edit.text };
  });
}

module.exports = { hasMarkers, merge, replacements };
