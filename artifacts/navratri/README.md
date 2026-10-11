# Night 'O' Navrathri web service

This artifact registers the existing Python Streamlit application for Replit
preview and publishing. It serves `/` on port 8080 using
`scripts/start-streamlit.sh`; the application remains in `streamlit_app/`.

The web-artifact template was used only for registration; its React/Vite
scaffolding was removed. Keep the service commands pointed at Streamlit rather
than adding a replacement frontend.

Production validates the Python dependencies declared in the root
`pyproject.toml` and starts Streamlit, not a static bundle. The startup health
check is `/_stcore/health`. The API remains separately routed under `/api`.

The two skeleton MP4s are kept in App Storage, not Git history. The launcher
restores missing guides into the root `assets/` folder using
`assets/dance_guides.json`, checks their SHA-256 hashes, and then starts
Streamlit. Existing matching local copies are reused.
