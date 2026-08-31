import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function numberFrom(text) {
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

export function parseCoverageSummary(output) {
  const line = String(output).split("\n").find((item) => /^#?\s*all files\s*\|/.test(item));
  if (!line) throw new Error("node:test coverage summary did not contain an all files row");
  const columns = line.replace(/^#\s*/, "").split("|").map((item) => item.trim());
  if (columns.length < 4) throw new Error(`invalid node:test coverage row: ${line}`);
  return { line: numberFrom(columns[1]), branch: numberFrom(columns[2]), function: numberFrom(columns[3]) };
}

function processId(file) {
  const match = path.basename(file).match(/^coverage-(\d+)-/);
  return match ? Number(match[1]) : null;
}

function sourceLine(file, offset, cache) {
  if (!cache.has(file)) cache.set(file, fs.readFileSync(file, "utf8"));
  return cache.get(file).slice(0, offset).split("\n").length;
}

function inSourceRoots(relative, roots) {
  return roots.some((root) => root === "." || relative === root || relative.startsWith(`${root}${path.sep}`));
}

export function aggregateV8Coverage(coverageDir, { root, sourceRoots = ["."], entrypoints = {} }) {
  const processFunctions = new Map();
  const entrypointProcesses = Object.fromEntries(Object.keys(entrypoints).map((metric) => [metric, new Set()]));
  const sourceCache = new Map();
  const files = fs.readdirSync(coverageDir).filter((name) => name.endsWith(".json")).sort();

  for (const name of files) {
    const pid = processId(name);
    if (!pid) continue;
    const payload = JSON.parse(fs.readFileSync(path.join(coverageDir, name), "utf8"));
    const perProcess = processFunctions.get(pid) || new Map();
    for (const script of payload.result || []) {
      if (!String(script.url || "").startsWith("file:")) continue;
      const file = fileURLToPath(script.url);
      if (file !== root && !file.startsWith(`${root}${path.sep}`)) continue;
      const relative = path.relative(root, file);
      if (!inSourceRoots(relative, sourceRoots)) continue;
      let scriptHit = false;
      for (const fn of script.functions || []) {
        const range = fn.ranges?.[0];
        const count = Number(range?.count || 0);
        if (count <= 0) continue;
        scriptHit = true;
        const key = `${file}\u0000${fn.functionName || "<anonymous>"}\u0000${range.startOffset}\u0000${range.endOffset}`;
        const current = perProcess.get(key);
        if (!current || count > current.count) {
          perProcess.set(key, {
            file: relative,
            function: fn.functionName || "<anonymous>",
            line: sourceLine(file, range.startOffset, sourceCache),
            start_offset: range.startOffset,
            end_offset: range.endOffset,
            count,
          });
        }
      }
      if (scriptHit) {
        for (const [metric, paths] of Object.entries(entrypoints)) {
          if (paths.includes(relative)) entrypointProcesses[metric].add(pid);
        }
      }
    }
    processFunctions.set(pid, perProcess);
  }

  const aggregate = new Map();
  for (const [pid, functions] of processFunctions.entries()) {
    for (const [key, fn] of functions.entries()) {
      const item = aggregate.get(key) || {
        file: fn.file,
        function: fn.function,
        line: fn.line,
        start_offset: fn.start_offset,
        end_offset: fn.end_offset,
        total_hits: 0,
        process_count: 0,
        max_hits_per_process: 0,
        processes: [],
      };
      item.total_hits += fn.count;
      item.process_count += 1;
      item.max_hits_per_process = Math.max(item.max_hits_per_process, fn.count);
      item.processes.push(pid);
      aggregate.set(key, item);
    }
  }

  const functions = [...aggregate.values()];
  const byProcesses = [...functions].sort((left, right) => (
    right.process_count - left.process_count || right.total_hits - left.total_hits
    || left.file.localeCompare(right.file) || left.line - right.line
  ));
  const byHits = [...functions].sort((left, right) => (
    right.total_hits - left.total_hits || left.process_count - right.process_count
    || left.file.localeCompare(right.file) || left.line - right.line
  ));
  return {
    total_hits: functions.reduce((sum, item) => sum + item.total_hits, 0),
    independent_processes: processFunctions.size,
    max_hits_single_process: functions.reduce((max, item) => Math.max(max, item.max_hits_per_process), 0),
    function_count: functions.length,
    ...Object.fromEntries(Object.entries(entrypointProcesses).map(([metric, pids]) => [metric, pids.size])),
    repeated_bootstrap: byProcesses.filter((item) => item.process_count >= 3).slice(0, 30),
    high_hit_low_process: byHits.filter((item) => item.process_count <= 2).slice(0, 30),
  };
}
