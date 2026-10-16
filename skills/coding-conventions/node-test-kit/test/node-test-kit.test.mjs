import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  expandFiles,
  initialize,
  normalizeConfig,
  runConfigured,
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
