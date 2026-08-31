import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { aggregateV8Coverage, parseCoverageSummary } from "./coverage.mjs";
import { selectTestFiles } from "./files.mjs";
import { createRunWorkspace } from "./fixtures.mjs";

function testSummary(output) {
  const value = (name) => {
    const match = String(output).match(new RegExp(`^# ${name} (\\d+)$`, "m"));
    return match ? Number(match[1]) : null;
  };
  const duration = String(output).match(/^# duration_ms ([\d.]+)$/m);
  return { tests: value("tests"), passed: value("pass"), failed: value("fail"), duration_ms: duration ? Number(duration[1]) : null };
}

function runBuild(config) {
  if (!config.build) return null;
  const result = spawnSync(config.build, {
    cwd: config.root,
    shell: true,
    encoding: "utf8",
    env: process.env,
    maxBuffer: 64 * 1024 * 1024,
  });
  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`build failed with status ${result.status}: ${config.build}`);
  return { command: config.build, status: result.status };
}

function workspace(config, diagnose) {
  return { ...createRunWorkspace(), temporaryHome: diagnose ? config.temporaryHome.diagnose : config.temporaryHome.run };
}

function testEnvironment(work, diagnose) {
  const environment = { ...process.env };
  delete environment.NODE_TEST_CONTEXT;
  environment.NODE_TEST_KIT_ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
  if (work.temporaryHome) environment.HOME = work.home;
  if (diagnose) environment.NODE_V8_COVERAGE = work.coverage;
  return environment;
}

function suiteArgs(suite, diagnose) {
  const args = ["--test", "--test-reporter=tap"];
  if (diagnose) {
    args.push("--experimental-test-coverage");
    for (const include of suite.coverageInclude) args.push(`--test-coverage-include=${include}`);
  }
  return [...args, ...suite.selectedFiles];
}

function printFailure(result) {
  const lines = `${result.stdout || ""}\n${result.stderr || ""}`.trim().split("\n");
  const first = lines.findIndex((line) => /^not ok\b/.test(line));
  return (first === -1 ? lines.slice(-80) : lines.slice(first, first + 120)).join("\n");
}

export function printRanking(title, items) {
  console.log(`\n${title}`);
  for (const item of items.slice(0, 10)) {
    console.log(`${String(item.process_count).padStart(3)} proc  ${String(item.total_hits).padStart(7)} hits  ${String(item.max_hits_per_process).padStart(7)} max  ${item.file}:${item.line} ${item.function}`);
  }
}

export function runConfigured(config, { diagnose = false, output, selectedFiles = [], quiet = false } = {}) {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  if (diagnose && (!Number.isInteger(nodeMajor) || nodeMajor < 20)) {
    throw new Error("node-test-kit coverage requires Node.js 20+ with --experimental-test-coverage");
  }
  if (config.preset === "node-ts-build") runBuild(config);
  const work = workspace(config, diagnose);
  try {
    const suites = [];
    for (const suite of selectTestFiles(config, selectedFiles)) {
      if (suite.selectedFiles.length === 0) throw new Error(`suite has no matching test files: ${suite.name}`);
      const result = spawnSync(process.execPath, suiteArgs(suite, diagnose), {
        cwd: suite.cwd,
        encoding: "utf8",
        env: testEnvironment(work, diagnose),
        maxBuffer: 64 * 1024 * 1024,
      });
      if (!quiet) {
        console.log(`\n[node-test-kit] suite=${suite.name}`);
        process.stdout.write(result.stdout || "");
        process.stderr.write(result.stderr || "");
      }
      if (result.error) throw result.error;
      if (result.status !== 0) throw new Error(`test suite ${suite.name} failed with status ${result.status}\n${printFailure(result)}`);
      suites.push({
        name: suite.name,
        cwd: path.relative(config.root, suite.cwd) || ".",
        files: suite.selectedFiles.map((file) => path.relative(config.root, file)),
        status: result.status,
        ...testSummary(result.stdout),
        ...(diagnose ? { coverage: parseCoverageSummary(result.stdout) } : {}),
      });
    }
    const report = {
      schema_version: config.reportSchema,
      generated_at: new Date().toISOString(),
      preset: config.preset,
      isolation: { temporary_home: work.temporaryHome, temporary_v8_coverage: diagnose },
      test: {
        status: 0,
        tests: suites.reduce((sum, suite) => sum + (suite.tests || 0), 0),
        passed: suites.reduce((sum, suite) => sum + (suite.passed || 0), 0),
        failed: suites.reduce((sum, suite) => sum + (suite.failed || 0), 0),
        files: suites.flatMap((suite) => suite.files),
        suites,
      },
      ...(diagnose ? { metrics: aggregateV8Coverage(work.coverage, config) } : {}),
    };
    if (diagnose && suites.length === 1) report.metrics.coverage = suites[0].coverage;
    if (diagnose) {
      const destination = output ? path.resolve(config.root, output) : config.defaultOutput;
      fs.mkdirSync(path.dirname(destination), { recursive: true });
      fs.writeFileSync(destination, `${JSON.stringify(report, null, 2)}\n`);
      if (!quiet) {
        console.log(`node-test-kit diagnose PASS tests=${report.test.passed}/${report.test.tests} processes=${report.metrics.independent_processes}`);
        for (const metric of Object.keys(config.entrypoints)) console.log(`${metric}=${report.metrics[metric]}`);
        console.log(`report=${destination}`);
        printRanking("Repeated bootstrap (high process count)", report.metrics.repeated_bootstrap);
        printRanking("Data loops (high hits, low process count)", report.metrics.high_hit_low_process);
      }
    }
    return report;
  } finally {
    fs.rmSync(work.root, { recursive: true, force: true });
  }
}
