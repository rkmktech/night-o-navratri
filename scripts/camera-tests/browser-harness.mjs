import { test as base, expect } from "@playwright/test";

// Runs before the component script. Only external boundaries are replaced:
// real DOM events, buttons, IntersectionObserver and MediaStream tracks remain.
function installHarness() {
  const deferred = () => {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
  };
  const pending = {};
  const harness = window.cameraTest = {
    requests: [], streams: [], stopped: [], frames: new Map(),
    calls: { load: 0, estimate: 0, predict: 0, play: 0 },
    mode: {},
    prediction: [{ className: "Garba step", probability: 0.95 }],
    setPrediction(className, probability) { this.prediction = [{ className, probability }]; },
    hold(stage) { this.mode[stage] = "pending"; },
    fail(stage, name = "Error") { this.mode[stage] = name; },
    resolve(stage) { pending[stage].shift().resolve(); },
    reject(stage, name) { pending[stage].shift().reject(new DOMException("Test failure", name)); },
    end(index = 0) {
      const track = this.streams[index].getVideoTracks()[0];
      track.stop();
      track.dispatchEvent(new Event("ended"));
    },
    hidePage() {
      Object.defineProperty(document, "hidden", { configurable: true, value: true });
      document.dispatchEvent(new Event("visibilitychange"));
    },
    nextFrame() {
      const callbacks = [...this.frames.values()];
      this.frames.clear();
      callbacks.forEach(callback => callback(performance.now()));
    },
  };
  async function boundary(stage) {
    harness.calls[stage] = (harness.calls[stage] || 0) + 1;
    const mode = harness.mode[stage];
    if (mode === "pending") {
      const item = deferred();
      (pending[stage] ||= []).push(item);
      await item.promise;
    } else if (mode) {
      throw new DOMException("Controlled test failure", mode);
    }
  }
  let frameId = 0;
  window.requestAnimationFrame = callback => {
    harness.frames.set(++frameId, callback);
    return frameId;
  };
  window.cancelAnimationFrame = id => harness.frames.delete(id);
  navigator.mediaDevices.getUserMedia = async constraints => {
    harness.requests.push(constraints);
    await boundary("permission");
    const source = document.createElement("canvas");
    source.width = source.height = 320;
    const stream = source.captureStream();
    const index = harness.streams.push(stream) - 1;
    for (const track of stream.getTracks()) {
      const realStop = track.stop.bind(track);
      track.stop = () => {
        realStop();
        harness.stopped.push(index);
        // Synchronous evidence survives unload (async exposed bindings may not).
        const stopped = JSON.parse(sessionStorage.getItem("camera-stops") || "[]");
        stopped.push(index);
        sessionStorage.setItem("camera-stops", JSON.stringify(stopped));
      };
    }
    return stream;
  };
  HTMLMediaElement.prototype.play = async function () { await boundary("play"); };
  // No real video frames in this deterministic harness.
  CanvasRenderingContext2D.prototype.drawImage = () => {};
  const model = {
    async estimatePose() {
      await boundary("estimate");
      return { pose: { score: 0.9, keypoints: [] }, posenetOutput: [] };
    },
    async predict() {
      const predictions = structuredClone(harness.prediction);
      await boundary("predict");
      return predictions;
    },
  };
  window.tmPose = {
    async load() { await boundary("load"); return model; },
    drawKeypoints() {}, drawSkeleton() {},
  };
}

export const test = base.extend({
  studio: async ({ page }, use) => {
    const unexpectedNetwork = [];
    const pageErrors = [];
    await page.addInitScript(installHarness);
    // Never use real CDN libraries, a real trained model or a real camera.
    await page.route("https://**/*", route => {
      if (route.request().url().startsWith("https://cdn.jsdelivr.net/npm/")) {
        return route.fulfill({ contentType: "application/javascript", body: "" });
      }
      unexpectedNetwork.push(route.request().url());
      return route.abort();
    });
    page.on("pageerror", error => pageErrors.push(error.message));
    await page.goto("/");
    const frame = page.frameLocator("#studio");
    await expect(frame.locator("#status")).toContainText("Camera is off");
    const run = (method, ...args) => frame.locator("body").evaluate(
      (_, { method, args }) => window.cameraTest[method](...args), { method, args },
    );
    const state = () => frame.locator("body").evaluate(() => ({
      requests: window.cameraTest.requests,
      calls: window.cameraTest.calls,
      tracks: window.cameraTest.streams.map(stream => stream.getTracks().map(track => track.readyState)),
      stopped: window.cameraTest.stopped,
      frames: window.cameraTest.frames.size,
      attached: document.getElementById("video").srcObject !== null,
    }));
    await use({ page, frame, run, state });
    expect(unexpectedNetwork, "No model/frame uploads or unexpected external requests").toEqual([]);
    expect(pageErrors, "No uncaught browser errors").toEqual([]);
  },
});

export { expect };

export async function startCamera(studio) {
  await studio.frame.locator("#start").click();
  await expect(studio.frame.locator("#status")).toContainText("Camera is on");
  await expect(studio.frame.locator("#scores")).toContainText("Garba step: 95.0%");
}

export async function expectOff(studio) {
  await expect(studio.frame.locator("#start")).toBeEnabled();
  await expect(studio.frame.locator("#stop")).toBeDisabled();
  await expect(studio.frame.locator("#canvas")).toBeHidden();
  await expect(studio.frame.locator("#scores")).toBeEmpty();
  await expect(studio.frame.locator("#feedback")).toHaveText("No prediction yet.");
  const state = await studio.state();
  expect(state.attached).toBe(false);
  expect(state.frames).toBe(0);
  expect(state.tracks.flat().every(state => state === "ended")).toBe(true);
}
