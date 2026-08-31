import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export async function withTempDirectory(prefix, callback) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  try {
    return await callback(directory);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

export function createRunWorkspace({ prefix = "node-test-kit-", temporaryRoot = os.tmpdir() } = {}) {
  const root = fs.mkdtempSync(path.join(temporaryRoot, prefix));
  const home = path.join(root, "home");
  const coverage = path.join(root, "v8-coverage");
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(coverage, { recursive: true });
  return { root, home, coverage };
}

export function runNodeCli(entrypoint, args = [], options = {}) {
  return spawnSync(process.execPath, [entrypoint, ...args], {
    cwd: options.cwd,
    encoding: "utf8",
    env: { ...process.env, ...options.env },
    input: options.input,
    maxBuffer: options.maxBuffer || 16 * 1024 * 1024,
  });
}

export async function listenOnLoopback(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("loopback server did not expose an address");
  return {
    host: "127.0.0.1",
    port: address.port,
    close: () => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())),
  };
}
