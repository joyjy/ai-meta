import { loadConfig } from "./config.mjs";
import { initialize } from "./init.mjs";
import { runConfigured } from "./run.mjs";

function parseOptions(argv) {
  const options = { selectedFiles: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
    const value = argv[index + 1];
    if (["--config", "--output", "--test-file", "--preset"].includes(option)) {
      if (!value) throw new Error(`${option} requires a value`);
      if (option === "--test-file") options.selectedFiles.push(value);
      else options[option.slice(2).replace("-", "_")] = value;
      index += 1;
    } else {
      throw new Error(`unknown option: ${option}`);
    }
  }
  return options;
}

export function usage() {
  return [
    "Usage: node-test-kit <init|run|coverage|diagnose> [options]",
    "",
    "Options:",
    "  --preset <node-js|node-ts-build>  preset used by init",
    "  --config <path>                   config file (default: node-test.config.mjs)",
    "  --test-file <path>                run one test file; repeatable",
    "  --output <path>                   diagnostic JSON destination",
  ].join("\n");
}

export async function main(argv, { cwd = process.cwd() } = {}) {
  const [command = "run", ...rest] = argv;
  if (["help", "--help", "-h"].includes(command) || rest.includes("--help") || rest.includes("-h")) {
    console.log(usage());
    return 0;
  }
  const options = parseOptions(rest);
  if (command === "init") {
    const destination = initialize({ cwd, preset: options.preset || "node-js" });
    console.log(`created ${destination}`);
    console.log("recommended scripts: test=$HOME/.ai/scripts/node-test-kit run; test:coverage=$HOME/.ai/scripts/node-test-kit diagnose");
    return 0;
  }
  if (!new Set(["run", "coverage", "diagnose"]).has(command)) throw new Error(`unknown command: ${command}`);
  const config = await loadConfig({ cwd, configPath: options.config || "node-test.config.mjs" });
  runConfigured(config, {
    diagnose: command !== "run",
    output: options.output,
    selectedFiles: options.selectedFiles,
  });
  return 0;
}
