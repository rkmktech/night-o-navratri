# Camera privacy regression tests

Run from the repository root:

```sh
pnpm test:camera
python -m unittest streamlit_app.test_dance_studio
```

The suite serves the actual output of `studio_html()` in a local iframe and
executes it in headless Chromium. Python project dependencies must be installed.
Replit's Chromium is detected automatically; elsewhere install Chromium with
`pnpm --filter @workspace/scripts exec playwright install chromium`, or set
`CAMERA_TEST_CHROMIUM` to your browser executable.

No real webcam, permission prompt, model download, or inference library is used.
The harness supplies real canvas-backed MediaStream tracks, controlled async
model/permission/playback boundaries, and a manual animation-frame queue.
Tests exercise the production buttons, event listeners and cleanup logic.
Unexpected external requests and uncaught browser errors fail the suite.

Coverage includes initial consent, video-only constraints, permission denial and
retry, library/model failure and retry, Stop at each async boundary, stale
prediction after restart, page navigation, visibility changes, iframe tab hiding,
and track-ended cleanup. Browser visibility is explicitly dispatched so results
do not depend on a headless browser's focus behavior; iframe hiding and navigation
use actual browser actions.

Traces for failed tests are under `generated-artifacts/camera-tests/`, excluded
from Git and deployments. These deterministic tests protect lifecycle behavior;
they do not prove real model/library compatibility or browser permission UI.

For real model/library inference, separately opt in with
`pnpm test:pose:compatibility`. See `../pose-compatibility/README.md` for its
public image fixture, network requirements and failure diagnostics. That check
does not alter this suite's offline, camera-free boundaries.
