import { spawn } from "node:child_process";
import process from "node:process";

const BASE_URL = process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5001";

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function fetchOk(url) {
  try {
    const res = await fetch(url, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForUp({ timeoutMs }) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await fetchOk(`${BASE_URL}/status`)) return true;
    await sleep(250);
  }
  return false;
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { stdio: "inherit", ...opts });
    child.on("exit", (code) => resolve(code ?? 1));
  });
}

async function main() {
  let trayProc = null;
  let startedTray = false;

  const alreadyUp = await fetchOk(`${BASE_URL}/status`);
  if (!alreadyUp) {
    const python = process.env.NEXUS_E2E_PYTHON || "python3";
    const trayScript = new URL("../../nexus_tray.py", import.meta.url).pathname;

    trayProc = spawn(python, [trayScript], {
      stdio: "inherit",
      env: { ...process.env, NEXUS_HEADLESS: "1" },
    });
    startedTray = true;

    const up = await waitForUp({ timeoutMs: 20_000 });
    if (!up) {
      if (trayProc) trayProc.kill("SIGTERM");
      console.error(`E2E blocked: Nexus Commander bridge not reachable at ${BASE_URL}.`);
      console.error("Fix: run `./nexus.sh` (or start the tray) and retry.");
      process.exit(2);
    }
  }

  const env = { ...process.env, PLAYWRIGHT_BROWSERS_PATH: "./.playwright-browsers" };

  // With channel=chrome, we don't need to install bundled chromium every run.
  const exitCode = await run("npx", ["playwright", "test"], { env });

  if (startedTray && trayProc) {
    trayProc.kill("SIGTERM");
  }
  process.exit(exitCode);
}

main().catch((e) => {
  console.error(String(e?.stack || e));
  process.exit(1);
});
