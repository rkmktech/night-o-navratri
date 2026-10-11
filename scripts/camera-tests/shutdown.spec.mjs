import { test, expect, startCamera, expectOff } from "./browser-harness.mjs";

for (const stage of ["load", "permission", "play", "estimate", "predict"]) {
  test(`Stop invalidates pending ${stage} work`, async ({ studio }) => {
    await studio.run("hold", stage);
    await studio.frame.locator("#start").click();
    await expect.poll(async () => (await studio.state()).calls[stage] || 0).toBe(1);
    await studio.frame.locator("#stop").click();
    await expectOff(studio);
    const stoppedStatus = await studio.frame.locator("#status").textContent();
    await studio.run("resolve", stage);
    // Drain promise continuations, then give any accidentally scheduled frame a turn.
    await studio.run("nextFrame");
    await expectOff(studio);
    await expect(studio.frame.locator("#status")).toHaveText(stoppedStatus);
    const state = await studio.state();
    if (stage === "load") expect(state.requests).toEqual([]);
    if (stage === "estimate") expect(state.calls.predict).toBe(0);
    if (stage === "permission") {
      expect(state.tracks).toEqual([["ended"]]);
      expect(state.stopped).toEqual([0]);
    }
  });
}

test("late permission denial cannot replace stopped feedback", async ({ studio }) => {
  await studio.run("hold", "permission");
  await studio.frame.locator("#start").click();
  await expect.poll(async () => (await studio.state()).requests.length).toBe(1);
  await studio.frame.locator("#stop").click();
  await studio.run("reject", "permission", "NotAllowedError");
  await expect(studio.frame.locator("#status")).toContainText("Camera is off");
  await expectOff(studio);
});

test("a stopped session's prediction cannot overwrite a restarted session", async ({ studio }) => {
  await studio.run("hold", "predict");
  await studio.frame.locator("#start").click();
  await expect.poll(async () => (await studio.state()).calls.predict).toBe(1);
  await studio.frame.locator("#stop").click();
  await studio.run("fail", "predict", "");
  await studio.run("setPrediction", "Dandiya step", 0.8);
  await studio.frame.locator("#start").click();
  await expect(studio.frame.locator("#scores")).toHaveText("Dandiya step: 80.0% ");
  const feedback = await studio.frame.locator("#feedback").textContent();
  await studio.run("resolve", "predict");
  await studio.run("nextFrame");
  await expect(studio.frame.locator("#feedback")).toHaveText(feedback);
  await expect(studio.frame.locator("#scores")).toHaveText("Dandiya step: 80.0% ");
  expect((await studio.state()).tracks).toEqual([["ended"], ["live"]]);
  // Exactly one scheduling chain belongs to the new session.
  expect((await studio.state()).frames).toBe(1);
  await studio.frame.locator("#stop").click();
  await expectOff(studio);
});

for (const event of ["visibility", "studio-tab", "track-ended"]) {
  test(`${event} stops the active camera and never auto-restarts`, async ({ studio }) => {
    await startCamera(studio);
    if (event === "visibility") await studio.run("hidePage");
    if (event === "studio-tab") await studio.page.locator("#hide").click();
    if (event === "track-ended") await studio.run("end");
    await expectOff(studio);
    await studio.run("nextFrame");
    if (event === "studio-tab") await studio.page.locator("#show").click();
    await expectOff(studio);
    expect((await studio.state()).requests).toHaveLength(1);
    await expect(studio.frame.locator("#status")).toContainText(
      event === "track-ended" ? "Reconnect it and click Start camera" : "Click Start camera to resume",
    );
  });
}

test("real navigation releases all active tracks", async ({ studio }) => {
  await startCamera(studio);
  await studio.page.goto("/left-studio");
  expect(await studio.page.evaluate(() => JSON.parse(sessionStorage.getItem("camera-stops")))).toEqual([0]);
});

test("late permission grant cannot stop or attach over a restarted camera", async ({ studio }) => {
  await studio.run("hold", "permission");
  await studio.frame.locator("#start").click();
  await expect.poll(async () => (await studio.state()).calls.permission).toBe(1);
  await studio.frame.locator("#stop").click();
  await studio.run("fail", "permission", "");
  await startCamera(studio);
  await studio.run("resolve", "permission");
  await studio.run("nextFrame");
  expect((await studio.state()).tracks).toEqual([["live"], ["ended"]]);
  await expect(studio.frame.locator("#status")).toContainText("Camera is on");
  await expect(studio.frame.locator("#scores")).toContainText("Garba step: 95.0%");
  await studio.frame.locator("#stop").click();
  await expectOff(studio);
});

for (const stage of ["load", "permission"]) {
  for (const event of ["pagehide", "visibility", "studio-tab"]) {
    test(`${event} invalidates pending ${stage}`, async ({ studio }) => {
      await studio.run("hold", stage);
      await studio.frame.locator("#start").click();
      await expect.poll(async () => (await studio.state()).calls[stage] || 0).toBe(1);
      if (event === "pagehide") {
        // Dispatch explicitly to retain the document for resolving delayed work.
        await studio.frame.locator("body").evaluate(() => window.dispatchEvent(new Event("pagehide")));
      } else if (event === "visibility") await studio.run("hidePage");
      else await studio.page.locator("#hide").click();
      await expectOff(studio);
      await studio.run("resolve", stage);
      await studio.run("nextFrame");
      await expectOff(studio);
      const state = await studio.state();
      if (stage === "load") expect(state.requests).toEqual([]);
      else expect(state.tracks).toEqual([["ended"]]);
    });
  }
}

test("a camera disconnect during pending video playback cleans up", async ({ studio }) => {
  await studio.run("hold", "play");
  await studio.frame.locator("#start").click();
  await expect.poll(async () => (await studio.state()).calls.play).toBe(1);
  await studio.run("end");
  await expectOff(studio);
  await studio.run("resolve", "play");
  await studio.run("nextFrame");
  await expectOff(studio);
  expect((await studio.state()).calls.estimate).toBe(0);
});
