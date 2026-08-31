import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";
import {
  aggregateV8Coverage,
  expandFiles,
  initialize,
  listenOnLoopback,
  main,
  normalizeConfig,
  parseCoverageSummary,
  runConfigured,
  runNodeCli,
  withTempDirectory,
} from "../src/index.mjs";

function temp(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function remove(directory) {
  fs.rmSync(directory, { recursive: true, force: true });
}

test("node-js config expands files and keeps suites inside the project", () => {
  const root = temp("node-test-kit-files-");
  try {
    fs.mkdirSync(path.join(root, "test", "nested"), { recursive: true });
    fs.writeFileSync(path.join(root, "test", "a.test.mjs"), "");
    fs.writeFileSync(path.join(root, "test", "nested", "b.test.mjs"), "");
    assert.deepEqual(
      expandFiles(root, ["test/**/*.test.mjs"]).map((file) => path.relative(root, file)),
      [path.join("test", "a.test.mjs"), path.join("test", "nested", "b.test.mjs")],
    );
    const config = normalizeConfig({ preset: "node-js", files: ["test/*.test.mjs"] }, root);
    assert.equal(config.suites[0].cwd, fs.realpathSync(root));
    assert.throws(() => normalizeConfig({ suites: [{ cwd: "..", files: [] }] }, root), /inside project root/);
  } finally {
    remove(root);
  }
});

test("node-ts-build requires a build and overwrites stale dist before testing", () => {
  const root = temp("node-test-kit-build-");
  try {
    fs.mkdirSync(path.join(root, "source"));
    fs.mkdirSync(path.join(root, "dist", "test"), { recursive: true });
    fs.writeFileSync(path.join(root, "source", "result.txt"), "pass");
    fs.writeFileSync(path.join(root, "dist", "test", "sample.test.mjs"), "throw new Error('stale dist');\n");
    fs.writeFileSync(path.join(root, "build.mjs"), [
      "import fs from 'node:fs';",
      "const result = fs.readFileSync('source/result.txt', 'utf8').trim();",
      "fs.mkdirSync('dist/test', { recursive: true });",
      "fs.writeFileSync('dist/test/sample.test.mjs', `import test from 'node:test'; import assert from 'node:assert/strict'; test('fresh', () => assert.equal('${result}', 'pass'));\\n`);",
    ].join("\n"));
    assert.throws(() => normalizeConfig({ preset: "node-ts-build" }, root), /requires a non-empty build/);
    const config = normalizeConfig({
      preset: "node-ts-build",
      build: "node build.mjs",
      files: ["dist/test/*.test.mjs"],
    }, root);
    const report = runConfigured(config, { quiet: true });
    assert.equal(report.test.passed, 1, JSON.stringify(report));
    assert.doesNotMatch(fs.readFileSync(path.join(root, "dist", "test", "sample.test.mjs"), "utf8"), /stale dist/);
  } finally {
    remove(root);
  }
});

test("diagnose collects V8 coverage and configured entrypoint process metrics", () => {
  const root = temp("node-test-kit-diagnose-");
  try {
    fs.mkdirSync(path.join(root, "src"));
    fs.mkdirSync(path.join(root, "test"));
    fs.writeFileSync(path.join(root, "src", "entry.mjs"), "export function answer() { return 42; }\n");
    fs.writeFileSync(path.join(root, "test", "entry.test.mjs"), [
      "import test from 'node:test';",
      "import assert from 'node:assert/strict';",
      "import { answer } from '../src/entry.mjs';",
      "test('answer', () => assert.equal(answer(), 42));",
    ].join("\n"));
    const config = normalizeConfig({
      preset: "node-js",
      files: ["test/*.test.mjs"],
      coverage: { include: ["src/**"] },
      diagnostics: { sourceRoots: ["src"], entrypoints: { cli_processes: "src/entry.mjs" } },
      report: { output: "tmp/report.json" },
    }, root);
    const report = runConfigured(config, { diagnose: true, quiet: true });
    assert.equal(report.test.passed, 1);
    assert.equal(report.metrics.cli_processes, 1, JSON.stringify(report.metrics));
    assert.ok(report.metrics.function_count >= 1);
    assert.equal(fs.existsSync(path.join(root, "tmp", "report.json")), true);
  } finally {
    remove(root);
  }
});

test("coverage aggregation preserves legacy summary and generic entrypoints", () => {
  const root = temp("node-test-kit-coverage-");
  try {
    const coverage = path.join(root, "coverage");
    const src = path.join(root, "src");
    fs.mkdirSync(coverage);
    fs.mkdirSync(src);
    const entry = path.join(src, "entry.mjs");
    fs.writeFileSync(entry, "export function run() { return 1; }\n");
    fs.writeFileSync(path.join(coverage, "coverage-123-1.json"), JSON.stringify({
      result: [{
        url: pathToFileURL(entry).href,
        functions: [{ functionName: "run", ranges: [{ startOffset: 7, endOffset: 34, count: 2 }] }],
      }],
    }));
    const result = aggregateV8Coverage(coverage, {
      root,
      sourceRoots: ["src"],
      entrypoints: { entry_processes: [path.join("src", "entry.mjs")] },
    });
    assert.equal(result.entry_processes, 1);
    assert.equal(result.total_hits, 2);
    assert.deepEqual(parseCoverageSummary("# all files | 80 | 70 | 60 |\n"), { line: 80, branch: 70, function: 60 });
  } finally {
    remove(root);
  }
});

test("init creates one preset config and refuses overwrite", () => {
  const root = temp("node-test-kit-init-");
  try {
    const destination = initialize({ cwd: root, preset: "node-ts-build" });
    assert.match(fs.readFileSync(destination, "utf8"), /node-ts-build/);
    assert.throws(() => initialize({ cwd: root }), /refusing to overwrite/);
  } finally {
    remove(root);
  }
});

test("CLI help is available without a project config", async () => {
  const lines = [];
  const original = console.log;
  console.log = (line) => lines.push(line);
  try {
    assert.equal(await main(["--help"]), 0);
    assert.match(lines.join("\n"), /node-test-kit <init\|run\|coverage\|diagnose>/);
  } finally {
    console.log = original;
  }
});

test("shared fixtures clean temp state, run Node CLIs, and own loopback lifecycle", async () => {
  let directory;
  const result = await withTempDirectory("node-test-kit-fixture-", async (root) => {
    directory = root;
    const cli = path.join(root, "cli.mjs");
    fs.writeFileSync(cli, "console.log(JSON.stringify({ args: process.argv.slice(2) }));\n");
    return runNodeCli(cli, ["one", "two"]);
  });
  assert.equal(fs.existsSync(directory), false);
  assert.deepEqual(JSON.parse(result.stdout), { args: ["one", "two"] });

  const server = http.createServer((request, response) => response.end("ok"));
  const loopback = await listenOnLoopback(server);
  const body = await fetch(`http://${loopback.host}:${loopback.port}`).then((response) => response.text());
  assert.equal(body, "ok");
  await loopback.close();
});
