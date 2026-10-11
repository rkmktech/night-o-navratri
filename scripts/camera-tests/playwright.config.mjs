import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
// Replit provides Chromium. Elsewhere use Playwright's installed browser.
const executablePath = process.env.CAMERA_TEST_CHROMIUM
  || (existsSync("/repl/tools/bin/chromium") ? "/repl/tools/bin/chromium" : undefined);

export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.mjs",
  fullyParallel: true,
  workers: 2,
  timeout: 15_000,
  expect: { timeout: 5_000 },
  reporter: "list",
  outputDir: `${root}/generated-artifacts/camera-tests`,
  use: {
    baseURL: "http://127.0.0.1:18765",
    browserName: "chromium",
    launchOptions: { executablePath, args: ["--no-sandbox"] },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "node scripts/camera-tests/server.mjs",
    cwd: root,
    url: "http://127.0.0.1:18765",
    reuseExistingServer: false,
  },
});
