#!/usr/bin/env node
// route-context - UserPromptSubmit adapter for Codex/Claude-style plugin hooks.

const { execFileSync } = require('child_process');
const path = require('path');

function readStdin(done) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => done(input));
  process.stdin.on('error', () => done(input));
  setTimeout(() => done(input), 1000).unref();
}

function pluginRoot() {
  return process.env.CLAUDE_PLUGIN_ROOT || path.resolve(__dirname, '..');
}

function cwdFromPayload(data) {
  return data.cwd || data.current_working_directory || process.cwd();
}

function hasContext(result) {
  return Boolean(
    (result.projects || []).some(project => project.source === 'prompt') ||
    (result.matches && result.matches.length) ||
    (result.resolved_paths && Object.keys(result.resolved_paths).length) ||
    (result.special_routes && result.special_routes.length) ||
    (result.notes && result.notes.length)
  );
}

function renderContext(result) {
  return [
    '<route-context>',
    'The following facts were resolved deterministically before agent execution.',
    'Treat resolved paths and routes as routing facts. When a special route has execution.required=true, execute that workflow in this turn unless a higher-priority instruction conflicts.',
    JSON.stringify(result, null, 2),
    '</route-context>',
  ].join('\n');
}

function hookOutput(additionalContext) {
  if (!additionalContext) {
    return {};
  }
  return {
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext,
    },
  };
}

function run(rawInput) {
  let data = {};
  try {
    data = JSON.parse(String(rawInput || '').replace(/^\uFEFF/, ''));
  } catch (_error) {
    return {};
  }

  const prompt = data.prompt || '';
  if (!prompt.trim()) {
    return {};
  }

  try {
    const resolver = path.join(pluginRoot(), 'scripts', 'route-context-resolve');
    const output = execFileSync(resolver, [
      '--cwd',
      cwdFromPayload(data),
      '--prompt',
      prompt,
    ], {
      encoding: 'utf8',
      timeout: 3000,
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    const result = JSON.parse(output);
    if (!hasContext(result)) {
      return {};
    }
    return hookOutput(renderContext(result));
  } catch (_error) {
    return {};
  }
}

readStdin(input => {
  process.stdout.write(JSON.stringify(run(input)));
});
