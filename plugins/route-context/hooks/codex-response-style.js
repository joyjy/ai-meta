#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

// Gate on the active turn's model, never the configured default or transcript.
const STYLED_MODELS = new Set(['gpt-6.1-sol', 'gpt-6-astra', 'gpt-6.1-terra']);

function responseStyle(input) {
  if (input?.hook_event_name !== 'UserPromptSubmit' || !STYLED_MODELS.has(input.model)) return {};
  return {
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext: fs.readFileSync(path.join(__dirname, 'codex-response-style.md'), 'utf8').trim(),
    },
  };
}

if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { raw += chunk; });
  process.stdin.on('end', () => {
    try { process.stdout.write(JSON.stringify(responseStyle(JSON.parse(raw)))); }
    catch (error) {
      process.stderr.write(`codex-response-style: ${error.message}\n`);
      process.exitCode = 1;
    }
  });
}

module.exports = { responseStyle };
