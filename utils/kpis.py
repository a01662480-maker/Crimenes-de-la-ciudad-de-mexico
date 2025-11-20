import streamlit as st

def format_number(n):
    return f"{n:,}"

def calculate_kpis(df):
    total_incidents = len(df)
    violent_incidents = df["delito"].str.contains("violencia", case=False).sum()
    high_risk_borough = df["alcaldia_hecho"].value_counts().idxmax() if not df.empty else "N/A"
    active_boroughs = df["alcaldia_hecho"].nunique()
    return total_incidents, violent_incidents, high_risk_borough, active_boroughs

def display_kpis(df):
    total_incidents, violent_incidents, high_risk_borough, active_boroughs = calculate_kpis(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Incidents", format_number(total_incidents), "vs previous period")
    col2.metric("Violent Incidents", format_number(violent_incidents), "increase")
    col3.metric("High-Risk Borough", high_risk_borough, f"{format_number(df['alcaldia_hecho'].value_counts().max() if not df.empty else 0)} incidents")
    col4.metric("Active Boroughs", format_number(active_boroughs), "monitoring zones")
