import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import lighthouse from "lighthouse";
import { launch as launchChrome } from "chrome-launcher";
import puppeteer from "puppeteer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..", "..");
const previewPort = 4173;
const targetUrl = `http://localhost:${previewPort}`;
const baselineTbtMs = Number(process.env.BASELINE_TBT_MS || 190);
const chromePath = process.env.CHROME_PATH || puppeteer.executablePath();

async function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const subprocess = spawn(command, args, { stdio: "inherit", ...options });
    subprocess.on("error", reject);
    subprocess.on("exit", (code) => {
      if (code === 0) {
        resolve(null);
      } else {
        reject(new Error(`${command} ${args.join(" ")} exited with code ${code}`));
      }
    });
  });
}

async function waitForServer(url, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url, { method: "GET" });
      if (response.ok) return;
    } catch (error) {
      if (Date.now() - start >= timeoutMs) {
        throw error;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Preview server did not start within ${timeoutMs}ms`);
}

async function runLighthouse() {
  await runCommand("npm", ["run", "build"], { cwd: projectRoot });

  const preview = spawn(
    "npm",
    ["run", "preview", "--", "--host", "0.0.0.0", "--port", String(previewPort)],
    { cwd: projectRoot, stdio: "inherit" },
  );

  try {
    await waitForServer(targetUrl);
    const chrome = await launchChrome({
      chromeFlags: ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"],
      chromePath,
    });

    try {
      const runnerResult = await lighthouse(
        targetUrl,
        {
          port: chrome.port,
          output: "json",
          preset: "desktop",
          onlyCategories: ["performance"],
        },
        {
          extends: "lighthouse:default",
        },
      );

      const tbtMs = Math.round(runnerResult.lhr.audits["total-blocking-time"].numericValue);
      const performanceScore = runnerResult.lhr.categories.performance.score;
      const improvementMs = baselineTbtMs - tbtMs;
      const improvementPct = Number(((improvementMs / baselineTbtMs) * 100).toFixed(2));

      await mkdir(path.join(projectRoot, "benchmark"), { recursive: true });
      const outputPath = path.join(projectRoot, "benchmark", "desktop-lighthouse.json");
      await writeFile(
        outputPath,
        JSON.stringify(
          {
            collectedAt: new Date().toISOString(),
            url: targetUrl,
            performanceScore,
            tbtMs,
            baselineTbtMs,
            improvementMs,
            improvementPct,
          },
          null,
          2,
        ),
      );

      console.log(`\nLighthouse desktop benchmark written to ${outputPath}`);
      console.log(`Total Blocking Time: ${tbtMs} ms`);
      console.log(`Performance score: ${performanceScore}`);
      console.log(`Baseline delta: ${improvementMs} ms (${improvementPct}% improvement)`);
    } finally {
      await chrome.kill();
    }
  } finally {
    preview.kill("SIGTERM");
  }
}

runLighthouse().catch((error) => {
  console.error(error);
  process.exit(1);
});
