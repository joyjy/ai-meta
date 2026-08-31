import fs from "node:fs";
import path from "node:path";

function globRegex(pattern) {
  const normalized = pattern.split(path.sep).join("/").replace(/^\.\//, "");
  let source = "^";
  for (let index = 0; index < normalized.length; index += 1) {
    const char = normalized[index];
    if (char === "*" && normalized[index + 1] === "*") {
      index += 1;
      if (normalized[index + 1] === "/") {
        index += 1;
        source += "(?:.*/)?";
      } else {
        source += ".*";
      }
    } else if (char === "*") {
      source += "[^/]*";
    } else if (char === "?") {
      source += "[^/]";
    } else {
      source += char.replace(/[\\^$+?.()|{}\[\]]/g, "\\$&");
    }
  }
  return new RegExp(`${source}$`);
}

function walk(root, current, output) {
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".git") continue;
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) walk(root, absolute, output);
    else if (entry.isFile()) output.push(path.relative(root, absolute).split(path.sep).join("/"));
  }
}

export function expandFiles(root, patterns) {
  const files = [];
  walk(root, root, files);
  const matchers = patterns.map(globRegex);
  return files
    .filter((file) => matchers.some((matcher) => matcher.test(file)))
    .sort()
    .map((file) => path.join(root, file));
}

export function selectTestFiles(config, selected = []) {
  if (selected.length === 0) {
    return config.suites.map((suite) => ({ ...suite, selectedFiles: expandFiles(suite.cwd, suite.files) }));
  }
  const selectedAbsolute = selected.map((file) => path.resolve(config.root, file));
  for (const file of selectedAbsolute) {
    if (!fs.existsSync(file)) throw new Error(`selected test file does not exist: ${file}`);
    if (file !== config.root && !file.startsWith(`${config.root}${path.sep}`)) {
      throw new Error(`selected test file must stay inside project root: ${file}`);
    }
  }
  const suites = config.suites.map((suite) => ({
    ...suite,
    selectedFiles: selectedAbsolute.filter((file) => file.startsWith(`${suite.cwd}${path.sep}`)),
  })).filter((suite) => suite.selectedFiles.length > 0);
  if (suites.reduce((sum, suite) => sum + suite.selectedFiles.length, 0) !== selectedAbsolute.length) {
    throw new Error("every selected test file must belong to a configured suite");
  }
  return suites;
}
