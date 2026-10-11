# Real pose compatibility check (opt-in, online)

From the repository root, run:

```sh
pnpm test:pose:compatibility
```

This is deliberately **not** part of `pnpm test:camera`, the default build, or
the offline consent/shutdown workflows. It uses Playwright's Chromium and the
Python `studio_html()` renderer; browser/Python prerequisites are described in
`../camera-tests/README.md`. No webcam or camera permission is used.

The check extracts the configured model URL and pinned library URLs from the
rendered `streamlit_app/pose_studio.html`, loads those real scripts, downloads
the real metadata and model weights, and calls both `estimatePose` and `predict`
on a local public image. It validates 17 finite pose keypoints, a finite pose
vector, class labels matching the downloaded metadata, and normalized finite
class probabilities. It does not assert a particular winning dance label:
this is compatibility coverage, not an accuracy or dance-quality benchmark.

Internet access to jsDelivr, Teachable Machine, and any model/PoseNet weight
hosts is required. Normal model-storage redirects are allowed. Failed requests,
HTTP error responses, stage-specific
timeouts and browser errors fail the command, rather than silently skipping or
falling back to mocks. Logs identify the failing URL/stage. JSON diagnostics and
failure traces go to `generated-artifacts/pose-compatibility/` (excluded from Git
and deployment). CDN/model availability failures are actionable failures of
this online check, not failures of the independent offline privacy suite.

Run this before shipping model or inference-library upgrades. A successful
model download alone does not establish runtime compatibility; choose the
TensorFlow version from the pose wrapper's peer dependencies, not export metadata.

## Fixture provenance

`fixtures/tennis.jpg` is the non-private public tennis demonstration image from
TensorFlow.js's PoseNet sample assets:
https://storage.googleapis.com/tfjs-models/assets/posenet/tennis_in_crowd.jpg

It is checked in so fixture availability does not depend on a third-party image
server during the test. No user camera images, recordings, or personal uploads
are used. The test resizes it to the same 320 × 320 input used by the studio.
