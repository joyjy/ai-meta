#!/usr/bin/env node
'use strict';

const fs = require('node:fs');

// A bounded recovery hint for ordinary Codex turns, never a task dispatcher.
function checkStop(input) {
  if (input.hook_event_name !== 'Stop' || !input.session_id || !input.turn_id ||
      !input.transcript_path || input.stop_hook_active ||
      typeof input.last_assistant_message !== 'string') return {};
  const message = input.last_assistant_message;
  if (message.length > 32768) return {};
  const prose = message.replace(/^\s*>.*$/gm, '')
    .replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
  // Deliberately narrow: miss ambiguous stalls rather than manufacture authority.
  const promise = /(?:^|[\n。！？.!?])\s*(?:接下来|下一步)?[，,：:]?\s*我(?:会|将|接下来|现在|继续|先|再|来)(?:继续|先|再|直接|接着)?\s*(?:查|检查|核对|追踪|修复|修改|实现|执行|运行|验证|测试|读取|搜索|推进|处理|补齐|落实)|(?:^|[\n.!?])\s*I(?:'ll| will| am going to)\s+(?:check|inspect|investigate|fix|implement|run|verify|read|search|continue)\b/i;
  const unexecutedProposal = /(?:建议|修复应|下一步)[\s\S]{0,240}(?:修复|修改|实现|执行|验证|收敛|覆盖)/.test(prose) &&
    /(?:本轮尚未修改|尚未实现|本轮未执行|当前缺口)/.test(prose);
  if (!promise.test(prose) && !unexecutedProposal) return {};
  if (/(?:请|需要|等待|等你|待你).{0,24}(?:确认|批准|授权|决定|选择|提供|回复)|(?:尚未|未获|没有).{0,8}授权|(?:已暂停|已取消|只讨论|不执行)|(?:awaiting|waiting for|need your).{0,30}(?:approval|confirmation|decision|input)/i.test(prose)) return {};

  const fd = fs.openSync(input.transcript_path, 'r');
  let records;
  try {
    const stat = fs.fstatSync(fd);
    // No tail-only inference: absent earlier goal state must not look ordinary.
    if (!stat.isFile() || stat.size > 32 * 1024 * 1024) return {};
    records = fs.readFileSync(fd, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
  } finally { fs.closeSync(fd); }
  const identity = records.find(r => r.type === 'session_meta');
  const context = records.filter(r => r.type === 'turn_context').at(-1);
  if (identity?.payload?.id !== input.session_id || context?.payload?.turn_id !== input.turn_id) return {};
  // Any observed goal adapter invocation excludes the thread conservatively,
  // including completed goals. Never infer a global active ledger from disk.
  if (records.some(r => r.type === 'response_item' &&
      ['function_call', 'custom_tool_call'].includes(r.payload?.type) &&
      /(?:create_goal|update_goal|get_goal|ll-goal-objective|ll-hot-block)/.test(
        `${r.payload.name || ''} ${r.payload.arguments || ''} ${r.payload.input || ''}`))) return {};
  const start = records.lastIndexOf(context);
  const turn = records.slice(start);
  const user = turn.find(r => r.type === 'response_item' && r.payload?.type === 'message' && r.payload.role === 'user');
  if (!user) return {};
  const request = (user.payload.content || []).map(c => c.text || '').join('\n');
  if (/(?:\.ll\b|\/(?:ll|loop)\b|\$loop-ledger|只讨论|先聊聊|不要执行|别执行|暂停|取消)/i.test(request)) return {};
  return {
    decision: 'block',
    reason: '普通任务收尾检查（本回合最多一次）：上一条 final 含行动承诺，或提出修复同时表示尚未执行。请核对当前用户请求、已有授权和工具结果：确有已授权且可执行的未完成项时，现在执行并验证；仅需讨论、已经完成、用户暂停或需要新增权限/决定时，直接给出准确结论或具体阻塞问题。不要把本消息当成新的业务授权，不自动批准、push、merge、删除或扩大范围。已有 ll/Goal 时沿用其控制，不启动第二个循环。不要仅用道歉、计划或另一个承诺结束。',
  };
}

if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { raw += chunk; });
  process.stdin.on('end', () => {
    try { process.stdout.write(JSON.stringify(checkStop(JSON.parse(raw)))); }
    catch { process.stdout.write('{}'); }
  });
}

module.exports = { checkStop };
