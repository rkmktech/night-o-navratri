import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

test("configured pose model and pinned libraries perform real inference without a camera", async ({ page }, testInfo) => {
  // Use the production rendering path, including URL validation. Do not maintain
  // a second copy of model or dependency URLs in this test.
  const html = execFileSync("python", [
    "-c", "from streamlit_app.dance_studio import studio_html; print(studio_html())",
  ], {
    cwd: fileURLToPath(new URL("../../", import.meta.url)),
    encoding: "utf8",
  });
  const modelMatch = html.match(/const modelURL = ("(?:[^"\\]|\\.)*");/);
  expect(modelMatch, "Rendered component must expose its configured model URL").not.toBeNull();
  const modelURL = JSON.parse(modelMatch[1]);
  const libraries = [...html.matchAll(/await loadScript\("(https:\/\/[^"]+)"\)/g)].map(match => match[1]);
  expect(libraries, "Read both inference library URLs from pose_studio.html").toHaveLength(2);
  for (const url of libraries) {
    expect(url, "Inference dependencies must remain version-pinned").toMatch(/@\d+\.\d+\.\d+\//);
  }

  const networkFailures = [];
  const browserErrors = [];
  const downloads = [];
  page.on("requestfailed", request => {
    networkFailures.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText}`);
  });
  page.on("response", response => {
    // Teachable Machine redirects model files to its storage host. Redirects
    // are expected; failed destinations still produce HTTP/request failures.
    if (response.status() >= 400) networkFailures.push(`HTTP ${response.status()} ${response.url()}`);
    if (response.url().startsWith("https://")) downloads.push({
      url: response.url(), status: response.status(),
    });
  });
  page.on("pageerror", error => browserErrors.push(error.message));
  // No media permissions are granted. Fail explicitly if anyone accidentally
  // changes the probe to use a camera rather than the non-private fixture.
  await page.addInitScript(() => {
    window.cameraCalls = 0;
    navigator.mediaDevices.getUserMedia = async () => {
      window.cameraCalls++;
      throw new Error("Camera access is forbidden in the compatibility probe");
    };
  });

  let result;
  try {
    await page.goto("/");
    result = await page.evaluate(async ({ modelURL, libraries }) => {
      const stage = async (name, action) => {
        window.poseCompatibilityStage = name;
        let timer;
        try {
          return await Promise.race([
            action(),
            new Promise((_, reject) => {
              timer = setTimeout(() => reject(new Error("Timed out after 45 seconds")), 45_000);
            }),
          ]);
        } catch (error) {
          throw new Error(`${name}: ${error.message}`);
        } finally {
          clearTimeout(timer);
        }
      };
      for (const url of libraries) {
        await stage(`Library download ${url}`, () => new Promise((resolve, reject) => {
          const script = document.createElement("script");
          script.src = url;
          script.onload = resolve;
          script.onerror = () => reject(new Error("Script download failed; see network diagnostics"));
          document.head.appendChild(script);
        }));
      }
      const metadata = await stage(`Metadata download ${modelURL}metadata.json`, async () => {
        const response = await fetch(modelURL + "metadata.json");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      });
      const model = await stage(`Model/weights download ${modelURL}`, () =>
        window.tmPose.load(modelURL + "model.json", modelURL + "metadata.json"));
      try {
        const image = await stage("Local public image fixture decoding", async () => {
          const image = new Image();
          image.src = "/fixtures/tennis.jpg";
          await image.decode();
          return image;
        });
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 320;
        canvas.getContext("2d").drawImage(image, 0, 0, 320, 320);
        const { pose, posenetOutput } = await stage("Real estimatePose", () => model.estimatePose(canvas));
        const predictions = await stage("Real predict", () => model.predict(posenetOutput));
        return {
          tfVersion: window.tf.version.tfjs,
          labels: metadata.labels,
          pose,
          posenetOutput: Array.from(posenetOutput),
          predictions,
          cameraCalls: window.cameraCalls,
        };
      } finally {
        model.dispose();
      }
    }, { modelURL, libraries });

    const probability = value => {
      expect(Number.isFinite(value), "Expected a finite numeric confidence").toBe(true);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    };
    expect(result.cameraCalls).toBe(0);
    probability(result.pose.score);
    expect(result.pose.keypoints).toHaveLength(17);
    expect(new Set(result.pose.keypoints.map(point => point.part)).size).toBe(17);
    for (const point of result.pose.keypoints) {
      expect(typeof point.part).toBe("string");
      probability(point.score);
      expect(Number.isFinite(point.position.x)).toBe(true);
      expect(Number.isFinite(point.position.y)).toBe(true);
    }
    expect(result.posenetOutput.length).toBeGreaterThan(0);
    expect(result.posenetOutput.every(Number.isFinite)).toBe(true);
    expect(result.labels.length).toBeGreaterThan(0);
    expect(result.labels.every(label => typeof label === "string" && label.trim().length > 0)).toBe(true);
    expect(result.predictions.map(item => item.className)).toEqual(result.labels);
    for (const prediction of result.predictions) probability(prediction.probability);
    expect(result.predictions.reduce((sum, item) => sum + item.probability, 0)).toBeCloseTo(1, 3);
    expect(networkFailures, "No library, metadata, model or weights download may fail").toEqual([]);
    expect(browserErrors, "No uncaught browser errors").toEqual([]);
    console.log(`Real pose inference passed: TensorFlow.js ${result.tfVersion}, ${result.pose.keypoints.length} keypoints, ${result.predictions.length} model labels.`);
  } catch (error) {
    throw new Error(`${error.message}\nNetwork failures:\n${networkFailures.join("\n") || "(none observed)"}\nBrowser errors:\n${browserErrors.join("\n") || "(none observed)"}`);
  } finally {
    await testInfo.attach("real-inference-diagnostics", {
      body: JSON.stringify({ modelURL, libraries, downloads, networkFailures, browserErrors, result }, null, 2),
      contentType: "application/json",
    });
  }
});
