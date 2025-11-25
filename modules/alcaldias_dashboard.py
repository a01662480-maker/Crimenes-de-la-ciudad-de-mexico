import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from supabase import create_client
from components.mckinsey_styling import apply_mckinsey_styles, create_kpi_card, format_number, format_delta_text

# ===============================
# Configuration
# ===============================
SUPABASE_URL = "https://xzeycsqwynjxnzgctydr.supabase.co"
SUPABASE_KEY = "sb_publishable_wSTGdAAY_IIuYKNpr6N6GA_rGZy-y29"
SUPABASE_TABLE = "FGJ"
SUPABASE_TABLE_CUADRANTS = "cuadrantes"

# ===============================
# Helper Functions
# ===============================
def normalize_alcaldia_name(name):
    """Normalize alcaldía names for matching"""
    if pd.isna(name):
        return None
    name = str(name).upper()
    replacements = {
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u'
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    name = name.replace('.', '').strip()
    if name.endswith(' DE MORELOS'):
        name = name.replace(' DE MORELOS', '')
    if name.startswith('LA '):
        name = name[3:]
    return name

def categorize_violence(delito_text):
    """Categorize crime by violence"""
    if pd.isna(delito_text):
        return 'unknown'
    delito_lower = str(delito_text).lower()
    if 'con violencia' in delito_lower:
        return 'violent'
    elif 'sin violencia' in delito_lower:
        return 'non_violent'
    return 'unknown'

@st.cache_data(ttl=3600)
def load_crime_data():
    """Load and preprocess crime data from Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        response = supabase.table(SUPABASE_TABLE).select(
            "alcaldia_hecho, anio_hecho, fecha_hecho, hora_hecho, hora, delito, latitud, longitud"
        ).execute()
        
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return df
        
        df['fecha_hecho'] = pd.to_datetime(df['fecha_hecho'], errors='coerce')
        df['year'] = df['fecha_hecho'].dt.year
        df['month'] = df['fecha_hecho'].dt.month
        df['day_of_week'] = df['fecha_hecho'].dt.dayofweek
        df['date'] = df['fecha_hecho'].dt.date
        
        # Use 'hora' column if available (should be numeric)
        if 'hora' in df.columns:
            df['hour'] = pd.to_numeric(df['hora'], errors='coerce')
            # If values are 1-24, convert to 0-23
            if df['hour'].max() == 24:
                df['hour'] = df['hour'].replace(24, 0)
            # Ensure values are in 0-23 range
            df['hour'] = df['hour'].apply(lambda x: x if pd.isna(x) or (0 <= x <= 23) else None)
        else:
            df['hour'] = None
        
        df['alcaldia_normalized'] = df['alcaldia_hecho'].apply(normalize_alcaldia_name)
        df['violence_category'] = df['delito'].apply(categorize_violence)
        df = df[df['alcaldia_normalized'].notna()]
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_population_data():
    """Load population data from JSON file"""
    try:
        with open('caractersticas-demogrficas-nivel-ageb.json', 'r', encoding='utf-8') as f:
            pop_data = json.load(f)
        
        if isinstance(pop_data, list):
            pop_df = pd.DataFrame(pop_data)
        elif isinstance(pop_data, dict):
            if 'alc' in pop_data:
                pop_df = pd.DataFrame([pop_data])
            else:
                pop_df = pd.DataFrame.from_dict(pop_data, orient='index')
        else:
            return None
        
        if 'alc' not in pop_df.columns:
            return None
        
        pop_df['alc_normalized'] = pop_df['alc'].apply(normalize_alcaldia_name)
        pop_df['pob'] = pd.to_numeric(pop_df['pob'], errors='coerce')
        population_by_alcaldia = pop_df.groupby('alc_normalized')['pob'].sum().to_dict()
        
        return population_by_alcaldia
    except:
        return None

@st.cache_data
def load_cuadrantes_count():
    """Load cuadrantes count per alcaldía"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table(SUPABASE_TABLE_CUADRANTS).select("alcaldia").execute()
        
        if response.data:
            cuad_df = pd.DataFrame(response.data)
            cuad_df['alcaldia_normalized'] = cuad_df['alcaldia'].apply(normalize_alcaldia_name)
            cuadrantes_count = cuad_df.groupby('alcaldia_normalized').size().to_dict()
            return cuadrantes_count
        return None
    except:
        return None
@st.cache_data
def load_cuadrantes_geojson():
    """Load cuadrantes GeoJSON data from Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table(SUPABASE_TABLE_CUADRANTS).select("*").execute()
        
        if response.data:
            cuad_df = pd.DataFrame(response.data)
            cuad_df['alcaldia_normalized'] = cuad_df['alcaldia'].apply(normalize_alcaldia_name)
            
            # Parse geo_shape if it's a string
            import ast
            def parse_shape(v):
                try:
                    return ast.literal_eval(v) if isinstance(v, str) else v
                except:
                    return None
            
            cuad_df['geo_shape'] = cuad_df['geo_shape'].apply(parse_shape)
            
            return cuad_df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading cuadrantes: {e}")
        return pd.DataFrame()
# ===============================
# Main Dashboard Function
# ===============================
def show():
    st.set_page_config(page_title="Alcaldía Dashboard", page_icon="🏙️", layout="wide")
    apply_mckinsey_styles()
    
    # McKinsey-style CSS for containers
    st.markdown("""
        <style>
        /* Compact info metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }
        
        /* Container styling for KPIs */
        div[data-testid="column"] > div {
            background: linear-gradient(135deg, #F8F9FA 0%, #ffffff 100%);
            border-left: 3px solid #0066CC;
            border-radius: 8px;
            padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
        }
        
        /* Remove default streamlit padding for tighter layout */
        .block-container {
            padding-top: 2rem;
        }
        
        /* Section headers */
        .section-header {
            background: linear-gradient(90deg, #0066CC 0%, #004C99 100%);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 2rem 0 1rem 0;
            font-size: 1.3rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Load data
    df = load_crime_data()
    population_data = load_population_data()
    cuadrantes_count = load_cuadrantes_count()
    cuadrantes_geojson = load_cuadrantes_geojson()
    
    if df.empty:
        st.warning("No data available")
        st.stop()
    
    # Get available years
    available_years = sorted([int(y) for y in df['year'].unique() if pd.notna(y)])
    if not available_years:
        st.error("No valid year data available")
        st.stop()
    
    min_year = min(available_years)
    max_year = max(available_years)
    
    # ===============================
    # TITLE & ALCALDÍA SELECTOR
    # ===============================
    st.title("🏙️ Panel de Análisis de Alcaldía")
    st.divider()
    
    st.subheader("📍 Seleccionar Alcaldía")
    
    # Get list of alcaldías
    alcaldias_list = sorted(df['alcaldia_normalized'].unique())
    alcaldias_display = [alc.title() for alc in alcaldias_list]
    
    selected_alcaldia_display = st.selectbox(
        "Elige una alcaldía para analizar:",
        options=alcaldias_display,
        index=0,
        key='alcaldia_selector'
    )
    
    # Convert back to normalized name
    selected_alcaldia = alcaldias_list[alcaldias_display.index(selected_alcaldia_display)]
    
    # Filter data for selected alcaldía
    alcaldia_df = df[df['alcaldia_normalized'] == selected_alcaldia].copy()
    
    st.divider()
    
    # ===============================
    # SECTION 1: RECENT ACTIVITY (LAST 30 DAYS)
    # ===============================
    st.markdown('<div class="section-header">📅 Sección 1: Actividad Reciente (Últimos 30 Días)</div>', unsafe_allow_html=True)
    
    # Calculate last 30 days data
    max_date = alcaldia_df['fecha_hecho'].max()
    if pd.notna(max_date):
        last_30_days_start = max_date - timedelta(days=30)
        last_30_df = alcaldia_df[alcaldia_df['fecha_hecho'] >= last_30_days_start]
        
        # Previous 30 days for comparison
        previous_30_start = last_30_days_start - timedelta(days=30)
        previous_30_df = alcaldia_df[
            (alcaldia_df['fecha_hecho'] >= previous_30_start) & 
            (alcaldia_df['fecha_hecho'] < last_30_days_start)
        ]
        
        # Display actual date range
        st.caption(f"Datos del {last_30_days_start.strftime('%Y-%m-%d')} al {max_date.strftime('%Y-%m-%d')}")
        
        # Calculate metrics
        total_crimes_30d = len(last_30_df)
        previous_crimes_30d = len(previous_30_df)
        daily_avg_30d = total_crimes_30d / 30
        
        # YoY change for 30 days
        if previous_crimes_30d > 0:
            change_30d = ((total_crimes_30d - previous_crimes_30d) / previous_crimes_30d) * 100
        else:
            change_30d = 0
        
        # Most common crime
        if not last_30_df.empty:
            top_crime = last_30_df['delito'].value_counts().index[0]
            top_crime_count = last_30_df['delito'].value_counts().iloc[0]
        else:
            top_crime = "N/A"
            top_crime_count = 0
        
        # Violence breakdown
        violent_count = len(last_30_df[last_30_df['violence_category'] == 'violent'])
        non_violent_count = len(last_30_df[last_30_df['violence_category'] == 'non_violent'])
        violent_pct = (violent_count / total_crimes_30d * 100) if total_crimes_30d > 0 else 0
        
        # Busiest day
        if not last_30_df.empty:
            daily_counts = last_30_df.groupby('date').size()
            busiest_day = daily_counts.idxmax()
            busiest_day_count = daily_counts.max()
        else:
            busiest_day = "N/A"
            busiest_day_count = 0
        
        # Trend direction
        trend_direction = "Aumentando ↑" if change_30d > 0 else "Disminuyendo ↓" if change_30d < 0 else "Estable →"
        trend_color = "negative" if change_30d > 0 else "positive" if change_30d < 0 else "neutral"
        
# ===============================
        # KPI CARDS - REWORKED
        # ===============================
        st.subheader("📊 Indicadores Clave")
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        
        with kpi_col1:
            delta_text = format_delta_text(total_crimes_30d, previous_crimes_30d, period_label="vs 30d ant.")
            delta_color = "negative" if change_30d > 0 else "positive" if change_30d < 0 else "neutral"
            create_kpi_card(
                label="Total de Delitos (30d)",
                value=format_number(total_crimes_30d),
                delta=delta_text,
                delta_color=delta_color
            )
        
        with kpi_col2:
            create_kpi_card(
                label="Promedio Diario",
                value=f"{daily_avg_30d:.1f}",
                delta="delitos por día",
                delta_color="neutral"
            )
        
        with kpi_col3:
            create_kpi_card(
                label="Dirección de Tendencia",
                value=trend_direction,
                delta=f"{abs(change_30d):.1f}% cambio",
                delta_color=trend_color
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ===============================
        # ROW 2: VISUAL CARDS (2 columns)
        # ===============================
        import plotly.graph_objects as go
        from scipy.ndimage import gaussian_filter1d
        import numpy as np
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            st.markdown("""
                <div style="background: linear-gradient(135deg, #F8F9FA 0%, #ffffff 100%);
                            border-left: 3px solid #0066CC;
                            border-radius: 8px;
                            padding: 1.2rem;
                            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
                            height: 100%;">
            """, unsafe_allow_html=True)
            
            st.markdown("**Violentos vs No Violentos**")
            
            if total_crimes_30d > 0:
                # Create donut chart
                fig_donut = go.Figure(data=[go.Pie(
                    labels=['Con Violencia', 'Sin Violencia'],
                    values=[violent_count, non_violent_count],
                    hole=0.65,
                    marker=dict(
                        colors=['#003d82', '#6fa8dc'],
                        line=dict(color='white', width=2)
                    ),
                    textinfo='percent',
                    textposition='outside',
                    textfont=dict(size=14, family='Arial', color='#333'),
                    hoverinfo='label+value+percent',
                    showlegend=True
                )])
                
                # Add center text showing violent percentage
                fig_donut.add_annotation(
                    text=f"<b>{violent_pct:.1f}%</b><br><span style='font-size:12px;'>Violentos</span>",
                    x=0.5, y=0.5,
                    font=dict(size=24, family='Arial', color='#003d82'),
                    showarrow=False
                )
                
                fig_donut.update_layout(
                    height=320,
                    margin=dict(l=20, r=20, t=20, b=60),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.15,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11)
                    )
                )
                
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
                
                # Show counts below
                st.caption(f"Con Violencia: **{violent_count}** | Sin Violencia: **{non_violent_count}**")
            else:
                st.info("No hay datos disponibles")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with viz_col2:
            st.markdown("""
                <div style="background: linear-gradient(135deg, #F8F9FA 0%, #ffffff 100%);
                            border-left: 3px solid #0066CC;
                            border-radius: 8px;
                            padding: 1.2rem;
                            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
                            height: 100%;">
            """, unsafe_allow_html=True)
            
            st.markdown("**Actividad Diaria (30 días)**")
            
            if not daily_counts.empty and len(daily_counts) > 0:
                # Prepare data for bar chart
                daily_df = daily_counts.reset_index()
                daily_df.columns = ['date', 'count']
                daily_df = daily_df.sort_values('date')
                
                # Create color array - highlight busiest day in red
                colors = ['#DC143C' if date == busiest_day else '#0066CC' for date in daily_df['date']]
                
                # Create bar chart
                fig_spark = go.Figure()
                
                fig_spark.add_trace(go.Bar(
                    x=daily_df['date'],
                    y=daily_df['count'],
                    marker=dict(
                        color=colors,
                        line=dict(color='white', width=1)
                    ),
                    hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Delitos: <b>%{y}</b><extra></extra>',
                    showlegend=False
                ))
                
                # Add annotation for busiest day (above bar)
                busiest_idx = daily_df[daily_df['date'] == busiest_day].index[0]
                busiest_y = daily_df.loc[busiest_idx, 'count']
                
                fig_spark.add_annotation(
                    x=busiest_day,
                    y=busiest_y,
                    text=f"<b>{busiest_day_count}</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor='#DC143C',
                    ax=0,
                    ay=-40,
                    font=dict(size=12, color='#DC143C', family='Arial', weight='bold'),
                    bgcolor='white',
                    bordercolor='#DC143C',
                    borderwidth=1,
                    borderpad=4
                )
                
                fig_spark.update_layout(
                    height=320,
                    margin=dict(l=40, r=20, t=40, b=60),
                    plot_bgcolor='white',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=False,
                        showticklabels=True,
                        tickformat='%d/%m',
                        nticks=8,
                        tickfont=dict(size=9),
                        tickangle=-45
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='#f0f0f0',
                        showticklabels=True,
                        tickfont=dict(size=10)
                    ),
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial"
                    )
                )
                
                st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})
                
                # Show busiest day info below
                st.caption(f"Día con más delitos: **{busiest_day.strftime('%d/%m/%Y')}** ({busiest_day_count} delitos)")
            else:
                st.info("No hay datos disponibles")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.divider()
        # ===============================
        # VISUALIZATIONS
        # ===============================
        st.subheader("📈 Visualizaciones")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            st.markdown("**Delitos Diarios**")
            
            # Toggle for breakdown
            show_breakdown = st.checkbox("Mostrar desglose por violencia", key="violence_breakdown_toggle")
            
            if not last_30_df.empty:
                # Prepare daily crime data
                daily_crimes = last_30_df.groupby('date').size().reset_index(name='total')
                daily_crimes['date'] = pd.to_datetime(daily_crimes['date'])
                daily_crimes = daily_crimes.sort_values('date')
                
                # Format dates as "Day dd/mm"
                daily_crimes['date_label'] = daily_crimes['date'].dt.strftime('%a %d/%m')
                
                if show_breakdown:
                    # Count by violence category per day
                    violent_daily = last_30_df[last_30_df['violence_category'] == 'violent'].groupby('date').size().reset_index(name='violent')
                    non_violent_daily = last_30_df[last_30_df['violence_category'] == 'non_violent'].groupby('date').size().reset_index(name='non_violent')
                    
                    # Convert date columns to datetime before merging
                    violent_daily['date'] = pd.to_datetime(violent_daily['date'])
                    non_violent_daily['date'] = pd.to_datetime(non_violent_daily['date'])
                    
                    # Merge with main daily data
                    daily_crimes = daily_crimes.merge(violent_daily, on='date', how='left')
                    daily_crimes = daily_crimes.merge(non_violent_daily, on='date', how='left')
                    daily_crimes['violent'] = daily_crimes['violent'].fillna(0)
                    daily_crimes['non_violent'] = daily_crimes['non_violent'].fillna(0)
                    
                    # Create line chart with breakdown
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=daily_crimes['date_label'],
                        y=daily_crimes['violent'],
                        mode='lines+markers',
                        name='Con Violencia',
                        line=dict(color='#003d82', width=2.5),
                        marker=dict(size=6)
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=daily_crimes['date_label'],
                        y=daily_crimes['non_violent'],
                        mode='lines+markers',
                        name='Sin Violencia',
                        line=dict(color='#6fa8dc', width=2.5),
                        marker=dict(size=6)
                    ))
                    
                    fig.update_layout(
                        xaxis_title="Fecha",
                        yaxis_title="Número de Delitos",
                        hovermode='x unified',
                        plot_bgcolor='white',
                        height=400,
                        margin=dict(l=40, r=40, t=20, b=80),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        xaxis=dict(
                            tickangle=-45,
                            showgrid=True,
                            gridcolor='#f0f0f0'
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='#f0f0f0'
                        )
                    )
                    
                else:
                    # Create simple line chart with total crimes
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=daily_crimes['date_label'],
                        y=daily_crimes['total'],
                        mode='lines+markers',
                        name='Total de Delitos',
                        line=dict(color='#0066CC', width=3),
                        marker=dict(size=7)
                    ))
                    
                    fig.update_layout(
                        xaxis_title="Fecha",
                        yaxis_title="Número de Delitos",
                        hovermode='x',
                        plot_bgcolor='white',
                        height=400,
                        margin=dict(l=40, r=40, t=20, b=80),
                        showlegend=False,
                        xaxis=dict(
                            tickangle=-45,
                            showgrid=True,
                            gridcolor='#f0f0f0'
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='#f0f0f0'
                        )
                    )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos disponibles para graficar")
        
        with viz_col2:
            st.markdown("**Top 5 Delitos**")
            
            if not last_30_df.empty:
                # Get top 5 crimes
                top_crimes = last_30_df['delito'].value_counts().head(5).reset_index()
                top_crimes.columns = ['delito', 'count']
                
                # Get violence category for each crime (most common category for that crime type)
                crime_violence = []
                for crime in top_crimes['delito']:
                    crime_data = last_30_df[last_30_df['delito'] == crime]
                    most_common_category = crime_data['violence_category'].mode()[0] if len(crime_data) > 0 else 'unknown'
                    crime_violence.append(most_common_category)
                
                top_crimes['violence_category'] = crime_violence
                
                # Assign colors based on violence category
                colors = []
                for category in top_crimes['violence_category']:
                    if category == 'violent':
                        colors.append('#003d82')  # Dark blue
                    elif category == 'non_violent':
                        colors.append('#6fa8dc')  # Light blue
                    else:
                        colors.append('#999999')  # Gray for unknown
                
                # Truncate long crime names for display
                top_crimes['delito_display'] = top_crimes['delito'].apply(
                    lambda x: x[:40] + '...' if len(x) > 40 else x
                )
                
                # Create horizontal bar chart
                import plotly.graph_objects as go
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    y=top_crimes['delito_display'][::-1],  # Reverse for top-to-bottom display
                    x=top_crimes['count'][::-1],
                    orientation='h',
                    marker=dict(
                        color=colors[::-1],
                        line=dict(color='white', width=1)
                    ),
                    text=top_crimes['count'][::-1],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>' +
                                  'Cantidad: <b>%{x}</b><br>' +
                                  '<extra></extra>'
                ))
                
                fig.update_layout(
                    xaxis_title="Número de Incidentes",
                    yaxis_title="",
                    plot_bgcolor='white',
                    height=400,
                    margin=dict(l=10, r=40, t=20, b=40),
                    showlegend=False,
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='#f0f0f0',
                        zeroline=False
                    ),
                    yaxis=dict(
                        showgrid=False,
                        automargin=True
                    ),
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial"
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add legend for colors
                st.caption("🔵 Azul oscuro = Con violencia | 🔵 Azul claro = Sin violencia")
            else:
                st.info("No hay datos disponibles para graficar")
        
    else:
        st.warning("No hay datos recientes disponibles para esta alcaldía")
    
    st.divider()
    
    # ===============================
    # SECTION 2: HISTORICAL TRENDS
    # ===============================
    st.markdown('<div class="section-header">📈 Sección 2: Tendencias Históricas</div>', unsafe_allow_html=True)
    
    st.subheader("📅 Período de Tiempo")
    
    year_range = st.slider(
        "Selecciona el rango de años:",
        min_value=min_year,
        max_value=max_year,
        value=(max_year - 1 if max_year > min_year else min_year, max_year),
        step=1,
        format="%d",
        key='alcaldia_year_slider'
    )
    
    start_year, end_year = year_range
    
    # Filter data for historical section
    filtered_alcaldia_df = alcaldia_df[(alcaldia_df['year'] >= start_year) & (alcaldia_df['year'] <= end_year)].copy()
    
    # ===============================
    # CALCULATE KPI METRICS
    # ===============================
    
    # 1. CRIME RANKING
    all_alcaldias_counts = df[
        (df['year'] >= start_year) & (df['year'] <= end_year)
    ].groupby('alcaldia_normalized').size().sort_values(ascending=False)
    
    alcaldia_rank = list(all_alcaldias_counts.index).index(selected_alcaldia) + 1
    total_alcaldias = len(all_alcaldias_counts)
    
    # 2. AVERAGE CRIMES PER MONTH
    if not filtered_alcaldia_df.empty:
        filtered_alcaldia_df['year_month'] = filtered_alcaldia_df['fecha_hecho'].dt.to_period('M')
        unique_months = filtered_alcaldia_df['year_month'].nunique()
        total_crimes = len(filtered_alcaldia_df)
        avg_crimes_per_month = total_crimes / unique_months if unique_months > 0 else 0
    else:
        total_crimes = 0
        avg_crimes_per_month = 0
    
    # 3. TOTAL CRIMES WITH YOY CHANGE
    latest_year = end_year
    previous_year = latest_year - 1
    
    latest_year_crimes = len(alcaldia_df[alcaldia_df['year'] == latest_year])
    previous_year_crimes = len(alcaldia_df[alcaldia_df['year'] == previous_year])
    
    if previous_year_crimes > 0:
        yoy_change = ((latest_year_crimes - previous_year_crimes) / previous_year_crimes) * 100
    else:
        yoy_change = 0
    
    # ===============================
    # KPI CARDS
    # ===============================
    st.subheader("📊 Indicadores Clave de Desempeño")
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    
    with kpi_col1:
        # Determine caption based on ranking
        if alcaldia_rank <= total_alcaldias / 2:
            caption = "⚠️ Zona de Alta Criminalidad"
        else:
            caption = "✅ Zona de Baja Criminalidad"
        
        create_kpi_card(
            label="Ranking de Delitos",
            value=f"#{alcaldia_rank}",
            delta=f"de {total_alcaldias}",
            delta_color="neutral",
            caption=caption
        )
    
    with kpi_col2:
        create_kpi_card(
            label="Prom. Delitos / Mes",
            value=format_number(avg_crimes_per_month),
            delta=f"{start_year}-{end_year}",
            delta_color="neutral"
        )
    
    with kpi_col3:
        # Format the YoY change
        delta_text = format_delta_text(
            latest_year_crimes, 
            previous_year_crimes, 
            period_label=f"vs {previous_year}"
        )
        
        # Determine color (inverse because lower crime is better)
        delta_color = "positive" if yoy_change < 0 else "negative" if yoy_change > 0 else "neutral"
        
        create_kpi_card(
            label=f"Total de Delitos ({latest_year})",
            value=format_number(latest_year_crimes),
            delta=delta_text,
            delta_color=delta_color
        )
    
    st.divider()
    
    # ===============================
    # VISUALIZATIONS
    # ===============================
    st.subheader("📈 Visualizaciones Históricas")
    
    # ===============================
    # ROW 1: LINE GRAPH OVER TIME (FULL WIDTH)
    # ===============================
    st.markdown("**Tendencia de Delitos a lo Largo del Tiempo**")
    
    show_breakdown_historical = st.checkbox("Mostrar desglose por violencia", key="violence_breakdown_historical")
    
    if not filtered_alcaldia_df.empty:
        # Aggregate by month
        monthly_crimes = filtered_alcaldia_df.groupby([filtered_alcaldia_df['fecha_hecho'].dt.to_period('M')]).size().reset_index(name='total')
        monthly_crimes['fecha_hecho'] = monthly_crimes['fecha_hecho'].dt.to_timestamp()
        monthly_crimes = monthly_crimes.sort_values('fecha_hecho')
        monthly_crimes['date_label'] = monthly_crimes['fecha_hecho'].dt.strftime('%b %Y')
        
        if show_breakdown_historical:
            # By violence category
            violent_monthly = filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'violent'].groupby(
                filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'violent']['fecha_hecho'].dt.to_period('M')
            ).size().reset_index(name='violent')
            violent_monthly['fecha_hecho'] = violent_monthly['fecha_hecho'].dt.to_timestamp()
            
            non_violent_monthly = filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'non_violent'].groupby(
                filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'non_violent']['fecha_hecho'].dt.to_period('M')
            ).size().reset_index(name='non_violent')
            non_violent_monthly['fecha_hecho'] = non_violent_monthly['fecha_hecho'].dt.to_timestamp()
            
            # Merge
            monthly_crimes = monthly_crimes.merge(violent_monthly, on='fecha_hecho', how='left')
            monthly_crimes = monthly_crimes.merge(non_violent_monthly, on='fecha_hecho', how='left')
            monthly_crimes['violent'] = monthly_crimes['violent'].fillna(0)
            monthly_crimes['non_violent'] = monthly_crimes['non_violent'].fillna(0)
            
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_crimes['date_label'],
                y=monthly_crimes['violent'],
                mode='lines+markers',
                name='Con Violencia',
                line=dict(color='#003d82', width=2.5),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly_crimes['date_label'],
                y=monthly_crimes['non_violent'],
                mode='lines+markers',
                name='Sin Violencia',
                line=dict(color='#6fa8dc', width=2.5),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                xaxis_title="Mes",
                yaxis_title="Número de Delitos",
                hovermode='x unified',
                plot_bgcolor='white',
                height=400,
                margin=dict(l=40, r=40, t=20, b=80),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis=dict(
                    tickangle=-45,
                    showgrid=True,
                    gridcolor='#f0f0f0'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#f0f0f0'
                )
            )
        else:
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_crimes['date_label'],
                y=monthly_crimes['total'],
                mode='lines+markers',
                name='Total de Delitos',
                line=dict(color='#0066CC', width=3),
                marker=dict(size=7)
            ))
            
            fig.update_layout(
                xaxis_title="Mes",
                yaxis_title="Número de Delitos",
                hovermode='x',
                plot_bgcolor='white',
                height=400,
                margin=dict(l=40, r=40, t=20, b=80),
                showlegend=False,
                xaxis=dict(
                    tickangle=-45,
                    showgrid=True,
                    gridcolor='#f0f0f0'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#f0f0f0'
                )
            )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos disponibles para graficar")
    
    st.divider()
    
# ===============================
    # GEOGRAPHIC HEATMAP
    # ===============================
    st.markdown("**Mapa de Zonas Calientes (Hotspots)**")
    
    # Create two columns: stats (left) and map (right)
    map_col_left, map_col_right = st.columns([2, 3])
    
    with map_col_left:
        st.markdown("#### 📊 Resumen de Criminalidad")
        
        if not filtered_alcaldia_df.empty:
            # Calculate metrics
            total_crimes_map = len(filtered_alcaldia_df)
            
            # Weekend vs Weekday
            # Weekend = Saturday (5) and Sunday (6)
            weekend_crimes = len(filtered_alcaldia_df[filtered_alcaldia_df['day_of_week'].isin([5, 6])])
            weekday_crimes = total_crimes_map - weekend_crimes
            weekend_ratio = (weekend_crimes / total_crimes_map * 100) if total_crimes_map > 0 else 0
            weekday_ratio = 100 - weekend_ratio
            
            # Violent vs Non-Violent
            violent_crimes_map = len(filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'violent'])
            non_violent_crimes_map = len(filtered_alcaldia_df[filtered_alcaldia_df['violence_category'] == 'non_violent'])
            violent_ratio_map = (violent_crimes_map / total_crimes_map * 100) if total_crimes_map > 0 else 0
            non_violent_ratio_map = 100 - violent_ratio_map
            
            # Display stats
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #F8F9FA 0%, #ffffff 100%);
                    border-left: 4px solid #0066CC;
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
                ">
                    <div style="font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.3rem;">
                        Total de Delitos
                    </div>
                    <div style="font-size: 2rem; font-weight: 700; color: #0066CC;">
                        {format_number(total_crimes_map)}
                    </div>
                    <div style="font-size: 0.8rem; color: #888; margin-top: 0.2rem;">
                        {start_year} - {end_year}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Weekend vs Weekday Chart
            st.markdown("**📅 Fines de Semana vs Entre Semana**")
            
            import plotly.graph_objects as go
            
            fig_weekend = go.Figure()
            
            fig_weekend.add_trace(go.Bar(
                x=['Entre Semana', 'Fin de Semana'],
                y=[weekday_crimes, weekend_crimes],
                marker=dict(
                    color=['#0066CC', '#6fa8dc'],
                    line=dict(color='white', width=1)
                ),
                text=[f"{weekday_ratio:.1f}%", f"{weekend_ratio:.1f}%"],
                textposition='outside',
                textfont=dict(size=11, weight='bold'),
                hovertemplate='<b>%{x}</b><br>Delitos: %{y:,}<br>Porcentaje: %{text}<extra></extra>',
                showlegend=False
            ))
            
            fig_weekend.update_layout(
                height=180,
                margin=dict(l=10, r=10, t=10, b=40),
                plot_bgcolor='white',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(size=10)
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#f0f0f0',
                    tickfont=dict(size=9)
                )
            )
            
            st.plotly_chart(fig_weekend, use_container_width=True, config={'displayModeBar': False})
            st.caption(f"Entre Semana: **{format_number(weekday_crimes)}** | Fin de Semana: **{format_number(weekend_crimes)}**")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Violent vs Non-Violent Pie Chart
            st.markdown("**🔪 Violentos vs No Violentos**")
            
            fig_violence = go.Figure(data=[go.Pie(
                labels=['No Violentos', 'Violentos'],
                values=[non_violent_crimes_map, violent_crimes_map],
                marker=dict(
                    colors=['#0066CC', '#DC143C'],  # Blue for non-violent, Red for violent
                    line=dict(color='white', width=2)
                ),
                textinfo='percent+label',
                textposition='inside',
                textfont=dict(size=11, color='white', weight='bold'),
                hovertemplate='<b>%{label}</b><br>Delitos: %{value:,}<br>Porcentaje: %{percent}<extra></extra>',
                showlegend=False
            )])
            
            fig_violence.update_layout(
                height=200,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_violence, use_container_width=True, config={'displayModeBar': False})
            st.caption(f"🔵 No Violentos: **{format_number(non_violent_crimes_map)}** | 🔴 Violentos: **{format_number(violent_crimes_map)}**")
            
        else:
            st.info("No hay datos disponibles para este período")
    
    with map_col_right:
        if not filtered_alcaldia_df.empty:
            # Filter data with valid coordinates
            map_crimes = filtered_alcaldia_df.dropna(subset=['latitud', 'longitud']).copy()
            map_crimes = map_crimes[(map_crimes['latitud'] != 0) & (map_crimes['longitud'] != 0)]
            
            if not map_crimes.empty:
                # Toggle for view mode
                view_mode = st.radio(
                    "Modo de Visualización:",
                    options=["Mapa de Calor", "Puntos Individuales"],
                    horizontal=True,
                    key="map_view_toggle"
                )
                
                import pydeck as pdk
                import json
                
                # Calculate center and zoom
                center_lat = map_crimes['latitud'].mean()
                center_lon = map_crimes['longitud'].mean()
                
                # Create layers list
                layers = []
                
                # Add cuadrantes boundaries layer (if available)
                if not cuadrantes_geojson.empty:
                    # Filter cuadrantes for selected alcaldía
                    alcaldia_cuadrantes = cuadrantes_geojson[
                        cuadrantes_geojson['alcaldia_normalized'] == selected_alcaldia
                    ].copy()
                    
                    if not alcaldia_cuadrantes.empty:
                        # Prepare GeoJSON for pydeck - ensure proper format
                        geojson_features = []
                        for idx, row in alcaldia_cuadrantes.iterrows():
                            if row['geo_shape'] is not None:
                                # Convert geo_shape to proper GeoJSON format
                                try:
                                    if isinstance(row['geo_shape'], str):
                                        geometry = json.loads(row['geo_shape'])
                                    elif isinstance(row['geo_shape'], dict):
                                        geometry = row['geo_shape']
                                    else:
                                        continue
                                    
                                    geojson_features.append({
                                        'type': 'Feature',
                                        'geometry': geometry,
                                        'properties': {
                                            'cuadrante': str(row.get('cve_cuad', 'N/A'))
                                        }
                                    })
                                except:
                                    continue
                        
                        if geojson_features:
                            # Create GeoJSON FeatureCollection
                            geojson_data = {
                                'type': 'FeatureCollection',
                                'features': geojson_features
                            }
                            
                            # Layer 1: Transparent blue fill for alcaldía area
                            alcaldia_fill_layer = pdk.Layer(
                                "GeoJsonLayer",
                                data=geojson_data,
                                stroked=False,
                                filled=True,
                                get_fill_color=[0, 102, 204, 30],  # Blue with low opacity
                                pickable=False
                            )
                            layers.append(alcaldia_fill_layer)
                            
                            # Layer 2: Cuadrante boundaries (light gray)
                            cuadrantes_boundaries = pdk.Layer(
                                "GeoJsonLayer",
                                data=geojson_data,
                                stroked=True,
                                filled=False,
                                get_line_color=[150, 150, 150, 120],  # Light gray
                                get_line_width=1,
                                line_width_min_pixels=1,
                                pickable=False
                            )
                            layers.append(cuadrantes_boundaries)
                            
                            # Layer 3: Alcaldía outer boundary (dark blue, thicker)
                            # Create a merged boundary for the entire alcaldía
                            alcaldia_boundary = pdk.Layer(
                                "GeoJsonLayer",
                                data=geojson_data,
                                stroked=True,
                                filled=False,
                                get_line_color=[0, 61, 130, 255],  # Dark blue
                                get_line_width=4,
                                line_width_min_pixels=3,
                                pickable=False
                            )
                            layers.append(alcaldia_boundary)
                
                # Add crime visualization layer
                if view_mode == "Mapa de Calor":
                    # Heatmap layer
                    crime_layer = pdk.Layer(
                        "HeatmapLayer",
                        data=map_crimes[['longitud', 'latitud']].to_dict('records'),
                        get_position='[longitud, latitud]',
                        opacity=0.8,
                        threshold=0.05,
                        radiusPixels=40,
                        colorRange=[
                            [255, 255, 204],  # Light yellow
                            [255, 237, 160],
                            [254, 217, 118],
                            [254, 178, 76],
                            [253, 141, 60],
                            [252, 78, 42],
                            [227, 26, 28],    # Dark red
                            [177, 0, 38]
                        ]
                    )
                else:
                    # Individual points layer - prepare data
                    points_data = map_crimes[['longitud', 'latitud', 'delito', 'fecha_hecho', 'violence_category']].copy()
                    points_data['fecha_hecho'] = points_data['fecha_hecho'].astype(str)
                    points_data_dict = points_data.to_dict('records')
                    
                    crime_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=points_data_dict,
                        get_position='[longitud, latitud]',
                        get_radius=30,
                        get_fill_color='[220, 20, 60, 160]',
                        pickable=True,
                        auto_highlight=True
                    )
                
                layers.append(crime_layer)
                
                # Create deck
                view_state = pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=12,
                    pitch=0,
                    bearing=0
                )
                
                # Tooltip for individual points
                tooltip = None
                if view_mode == "Puntos Individuales":
                    tooltip = {
                        "html": "<b>Delito:</b> {delito}<br/><b>Fecha:</b> {fecha_hecho}<br/><b>Violencia:</b> {violence_category}",
                        "style": {
                            "backgroundColor": "white",
                            "color": "#333",
                            "fontFamily": "Arial, sans-serif",
                            "fontSize": "12px",
                            "padding": "8px"
                        }
                    }
                
                deck = pdk.Deck(
                    layers=layers,
                    initial_view_state=view_state,
                    map_style='mapbox://styles/mapbox/light-v10',
                    tooltip=tooltip
                )
                
                st.pydeck_chart(deck, use_container_width=True, height=400)
                
                # Info caption
                st.caption(f"📍 Mostrando {format_number(len(map_crimes))} delitos en {selected_alcaldia.title()}")
                
            else:
                st.warning("No hay datos con coordenadas válidas para mostrar en el mapa")
        else:
            st.info("No hay datos disponibles para este período")
    


if __name__ == "__main__":
    show()