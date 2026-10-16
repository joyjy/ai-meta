'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

test('ordinary promise triggers one bounded recovery, while completion and human gates stop', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'amt-continuation-'));
  try {
    const transcript = path.join(dir, 'rollout.jsonl');
    const records = [
      { type: 'session_meta', payload: { id: 's' } },
      { type: 'turn_context', payload: { turn_id: 't' } },
      { type: 'response_item', payload: { type: 'message', role: 'user', content: [{ text: '修复测试并验证。' }] } },
    ];
    const write = extra => fs.writeFileSync(transcript, [...records, ...extra].map(JSON.stringify).join('\n'));
    write([]);
    const run = (message, extra = {}) => {
      const result = spawnSync(process.execPath, [path.join(__dirname, '../hooks/task-continuation-stop.js')], {
        input: JSON.stringify({ hook_event_name: 'Stop', session_id: 's', turn_id: 't', transcript_path: transcript,
          last_assistant_message: message, ...extra }), encoding: 'utf8',
      });
      assert.equal(result.status, 0, result.stderr);
      return JSON.parse(result.stdout);
    };
    const promise = '我会追踪原实现，修复测试并验证。';
    assert.equal(run(promise).decision, 'block');
    assert.equal(run('建议直接收敛为：执行报错就记为 failed。\n本轮尚未修改这部分代码。').decision, 'block');
    assert.deepEqual(run(promise, { stop_hook_active: true }), {});
    assert.deepEqual(run('已修复，测试通过。'), {});
    assert.deepEqual(run('我会修复，但需要你确认修改范围。'), {});
    assert.deepEqual(run('示例：\n> 我会修复测试。'), {});
    assert.deepEqual(run(promise, { session_id: 'other' }), {});
    assert.deepEqual(run(promise, { turn_id: 'old' }), {});
    write([{ type: 'response_item', payload: { type: 'function_call', name: 'functions.exec', arguments: 'await tools.create_goal({objective:"x"})' } }]);
    assert.deepEqual(run(promise), {});
    records[2].payload.content[0].text = '先聊聊，不要执行';
    write([]);
    assert.deepEqual(run(promise), {});
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
