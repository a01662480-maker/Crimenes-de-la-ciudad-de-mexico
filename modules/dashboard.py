import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

def format_number(n):
    return f"{int(n):,}" if isinstance(n, (int, float)) else n

def show():
    st.title("📈 CDMX Crime Analytics Dashboard - Thales")
    st.markdown("Insights and visual trends.")

    df = load_data()
    if df.empty:
        st.stop()

    # ===============================
    # Filters
    # ===============================
    col1, col2 = st.columns(2)
    with col1:
        boroughs = df["alcaldia_hecho"].dropna().unique()
        selected_boroughs = st.multiselect("Select Boroughs", sorted(boroughs))

    with col2:
        years = sorted(df["anio_hecho"].dropna().unique())
        selected_year = st.selectbox("Select Year", [None] + list(years), index=0)

    # Apply filters
    filtered_df = df.copy()
    if selected_boroughs:
        filtered_df = filtered_df[filtered_df["alcaldia_hecho"].isin(selected_boroughs)]
    if selected_year is not None:
        filtered_df = filtered_df[filtered_df["anio_hecho"] == selected_year]

    # ===============================
    # KPIs
    # ===============================
    total_incidents = len(filtered_df)
    violent_incidents = filtered_df[filtered_df["delito"].str.contains("con violencia", case=False, na=False)].shape[0]
    top_borough = filtered_df["alcaldia_hecho"].value_counts().idxmax() if not filtered_df.empty else "N/A"
    active_boroughs = filtered_df["alcaldia_hecho"].nunique()

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Incidents", format_number(total_incidents), "vs previous period")
    col2.metric("Violent Incidents", format_number(violent_incidents), "increase")
    col3.metric("High-Risk Borough", top_borough, f"{format_number(filtered_df['alcaldia_hecho'].value_counts().max() if not filtered_df.empty else 0)} incidents")
    col4.metric("Active Boroughs", format_number(active_boroughs), "monitoring zones")

    st.markdown("---")

    # ===============================
    # Visualizations
    # ===============================
    def plot_crimes_by_borough(df):
        counts = df["alcaldia_hecho"].value_counts().reset_index()
        counts.columns = ["Borough", "Cases"]
        fig = px.bar(counts, x="Borough", y="Cases", color="Cases", text=counts["Cases"].apply(format_number))
        fig.update_traces(textposition="outside")
        fig.update_layout(
            title="Crimes per Borough",
            xaxis_title="Borough",
            yaxis_title="Number of Cases",
            template="plotly_white",
        )
        return fig

    def plot_trend_over_time(df):
        df["month"] = df["fecha_hecho"].dt.month
        trend = df.groupby("month").size().reset_index(name="Cases")
        fig = px.line(trend, x="month", y="Cases", markers=True, text=trend["Cases"].apply(format_number))
        fig.update_traces(textposition="top right")
        fig.update_layout(
            title="Monthly Crime Trend",
            xaxis_title="Month",
            yaxis_title="Number of Cases",
            template="plotly_white",
        )
        return fig

    st.plotly_chart(plot_crimes_by_borough(filtered_df), use_container_width=True)
    st.plotly_chart(plot_trend_over_time(filtered_df), use_container_width=True)
