from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

if __package__:
    from .dance_studio import render_pose_studio
else:
    from dance_studio import render_pose_studio


DATA_FILE = Path(__file__).resolve().parent.parent / "navratri_festival_analytics.csv"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
REQUIRED_COLUMNS = [
    "Event_Name",
    "Location_City",
    "Booking_Platform",
    "Ticket_Price_USD_INR",
    "Availability_Status",
    "Date",
    "Event_Time",
    "Food_Available",
    "Booking_Link_Placeholder",
]
PRICE_COLUMN = "Ticket_Price_USD_INR"
EMPTY_MESSAGE = "No festival data matches your filters."
APP_NAME = "Night 'O' Navrathri"
APP_TITLE = "Night 'O' Navratri: Ticket Finder & Dance Studio"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🪔",
    layout="wide",
)


def load_data(path: Path = DATA_FILE) -> pd.DataFrame:
    """Load and validate mock ticket listings without mixing currency units."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path.name}. Place the CSV in the project root."
        )

    data = pd.read_csv(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data]
    if missing_columns:
        raise ValueError(
            "The festival CSV is missing required columns: "
            + ", ".join(missing_columns)
        )

    data = data[REQUIRED_COLUMNS].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="raise").dt.normalize()
    data[PRICE_COLUMN] = pd.to_numeric(data[PRICE_COLUMN], errors="raise").astype(float)
    if data.empty or data.isna().any().any():
        raise ValueError("The ticket dataset must contain complete event listings.")
    if (data[PRICE_COLUMN] < 0).any() or data[PRICE_COLUMN].isin(
        [float("inf"), float("-inf")]
    ).any():
        raise ValueError("Ticket prices must be finite, non-negative numbers.")
    return data.sort_values("Date").reset_index(drop=True)


def compute_metrics(data: pd.DataFrame) -> dict:
    """Summarize the ticket listings matching the shared filters."""
    return {
        "total_events": len(data),
        "cheapest_ticket": float(data[PRICE_COLUMN].min()) if not data.empty else None,
        "platforms_compared": data["Booking_Platform"].nunique(),
    }


def filter_data(
    data: pd.DataFrame, start_date, end_date, selections: dict[str, list[str]]
) -> pd.DataFrame:
    """Apply date and categorical filters consistently to every tab."""
    mask = data["Date"].dt.date.between(start_date, end_date)
    for column, selected_values in selections.items():
        mask &= data[column].isin(selected_values)
    return data.loc[mask].copy()


def search_events(data: pd.DataFrame, query: str) -> pd.DataFrame:
    """Search listing text literally, including names, cities, and platforms."""
    if not query.strip() or data.empty:
        return data.copy()
    searchable = data.astype(str).agg(" ".join, axis=1)
    return data.loc[
        searchable.str.contains(query.strip(), case=False, na=False, regex=False)
    ].copy()


def render_sidebar(data: pd.DataFrame) -> pd.DataFrame:
    """Collect shared filters and apply them before rendering any tab."""
    st.sidebar.header(APP_NAME)
    st.sidebar.caption(
        "Find your festival night. Shared filters apply to ticket listings "
        "and all comparison charts."
    )

    min_date = data["Date"].min().date()
    max_date = data["Date"].max().date()
    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date, end_date = min_date, max_date

    selections: dict[str, list[str]] = {}
    for column, label in [
        ("Location_City", "City"),
        ("Booking_Platform", "Booking Platform"),
        ("Availability_Status", "Availability Status"),
        ("Food_Available", "Food Available"),
    ]:
        options = sorted(data[column].dropna().unique().tolist())
        selections[column] = st.sidebar.multiselect(
            label,
            options=options,
            default=options,
        )

    st.sidebar.caption(
        "Select Available or Fast Filling to find open slots. "
        "Clearing a selection returns no matches."
    )
    return filter_data(data, start_date, end_date, selections)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def render_ticket_finder(data: pd.DataFrame) -> None:
    st.subheader(f"{APP_NAME} · Find your festival night")
    metrics = compute_metrics(data)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Total Events Found", f'{metrics["total_events"]:,}')
    metric_columns[1].metric(
        "Cheapest Ticket Price",
        format_currency(metrics["cheapest_ticket"])
        if metrics["cheapest_ticket"] is not None else "—",
    )
    metric_columns[2].metric("Platforms Compared", metrics["platforms_compared"])
    st.caption("KPIs reflect all listings matching your sidebar filters.")
    if data.empty:
        st.info(EMPTY_MESSAGE)
        return

    st.subheader("Discover Garba, Dandiya, and festive celebrations")
    search_term = st.text_input(
        "Search events",
        placeholder="Search events, cities, platforms, food options, or timings",
    )
    table_data = search_events(data, search_term).sort_values(
        [PRICE_COLUMN, "Date"]
    )
    st.caption(f"{len(table_data):,} matching listings · cheapest first")
    if table_data.empty:
        st.info("No events match your search. Try a different keyword.")
    st.download_button(
        "Download filtered tickets (CSV)",
        data=table_data.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8"),
        file_name="navratri_filtered_tickets.csv",
        mime="text/csv",
        disabled=table_data.empty,
        help="Includes sidebar filters and the current search. Prices are USD equivalent.",
    )
    st.dataframe(
        table_data,
        width="stretch",
        hide_index=True,
        column_order=[
            "Event_Name", "Location_City", "Date", "Event_Time",
            PRICE_COLUMN, "Availability_Status", "Food_Available",
            "Booking_Platform", "Booking_Link_Placeholder",
        ],
        column_config={
            "Event_Name": "Event",
            "Location_City": "City",
            "Booking_Platform": "Booking Platform",
            PRICE_COLUMN: st.column_config.NumberColumn(
                "Ticket Price (USD equivalent)", format="$%.2f"
            ),
            "Availability_Status": "Availability",
            "Date": st.column_config.DateColumn("Date", format="MMM D, YYYY"),
            "Event_Time": st.column_config.TextColumn("Event Time", width="medium"),
            "Food_Available": st.column_config.TextColumn("Food Available", width="medium"),
            "Booking_Link_Placeholder": st.column_config.TextColumn(
                "Booking Link (placeholder)"
            ),
        },
    )


def compute_food_comparison(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate food-option averages and sample sizes from filtered listings."""
    return data.groupby("Food_Available", as_index=False).agg(
        Average_Ticket_Price=(PRICE_COLUMN, "mean"),
        Events=(PRICE_COLUMN, "size"),
    )


def render_price_comparison(data: pd.DataFrame) -> None:
    st.subheader(f"{APP_NAME} · Compare prices & dining")
    if data.empty:
        st.info(EMPTY_MESSAGE)
        return

    average_prices = (
        data.groupby("Booking_Platform", as_index=False)[PRICE_COLUMN]
        .mean()
        .sort_values(PRICE_COLUMN)
    )
    platform_chart = px.bar(
        average_prices,
        x=PRICE_COLUMN,
        y="Booking_Platform",
        orientation="h",
        category_orders={"Booking_Platform": average_prices["Booking_Platform"].tolist()},
        text_auto=".2f",
        labels={
            "Booking_Platform": "Booking Platform",
            PRICE_COLUMN: "Average ticket price (USD equivalent)",
        },
        title="Average ticket price by booking platform",
        color_discrete_sequence=["#B43E52"],
    )
    platform_chart.update_xaxes(rangemode="tozero")
    st.plotly_chart(platform_chart, width="stretch")
    st.caption(
        "These are averages across matching mock listings, not quotes for the same "
        "event on each platform. Differences can reflect the event and city mix."
    )

    st.subheader("Find the best value for your festive night")
    food_summary = compute_food_comparison(data)
    food_chart = px.bar(
        food_summary,
        x="Food_Available",
        y="Average_Ticket_Price",
        text_auto=".2f",
        hover_data={"Events": True, "Average_Ticket_Price": ":.2f"},
        labels={
            "Food_Available": "Food Available",
            "Average_Ticket_Price": "Average ticket price (USD equivalent)",
        },
        title="Average ticket price by food option",
        color_discrete_sequence=["#E6A23C"],
    )
    food_chart.update_yaxes(rangemode="tozero")
    st.plotly_chart(food_chart, width="stretch")

    with_food = data.loc[data["Food_Available"] != "No Food", PRICE_COLUMN]
    without_food = data.loc[data["Food_Available"] == "No Food", PRICE_COLUMN]
    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "Average ticket · food offered",
        format_currency(with_food.mean()) if not with_food.empty else "N/A",
    )
    metric_columns[1].metric(
        "Average ticket · no food",
        format_currency(without_food.mean()) if not without_food.empty else "N/A",
    )
    if not with_food.empty and not without_food.empty:
        difference = float(with_food.mean() - without_food.mean())
        metric_columns[2].metric(
            "Food offered − no food", f"{difference:+.2f} USD"
        )
        st.caption(
            f"Food-offering listings average {format_currency(abs(difference))} "
            f"{'more' if difference >= 0 else 'less'} than no-food listings "
            "under your current filters."
        )
    else:
        metric_columns[2].metric("Food offered − no food", "N/A")
        st.info("Select both food-offering and no-food events to compare their prices.")
    st.caption(
        "Complimentary food is included; paid-stall purchases cost extra and are "
        "not included in ticket prices. These mock averages do not isolate the "
        "cost of food: cities, events, and platforms can also affect prices."
    )

    city_chart = px.box(
        data,
        x="Location_City",
        y=PRICE_COLUMN,
        points="all",
        hover_data=[
            "Event_Name", "Booking_Platform", "Availability_Status", "Date",
            "Food_Available", "Event_Time",
        ],
        labels={
            "Location_City": "City",
            PRICE_COLUMN: "Ticket price (USD equivalent)",
        },
        title="Ticket price spread by city",
        color_discrete_sequence=["#E6A23C"],
    )
    st.plotly_chart(city_chart, width="stretch")
    st.caption("Boxes show the middle 50% of prices; dots show individual listings.")


def render_skeleton_video(asset_path: Path) -> None:
    """Play a local guide when uploaded, with an explicit missing-file state."""
    if not asset_path.is_file():
        st.info("Skeleton guide video not uploaded yet.")
        st.caption(f"Expected file: assets/{asset_path.name}")
        return
    try:
        st.video(str(asset_path), autoplay=False)
    except (OSError, ValueError):
        st.warning("This video could not be loaded. Please upload a valid MP4.")


def render_dance_studio() -> None:
    guide_columns = st.columns(2)
    guides = [
        (
            "Garbha Dance Basic Step",
            ASSETS_DIR / "garba_skeleton.mp4",
        ),
        (
            "Dandiya Dance Basic Step",
            ASSETS_DIR / "dandiya_skeleton.mp4",
        ),
    ]
    for column, (title, asset_path) in zip(guide_columns, guides):
        with column, st.container(border=True):
            st.markdown(f"#### {title}")
            render_skeleton_video(asset_path)

    st.divider()
    st.markdown("#### 🎥 Live Practice Tracker")
    st.write(
        "Watch the skeleton guides above, click Start Camera below, "
        "and see if your moves match our AI system!"
    )
    st.caption(
        "Practice the Garba and Dandiya steps and see your pose-match confidence. "
        "Camera access is requested only after you click Start camera."
    )
    render_pose_studio()


def main() -> None:
    mascot_column, title_column = st.columns([1, 6], vertical_alignment="center")
    with mascot_column:
        st.image(str(ASSETS_DIR / "krishna_radha_raas_leela.png"), width="stretch")
    with title_column:
        st.title(APP_TITLE)
    st.subheader(
        "Lock in a ticket, Learn the Dance, Celebrate Navrathri with Confidence and Joy"
    )
    st.write(
        "Celebrate with Night 'O' Navrathri: find your perfect festival night, "
        "compare ticket prices and dining options, and practice your Garba and Dandiya steps."
    )
    st.caption(
        "Mock listings · October 10 – November 10, 2026 · All prices are USD "
        "equivalent, including Indian events. Booking links are placeholders."
    )

    try:
        data = load_data()
    except (OSError, ValueError) as error:
        st.error(f"Could not load ticket listings: {error}")
        st.stop()
    filtered_data = render_sidebar(data)

    finder_tab, comparison_tab, dance_tab = st.tabs(
        ["Ticket Availability Finder", "Price & Amenity Comparison", "AI Dance Studio"]
    )
    with finder_tab:
        render_ticket_finder(filtered_data)
    with comparison_tab:
        render_price_comparison(filtered_data)
    with dance_tab:
        render_dance_studio()


if __name__ == "__main__":
    main()
