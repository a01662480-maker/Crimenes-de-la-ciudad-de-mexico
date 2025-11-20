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
            "alcaldia_hecho, anio_hecho, fecha_hecho, delito, latitud, longitud"
        ).execute()
        
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return df
        
        df['fecha_hecho'] = pd.to_datetime(df['fecha_hecho'], errors='coerce')
        df['year'] = df['fecha_hecho'].dt.year
        df['month'] = df['fecha_hecho'].dt.month
        df['date'] = df['fecha_hecho'].dt.date
        
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
    st.set_page_config(page_title="Place holder predictions", page_icon="🏙️", layout="wide")
    apply_mckinsey_styles()

if __name__ == "__main__":
    show()