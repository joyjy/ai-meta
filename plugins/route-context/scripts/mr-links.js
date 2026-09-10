'use strict';

const fs = require('node:fs');

const TRANSCRIPT_BYTES = 2 * 1024 * 1024;
const RESPONSE_CHARS = 128 * 1024;

// This is deliberately a small Codex transcript adapter, not a generic history
// crawler. Unknown records are ignored; assistant prose is never URL evidence.
function sourceTexts(record) {
  if (record.type !== 'response_item') return [];
  const item = record.payload || {};
  if (['function_call_output', 'custom_tool_call_output'].includes(item.type)) {
    return textValues(item.output);
  }
  if (item.type === 'message' && item.role === 'user') return textValues(item.content);
  return [];
}

function textValues(value) {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(textValues);
  if (value && typeof value === 'object') {
    // Model-facing tool content can be text blocks, not just a plain string.
    if (typeof value.text === 'string') return [value.text];
    if (value.content) return textValues(value.content);
  }
  return [];
}

function transcriptSources(file) {
  const descriptor = fs.openSync(file, 'r');
  try {
    const stat = fs.fstatSync(descriptor);
    if (!stat.isFile()) return [];
    const start = Math.max(0, stat.size - TRANSCRIPT_BYTES);
    const buffer = Buffer.alloc(Math.min(stat.size, TRANSCRIPT_BYTES));
    const bytes = fs.readSync(descriptor, buffer, 0, buffer.length, start);
    const lines = buffer.subarray(0, bytes).toString('utf8').split('\n');
    if (start) lines.shift(); // A partial first record is not evidence.
    return lines.flatMap(line => {
      try { return sourceTexts(JSON.parse(line)); } catch { return []; }
    });
  } finally {
    fs.closeSync(descriptor);
  }
}

function mrUrls(texts) {
  const urls = new Map();
  for (const text of texts) {
    // JSON tool output occasionally escapes URL slashes.
    for (const match of text.replace(/\\\//g, '/').matchAll(/https?:\/\/[^\s<>"'`\\]+/g)) {
      let parsed;
      try { parsed = new URL(match[0].replace(/[).,;，。；]+$/, '')); } catch { continue; }
      if (parsed.username || parsed.password) continue;
      const path = parsed.pathname.match(/^\/([A-Za-z0-9_.~-]+(?:\/[A-Za-z0-9_.~-]+)+)\/-\/merge_requests\/([1-9]\d*)\/?$/);
      if (!path || parsed.search || parsed.hash) continue;
      const url = `${parsed.origin}/${path[1]}/-/merge_requests/${path[2]}`;
      urls.set(url, { url, repo: path[1], iid: path[2] });
    }
  }
  return [...urls.values()];
}

function proseWithoutLinks(text) {
  // Preserve whitespace boundaries so removing markup cannot join references.
  return text
    .replace(/^\s*(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\s*\1\s*$/gm, ' ')
    .replace(/`+[^`\n]*`+/g, ' ')
    .replace(/\[[^\]\n]*\]\((?:[^()\n]|\([^()\n]*\))*\)/g, ' ')
    .replace(/\[([^\]\n]+)\]\[([^\]\n]*)\]/g, (match, label, id) => {
      const key = (id || label).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return new RegExp(`^\\s*\\[${key}\\]:\\s*https?://`, 'mi').test(text) ? ' ' : match;
    })
    .replace(/https?:\/\/[^\s<>]+/g, ' ');
}

function missingMrLinks(message, sources) {
  if (typeof message !== 'string' || message.length > RESPONSE_CHARS) return [];
  const known = mrUrls(sources);
  const missing = new Map();
  const prose = proseWithoutLinks(message);
  for (const match of prose.matchAll(/(?<![\w/!])(?:([A-Za-z0-9_.~-]+(?:\/[A-Za-z0-9_.~-]+)*)\s*)?!([1-9]\d*)\b/g)) {
    const name = match[1] && !/^(?:MR|PR)$/i.test(match[1]) ? match[1] : null;
    const candidates = known.filter(item => {
      if (item.iid !== match[2]) return false;
      if (!name) return true;
      const basename = item.repo.split('/').at(-1);
      return item.repo === name || basename === name || (!name.includes('/') && basename.endsWith(`-${name}`));
    });
    if (candidates.length !== 1) continue;
    const label = match[0].trim();
    missing.set(label, { label, url: candidates[0].url });
  }
  return [...missing.values()].slice(0, 12);
}

module.exports = { sourceTexts, transcriptSources, missingMrLinks };
