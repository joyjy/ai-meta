'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const { sourceTexts, missingMrLinks } = require('./mr-links.js');
const { checkStop } = require('../hooks/context-stop.js');

const items = [
  ['arch-hub', '254'], ['auth-api', '1602'], ['common', '201'], ['app-service', '327'],
  ['mgmt-api', '919'], ['mgmt-ui', '521'], ['node-sdk', '90'], ['integration', '1927'],
];
const url = (name, iid) => `https://gitlab.example.com/team/iam-${name}/-/merge_requests/${iid}`;
const source = items.map(([name, iid]) => `[team/iam-${name}!${iid}](${url(name, iid)})`).join('\n');

test('the eight-MR incident detects bare table and recommendation references from linked source', () => {
  const message = items.map(([name, iid]) => `| 环节 | ${name} !${iid} |`).join('\n') + '\n建议 !254 → !1602 + !201';
  const missing = missingMrLinks(message, [source]);
  assert.equal(missing.length, 8);
  assert.equal(missing[0].url, url('arch-hub', '254'));
  assert.equal(missing.at(-1).url, url('integration', '1927'));
  assert.deepEqual(missingMrLinks(source, [source]), []);
});

test('one link per MR covers repeated table and prose mentions throughout the response', () => {
  const first = url('endpoint', '19');
  const second = url('endpoint', '20');
  const sources = [first, second];
  const message = `| [endpoint !19](${first}) | 待 approve |\n| [endpoint !20](${second}) | 叠在 !19 上 |\n建议先查 !19，再看 !20；endpoint !20 已完成基础。`;
  assert.deepEqual(missingMrLinks(message, sources), []);
  assert.deepEqual(missingMrLinks(`先查 !19，再看 !20。\n${message}`, sources), []);
  assert.deepEqual(missingMrLinks(`[endpoint !19](${first})，建议先看 !19。\n随后处理 endpoint !20，再回看 !20。`, sources), [{ label: 'endpoint !20', url: second }]);
  assert.deepEqual(missingMrLinks(`!19、endpoint !19；!20、endpoint !20\n[!19](${first})`, sources), [{ label: '!20', url: second }]);
  assert.deepEqual(missingMrLinks(`!19\n[来源][mr]\n[mr]: ${first}`, sources), []);
  // A code example or a different repository's same IID is not this MR's link.
  for (const link of [`\`${first}\``, `\`\`\`text\n${first}\n\`\`\``, `[other !19](${url('other', '19')})`]) {
    assert.deepEqual(missingMrLinks(`endpoint !19\n${link}`, sources), [{ label: 'endpoint !19', url: first }]);
  }
});

test('links, code, unknown repositories, ordinary numbers and ambiguous IDs do not trigger', () => {
  const other = 'https://other.example.com/team/iam-arch-hub/-/merge_requests/254';
  for (const [message, sources] of [
    [source, [source]],
    ['正文 254、版本 1602，unknown!254 和 !9999', [source]],
    ['`arch-hub !254`\n```text\n!1602\n```', [source]],
    ['[arch-hub !254][mr]\n[mr]: ' + url('arch-hub', '254'), [source]],
    ['!254', [source, other]],
    ['arch-hub!254', [source, other]],
    ['!254', ['https://user:secret@gitlab.example.com/team/arch-hub/-/merge_requests/254']],
  ]) assert.deepEqual(missingMrLinks(message, sources), [], message);
});

test('source evidence accepts only observed Codex user/tool text, not assistant claims or arbitrary fields', () => {
  const tool = { type: 'response_item', payload: { type: 'custom_tool_call_output', output: [{ type: 'text', text: source }] } };
  assert.equal(missingMrLinks('!254', sourceTexts(tool)).length, 1);
  const user = { type: 'response_item', payload: { type: 'message', role: 'user', content: [{ type: 'input_text', text: source }] } };
  assert.deepEqual(sourceTexts(user), [source]);
  assert.deepEqual(sourceTexts({ ...user, payload: { ...user.payload, role: 'assistant' } }), []);
  assert.deepEqual(sourceTexts({ ...tool, type: 'event_msg' }), []);
  assert.deepEqual(sourceTexts({ ...tool, payload: { type: 'function_call', arguments: source } }), []);
});

test('real Stop adapter requests one correction, then warns without another continuation', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'context-stop-test-'));
  try {
    const transcript = path.join(root, 'rollout.jsonl');
    fs.writeFileSync(transcript, JSON.stringify({ type: 'response_item', payload: { type: 'function_call_output', output: source } }) + '\n');
    const input = { hook_event_name: 'Stop', session_id: 'session', turn_id: 'turn',
      transcript_path: transcript, stop_hook_active: false, last_assistant_message: '建议先看 arch-hub !254。' };
    const result = spawnSync(process.execPath, [path.join(__dirname, '../hooks/context-stop.js')], { input: JSON.stringify(input), encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const decision = JSON.parse(result.stdout);
    assert.equal(decision.decision, 'block');
    assert.ok(decision.reason.includes(`[arch-hub !254](${url('arch-hub', '254')})`));
    assert.deepEqual(checkStop({ ...input, last_assistant_message: `[arch-hub !254](${url('arch-hub', '254')})` }), {});
    assert.deepEqual(checkStop({ ...input, last_assistant_message: `[arch-hub !254](${url('arch-hub', '254')})\n建议先看 !254。` }), {});
    assert.equal(checkStop({ ...input, stop_hook_active: true }).decision, undefined);
    assert.ok(checkStop({ ...input, stop_hook_active: true }).systemMessage);
    assert.deepEqual(checkStop({ ...input, turn_id: null }), {});
    assert.equal(fs.readdirSync(root).length, 1); // no session ledger or transcript rewrites
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('unknown or unreadable transcript format fails open without broadening the read boundary', () => {
  const input = { hook_event_name: 'Stop', turn_id: 'turn', transcript_path: '/nonexistent/context-test.jsonl', last_assistant_message: '!254' };
  const result = spawnSync(process.execPath, [path.join(__dirname, '../hooks/context-stop.js')], { input: JSON.stringify(input), encoding: 'utf8' });
  assert.equal(result.status, 0);
  assert.deepEqual(JSON.parse(result.stdout), {});
});
