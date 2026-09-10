#!/usr/bin/env node
'use strict';

const { transcriptSources, missingMrLinks } = require('../scripts/mr-links.js');

function checkStop(input) {
  // Only the Codex Stop contract is supported. Other clients remain unchanged.
  if (input.hook_event_name !== 'Stop' || !input.turn_id || !input.transcript_path ||
      typeof input.last_assistant_message !== 'string') return {};
  const missing = missingMrLinks(input.last_assistant_message, transcriptSources(input.transcript_path));
  if (!missing.length) return {};
  if (input.stop_hook_active) {
    return { systemMessage: 'Context 套件：补正后仍有 MR 引用未带链接；本轮不再自动续轮。' };
  }
  return {
    decision: 'block',
    reason: [
      'Context 套件检测到回复中的 MR 引用遗漏了会话来源中已有的链接。请只补齐这些引用的 Markdown 链接，并保留其余结论；不要执行命令、修改文件、查询远端或操作 MR。',
      ...missing.map(item => `- [${item.label}](${item.url})`),
      '这是一次输出格式补正，不是新的业务任务。',
    ].join('\n'),
  };
}

if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try { process.stdout.write(JSON.stringify(checkStop(JSON.parse(input)))); }
    catch { process.stdout.write('{}'); } // Missing/changed transcript must not stop the task.
  });
}

module.exports = { checkStop };
