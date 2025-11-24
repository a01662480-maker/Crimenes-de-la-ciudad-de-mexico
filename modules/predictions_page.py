import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import json
import os
import requests
import uuid

# ===============================
# Configuration
# ===============================
SUPABASE_URL = "https://xzeycsqwynjxnzgctydr.supabase.co"
SUPABASE_KEY = "sb_publishable_wSTGdAAY_IIuYKNpr6N6GA_rGZy-y29"

# N8N Chatbot Configuration
N8N_WEBHOOK_URL = "https://thebuttoncdmx.app.n8n.cloud/webhook/thaleschat"

# McKinsey Color Palette (matching rest of app)
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

# Risk level colors
RISK_COLORS = {
    'very_high': '#DC3545',  # Red
    'high': '#FF9800',       # Orange
    'medium': '#FFC107',     # Yellow
    'low': '#4CAF50',        # Green
    'zero': '#E0E0E0'        # Gray for 0 crimes
}

# Turno colors
TURNO_COLORS = {
    'MORNING': '#64B5F6',    # Light Blue
    'AFTERNOON': '#FFA726',  # Orange
    'EVENING': '#AB47BC',    # Purple
    'NIGHT': '#5C6BC0'       # Indigo
}

# Alcaldías de CDMX (Display names)
ALCALDIAS = [
    'ÁLVARO OBREGÓN',
    'AZCAPOTZALCO',
    'BENITO JUÁREZ',
    'COYOACÁN',
    'CUAJIMALPA DE MORELOS',
    'CUAUHTÉMOC',
    'GUSTAVO A. MADERO',
    'IZTACALCO',
    'IZTAPALAPA',
    'LA MAGDALENA CONTRERAS',
    'MIGUEL HIDALGO',
    'MILPA ALTA',
    'TLÁHUAC',
    'TLALPAN',
    'VENUSTIANO CARRANZA',
    'XOCHIMILCO'
]

# Mapping from display names to database names (no spaces, no accents)
ALCALDIA_DB_MAPPING = {
    'ÁLVARO OBREGÓN': 'ALVARO OBREGON',
    'AZCAPOTZALCO': 'AZCAPOTZALCO',
    'BENITO JUÁREZ': 'BENITO JUAREZ',
    'COYOACÁN': 'COYOACAN',
    'CUAJIMALPA DE MORELOS': 'CUAJIMALPA',
    'CUAUHTÉMOC': 'CUAUHTEMOC',
    'GUSTAVO A. MADERO': 'GUSTAVO A MADERO',
    'IZTACALCO': 'IZTACALCO',
    'IZTAPALAPA': 'IZTAPALAPA',
    'LA MAGDALENA CONTRERAS': 'MAGDALENA CONTRERAS',
    'MIGUEL HIDALGO': 'MIGUEL HIDALGO',
    'MILPA ALTA': 'MILPA ALTA',
    'TLÁHUAC': 'TLAHUAC',
    'TLALPAN': 'TLALPAN',
    'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA',
    'XOCHIMILCO': 'XOCHIMILCO'
}

# Spanish labels for turnos
TURNO_LABELS = {
    'MORNING': 'Mañana',
    'AFTERNOON': 'Tarde',
    'EVENING': 'Noche',
    'NIGHT': 'Madrugada'
}

# Hardcoded Alcaldía Centers [lat, lon]
ALCALDIA_CENTERS = {
    'ÁLVARO OBREGÓN': [19.3667, -99.2000],
    'AZCAPOTZALCO': [19.4900, -99.1860],
    'BENITO JUÁREZ': [19.3700, -99.1650],
    'COYOACÁN': [19.3467, -99.1617],
    'CUAJIMALPA DE MORELOS': [19.3550, -99.2917],
    'CUAUHTÉMOC': [19.4326, -99.1332],
    'GUSTAVO A. MADERO': [19.4850, -99.1150],
    'IZTACALCO': [19.3850, -99.1133],
    'IZTAPALAPA': [19.3570, -99.0550],
    'LA MAGDALENA CONTRERAS': [19.2783, -99.2461],
    'MIGUEL HIDALGO': [19.4370, -99.2020],
    'MILPA ALTA': [19.1920, -99.0230],
    'TLÁHUAC': [19.2458, -99.0139],
    'TLALPAN': [19.2900, -99.1700],
    'VENUSTIANO CARRANZA': [19.4400, -99.1000],
    'XOCHIMILCO': [19.2570, -99.1050]
}

# ===============================
# Helper Functions
# ===============================

def format_number(num):
    """Format large numbers with commas"""
    return f"{int(num):,}"


def normalize_alcaldia_for_db(alcaldia_display_name):
    """Convert display name to database format (no spaces at end, no accents)"""
    return ALCALDIA_DB_MAPPING.get(alcaldia_display_name, alcaldia_display_name)


def get_dynamic_risk_thresholds(days):
    """Calculate risk thresholds based on number of days selected"""
    # Base thresholds per day
    base_per_day = {
        'very_high': 400,
        'high': 200,
        'medium': 100,
        'low': 1
    }
    
    # Multiply by days
    return {k: v * days for k, v in base_per_day.items()}


def get_risk_level(crimes, thresholds):
    """Determine risk level based on crime count and dynamic thresholds"""
    if crimes == 0:
        return 'zero'
    elif crimes >= thresholds['very_high']:
        return 'very_high'
    elif crimes >= thresholds['high']:
        return 'high'
    elif crimes >= thresholds['medium']:
        return 'medium'
    else:
        return 'low'


def get_risk_color(crimes, thresholds):
    """Get color based on crime count and dynamic thresholds"""
    risk_level = get_risk_level(crimes, thresholds)
    return RISK_COLORS[risk_level]


def get_risk_label(crimes):
    """Get Spanish label for risk level"""
    if crimes == 0:
        return 'Sin Predicciones'
    # Note: This is just for display, actual categorization uses dynamic thresholds
    else:
        return 'Variable'


def normalize_alcaldia_name(name):
    """Normalize alcaldía name for matching between geojson and database"""
    # The alcaldias.json uses proper capitalization like "Álvaro Obregón"
    # The cuadrantes table uses uppercase like "ALVARO OBREGON"
    
    name_upper = name.upper()
    
    # Remove accents for matching
    replacements = {
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u'
    }
    
    normalized = name_upper
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    # Remove periods
    normalized = normalized.replace('.', '')
    
    # Handle special cases for matching
    # Map alcaldias.json names to database format
    special_mappings = {
        'GUSTAVO A MADERO': 'GUSTAVO A MADERO',
        'CUAJIMALPA DE MORELOS': 'CUAJIMALPA',
        'LA MAGDALENA CONTRERAS': 'MAGDALENA CONTRERAS',
        'ALVARO OBREGON': 'ALVARO OBREGON',
        'BENITO JUAREZ': 'BENITO JUAREZ',
        'MIGUEL HIDALGO': 'MIGUEL HIDALGO',
        'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA',
        'AZCAPOTZALCO': 'AZCAPOTZALCO',
        'COYOACAN': 'COYOACAN',
        'CUAUHTEMOC': 'CUAUHTEMOC',
        'IZTACALCO': 'IZTACALCO',
        'IZTAPALAPA': 'IZTAPALAPA',
        'MILPA ALTA': 'MILPA ALTA',
        'TLAHUAC': 'TLAHUAC',
        'TLALPAN': 'TLALPAN',
        'XOCHIMILCO': 'XOCHIMILCO'
    }
    
    normalized = normalized.strip()
    
    # Return mapped version if exists
    return special_mappings.get(normalized, normalized)


# ===============================
# Data Loading Functions
# ===============================

@st.cache_data(ttl=3600)
def load_alcaldias_geojson():
    """Load alcaldías geographic boundaries from JSON file"""
    try:
        # Get path relative to this file (predictions.py is in modules/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        alcaldias_path = os.path.join(current_dir, '..', 'alcaldias.json')
        
        with open(alcaldias_path, 'r', encoding='utf-8') as f:
            alcaldias_data = json.load(f)
        
        return alcaldias_data
    
    except FileNotFoundError:
        st.error("❌ No se encontró el archivo alcaldias.json")
        return None
    except Exception as e:
        st.error(f"❌ Error al cargar alcaldias.json: {e}")
        return None


@st.cache_data(ttl=3600)
def load_predictions():
    """Load crime predictions from Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Query predictions table
        response = supabase.table("CrimePredictions").select("*").execute()
        
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert date column
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        
        # Ensure numeric types
        df['Cuadrante'] = df['Cuadrante'].astype(str)
        df['Crímenes Predichos'] = pd.to_numeric(df['Crímenes Predichos'], errors='coerce')
        df['HOLIDAY'] = pd.to_numeric(df['HOLIDAY'], errors='coerce')
        df['PAY_DAY'] = pd.to_numeric(df['PAY_DAY'], errors='coerce')
        
        return df
    
    except Exception as e:
        st.error(f"❌ Error al cargar predicciones: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_cuadrantes_geojson():
    """Load cuadrantes geographic data from Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Query cuadrantes table
        response = supabase.table("cuadrantes").select("*").execute()
        
        cuadrantes_data = response.data
        
        if not cuadrantes_data:
            st.error("❌ No se encontraron datos en la tabla cuadrantes")
            return None
        
        # Convert to GeoJSON format
        features = []
        invalid_count = 0
        
        for item in cuadrantes_data:
            try:
                # Get geometry from geo_shape field (the correct field name in your DB)
                geometry = item.get('geo_shape')
                
                if not geometry:
                    invalid_count += 1
                    continue
                
                # Parse geometry if it's a string (handle multiple formats)
                if isinstance(geometry, str):
                    # Remove any extra whitespace
                    geometry = geometry.strip()
                    
                    # Try to parse as JSON
                    try:
                        geometry = json.loads(geometry)
                    except json.JSONDecodeError:
                        # If that fails, try replacing single quotes with double quotes
                        try:
                            geometry = json.loads(geometry.replace("'", '"'))
                        except json.JSONDecodeError:
                            invalid_count += 1
                            continue
                
                # Validate geometry has required fields
                if not isinstance(geometry, dict):
                    invalid_count += 1
                    continue
                    
                if 'type' not in geometry or 'coordinates' not in geometry:
                    invalid_count += 1
                    continue
                
                # Validate it's a proper geometry type
                if geometry['type'] not in ['Polygon', 'MultiPolygon', 'Point', 'LineString']:
                    invalid_count += 1
                    continue
                    
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": str(item.get('id', '')),  # Ensure string type
                        "name": f"Cuadrante {item.get('id', '')}",
                        "alcaldia": str(item.get('alcaldia', '')).strip().upper()  # Normalize
                    },
                    "geometry": geometry
                }
                features.append(feature)
                
            except Exception as e:
                # Skip this feature if any error occurs
                invalid_count += 1
                continue
        
        # Only show warning if significant number of features are invalid
        if invalid_count > 10:
            st.warning(f"⚠️ {invalid_count} cuadrantes sin geometría válida fueron omitidos")
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return geojson
    
    except Exception as e:
        st.error(f"❌ Error al cargar datos geográficos: {e}")
        return None


@st.cache_data(ttl=3600)
def get_alcaldia_cuadrantes(_geojson, alcaldia):
    """Get list of cuadrante IDs for a given alcaldía"""
    if _geojson is None:
        return []
    
    # Normalize alcaldía name for database lookup
    alcaldia_db = normalize_alcaldia_for_db(alcaldia)
    
    cuadrantes = []
    alcaldias_found = set()  # Track what alcaldías we find
    
    for feature in _geojson['features']:
        feature_alcaldia = feature['properties'].get('alcaldia', '').upper().strip()
        alcaldias_found.add(feature_alcaldia)
        
        if feature_alcaldia == alcaldia_db:
            cuadrantes.append(str(feature['properties']['id']))
    
    # Debug: Show what alcaldías exist in geojson
    if not cuadrantes:
        st.warning(f"⚠️ No se encontraron cuadrantes para '{alcaldia_db}'. Alcaldías en geojson: {sorted(alcaldias_found)[:10]}")
    
    return cuadrantes


@st.cache_data(ttl=3600)
def filter_geojson_by_alcaldia(_geojson, alcaldia):
    """Filter geojson to only include features from selected alcaldía"""
    if _geojson is None:
        return None
    
    # Normalize alcaldía name for database lookup
    alcaldia_db = normalize_alcaldia_for_db(alcaldia)
    
    filtered_features = []
    for feature in _geojson['features']:
        feature_alcaldia = feature['properties'].get('alcaldia', '').upper().strip()
        if feature_alcaldia == alcaldia_db:
            filtered_features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": filtered_features
    }


# ===============================
# Map Creation Function
# ===============================

def create_alcaldia_map(alcaldia_summary, alcaldias_geojson, days_ahead):
    """Create Folium map showing all alcaldías colored by crime predictions"""
    
    if alcaldias_geojson is None or 'features' not in alcaldias_geojson:
        return None
    
    # Create base map centered on CDMX
    m = folium.Map(
        location=[19.4326, -99.1332],  # CDMX center
        zoom_start=10,
        tiles='OpenStreetMap',
        control_scale=True,
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True
    )
    
    # Get dynamic thresholds based on days selected
    thresholds = get_dynamic_risk_thresholds(days_ahead)
    
    # Create crime dictionary for quick lookup
    # Normalize alcaldía names for matching
    crime_dict = {}
    for _, row in alcaldia_summary.iterrows():
        normalized_name = normalize_alcaldia_name(row['Alcaldía'])
        crime_dict[normalized_name] = row['Total_Crimes']
    
    # Add choropleth layer
    for feature in alcaldias_geojson['features']:
        try:
            alcaldia_name = feature['properties']['NOMGEO']
            normalized_name = normalize_alcaldia_name(alcaldia_name)
            
            crime_count = crime_dict.get(normalized_name, 0)
            
            # Determine color using dynamic thresholds
            fill_color = get_risk_color(crime_count, thresholds)
            
            # Get risk level label
            risk_level = get_risk_level(crime_count, thresholds)
            risk_labels = {
                'very_high': 'Muy Alto',
                'high': 'Alto',
                'medium': 'Medio',
                'low': 'Bajo',
                'zero': 'Sin Predicciones'
            }
            risk_label = risk_labels.get(risk_level, 'N/A')
            
            # Create popup text
            popup_text = f"""
            <div style='font-family: Inter, sans-serif; padding: 8px;'>
                <b>{alcaldia_name}</b><br>
                Delitos Predichos: <b>{int(crime_count)}</b><br>
                Nivel de Riesgo: <b>{risk_label}</b><br>
                <small>({days_ahead} día{'s' if days_ahead > 1 else ''})</small>
            </div>
            """
            
            # Add GeoJson feature
            folium.GeoJson(
                feature,
                style_function=lambda x, fc=fill_color: {
                    'fillColor': fc,
                    'color': '#333333',
                    'weight': 2,
                    'fillOpacity': 0.7,
                    'opacity': 1
                },
                tooltip=folium.Tooltip(popup_text),
                popup=folium.Popup(popup_text, max_width=250)
            ).add_to(m)
            
        except Exception as e:
            # Skip invalid features
            continue
    
    return m


# ===============================
# Chatbot Functions
# ===============================

def send_prompt_to_n8n(prompt: str):
    """Send prompt to n8n webhook"""
    try:
        session_id = uuid.uuid4().hex  # Generate unique sessionId
        
        payload = {
            "prompt": prompt,
            "sessionId": session_id
        }
        
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        # Try to parse JSON
        try:
            result = response.json()
        except:
            result = {"output": response.text}
        
        if "output" not in result:
            result = {"output": result}
        
        result["sessionId_enviado"] = session_id
        return result
        
    except requests.exceptions.Timeout:
        return {"output": "⏱️ Error: La solicitud tardó demasiado tiempo. Por favor intenta de nuevo."}
    except requests.exceptions.ConnectionError:
        return {"output": "🔌 Error: No se pudo conectar con el servidor. Verifica tu conexión a internet."}
    except requests.exceptions.RequestException as e:
        return {"output": f"❌ Error de red: {str(e)}"}
    except Exception as e:
        return {"output": f"❌ Error inesperado: {str(e)}"}
        return {"output": f"❌ Error inesperado: {str(e)}"}


# ===============================
# Visualization Functions
# ===============================

def create_timeline_chart(cuadrante_data, selected_turnos):
    """Create timeline chart showing crime predictions by date and turno"""
    
    # Group by date and turno
    timeline = cuadrante_data.groupby(['Fecha', 'Turno']).agg({
        'Crímenes Predichos': 'sum'
    }).reset_index()
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Add traces for each turno
    for turno in selected_turnos:
        turno_data = timeline[timeline['Turno'] == turno]
        
        fig.add_trace(go.Scatter(
            x=turno_data['Fecha'],
            y=turno_data['Crímenes Predichos'],
            mode='lines+markers',
            name=TURNO_LABELS[turno],  # Use Spanish label
            line=dict(color=TURNO_COLORS[turno], width=3),
            marker=dict(size=8)
        ))
    
    # Update layout
    fig.update_layout(
        title='Tendencia de Predicciones por Turno',
        xaxis_title='Fecha',
        yaxis_title='Delitos Predichos',
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=12, color=MCKINSEY_COLORS['text']),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400
    )
    
    fig.update_xaxes(showgrid=True, gridcolor=MCKINSEY_COLORS['grid'])
    fig.update_yaxes(showgrid=True, gridcolor=MCKINSEY_COLORS['grid'])
    
    return fig


def create_turno_distribution(cuadrante_data):
    """Create pie chart showing distribution by turno"""
    
    turno_totals = cuadrante_data.groupby('Turno')['Crímenes Predichos'].sum()
    
    # Create Spanish labels for display
    spanish_labels = [TURNO_LABELS[turno] for turno in turno_totals.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=spanish_labels,  # Use Spanish labels
        values=turno_totals.values,
        marker=dict(colors=[TURNO_COLORS[t] for t in turno_totals.index]),
        hole=0.4,
        textinfo='label+percent',
        textfont=dict(size=14)
    )])
    
    fig.update_layout(
        title='Distribución por Turno',
        font=dict(family='Inter, sans-serif', size=12, color=MCKINSEY_COLORS['text']),
        showlegend=False,
        height=350,
        paper_bgcolor='white'
    )
    
    return fig


# ===============================
# Main Show Function
# ===============================

def show():
    """Main function to display the predictions page"""
    
    # Apply custom styling
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .main {{
            background-color: white;
        }}
        
        h1 {{
            color: {MCKINSEY_COLORS['text']} !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 2.2rem !important;
            margin-bottom: 0.3rem !important;
        }}
        
        .subtitle {{
            color: {MCKINSEY_COLORS['text_light']};
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            margin-bottom: 2rem;
            font-weight: 400;
        }}
        
        .filter-container {{
            background: {MCKINSEY_COLORS['card_bg']};
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid {MCKINSEY_COLORS['border']};
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
        }}
        
        .section-header {{
            color: {MCKINSEY_COLORS['primary_blue']} !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
            border-bottom: 2px solid {MCKINSEY_COLORS['primary_blue']};
            padding-bottom: 0.5rem;
        }}
        
        .legend-card {{
            background: white;
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid {MCKINSEY_COLORS['border']};
            margin-bottom: 1rem;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 0.5rem;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 8px;
            border: 1px solid #ccc;
        }}
        
        .metric-card {{
            background: {MCKINSEY_COLORS['card_bg']};
            padding: 1.2rem;
            border-radius: 8px;
            border: 1px solid {MCKINSEY_COLORS['border']};
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {MCKINSEY_COLORS['primary_blue']};
            font-family: 'Inter', sans-serif;
        }}
        
        .metric-label {{
            font-size: 0.9rem;
            color: {MCKINSEY_COLORS['text_light']};
            font-family: 'Inter', sans-serif;
            margin-top: 0.3rem;
        }}
        
        .stSelectbox label, .stMultiSelect label, .stSlider label {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            color: {MCKINSEY_COLORS['text']} !important;
        }}
        
        .map-container {{
            border: 1px solid {MCKINSEY_COLORS['border']};
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # ===============================
    # SESSION STATE INITIALIZATION
    # ===============================
    
    if 'selected_cuadrante' not in st.session_state:
        st.session_state.selected_cuadrante = None
    
    if 'last_alcaldia' not in st.session_state:
        st.session_state.last_alcaldia = None
    
    # ===============================
    # PAGE HEADER
    # ===============================
    st.title("🔮 Predicciones de Delitos")
    st.markdown('<p class="subtitle">Análisis predictivo basado en Machine Learning para los próximos 5 días</p>', unsafe_allow_html=True)
    
    # ===============================
    # LOAD DATA
    # ===============================
    
    with st.spinner("⏳ Cargando datos de predicciones..."):
        predictions_df = load_predictions()
        cuadrantes_geojson = load_cuadrantes_geojson()
        alcaldias_geojson = load_alcaldias_geojson()
    
    # Check if data loaded successfully
    if predictions_df.empty:
        st.error("❌ No se encontraron predicciones en la base de datos")
        st.stop()
    
    if alcaldias_geojson is None:
        st.error("❌ No se pudo cargar el mapa de alcaldías")
        st.stop()
    
    # ===============================
    # FILTERS SECTION (HIDDEN - Using map sidebar instead)
    # ===============================
    
    # Set default values if not in session state
    if 'selected_turnos' not in st.session_state:
        st.session_state.selected_turnos = ['MORNING', 'AFTERNOON', 'EVENING', 'NIGHT']
    if 'days_ahead' not in st.session_state:
        st.session_state.days_ahead = 5
    
    # ===============================
    # FILTER DATA AND AGGREGATE BY ALCALDÍA
    # ===============================
    
    # Get filter values from session state (will be updated by map sidebar)
    selected_turnos = st.session_state.selected_turnos
    days_ahead = st.session_state.days_ahead
    
    # Convert turno names to Spanish for display (define early for use in chatbot)
    spanish_turnos = [TURNO_LABELS[t] for t in selected_turnos]
    
    # Filter by turno
    filtered_df = predictions_df[predictions_df['Turno'].isin(selected_turnos)].copy()
    
    # Filter by days ahead
    if not filtered_df.empty:
        today = filtered_df['Fecha'].min()
        max_date = today + timedelta(days=days_ahead - 1)
        filtered_df = filtered_df[filtered_df['Fecha'] <= max_date]
    
    if filtered_df.empty:
        st.warning("⚠️ No hay predicciones disponibles con los filtros seleccionados")
        st.stop()
    
    # Map cuadrantes to alcaldías
    cuadrante_to_alcaldia = {}
    alcaldias_in_db = set()
    
    if cuadrantes_geojson:
        for feature in cuadrantes_geojson['features']:
            cuadrante_id = str(feature['properties']['id'])
            alcaldia_name = feature['properties'].get('alcaldia', '').strip().upper()
            cuadrante_to_alcaldia[cuadrante_id] = alcaldia_name
            alcaldias_in_db.add(alcaldia_name)
    
    # Add alcaldía column to predictions
    filtered_df['Alcaldía_DB'] = filtered_df['Cuadrante'].map(cuadrante_to_alcaldia)
    
    # Remove rows without alcaldía mapping
    filtered_df = filtered_df[filtered_df['Alcaldía_DB'].notna()]
    
    # Aggregate by alcaldía
    alcaldia_summary = filtered_df.groupby('Alcaldía_DB').agg({
        'Crímenes Predichos': 'sum'
    }).reset_index()
    alcaldia_summary.columns = ['Alcaldía', 'Total_Crimes']
    
    # DEBUG: Show alcaldía matching
    with st.expander("🔍 Debug: Ver coincidencia de nombres de alcaldías"):
        st.write("**Alcaldías en cuadrantes DB (formato original):**")
        st.write(sorted(alcaldias_in_db))
        
        st.write("**Alcaldías en alcaldias.json (normalizadas):**")
        if alcaldias_geojson:
            json_alcaldias = [normalize_alcaldia_name(f['properties']['NOMGEO']) 
                             for f in alcaldias_geojson['features']]
            st.write(sorted(set(json_alcaldias)))
        
        st.write("**Alcaldías con predicciones (después de agregación):**")
        st.dataframe(alcaldia_summary.sort_values('Total_Crimes', ascending=False))
    
    # ===============================
    # SUMMARY STATISTICS
    # ===============================
    
    st.markdown("---")
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    with summary_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(alcaldia_summary)}</div>
            <div class="metric-label">Alcaldías</div>
        </div>
        """, unsafe_allow_html=True)
    
    with summary_col2:
        total_crimes = int(alcaldia_summary['Total_Crimes'].sum())
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_number(total_crimes)}</div>
            <div class="metric-label">Delitos Predichos (CDMX)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with summary_col3:
        avg_crimes = alcaldia_summary['Total_Crimes'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_number(avg_crimes)}</div>
            <div class="metric-label">Promedio por Alcaldía</div>
        </div>
        """, unsafe_allow_html=True)
    
    with summary_col4:
        max_crimes = int(alcaldia_summary['Total_Crimes'].max())
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_number(max_crimes)}</div>
            <div class="metric-label">Máximo (Alcaldía)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ===============================
    # MAP SECTION
    # ===============================
    
    st.markdown('<h2 class="section-header">🗺️ Mapa de Riesgo por Alcaldía</h2>', unsafe_allow_html=True)
    
    # Get dynamic thresholds for legend
    thresholds = get_dynamic_risk_thresholds(days_ahead)
    
    map_col1, map_col2 = st.columns([4, 1])
    
    with map_col2:
        st.markdown("##### 🎛️ Filtros de Visualización")
        
        # Turno filter (multiselect) - Show Spanish labels but store English values
        selected_turnos_new = st.multiselect(
            "🕐 Turno",
            options=['MORNING', 'AFTERNOON', 'EVENING', 'NIGHT'],
            default=st.session_state.selected_turnos,
            format_func=lambda x: TURNO_LABELS[x],  # Display Spanish labels
            help="Selecciona uno o más turnos",
            key="turno_filter"
        )
        
        # Update session state if changed
        if selected_turnos_new and selected_turnos_new != st.session_state.selected_turnos:
            st.session_state.selected_turnos = selected_turnos_new
            st.rerun()
        elif not selected_turnos_new:
            st.warning("⚠️ Selecciona al menos un turno")
        
        # Days ahead slider
        days_ahead_new = st.slider(
            "📅 Días de Predicción",
            min_value=1,
            max_value=5,
            value=st.session_state.days_ahead,
            help="Suma de delitos predichos en los próximos N días",
            key="days_filter"
        )
        
        # Update session state if changed
        if days_ahead_new != st.session_state.days_ahead:
            st.session_state.days_ahead = days_ahead_new
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("##### 🎨 Leyenda de Riesgo")
        
        # Dynamic legend based on days selected
        st.markdown(f"""
        <div class="legend-card">
            <div class="legend-item">
                <div class="legend-color" style="background-color: {RISK_COLORS['very_high']};"></div>
                <span>🔴 Muy Alto ({format_number(thresholds['very_high'])}+)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: {RISK_COLORS['high']};"></div>
                <span>🟠 Alto ({format_number(thresholds['high'])}-{format_number(thresholds['very_high']-1)})</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: {RISK_COLORS['medium']};"></div>
                <span>🟡 Medio ({format_number(thresholds['medium'])}-{format_number(thresholds['high']-1)})</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: {RISK_COLORS['low']};"></div>
                <span>🟢 Bajo (1-{format_number(thresholds['medium']-1)})</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: {RISK_COLORS['zero']};"></div>
                <span>⚪ Sin Predicciones</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption(f"*Escala ajustada para {days_ahead} día{'s' if days_ahead > 1 else ''}*")
    
    with map_col1:
        # Create and display alcaldía map
        crime_map = create_alcaldia_map(alcaldia_summary, alcaldias_geojson, days_ahead)
        
        if crime_map:
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            
            # Display map
            st_folium(
                crime_map,
                width=None,
                height=650,
                key="alcaldia_map",
                returned_objects=[]
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("❌ No se pudo generar el mapa")
    
    # ===============================
    # CHATBOT SECTION
    # ===============================
    
    st.markdown('<h2 class="section-header">💬 Asistente IA - Consultas sobre Delitos Históricos</h2>', unsafe_allow_html=True)
    
    with st.expander("🤖 Chatear con TheButton (Base de Datos FGJ)", expanded=False):
        st.info("💡 **Este asistente responde preguntas sobre delitos históricos en la base de datos FGJ.**")
        st.caption("⚠ TheButton es un modelo experimental y puede cometer errores.")
        
        # Initialize chat history in session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Show chat history (last 5 messages)
        if st.session_state.chat_history:
            st.markdown("#### 📝 Historial de Conversación")
            for i, message in enumerate(reversed(st.session_state.chat_history[-5:])):
                st.markdown(f"""
                <div style='background: {MCKINSEY_COLORS['card_bg']}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid {MCKINSEY_COLORS['primary_blue']};'>
                    <p style='margin: 0; color: {MCKINSEY_COLORS['text']}; font-weight: 600;'>👤 Pregunta:</p>
                    <p style='margin: 0.5rem 0; color: {MCKINSEY_COLORS['text']};'>{message['question']}</p>
                    <p style='margin: 1rem 0 0 0; color: {MCKINSEY_COLORS['primary_blue']}; font-weight: 600;'>🤖 Respuesta:</p>
                    <p style='margin: 0.5rem 0 0 0; color: {MCKINSEY_COLORS['text']};'>{message['answer']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            if len(st.session_state.chat_history) > 5:
                st.caption(f"Mostrando últimas 5 de {len(st.session_state.chat_history)} conversaciones")
            
            st.markdown("---")
        
        # Chat input
        st.markdown("#### 💬 Tu Pregunta")
        
        user_prompt = st.text_area(
            "Escribe tu pregunta sobre delitos históricos:",
            height=100,
            placeholder="Ejemplo: ¿Qué alcaldía tuvo más crímenes en 2023?",
            key="chat_input"
        )
        
        col1, col2 = st.columns([1, 5])
        
        with col1:
            send_button = st.button("📤 Enviar", type="primary", use_container_width=True)
        
        with col2:
            if st.button("🗑️ Limpiar Historial", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        if send_button:
            if not user_prompt.strip():
                st.warning("⚠ Escribe una pregunta antes de enviar.")
            else:
                # Send to n8n - simple and clean, just like original code
                with st.spinner("⏳ Pensando..."):
                    result = send_prompt_to_n8n(user_prompt)
                
                # Add to history
                st.session_state.chat_history.append({
                    'question': user_prompt,
                    'answer': result["output"],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Rerun to show updated history
                st.rerun()
    
    # ===============================
    # FOOTER INFO
    # ===============================
    
    st.markdown("---")
    
    st.caption(f"📊 Mostrando predicciones para **Ciudad de México** | Turnos: **{', '.join(spanish_turnos)}** | Próximos **{days_ahead} días**")
    st.caption(f"🔄 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ===============================
# Entry Point
# ===============================

if __name__ == "__main__":
    show()