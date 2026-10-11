import { defineConfig } from "@playwright/test";
import cameraConfig from "../camera-tests/playwright.config.mjs";

// Separate discovery, server, output and command: never part of offline tests.
export default defineConfig({
  ...cameraConfig,
  testDir: ".",
  testMatch: "compatibility.spec.mjs",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  outputDir: cameraConfig.outputDir.replace("camera-tests", "pose-compatibility"),
  use: {
    ...cameraConfig.use,
    baseURL: "http://127.0.0.1:18766",
    actionTimeout: 30_000,
    navigationTimeout: 30_000,
  },
  webServer: {
    ...cameraConfig.webServer,
    command: "node scripts/pose-compatibility/server.mjs",
    url: "http://127.0.0.1:18766",
  },
});
