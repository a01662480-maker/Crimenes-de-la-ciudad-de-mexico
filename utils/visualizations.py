import plotly.express as px

def plot_incidents_by_borough(df):
    counts = df['alcaldia_hecho'].value_counts().reset_index()
    counts.columns = ['alcaldia_hecho', 'cases']
    counts['cases_formatted'] = counts['cases'].apply(lambda x: f"{x:,}")
    fig = px.bar(counts, x='alcaldia_hecho', y='cases', text='cases_formatted', title="Incidents by Borough", color='cases')
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_title="Borough", yaxis_title="Number of Cases")
    return fig

def plot_monthly_trend(df):
    df['month'] = df['fecha_hecho'].dt.month
    trend = df.groupby('month').size().reset_index(name='cases')
    trend['cases_formatted'] = trend['cases'].apply(lambda x: f"{x:,}")
    fig = px.line(trend, x='month', y='cases', text='cases_formatted', title="Monthly Trend of Incidents", markers=True)
    fig.update_traces(textposition='top right')
    fig.update_layout(xaxis_title="Month", yaxis_title="Number of Cases")
    return fig

def plot_map(df):
    fig = px.scatter_mapbox(
        df, lat="latitud", lon="longitud", hover_name="delito",
        hover_data=["alcaldia_hecho", "fecha_hecho"],
        color_discrete_sequence=["red"], zoom=10, height=500
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, title="Map of Incidents")
    return fig
