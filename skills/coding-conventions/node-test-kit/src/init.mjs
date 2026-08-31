import fs from "node:fs";
import path from "node:path";
import { PRESETS } from "./config.mjs";

function template(preset) {
  if (preset === "node-ts-build") {
    return `export default {\n  preset: "node-ts-build",\n  build: "npm run build",\n  suites: [\n    { name: "default", cwd: ".", files: ["dist/test/*.test.js"] },\n  ],\n  coverage: { include: ["dist/src/**"] },\n  diagnostics: {\n    sourceRoots: ["dist/src"],\n    entrypoints: {},\n  },\n};\n`;
  }
  return `export default {\n  preset: "node-js",\n  suites: [\n    { name: "default", cwd: ".", files: ["test/*.test.mjs"] },\n  ],\n  coverage: { include: ["src/**"] },\n  diagnostics: {\n    sourceRoots: ["src"],\n    entrypoints: {},\n  },\n};\n`;
}

export function initialize({ cwd = process.cwd(), preset = "node-js" } = {}) {
  if (!PRESETS.has(preset)) throw new Error(`unsupported preset: ${preset}`);
  const destination = path.join(path.resolve(cwd), "node-test.config.mjs");
  if (fs.existsSync(destination)) throw new Error(`refusing to overwrite existing config: ${destination}`);
  fs.writeFileSync(destination, template(preset));
  return destination;
}
