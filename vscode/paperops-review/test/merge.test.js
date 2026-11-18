'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { merge, hasMarkers, replacements } = require('../merge');

const cases = [
  ['別段落', 'A\n\nB\n', '%> 出典は？\nA\n\nB\n', 'A\n\nB2\n', '%> 出典は？\nA\n\nB2\n'],
  ['コメントのすぐ下の段落', '元の本文。\n', '%> 根拠は？\n元の本文。\n', '改訂本文。\n', '%> 根拠は？\n改訂本文。\n'],
  ['行末のコメント', '月面で測った。\n', '月面で測った。 %> 単位は？\n', '極域で測った。\n', '極域で測った。 %> 単位は？\n'],
  ['同じ修正の重複', 'A\nB\nC', 'X\nB\nC', 'X\nB\nZ', 'X\nB\nZ'],
  ['末尾改行と絵文字', '月🌙\n\nA', '月🌙\n\nA\n', '地球🌍\n\nA', '地球🌍\n\nA\n']
];
for (const [name, base, local, incoming, expected] of cases) {
  test(name, () => {
    assert.equal(merge(base, local, incoming), expected);
    assert.equal(merge(base, incoming, local), expected);
  });
}
test('競合の外は統合し、両案と祖先を競合箇所に残す', () => {
  const text = merge('A\n\n値 1\n\nZ\n', 'B\n\n値 2\n\nZ\n', 'A\n\n値 3\n\nY\n');
  assert.ok(hasMarkers(text));
  assert.match(text, /^B\n\n<<<<<<</);
  assert.match(text, /値 2\n\|{7} Paperops: 編集開始時\n値 1\n=======\n値 3\n/);
  assert.ok(text.endsWith('\n\nY\n'));
});
test('同じ位置で違う挿入と、対象の削除は確認する', () => {
  assert.ok(hasMarkers(merge('', 'A', 'B')));
  assert.ok(hasMarkers(merge('本文\n', '%> 質問\n本文\n', '')));
});
test('エディターに適用する範囲は UTF-16 と CRLF を維持する', () => {
  const before = 'A🌙\r\n中央\r\nB\r\n';
  const after = 'X🌙\r\n中央\r\nY\r\n';
  let text = before;
  const edits = replacements(before, after);
  assert.equal(edits.length, 2);
  for (const {start, end, text: replacement} of edits.reverse()) {
    text = text.slice(0, start) + replacement + text.slice(end);
  }
  assert.equal(text, after);
});
