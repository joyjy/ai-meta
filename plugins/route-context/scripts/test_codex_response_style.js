'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

test('Codex hook injects style only for the exact active model', () => {
  const run = input => {
    const result = spawnSync(process.execPath, [path.join(__dirname, '../hooks/codex-response-style.js')], {
      input: JSON.stringify(input), encoding: 'utf8',
    });
    assert.equal(result.status, 0, result.stderr);
    return JSON.parse(result.stdout);
  };
  const active = { hook_event_name: 'UserPromptSubmit', model: 'gpt-6.1-sol' };
  const output = run(active).hookSpecificOutput;
  assert.equal(output.hookEventName, 'UserPromptSubmit');
  assert.ok(output.additionalContext.startsWith('<response-style>'));
  assert.ok(output.additionalContext.includes('必需的风险、授权限制和证据缺口照常交代'));
  for (const model of ['gpt-6.1-terra', 'gpt-6-sol', 'gpt-6.1-sol-preview', undefined]) {
    assert.deepEqual(run({ ...active, model }), {});
  }
  assert.deepEqual(run({ ...active, hook_event_name: 'Stop' }), {});
});
