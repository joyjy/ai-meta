import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const CONFIG_FILE = "node-test.config.mjs";
export const PRESETS = new Set(["node-js", "node-ts-build"]);

function stringArray(value, field, fallback = []) {
  const result = value === undefined ? fallback : value;
  if (!Array.isArray(result) || result.some((item) => typeof item !== "string" || !item)) {
    throw new Error(`${field} must be an array of non-empty strings`);
  }
  return [...result];
}

function inside(root, target, field) {
  const resolved = path.resolve(root, target);
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
    throw new Error(`${field} must stay inside project root: ${target}`);
  }
  return resolved;
}

function normalizeSuites(config, root) {
  const raw = config.suites || [{
    name: "default",
    cwd: ".",
    files: config.files || ["test/*.test.mjs"],
  }];
  if (!Array.isArray(raw) || raw.length === 0) throw new Error("suites must be a non-empty array");
  return raw.map((suite, index) => {
    if (!suite || typeof suite !== "object") throw new Error(`suites[${index}] must be an object`);
    const name = suite.name || `suite-${index + 1}`;
    if (typeof name !== "string") throw new Error(`suites[${index}].name must be a string`);
    const cwd = inside(root, suite.cwd || ".", `suites[${index}].cwd`);
    return {
      name,
      cwd,
      files: stringArray(suite.files, `suites[${index}].files`),
      coverageInclude: stringArray(
        suite.coverage?.include,
        `suites[${index}].coverage.include`,
        stringArray(config.coverage?.include, "coverage.include"),
      ),
    };
  });
}

function normalizeEntrypoints(value, root) {
  if (value === undefined) return {};
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("diagnostics.entrypoints must be an object");
  }
  return Object.fromEntries(Object.entries(value).map(([metric, entrypoint]) => {
    if (!/^[a-z][a-z0-9_]*$/.test(metric)) throw new Error(`invalid entrypoint metric: ${metric}`);
    const values = typeof entrypoint === "string" ? [entrypoint] : entrypoint;
    const paths = stringArray(values, `diagnostics.entrypoints.${metric}`)
      .map((item) => path.relative(root, inside(root, item, `diagnostics.entrypoints.${metric}`)));
    return [metric, paths];
  }));
}

export function defineNodeTestConfig(config) {
  return config;
}

export function normalizeConfig(config, root = process.cwd()) {
  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new Error("node-test config must export an object");
  }
  const projectRoot = fs.realpathSync(path.resolve(root));
  const preset = config.preset || "node-js";
  if (!PRESETS.has(preset)) throw new Error(`unsupported preset: ${preset}`);
  if (preset === "node-ts-build" && (typeof config.build !== "string" || !config.build.trim())) {
    throw new Error("node-ts-build requires a non-empty build command");
  }
  const sourceRoots = stringArray(config.diagnostics?.sourceRoots, "diagnostics.sourceRoots", ["."])
    .map((item) => path.relative(projectRoot, inside(projectRoot, item, "diagnostics.sourceRoots")) || ".");
  const temporaryHome = config.environment?.temporaryHome;
  if (temporaryHome !== undefined && typeof temporaryHome !== "boolean"
      && (!temporaryHome || typeof temporaryHome !== "object" || Array.isArray(temporaryHome))) {
    throw new Error("environment.temporaryHome must be a boolean or { run, diagnose }");
  }
  return {
    preset,
    root: projectRoot,
    build: config.build?.trim() || null,
    suites: normalizeSuites(config, projectRoot),
    temporaryHome: {
      run: temporaryHome === true || temporaryHome?.run === true,
      diagnose: temporaryHome === true || temporaryHome?.diagnose === true,
    },
    sourceRoots,
    entrypoints: normalizeEntrypoints(config.diagnostics?.entrypoints, projectRoot),
    reportSchema: config.report?.schema || "node-test-kit.report.v1",
    defaultOutput: path.resolve(projectRoot, config.report?.output || "tmp/node-test-report.json"),
  };
}

export async function loadConfig({ cwd = process.cwd(), configPath = CONFIG_FILE } = {}) {
  const root = path.resolve(cwd);
  const absolute = inside(root, configPath, "config path");
  if (!fs.existsSync(absolute)) throw new Error(`node-test config does not exist: ${absolute}`);
  const url = `${pathToFileURL(absolute).href}?mtime=${fs.statSync(absolute).mtimeMs}`;
  const module = await import(url);
  return normalizeConfig(module.default, root);
}
