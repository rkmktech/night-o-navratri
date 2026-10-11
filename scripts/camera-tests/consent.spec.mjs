import { test, expect, startCamera, expectOff } from "./browser-harness.mjs";

test("camera and model remain untouched until Start; permission is video-only", async ({ studio }) => {
  await studio.run("nextFrame");
  expect((await studio.state()).requests).toEqual([]);
  expect((await studio.state()).calls.load).toBe(0);
  await expect(studio.frame.locator("script[src]")).toHaveCount(0);
  await startCamera(studio);
  expect((await studio.state()).requests).toEqual([{
    video: { width: 320, height: 320, facingMode: "user" }, audio: false,
  }]);
  await studio.frame.locator("#stop").click();
  await expectOff(studio);
});

test("permission denial has actionable feedback and supports explicit retry", async ({ studio }) => {
  await studio.run("fail", "permission", "NotAllowedError");
  await studio.frame.locator("#start").click();
  await expect(studio.frame.locator("#status")).toContainText("Allow camera access in browser settings, then try again");
  await expectOff(studio);
  expect((await studio.state()).requests).toHaveLength(1);
  await studio.run("fail", "permission", "");
  await startCamera(studio);
  expect((await studio.state()).requests).toHaveLength(2);
  await studio.frame.locator("#stop").click();
  await expectOff(studio);
});

test("model failure explains retry without ever opening the camera", async ({ studio }) => {
  await studio.run("fail", "load");
  await studio.frame.locator("#start").click();
  await expect(studio.frame.locator("#status")).toContainText("Check your connection and try again");
  await expectOff(studio);
  expect((await studio.state()).requests).toEqual([]);
  await studio.run("fail", "load", "");
  await startCamera(studio);
  expect((await studio.state()).calls.load).toBe(2);
});

test("library download failure stays camera-free and can be retried", async ({ studio }) => {
  const pattern = "**/tf.min.js";
  await studio.page.route(pattern, route => route.abort());
  await studio.frame.locator("#start").click();
  await expect(studio.frame.locator("#status")).toContainText("Check your connection and try again");
  expect((await studio.state()).requests).toEqual([]);
  await expectOff(studio);
  await studio.page.unroute(pattern);
  await startCamera(studio);
});
