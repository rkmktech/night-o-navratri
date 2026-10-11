# Night 'O' Navratri: Ticket Finder & AI Dance Studio

**Lock in a ticket, Learn the Dance, Celebrate Navrathri with Confidence and Joy**

## Project Overview

Night 'O' Navratri is a Streamlit application that brings festival planning and dance practice into one dashboard. Explore event availability, compare ticket prices and dining options, and practice Garba and Dandiya with skeleton-video demonstrations and browser-based AI pose feedback.

The application includes three tabs:

1. **Ticket Availability Finder**
2. **Price & Amenity Comparison**
3. **AI Dance Studio**

> **Demo data:** The ticket portal uses 100 mock event listings dated October 10–November 10, 2026. Prices are shown as USD equivalents, including Indian events. Booking links are placeholders; this application does not provide live inventory or ticket checkout.

## Features

### Ticket Search Portal

- View summary cards for **Total Events Found**, **Cheapest Ticket Price**, and **Platforms Compared**.
- Filter listings by city, booking platform, date range, availability status, and food options.
- Search events and view event dates, timings, prices, dining options, and availability in a searchable table.
- Compare listings from **Sulekha**, **Eventbrite**, **Ticketmaster**, **Local Booking**, and **Gujarati California Association**.
- Explore complimentary food, paid food stalls, and no-food options.
- Download the filtered search results as a CSV file.

### Plotly Price Comparisons

- Compare average ticket prices across booking platforms with an interactive bar chart.
- Explore average prices by food availability and the difference between events offering food and events without food.
- Inspect city-level ticket-price distributions with a box plot.
- Apply shared sidebar filters to both the ticket listings and comparison charts.

Food comparisons describe ticket prices, not the total cost of attending: paid food-stall purchases are not included.

### Pollo AI-Generated Skeleton Dance Studio Using Teachable Machine

- Watch two custom **Pollo AI-generated skeleton dance videos** side by side:
  - **Garbha Dance Basic Step** — `assets/garba_skeleton.mp4`
  - **Dandiya Dance Basic Step** — `assets/dandiya_skeleton.mp4`
- Practice in the open **Live Practice Tracker** directly underneath the guides.
- Use **Start camera** and **Stop camera** to control webcam access.
- Receive live pose-match confidence from an already-trained Google Teachable Machine pose model.
- Keep the public interface focused on practice, without model-training instructions or external training links.

**Privacy and limitations:** Camera access begins only after the visitor selects **Start camera** and grants browser permission. Camera frames are processed in the browser and are not recorded or uploaded by the app. The browser downloads model files from Google and JavaScript libraries from jsDelivr, so internet access is required. The model recognizes five trained sample classes; confidence is not a dance-quality or rhythm score, and unfamiliar movements may be misclassified. The two guide videos do not establish an exact demonstration for every model class.

Pollo AI is used to create the demonstration media; the application does not call a Pollo AI API at runtime.

## How to Run

### Prerequisites

- **Python 3.13 or newer**, matching the project's declared Python requirement.
- Python package installation support.
- A modern browser and webcam for live practice.
- Internet access for browser-side model and library downloads.

### 1. Install Dependencies

From the project root:

```bash
python -m pip install -r streamlit_app/requirements.txt
```

### 2. Check the Required Files

Keep the dataset and assets in their expected locations:

```text
.
├── README.md
├── .streamlit/
│   └── config.toml
├── assets/
│   ├── krishna_radha_raas_leela.png
│   ├── garba_skeleton.mp4
│   └── dandiya_skeleton.mp4
├── navratri_festival_analytics.csv
├── scripts/
│   └── start-streamlit.sh
└── streamlit_app/
    ├── app.py
    ├── dance_config.json
    ├── dance_studio.py
    ├── pose_studio.html
    └── requirements.txt
```

Both skeleton-guide MP4 files are tracked in Git and included in the public repository under `assets/`, so a clone includes the demonstration videos. App Storage backups remain available for deployment restoration. Missing guide videos produce an explanatory message instead of a player.

### 3. Start the Application

Use the project startup script:

```bash
bash scripts/start-streamlit.sh
```

Or run Streamlit directly:

```bash
python -m streamlit run streamlit_app/app.py \
  --server.port 8080 \
  --server.address 0.0.0.0 \
  --server.headless true
```

The server is configured in `.streamlit/config.toml` to run headlessly on **port 8080**. Open `http://localhost:8080` when running locally, or use the workspace's web preview.

Before publishing, run the deployment regression check:

```bash
pnpm test:deployment
```

This checks the registered root web service, port 8080, the Streamlit startup
health path, and the separate `/api` service. It runs the production build
dependency check and the actual production pnpm command, with Streamlit and
asset syncing stubbed to avoid starting a second server or downloading videos.
It also checks launcher working-directory handling, forced bind settings, and
failure propagation. It does not verify live HTTP health, storage credentials,
or public deployment visibility.

### 4. Practice with the Webcam

Open **AI Dance Studio**, watch the skeleton guides, and select **Start camera**. Allow camera access when prompted and position yourself so your full body is visible. Select **Stop camera** when finished.

Browser camera access requires a secure context: use HTTPS for a remotely hosted application or localhost for local development. Camera permissions must also be allowed by the browser and any hosting preview frame.

## Tech Stack Used

| Technology | Role |
| --- | --- |
| **Streamlit** | Python dashboard, tabs, filters, tables, metrics, and media components |
| **Pandas** | CSV loading, filtering, search, and price aggregation |
| **Plotly** | Interactive platform, food-amenity, and city price comparisons |
| **JavaScript** | Browser webcam controls, pose inference, and live feedback rendering |
| **Google Teachable Machine / TensorFlow.js** | Loading and running the trained pose classifier in the browser |
| **Pollo AI** | Creation of the skeleton-guide video assets |

The application's Python dependencies are listed in `streamlit_app/requirements.txt`; project-level dependency declarations are also available in `pyproject.toml`.
