import streamlit as st
import pandas as pd
import json
import os
os.environ['MAPBOX_API_KEY'] = "pk.eyJ1IjoiYW5keTMxMiIsImEiOiJjbWh0dnljOTUxdDg4Mm5wdnpiYnYxbWhrIn0.p2bRkfMhXBf2V3Gf94gI7w"
from datetime import datetime, timedelta
from supabase import create_client
from components.charts import render_crime_timeline_chart
from components.mckinsey_styling import apply_mckinsey_styles

# ===============================
# Configuration
# ===============================
SUPABASE_URL = "https://xzeycsqwynjxnzgctydr.supabase.co"
SUPABASE_KEY = "sb_publishable_wSTGdAAY_IIuYKNpr6N6GA_rGZy-y29"
SUPABASE_TABLE = "FGJ"

# McKinsey Color Palette
MCKINSEY_COLORS = {
    'primary_blue': '#0066CC',
    'dark_blue': '#003D82',
    'light_blue': '#4D94D9',
    'accent_blue': '#00A3E0',
    'gray_blue': '#6C8CA8',
    'background': '#F8F9FA',
    'card_bg': '#F5F7FA',
    'text': '#2C3E50',
    'text_light': '#5A6C7D',
    'border': '#E1E8ED',
    'grid': '#E8EDF2'
}

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
def estimate_population_from_crimes(df):
    """Fallback: estimate rough population distribution from crime density"""
    CDMX_TOTAL_POP = 9200000
    
    alcaldia_crime_counts = df.groupby('alcaldia_normalized').size()
    total_crimes = alcaldia_crime_counts.sum()
    
    population_by_alcaldia = {}
    for alcaldia, crime_count in alcaldia_crime_counts.items():
        proportion = crime_count / total_crimes
        population_by_alcaldia[alcaldia] = int(CDMX_TOTAL_POP * proportion)
    
    return population_by_alcaldia

def format_number(num):
    """Format large numbers with commas"""
    return f"{int(num):,}"

def format_percentage(num):
    """Format percentage with + or - sign"""
    sign = "+" if num > 0 else ""
    return f"{sign}{num:.1f}%"


# Spanish day and month names
DAY_NAMES_ES = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado',
    6: 'Domingo'
}

MONTH_NAMES_ES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre'
}

# ===============================
# Main Dashboard Function
# ===============================
def show():
    # Apply McKinsey styling from library
    apply_mckinsey_styles()
    
    # Apply additional custom styling
    st.markdown(f"""
        <style>
        /* Import professional font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global styling */
        .main {{
            background-color: white;
        }}
        
        /* Title styling */
        h1 {{
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 2.2rem !important;
            margin-bottom: 0.3rem !important;
        }}
        
        /* Subtitle styling */
        .subtitle {{
            color: var(--text-color); opacity: 0.7;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            margin-bottom: 1.5rem;
            font-weight: 400;
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: {MCKINSEY_COLORS['background']};
        }}
        
        [data-testid="stSidebar"] h3 {{
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            border-bottom: 2px solid {MCKINSEY_COLORS['primary_blue']};
            padding-bottom: 0.5rem;
            margin-bottom: 1rem !important;
        }}
        
        /* Filters container styling */
        .filters-container {{
            background: var(--secondary-background-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border: 1px solid {MCKINSEY_COLORS['border']};
        }}
        
        /* KPI Card Styling */
        .kpi-card {{
            background: var(--secondary-background-color);
            border-left: 3px solid {MCKINSEY_COLORS['primary_blue']};
            border-radius: 8px;
            padding: 1rem 1.2rem;
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
            margin-bottom: 0.5rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 102, 204, 0.12);
        }}
        
        .kpi-label {{
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            color: var(--text-color); opacity: 0.7;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.3rem;
        }}
        
        .kpi-value {{
            font-family: 'Inter', sans-serif;
            font-size: 1.8rem;
            color: var(--text-color);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.2rem;
        }}
        
        .kpi-delta {{
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 0.2rem;
        }}
        
        .kpi-caption {{
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            color: var(--text-color); opacity: 0.7;
            margin-top: 0.2rem;
        }}
        
        /* Section headers */
        h3 {{
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.8rem !important;
            border-bottom: 2px solid {MCKINSEY_COLORS['primary_blue']};
            padding-bottom: 0.4rem;
        }}
        
        /* Radio buttons styling */
        .stRadio > div {{
            background-color: {MCKINSEY_COLORS['background']};
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }}
        
        /* Metric styling override */
        [data-testid="stMetricValue"] {{
            font-size: 1.8rem;
            color: var(--text-color);
            font-weight: 700;
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: 0.8rem;
            color: var(--text-color); opacity: 0.7;
            font-weight: 500;
        }}
        
        /* Compact metrics section */
        .metrics-container {{
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }}
        
        /* Divider styling */
        hr {{
            margin: 1rem 0;
            border-color: {MCKINSEY_COLORS['border']};
        }}
        
        /* Button styling */
        .stButton > button {{
            background-color: {MCKINSEY_COLORS['primary_blue']};
            color: white;
            border: none;
            border-radius: 6px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            transition: background-color 0.2s ease;
        }}
        
        .stButton > button:hover {{
            background-color: var(--text-color);
        }}
        
        /* Expander styling */
        .streamlit-expanderHeader {{
            font-family: 'Inter', sans-serif;
            color: var(--text-color);
            font-weight: 500;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.title("📈 Panel de Análisis de Delitos CDMX")
    st.markdown(f'<p class="subtitle">Comprehensive overview of crime trends across Mexico City</p>', unsafe_allow_html=True)
    
    # Load data
    df = load_crime_data()
    population_data = load_population_data()
    
    if population_data is None:
        population_data = estimate_population_from_crimes(df)
    
    if df.empty:
        st.warning("No hay datos disponibles")
        st.stop()
    
    # ===============================
    # GET AVAILABLE YEARS
    # ===============================
    available_years = sorted([int(y) for y in df['year'].unique() if pd.notna(y)])
    
    if not available_years:
        st.error("No hay datos de año válidos disponibles")
        st.stop()
    
    min_year = min(available_years)
    max_year = max(available_years)
    
    # ===============================
    # INITIALIZE SESSION STATE
    # ===============================
    if 'year_range' not in st.session_state:
        st.session_state.year_range = (max_year - 1 if max_year > min_year else min_year, max_year)
    if 'violence_filter' not in st.session_state:
        st.session_state.violence_filter = "Todos los Delitos"
    if 'measurement_type' not in st.session_state:
        st.session_state.measurement_type = "Cantidad Total"
    if 'composition_type' not in st.session_state:
        st.session_state.composition_type = "Delitos Totales"
    if 'breakdown_option' not in st.session_state:
        st.session_state.breakdown_option = "Delitos Totales"
    
    
    # ===============================
    # SIDEBAR FILTERS (Multi-page compatible)
    # ===============================
    # Add spacing after page navigation
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Filtros")
    
    # Year range slider in sidebar
    sidebar_year_range = st.sidebar.slider(
        "📅 Rango de Años",
        min_value=min_year,
        max_value=max_year,
        value=st.session_state.year_range,
        step=1,
        format="%d",
        help=f"Select a continuous range from {min_year} to {max_year}",
        key='sidebar_year_slider'
    )
    # Update session state
    if sidebar_year_range != st.session_state.year_range:
        st.session_state.year_range = sidebar_year_range
        st.rerun()
    
    start_year_sidebar, end_year_sidebar = sidebar_year_range
    
    # Display selected range
    if start_year_sidebar == end_year_sidebar:
        st.sidebar.caption(f"📊 Analyzing: **{start_year_sidebar}**")
    else:
        st.sidebar.caption(f"📊 Analyzing: **{start_year_sidebar} to {end_year_sidebar}** ({end_year_sidebar - start_year_sidebar + 1} years)")
    
    st.sidebar.markdown("---")
    
    # Violence filter in sidebar
    violence_options = ["Todos los Delitos", "Solo Violentos", "Solo No Violentos"]
    sidebar_violence = st.sidebar.selectbox(
        "🔪 Tipo de Delito",
        options=violence_options,
        index=violence_options.index(st.session_state.violence_filter),
        key='sidebar_violence_select'
    )
    # Update session state
    if sidebar_violence != st.session_state.violence_filter:
        st.session_state.violence_filter = sidebar_violence
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Refresh button in sidebar
    if st.sidebar.button("🔄 Actualizar Datos", use_container_width=True, key='sidebar_refresh'):
        st.cache_data.clear()
        st.rerun()
    
    # Info section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Acerca de")
    st.sidebar.markdown("""
    This dashboard provides real-time analytics on crime trends across Mexico City's alcaldías.
    
    **Data Source:** FGJ (Fiscalía General de Justicia)
    
    **Last Updated:** Real-time
    """)
    
    # ===============================
    # TOP FILTERS (Synchronized)
    # ===============================
    st.markdown('<div class="filters-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        top_year_range = st.slider(
            "📅 Selecciona Rango de Años",
            min_value=min_year,
            max_value=max_year,
            value=st.session_state.year_range,
            step=1,
            format="%d",
            help=f"Select a continuous range from {min_year} to {max_year}",
            key='top_year_slider'
        )
        # Update session state
        if top_year_range != st.session_state.year_range:
            st.session_state.year_range = top_year_range
            st.rerun()
        
        start_year, end_year = st.session_state.year_range
    
    with col2:
        top_violence = st.selectbox(
            "🔪 Tipo de Delito",
            options=violence_options,
            index=violence_options.index(st.session_state.violence_filter),
            key='top_violence_select'
        )
        # Update session state
        if top_violence != st.session_state.violence_filter:
            st.session_state.violence_filter = top_violence
            st.rerun()
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True, key='top_refresh'):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Filter data by year range
    start_year, end_year = st.session_state.year_range
    violence_filter = st.session_state.violence_filter
    
    filtered_df = df[(df['year'] >= start_year) & (df['year'] <= end_year)].copy()
    
    if violence_filter == "Solo Violentos":
        filtered_df = filtered_df[filtered_df['violence_category'] == 'violent']
    elif violence_filter == "Solo No Violentos":
        filtered_df = filtered_df[filtered_df['violence_category'] == 'non_violent']
    
    # ===============================
    # CALCULATE METRICS
    # ===============================
    total_crimes_current = len(filtered_df)
    
    latest_year = end_year
    previous_year = latest_year - 1
    
    latest_df = filtered_df[filtered_df['year'] == latest_year]
    total_crimes_latest = len(latest_df)
    
    previous_df = df[(df['year'] == previous_year)]
    if violence_filter == "Solo Violentos":
        previous_df = previous_df[previous_df['violence_category'] == 'violent']
    elif violence_filter == "Solo No Violentos":
        previous_df = previous_df[previous_df['violence_category'] == 'non_violent']
    total_crimes_previous = len(previous_df)
    
    if total_crimes_previous > 0:
        yoy_change = ((total_crimes_latest - total_crimes_previous) / total_crimes_previous) * 100
    else:
        yoy_change = 0
    
    violent_count = len(filtered_df[filtered_df['violence_category'] == 'violent'])
    violent_pct = (violent_count / total_crimes_current * 100) if total_crimes_current > 0 else 0
    
    alcaldia_counts = filtered_df.groupby('alcaldia_normalized').size().sort_values(ascending=False)
    most_dangerous_alcaldia = alcaldia_counts.index[0] if len(alcaldia_counts) > 0 else "N/A"
    most_dangerous_count = alcaldia_counts.iloc[0] if len(alcaldia_counts) > 0 else 0
    
    if total_crimes_current > 0:
        filtered_df['year_month'] = filtered_df['fecha_hecho'].dt.to_period('M')
        unique_months = filtered_df['year_month'].nunique()
        avg_crimes_per_month = total_crimes_current / unique_months if unique_months > 0 else 0
    else:
        avg_crimes_per_month = 0
    
    # ===============================
    # KPI CARDS (Custom Styled)
    # ===============================
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    years_text = f"{start_year}-{end_year}" if start_year != end_year else str(start_year)
    
    with kpi1:
        delta_color = "🔴" if yoy_change > 0 else "🟢"
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Total Crimes</div>
                <div class="kpi-value">{format_number(total_crimes_current)}</div>
                <div class="kpi-delta">{delta_color} {format_percentage(yoy_change)}</div>
                <div class="kpi-caption">in {years_text} (YoY: {latest_year} vs {previous_year})</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Avg Crimes/Month</div>
                <div class="kpi-value">{format_number(avg_crimes_per_month)}</div>
                <div class="kpi-caption">average per month ({years_text})</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Violent Crimes</div>
                <div class="kpi-value">{violent_pct:.1f}%</div>
                <div class="kpi-delta">{format_number(violent_count)} incidents</div>
                <div class="kpi-caption">of all crimes ({years_text})</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Highest Crime</div>
                <div class="kpi-value">{most_dangerous_alcaldia.title()}</div>
                <div class="kpi-delta">{format_number(most_dangerous_count)} crimes</div>
                <div class="kpi-caption">most active alcaldía ({years_text})</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===============================
    # VISUALIZATION: CRIMES OVER TIME
    # ===============================
    st.markdown("### 📈 Tendencias Delictivas a lo Largo del Tiempo")
    
    breakdown_option = st.radio(
        "Ver por:",
        options=["Delitos Totales", "Desglose por Violencia"],
        horizontal=True,
        label_visibility="collapsed",
        index=["Delitos Totales", "Desglose por Violencia"].index(st.session_state.breakdown_option),
        key='breakdown_radio'
    )
    if breakdown_option != st.session_state.breakdown_option:
        st.session_state.breakdown_option = breakdown_option
        st.rerun()
    
    if breakdown_option == "Delitos Totales":
        time_series = filtered_df.groupby(filtered_df['fecha_hecho'].dt.to_period('M')).size().reset_index()
        time_series.columns = ['month', 'crimes']
        time_series['month'] = time_series['month'].dt.to_timestamp()
        
        chart_data = [{
            'date': row['month'].strftime('%Y-%m-%d'),
            'value': int(row['crimes']),
            'label': 'Total Crimes'
        } for _, row in time_series.iterrows()]
        
        mode = 'single'
        
    else:
        time_series_breakdown = filtered_df.groupby([
            filtered_df['fecha_hecho'].dt.to_period('M'),
            'violence_category'
        ]).size().reset_index()
        time_series_breakdown.columns = ['month', 'category', 'crimes']
        time_series_breakdown['month'] = time_series_breakdown['month'].dt.to_timestamp()
        
        time_series_breakdown = time_series_breakdown[
            time_series_breakdown['category'].isin(['violent', 'non_violent'])
        ]
        
        chart_data = [{
            'date': row['month'].strftime('%Y-%m-%d'),
            'value': int(row['crimes']),
            'category': row['category']
        } for _, row in time_series_breakdown.iterrows()]
        
        mode = 'breakdown'
    
    chart_html = render_crime_timeline_chart(chart_data, mode)
    st.components.v1.html(chart_html, height=550)
    
    st.markdown("---")
    
    # ===============================
    # VISUALIZATION: INSIGHTS & HEATMAP
    # ===============================
    st.markdown("### 🔍 Análisis de Patrones Temporales")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("#### 💡 Puntos Clave")
        
        # Generate automated insights
        insights = []
        
        # 1. YoY Trend
        if yoy_change > 10:
            insights.append({
                'icon': '⚠️',
                'text': f'Los delitos aumentaron significativamente en {format_percentage(yoy_change)} comparado con {previous_year}',
                'color': '#dc3545'
            })
        elif yoy_change < -10:
            insights.append({
                'icon': '✅',
                'text': f'Los delitos disminuyeron en {format_percentage(yoy_change)} comparado con {previous_year}',
                'color': '#28a745'
            })
        else:
            insights.append({
                'icon': '➡️',
                'text': f'Las tasas de delito se mantuvieron estables ({format_percentage(yoy_change)}) vs {previous_year}',
                'color': MCKINSEY_COLORS['gray_blue']
            })
        
        # 2. Peak Hour Analysis
        if not filtered_df.empty and 'hour' in filtered_df.columns:
            # Filter out null hours
            valid_hours_df = filtered_df[filtered_df['hour'].notna()]
            if not valid_hours_df.empty:
                hourly_crimes = valid_hours_df.groupby('hour').size()
                if not hourly_crimes.empty:
                    peak_hour = int(hourly_crimes.idxmax())
                    peak_hour_count = hourly_crimes.max()
                    insights.append({
                        'icon': '🕐',
                        'text': f'Hora pico de delitos: {peak_hour:02d}:00-{(peak_hour+1)%24:02d}:00 ({format_number(peak_hour_count)} incidents)',
                        'color': MCKINSEY_COLORS['primary_blue']
                    })
        
        # 3. Peak Day Analysis
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        daily_crimes = filtered_df.groupby('day_of_week').size()
        if not daily_crimes.empty:
            peak_day_num = daily_crimes.idxmax()
            peak_day_name = day_names[int(peak_day_num)]
            peak_day_count = daily_crimes.max()
            insights.append({
                'icon': '📅',
                'text': f'{peak_day_name}s are most dangerous ({format_number(peak_day_count)} incidents)',
                'color': MCKINSEY_COLORS['primary_blue']
            })
        
        # 4. Violence Ratio
        if violent_pct > 60:
            insights.append({
                'icon': '🔴',
                'text': f'Alta tasa de violencia: {violent_pct:.1f}% de los delitos son violentos',
                'color': '#dc3545'
            })
        elif violent_pct < 30:
            insights.append({
                'icon': '🟢',
                'text': f'Baja tasa de violencia: Solo {violent_pct:.1f}% de los delitos son violentos',
                'color': '#28a745'
            })
        else:
            insights.append({
                'icon': '🟡',
                'text': f'Tasa de violencia moderada: {violent_pct:.1f}% de los delitos son violentos',
                'color': MCKINSEY_COLORS['accent_blue']
            })
        
        # 5. Alcaldía Concentration
        if len(alcaldia_counts) >= 3:
            top_3_crimes = alcaldia_counts.head(3).sum()
            concentration_pct = (top_3_crimes / total_crimes_current * 100) if total_crimes_current > 0 else 0
            if concentration_pct > 50:
                insights.append({
                    'icon': '⚡',
                    'text': f'{concentration_pct:.0f}% of crimes concentrated in top 3 alcaldías',
                    'color': MCKINSEY_COLORS['accent_blue']
                })
        
        # 6. Monthly Average
        if avg_crimes_per_month > 0:
            insights.append({
                'icon': '📊',
                'text': f'Promedio de {format_number(avg_crimes_per_month)} delitos por mes',
                'color': MCKINSEY_COLORS['gray_blue']
            })
        
        # Display insights in styled cards
        for insight in insights[:6]:  # Show up to 6 insights
            st.markdown(f"""
                <div style="
                    background: var(--secondary-background-color);
                    border-left: 4px solid {insight['color']};
                    border-radius: 6px;
                    padding: 0.9rem 1rem;
                    margin-bottom: 0.7rem;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
                    font-family: 'Inter', sans-serif;
                ">
                    <span style="font-size: 1.3rem; margin-right: 0.5rem;">{insight['icon']}</span>
                    <span style="color: var(--text-color); font-size: 0.9rem;">{insight['text']}</span>
                </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("#### 🗓️ Mapa de Calor de Delitos: Día × Hora")
        
        # Prepare heatmap data
        if not filtered_df.empty and 'hour' in filtered_df.columns:
            # Filter out rows with no hour data
            valid_heatmap_df = filtered_df[filtered_df['hour'].notna()].copy()
            
            if not valid_heatmap_df.empty:
                # Create pivot table for heatmap
                heatmap_data = valid_heatmap_df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
                heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)
                
                # Reindex to ensure all hours and days are present
                heatmap_pivot = heatmap_pivot.reindex(index=range(7), columns=range(24), fill_value=0)
                
                # Map day numbers to names
                day_labels = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                heatmap_pivot.index = [day_labels[int(i)] for i in heatmap_pivot.index]
                
                # Create Plotly heatmap
                import plotly.graph_objects as go

                fig = go.Figure(data=go.Heatmap(
                    z=heatmap_pivot.values,
                    x=[f"{h:02d}:00" for h in range(24)],
                    y=heatmap_pivot.index,
                    colorscale=[
                        [0, '#E8F4F8'],      # Very light blue
                        [0.2, '#B3D9E8'],    # Light blue
                        [0.4, '#7DB8D6'],    # Medium light blue
                        [0.6, MCKINSEY_COLORS['light_blue']],
                        [0.8, MCKINSEY_COLORS['primary_blue']],
                        [1, MCKINSEY_COLORS['dark_blue']]
                    ],
                    hovertemplate='<b>%{y}</b><br>Hour: %{x}<br>Crimes: %{z}<extra></extra>',
                    colorbar=dict(
                        title=dict(text="Delitos", font=dict(family='Inter', size=12)),
                        thickness=15,
                        len=0.7,
                        tickfont=dict(family='Inter', size=10)
                    )
                ))
                
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family='Inter', color=MCKINSEY_COLORS['text']),
                    xaxis=dict(
                        title=dict(text='Hour of Day', font=dict(size=12, family='Inter')),
                        showgrid=False,
                        side='bottom',
                        tickfont=dict(size=9)
                    ),
                    yaxis=dict(
                        title=dict(text='Day of Week', font=dict(size=12, family='Inter')),
                        showgrid=False,
                        tickfont=dict(size=10)
                    ),
                    margin=dict(l=80, r=20, t=20, b=60),
                    height=450
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                # Show data quality note
                total_with_hour = len(valid_heatmap_df)
                total_filtered = len(filtered_df)
                coverage_pct = (total_with_hour / total_filtered * 100) if total_filtered > 0 else 0
                st.caption(f"📊 Mostrando {format_number(total_with_hour)} delitos con datos de tiempo ({coverage_pct:.1f}% de los datos filtrados)")
            else:
                st.info("No hay datos de tiempo disponibles para los filtros seleccionados")
        else:
            st.info("Datos de hora no disponibles en el conjunto de datos")
    
    st.markdown("---")
    st.markdown("---")
    
    # ===============================
    # VISUALIZATION: CRIME BY ALCALDÍA
    # ===============================
    st.markdown("### 🏙️ Distribución de Delitos por Alcaldía")
    
    # Create two columns: chart on left, stats on right
    chart_col, stats_col = st.columns([2, 1])
    
    with chart_col:
        # Toggle controls
        toggle_col1, toggle_col2 = st.columns(2)
        
        with toggle_col1:
            measurement_type = st.radio(
                "Medición:",
                options=["Cantidad Total", "Per Cápita (por 100k)"],
                horizontal=True,
                index=["Cantidad Total", "Per Cápita (por 100k)"].index(st.session_state.measurement_type),
                key='measurement_toggle'
            )
            if measurement_type != st.session_state.measurement_type:
                st.session_state.measurement_type = measurement_type
                st.rerun()
        
        with toggle_col2:
            composition_type = st.radio(
                "Composición:",
                options=["Delitos Totales", "Desglose por Violencia"],
                horizontal=True,
                index=["Delitos Totales", "Desglose por Violencia"].index(st.session_state.composition_type),
                key='composition_toggle'
            )
            if composition_type != st.session_state.composition_type:
                st.session_state.composition_type = composition_type
                st.rerun()
        
        # Prepare data based on composition type
        if composition_type == "Delitos Totales":
            # Simple aggregation
            alcaldia_stats = filtered_df.groupby('alcaldia_normalized').size().reset_index(name='crimes')
            
            # Add population data if needed
            if measurement_type == "Per Cápita (por 100k)" and population_data:
                alcaldia_stats['population'] = alcaldia_stats['alcaldia_normalized'].map(population_data)
                alcaldia_stats['value'] = (alcaldia_stats['crimes'] / alcaldia_stats['population'] * 100000).round(1)
                alcaldia_stats = alcaldia_stats.dropna(subset=['value'])
            else:
                alcaldia_stats['value'] = alcaldia_stats['crimes']
            
            # Sort and prepare for plotting
            alcaldia_stats = alcaldia_stats.sort_values('value', ascending=True)
            
            # Create simple bar chart
            import plotly.graph_objects as go
            
            fig = go.Figure(data=[
                go.Bar(
                    y=alcaldia_stats['alcaldia_normalized'].str.title(),
                    x=alcaldia_stats['value'],
                    orientation='h',
                    marker=dict(
                        color=alcaldia_stats['value'],
                        colorscale=[
                            [0, MCKINSEY_COLORS['light_blue']],
                            [0.5, MCKINSEY_COLORS['primary_blue']],
                            [1, MCKINSEY_COLORS['dark_blue']]
                        ],
                        showscale=False
                    ),
                    hovertemplate='<b>%{y}</b><br>Value: %{x:,.1f}<extra></extra>',
                    text=alcaldia_stats['value'],
                    texttemplate='%{text:,.0f}' if measurement_type == "Cantidad Total" else '%{text:,.1f}',
                    textposition='outside',
                    textfont=dict(size=9, family='Inter')
                )
            ])
            
        else:  # Violence Breakdown
            # Aggregate by alcaldia and violence category
            alcaldia_violence = filtered_df.groupby(['alcaldia_normalized', 'violence_category']).size().reset_index(name='crimes')
            
            # Pivot to get violent and non-violent columns
            alcaldia_pivot = alcaldia_violence.pivot(
                index='alcaldia_normalized', 
                columns='violence_category', 
                values='crimes'
            ).fillna(0)
            
            # Ensure both columns exist
            if 'violent' not in alcaldia_pivot.columns:
                alcaldia_pivot['violent'] = 0
            if 'non_violent' not in alcaldia_pivot.columns:
                alcaldia_pivot['non_violent'] = 0
            
            alcaldia_pivot['total'] = alcaldia_pivot['violent'] + alcaldia_pivot['non_violent']
            alcaldia_pivot = alcaldia_pivot.reset_index()
            
            # Add population data if needed
            if measurement_type == "Per Cápita (por 100k)" and population_data:
                alcaldia_pivot['population'] = alcaldia_pivot['alcaldia_normalized'].map(population_data)
                alcaldia_pivot['violent_value'] = (alcaldia_pivot['violent'] / alcaldia_pivot['population'] * 100000).round(1)
                alcaldia_pivot['non_violent_value'] = (alcaldia_pivot['non_violent'] / alcaldia_pivot['population'] * 100000).round(1)
                alcaldia_pivot['total_value'] = alcaldia_pivot['violent_value'] + alcaldia_pivot['non_violent_value']
                alcaldia_pivot = alcaldia_pivot.dropna(subset=['population'])
            else:
                alcaldia_pivot['violent_value'] = alcaldia_pivot['violent']
                alcaldia_pivot['non_violent_value'] = alcaldia_pivot['non_violent']
                alcaldia_pivot['total_value'] = alcaldia_pivot['total']
            
            # Sort by total
            alcaldia_pivot = alcaldia_pivot.sort_values('total_value', ascending=True)
            
            # Create stacked bar chart
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            # Non-violent crimes (bottom)
            fig.add_trace(go.Bar(
                y=alcaldia_pivot['alcaldia_normalized'].str.title(),
                x=alcaldia_pivot['non_violent_value'],
                name='No Violentos',
                orientation='h',
                marker=dict(color=MCKINSEY_COLORS['light_blue']),
                hovertemplate='<b>%{y}</b><br>Non-Violent: %{x:,.1f}<extra></extra>',
                text=alcaldia_pivot['non_violent_value'],
                texttemplate='%{text:,.0f}' if measurement_type == "Cantidad Total" else '%{text:,.1f}',
                textposition='inside',
                textfont=dict(size=8, family='Inter', color='white')
            ))
            
            # Violent crimes (top)
            fig.add_trace(go.Bar(
                y=alcaldia_pivot['alcaldia_normalized'].str.title(),
                x=alcaldia_pivot['violent_value'],
                name='Violentos',
                orientation='h',
                marker=dict(color=MCKINSEY_COLORS['dark_blue']),
                hovertemplate='<b>%{y}</b><br>Violent: %{x:,.1f}<extra></extra>',
                text=alcaldia_pivot['violent_value'],
                texttemplate='%{text:,.0f}' if measurement_type == "Cantidad Total" else '%{text:,.1f}',
                textposition='inside',
                textfont=dict(size=8, family='Inter', color='white')
            ))
            
            fig.update_layout(barmode='stack')
        
        # Common layout settings
        x_title = "Number of Crimes" if measurement_type == "Cantidad Total" else "Crime Rate (per 100,000 residents)"
        
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter', color=MCKINSEY_COLORS['text']),
            xaxis=dict(
                title=dict(text=x_title, font=dict(size=11, family='Inter')),
                showgrid=True,
                gridcolor=MCKINSEY_COLORS['grid'],
                tickfont=dict(size=9)
            ),
            yaxis=dict(
                title=None,
                showgrid=False,
                tickfont=dict(size=9)
            ),
            margin=dict(l=100, r=40, t=10, b=50),
            height=550,
            showlegend=(composition_type == "Desglose por Violencia"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10, family='Inter')
            )
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    with stats_col:
        # Calculate stats for display
        if composition_type == "Delitos Totales":
            display_stats = alcaldia_stats.copy()
        else:
            display_stats = alcaldia_pivot[['alcaldia_normalized', 'total', 'total_value']].rename(
                columns={'total': 'crimes', 'total_value': 'value'}
            )
        
        st.markdown("#### 🔴 Mayor Delincuencia")
        top_5 = display_stats.sort_values('crimes', ascending=False).head(5)
        for idx, row in top_5.iterrows():
            pct = (row['crimes'] / total_crimes_current * 100) if total_crimes_current > 0 else 0
            st.markdown(f"""
                <div style="
                    background: var(--secondary-background-color);
                    border-radius: 6px;
                    padding: 0.6rem 0.8rem;
                    margin-bottom: 0.4rem;
                    font-family: 'Inter', sans-serif;
                ">
                    <span style="font-weight: 600; color: var(--text-color); font-size: 0.9rem;">
                        {row['alcaldia_normalized'].title()}
                    </span><br>
                    <span style="font-size: 0.8rem; color: var(--text-color); opacity: 0.7;">
                        {format_number(row['crimes'])} crimes ({pct:.1f}%)
                    </span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("#### 🟢 Menor Delincuencia")
        bottom_5 = display_stats.sort_values('crimes', ascending=True).head(5)
        for idx, row in bottom_5.iterrows():
            pct = (row['crimes'] / total_crimes_current * 100) if total_crimes_current > 0 else 0
            st.markdown(f"""
                <div style="
                    background: var(--secondary-background-color);
                    border-radius: 6px;
                    padding: 0.6rem 0.8rem;
                    margin-bottom: 0.4rem;
                    font-family: 'Inter', sans-serif;
                ">
                    <span style="font-weight: 600; color: var(--text-color); font-size: 0.9rem;">
                        {row['alcaldia_normalized'].title()}
                    </span><br>
                    <span style="font-size: 0.8rem; color: var(--text-color); opacity: 0.7;">
                        {format_number(row['crimes'])} crimes ({pct:.1f}%)
                    </span>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    


    # ===============================
    # AGENCIAS MAP SECTION
    # ===============================
    st.markdown("---")
    st.markdown("### 🏛️ Mapa de Agencias y Delitos Reportados")

    # Your Mapbox token
    MAPBOX_TOKEN = "pk.eyJ1IjoiYW5keTMxMiIsImEiOiJjbWh0dnljOTUxdDg4Mm5wdnpiYnYxbWhrIn0.p2bRkfMhXBf2V3Gf94gI7w"

    # Load agencias data
    @st.cache_data
    def load_agencias_geocoded():
        """Load geocoded agencias from CSV"""
        try:
            agencias_df = pd.read_csv('agencias_geocoded.csv')
            agencias_df = agencias_df.dropna(subset=['latitud', 'longitud'])
            agencias_df['agencia_normalized'] = agencias_df['agencia'].apply(normalize_alcaldia_name)
            return agencias_df
        except FileNotFoundError:
            st.error("❌ Archivo 'agencias_geocoded.csv' no encontrado.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading agencias: {e}")
            return pd.DataFrame()

    # Load crime data with agencia field
    @st.cache_data(ttl=3600)
    def load_crime_data_with_agencia():
        """Load crime data including agencia field"""
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            response = supabase.table(SUPABASE_TABLE).select(
                "alcaldia_hecho, anio_hecho, fecha_hecho, agencia, delito, latitud, longitud"
            ).execute()
            
            df = pd.DataFrame(response.data)
            if df.empty:
                return df
            
            df['fecha_hecho'] = pd.to_datetime(df['fecha_hecho'], errors='coerce')
            df['year'] = df['fecha_hecho'].dt.year
            df['agencia_normalized'] = df['agencia'].apply(normalize_alcaldia_name)
            df = df.dropna(subset=['latitud', 'longitud'])
            df = df[(df['latitud'] != 0) & (df['longitud'] != 0)]
            
            return df
        except Exception as e:
            st.error(f"Error loading crime data: {e}")
            return pd.DataFrame()

    agencias_df = load_agencias_geocoded()
    crime_df_agencia = load_crime_data_with_agencia()

    if agencias_df.empty:
        st.warning("⚠️ No hay datos de agencias disponibles")
    else:
        # Get unique agencias from crimes database (excluding NaN)
        crime_agencias_with_names = crime_df_agencia[
            crime_df_agencia['agencia'].notna() & 
            (crime_df_agencia['agencia'] != '') &
            (crime_df_agencia['agencia'] != 'nan')
        ].copy()
        
        # Get unique agencia names and normalized names from crimes
        unique_crime_agencias = crime_agencias_with_names[['agencia', 'agencia_normalized']].drop_duplicates()
        
        # Match with coordinates from agencias_geocoded
        agencias_with_crimes = agencias_df.merge(
            unique_crime_agencias,
            on='agencia_normalized',
            how='inner'  # Only keep agencias that have both coordinates AND crimes
        )
        
        # Remove duplicates in case there are any
        agencias_with_crimes = agencias_with_crimes.drop_duplicates(subset=['agencia_normalized'])
        
        # Add crime counts to agencias
        agencia_crime_counts = crime_agencias_with_names.groupby('agencia_normalized').size().reset_index(name='crime_count')
        agencias_with_crimes = agencias_with_crimes.merge(agencia_crime_counts, on='agencia_normalized', how='left')
        agencias_with_crimes['crime_count'] = agencias_with_crimes['crime_count'].fillna(0).astype(int)
        
        st.caption(f"📍 Mostrando {len(agencias_with_crimes)} agencias con delitos registrados y coordenadas válidas")
        
        # Initialize session state for selected agencia
        if 'selected_agencia_map' not in st.session_state:
            st.session_state.selected_agencia_map = None
        
        # Controls row
        control_col1, control_col2, control_col3 = st.columns([2, 2, 1])
        
        with control_col1:
            # Dropdown menu for agencia selection (only agencias with valid names from crime database)
            agencia_options = ['Ninguna (Ver todas)'] + sorted(
                agencias_with_crimes['agencia_x'].tolist()  # Use agencia_x from the merge
            )
            
            # Find current index
            if st.session_state.selected_agencia_map:
                matching_agencia = agencias_with_crimes[
                    agencias_with_crimes['agencia_normalized'] == st.session_state.selected_agencia_map
                ]
                if not matching_agencia.empty:
                    current_index = agencia_options.index(matching_agencia.iloc[0]['agencia_x'])
                else:
                    current_index = 0
            else:
                current_index = 0
            
            selected_agencia_name = st.selectbox(
                "🏛️ Seleccionar Agencia",
                options=agencia_options,
                index=current_index,
                key="agencia_dropdown",
                help="Selecciona una agencia para ver sus delitos reportados"
            )
            
            # Update session state based on selection
            if selected_agencia_name == 'Ninguna (Ver todas)':
                if st.session_state.selected_agencia_map is not None:
                    st.session_state.selected_agencia_map = None
                    st.rerun()
            else:
                new_selection = agencias_with_crimes[
                    agencias_with_crimes['agencia_x'] == selected_agencia_name
                ]['agencia_normalized'].iloc[0]
                if st.session_state.selected_agencia_map != new_selection:
                    st.session_state.selected_agencia_map = new_selection
                    st.rerun()
        
        with control_col2:
            # View mode toggle (only shown when agencia is selected)
            if st.session_state.selected_agencia_map:
                view_mode = st.radio(
                    "Visualización de Delitos:",
                    options=["Mapa de Calor", "Puntos", "Hexágonos"],
                    horizontal=True,
                    key="agencia_view_mode",
                    help="Cambia cómo se visualizan los delitos en el mapa"
                )
            else:
                view_mode = "Mapa de Calor"
                st.info("👆 Selecciona una agencia para ver los delitos")
        
        with control_col3:
            # Clear selection button
            if st.session_state.selected_agencia_map:
                if st.button("✕ Limpiar", use_container_width=True, key="clear_agencia_selection"):
                    st.session_state.selected_agencia_map = None
                    st.rerun()
        
        # Filter crimes by year range (respecting dashboard filters) - only crimes with valid agencia names
        filtered_crime_df = crime_df_agencia[
            (crime_df_agencia['year'] >= start_year) &
            (crime_df_agencia['year'] <= end_year) &
            (crime_df_agencia['agencia'].notna()) &
            (crime_df_agencia['agencia'] != '') &
            (crime_df_agencia['agencia'] != 'nan')
        ]
        
        # Info panel for selected agencia
        if st.session_state.selected_agencia_map:
            selected_agencia_info = agencias_with_crimes[
                agencias_with_crimes['agencia_normalized'] == st.session_state.selected_agencia_map
            ].iloc[0]
            
            # Filter crimes by selected agencia
            selected_crimes = filtered_crime_df[
                filtered_crime_df['agencia_normalized'] == st.session_state.selected_agencia_map
            ]
            
            # Get agencia name (use agencia_x from merge, which is from crimes database)
            agencia_display_name = selected_agencia_info['agencia_x']
            
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {MCKINSEY_COLORS['background']} 0%, #ffffff 100%);
                    border-left: 4px solid {MCKINSEY_COLORS['primary_blue']};
                    border-radius: 8px;
                    padding: 1rem 1.5rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: {MCKINSEY_COLORS['primary_blue']}; font-family: 'Inter', sans-serif;">
                                🏛️ {agencia_display_name}
                            </h4>
                            <p style="margin: 0.3rem 0 0 0; color: {MCKINSEY_COLORS['text_light']}; font-size: 0.9rem;">
                                📍 {selected_agencia_info['direccion']}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2rem; font-weight: 700; color: {MCKINSEY_COLORS['primary_blue']};">
                                {format_number(len(selected_crimes))}
                            </div>
                            <div style="font-size: 0.8rem; color: {MCKINSEY_COLORS['text_light']};">
                                delitos ({start_year}-{end_year})
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            selected_crimes = pd.DataFrame()
        
        # Build the map using PyDeck
        import pydeck as pdk
        
        # Prepare agencia markers data
        agencias_layer_data = agencias_with_crimes.copy()
        
        # Determine which agencias are selected, dimmed, or normal
        if st.session_state.selected_agencia_map:
            agencias_layer_data['is_selected'] = (
                agencias_layer_data['agencia_normalized'] == st.session_state.selected_agencia_map
            )
            agencias_layer_data['size'] = agencias_layer_data['is_selected'].apply(lambda x: 7 if x else 4)
            agencias_layer_data['color'] = agencias_layer_data['is_selected'].apply(
                lambda x: [34, 197, 94, 255] if x else [0, 102, 204, 100]  # Green for selected, blue dimmed for others
            )
            
            # Center on selected agencia
            selected_agencia_info = agencias_with_crimes[
                agencias_with_crimes['agencia_normalized'] == st.session_state.selected_agencia_map
            ].iloc[0]
            center_lat = selected_agencia_info['latitud']
            center_lon = selected_agencia_info['longitud']
            zoom = 13
            pitch = 0 if view_mode != "Hexágonos" else 45
        else:
            agencias_layer_data['size'] = 6
            agencias_layer_data['color'] = [[0, 102, 204, 200]] * len(agencias_layer_data)  # Blue for all
            
            # Center on CDMX
            center_lat = 19.4326
            center_lon = -99.1332
            zoom = 10.5
            pitch = 0
        
        # Create agencia markers layer
        agencias_layer = pdk.Layer(
            "ScatterplotLayer",
            data=agencias_layer_data,
            get_position='[longitud, latitud]',
            get_radius='size * 50',
            get_fill_color='color',
            pickable=True,
            auto_highlight=True,
            highlight_color=[255, 215, 0, 200]  # Gold on hover
        )
        
        layers = [agencias_layer]
        
        # Add crime layer if agencia is selected
        if st.session_state.selected_agencia_map and not selected_crimes.empty:
            if view_mode == "Mapa de Calor":
                crime_layer = pdk.Layer(
                    "HeatmapLayer",
                    data=selected_crimes,
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
                        [227, 26, 28],
                        [189, 0, 38],
                        [128, 0, 38]     # Dark red
                    ]
                )
            elif view_mode == "Puntos":
                crime_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=selected_crimes,
                    get_position='[longitud, latitud]',
                    get_radius=40,
                    get_fill_color=[220, 20, 60, 160],
                    pickable=True,
                    auto_highlight=True
                )
            else:  # Hexágonos
                crime_layer = pdk.Layer(
                    "HexagonLayer",
                    data=selected_crimes,
                    get_position='[longitud, latitud]',
                    radius=150,
                    elevation_scale=1.5,
                    elevation_range=[0, 1000],
                    pickable=True,
                    extruded=True,
                    coverage=0.88,
                    auto_highlight=True,
                    color_range=[
                        [255, 255, 204],
                        [254, 217, 118],
                        [254, 178, 76],
                        [253, 141, 60],
                        [252, 78, 42],
                        [227, 26, 28]
                    ]
                )
            
            # Insert crime layer before agencias so agencias appear on top
            layers.insert(0, crime_layer)
        
        # Set view state
        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=pitch,
            bearing=0
        )
        
        # Create deck (Streamlit PyDeck uses environment variable)
        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/light-v10',
            tooltip={
                "html": """
                <div style="font-family: Inter, sans-serif; padding: 8px;">
                    <b style="color: #0066CC;">{agencia}</b><br/>
                    <span style="font-size: 0.9em; color: #5A6C7D;">
                        {direccion}
                    </span><br/>
                    <span style="font-size: 0.85em; color: #2C3E50;">
                        Total delitos: <b>{crime_count}</b>
                    </span>
                </div>
                """,
                "style": {
                    "backgroundColor": "white",
                    "color": MCKINSEY_COLORS['text'],
                    "border": f"2px solid {MCKINSEY_COLORS['primary_blue']}",
                    "borderRadius": "8px",
                    "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                }
            }
        )
        
        # Display map
        st.pydeck_chart(deck, use_container_width=True)
        
        # Map legend
        if st.session_state.selected_agencia_map:
            legend_cols = st.columns([1, 1, 1, 2])
            with legend_cols[0]:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                        <div style="width: 14px; height: 14px; background: rgb(34, 197, 94); border-radius: 50%;"></div>
                        <span>Agencia Seleccionada</span>
                    </div>
                """, unsafe_allow_html=True)
            with legend_cols[1]:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                        <div style="width: 12px; height: 12px; background: rgba(0, 102, 204, 0.4); border-radius: 50%;"></div>
                        <span>Otras Agencias</span>
                    </div>
                """, unsafe_allow_html=True)
            with legend_cols[2]:
                crime_color = "rgba(220, 20, 60, 0.6)" if view_mode == "Puntos" else "linear-gradient(90deg, #ffff99, #e31a1c)"
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                        <div style="width: 16px; height: 16px; background: {crime_color}; border-radius: 50%;"></div>
                        <span>Delitos</span>
                    </div>
                """, unsafe_allow_html=True)
        
        # Top 5 Most/Least Crime Agencias (simple lists below map)
        st.markdown("---")
        
        # Calculate crime counts per agencia for current year range (only valid agencias)
        agencia_crime_ranking = filtered_crime_df.groupby('agencia_normalized').size().reset_index(name='crime_count')
        agencia_crime_ranking = agencia_crime_ranking.merge(
            agencias_with_crimes[['agencia_normalized', 'agencia_x']], 
            on='agencia_normalized', 
            how='left'
        )
        agencia_crime_ranking = agencia_crime_ranking.dropna(subset=['agencia_x'])  # Remove any remaining NaN
        agencia_crime_ranking = agencia_crime_ranking.sort_values('crime_count', ascending=False)
        
        # Get top 5 and bottom 5
        top_5_agencias = agencia_crime_ranking.head(5)
        bottom_5_agencias = agencia_crime_ranking.tail(5).sort_values('crime_count', ascending=True)
        
        # Display in two columns
        rank_col_left, rank_col_right = st.columns(2)
        
        with rank_col_left:
            st.markdown("#### 🔴 Top 5 Agencias con Más Delitos")
            
            for i, (idx, row) in enumerate(top_5_agencias.iterrows(), 1):
                st.markdown(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.6rem 0;
                        border-bottom: 1px solid {MCKINSEY_COLORS['border']};
                        font-family: 'Inter', sans-serif;
                    ">
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span style="
                                font-weight: 700;
                                font-size: 1.1rem;
                                color: {MCKINSEY_COLORS['primary_blue']};
                                min-width: 25px;
                            ">{i}.</span>
                            <span style="
                                font-size: 0.9rem;
                                color: {MCKINSEY_COLORS['text']};
                            ">{row['agencia_x']}</span>
                        </div>
                        <span style="
                            font-weight: 600;
                            font-size: 0.9rem;
                            color: {MCKINSEY_COLORS['text']};
                        ">{format_number(row['crime_count'])}</span>
                    </div>
                """, unsafe_allow_html=True)
        
        with rank_col_right:
            st.markdown("#### 🟢 Top 5 Agencias con Menos Delitos")
            
            for i, (idx, row) in enumerate(bottom_5_agencias.iterrows(), 1):
                st.markdown(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.6rem 0;
                        border-bottom: 1px solid {MCKINSEY_COLORS['border']};
                        font-family: 'Inter', sans-serif;
                    ">
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span style="
                                font-weight: 700;
                                font-size: 1.1rem;
                                color: {MCKINSEY_COLORS['primary_blue']};
                                min-width: 25px;
                            ">{i}.</span>
                            <span style="
                                font-size: 0.9rem;
                                color: {MCKINSEY_COLORS['text']};
                            ">{row['agencia_x']}</span>
                        </div>
                        <span style="
                            font-weight: 600;
                            font-size: 0.9rem;
                            color: {MCKINSEY_COLORS['text']};
                        ">{format_number(row['crime_count'])}</span>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Stats below map
        if st.session_state.selected_agencia_map and not selected_crimes.empty:
            st.markdown("#### 📊 Estadísticas Detalladas")
            
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            
            # Calculate stats
            selected_violent = len(selected_crimes[
                selected_crimes['delito'].str.contains('con violencia', case=False, na=False)
            ])
            violent_pct_selected = (selected_violent / len(selected_crimes) * 100) if len(selected_crimes) > 0 else 0
            
            # Most common crime
            top_crime_selected = selected_crimes['delito'].value_counts().index[0] if not selected_crimes.empty else "N/A"
            top_crime_count = selected_crimes['delito'].value_counts().iloc[0] if not selected_crimes.empty else 0
            
            # Most affected alcaldía
            if 'alcaldia_hecho' in selected_crimes.columns:
                top_alcaldia = selected_crimes['alcaldia_hecho'].value_counts().index[0] if not selected_crimes.empty else "N/A"
                top_alcaldia_count = selected_crimes['alcaldia_hecho'].value_counts().iloc[0] if not selected_crimes.empty else 0
            else:
                top_alcaldia = "N/A"
                top_alcaldia_count = 0
            
            with stat_col1:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Total Delitos</div>
                        <div class="kpi-value">{format_number(len(selected_crimes))}</div>
                        <div class="kpi-caption">en rango seleccionado</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with stat_col2:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Tasa de Violencia</div>
                        <div class="kpi-value">{violent_pct_selected:.1f}%</div>
                        <div class="kpi-caption">{format_number(selected_violent)} violentos</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with stat_col3:
                crime_display = top_crime_selected[:30] + "..." if len(str(top_crime_selected)) > 30 else top_crime_selected
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Delito Más Común</div>
                        <div class="kpi-value" style="font-size: 0.8rem;">{crime_display}</div>
                        <div class="kpi-caption">{format_number(top_crime_count)} casos</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with stat_col4:
                alcaldia_display = str(top_alcaldia)[:20]
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Alcaldía Principal</div>
                        <div class="kpi-value" style="font-size: 1.0rem;">{alcaldia_display}</div>
                        <div class="kpi-caption">{format_number(top_alcaldia_count)} casos</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # Additional insights
            st.markdown("---")
            st.markdown("#### 💡 Análisis Temporal")
            
            insight_col1, insight_col2 = st.columns(2)
            
            with insight_col1:
                # Monthly trend
                if not selected_crimes.empty and 'fecha_hecho' in selected_crimes.columns:
                    monthly_crimes = selected_crimes.groupby(
                        selected_crimes['fecha_hecho'].dt.to_period('M')
                    ).size().reset_index(name='count')
                    
                    if len(monthly_crimes) > 1:
                        avg_monthly = monthly_crimes['count'].mean()
                        max_month = monthly_crimes.loc[monthly_crimes['count'].idxmax()]
                        
                        st.markdown(f"""
                            <div style="
                                background: {MCKINSEY_COLORS['card_bg']};
                                border-radius: 6px;
                                padding: 1rem;
                                margin-bottom: 0.5rem;
                            ">
                                <div style="font-weight: 600; color: {MCKINSEY_COLORS['text']}; margin-bottom: 0.5rem;">
                                    📅 Tendencia Mensual
                                </div>
                                <div style="font-size: 0.9rem; color: {MCKINSEY_COLORS['text_light']};">
                                    • Promedio mensual: <b>{avg_monthly:.0f}</b> delitos<br/>
                                    • Mes pico: <b>{max_month['fecha_hecho']}</b> ({max_month['count']} delitos)
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            
            with insight_col2:
                # Year-over-year comparison
                if not selected_crimes.empty and len(selected_crimes['year'].unique()) > 1:
                    yearly_crimes = selected_crimes.groupby('year').size()
                    latest_year_crimes = yearly_crimes.iloc[-1]
                    previous_year_crimes = yearly_crimes.iloc[-2] if len(yearly_crimes) > 1 else 0
                    
                    if previous_year_crimes > 0:
                        yoy_change_agencia = ((latest_year_crimes - previous_year_crimes) / previous_year_crimes) * 100
                        trend_emoji = "📈" if yoy_change_agencia > 0 else "📉"
                        trend_color = "#dc3545" if yoy_change_agencia > 0 else "#28a745"
                        
                        st.markdown(f"""
                            <div style="
                                background: {MCKINSEY_COLORS['card_bg']};
                                border-radius: 6px;
                                padding: 1rem;
                                margin-bottom: 0.5rem;
                            ">
                                <div style="font-weight: 600; color: {MCKINSEY_COLORS['text']}; margin-bottom: 0.5rem;">
                                    {trend_emoji} Comparación Anual
                                </div>
                                <div style="font-size: 0.9rem; color: {MCKINSEY_COLORS['text_light']};">
                                    • Año actual: <b>{latest_year_crimes}</b> delitos<br/>
                                    • Cambio YoY: <b style="color: {trend_color};">{format_percentage(yoy_change_agencia)}</b>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        
        elif st.session_state.selected_agencia_map and selected_crimes.empty:
            st.info(f"📊 No hay delitos reportados para esta agencia en el rango {start_year}-{end_year}")
        else:
            st.info("💡 **Tip:** Selecciona una agencia del menú desplegable para ver los delitos reportados y estadísticas detalladas.")              
    
    # Debug info
    with st.expander("🔍 Información de Depuración"):
        st.write(f"Total records loaded: {len(df):,}")
        st.write(f"Filtered records: {len(filtered_df):,}")
        st.write(f"Date range: {df['fecha_hecho'].min()} to {df['fecha_hecho'].max()}")
        st.write(f"Alcaldías: {df['alcaldia_normalized'].nunique()}")
        st.write(f"Selected range: {start_year} to {end_year}")
        
        # Hour data analysis
        if 'hour' in df.columns:
            valid_hours = df[df['hour'].notna()]['hour']
            st.write(f"Hour data available: {len(valid_hours):,} records ({len(valid_hours)/len(df)*100:.1f}%)")
            if len(valid_hours) > 0:
                st.write(f"Hour range: {valid_hours.min():.0f} to {valid_hours.max():.0f}")
                st.write(f"Sample hours: {valid_hours.head(10).tolist()}")


if __name__ == "__main__":
    show()