# pages/data_checker.py
import streamlit as st
import pandas as pd
import json
import ast
from supabase import create_client

# -------------------------
# Supabase Configuration
# -------------------------
SUPABASE_URL = "https://xzeycsqwynjxnzgctydr.supabase.co"
SUPABASE_KEY = "sb_publishable_wSTGdAAY_IIuYKNpr6N6GA_rGZy-y29"
SUPABASE_TABLE = "FGJ"
SUPABASE_TABLE_CUADRANTS = "cuadrantes"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# Data Loading Functions
# -------------------------
@st.cache_data(show_spinner=True)
def load_crime_data():
    """Load crime data from Supabase"""
    st.info("📡 Loading crime data...")
    all_data = []
    batch_size = 1000
    offset = 0

    while True:
        res = supabase.table(SUPABASE_TABLE).select("*").range(offset, offset + batch_size - 1).execute()
        if not res.data:
            break
        all_data.extend(res.data)
        offset += batch_size

    df = pd.DataFrame(all_data)
    df = df.dropna(subset=['latitud', 'longitud'])
    df = df[(df['latitud'] != 0) & (df['longitud'] != 0)]
    
    st.success(f"✅ Loaded {len(df):,} records")
    return df


@st.cache_data(show_spinner=True)
def load_cuadrantes():
    """Load cuadrantes from Supabase"""
    st.info("📡 Loading cuadrantes...")
    res = supabase.table(SUPABASE_TABLE_CUADRANTS).select("*").execute()
    cuadrantes = pd.DataFrame(res.data)
    
    if "geo_shape" in cuadrantes.columns:
        def parse_shape(v):
            try:
                return ast.literal_eval(v) if isinstance(v, str) else v
            except:
                return None
        cuadrantes["geo_shape"] = cuadrantes["geo_shape"].apply(parse_shape)
    
    st.success(f"✅ Loaded {len(cuadrantes)} cuadrantes")
    return cuadrantes


def show():
    st.title("🔍 Data Structure Checker")
    
    # Load data
    df = load_crime_data()
    cuadrantes = load_cuadrantes()
    
    # ==========================================
    # CRIME DATA STRUCTURE
    # ==========================================
    st.header("1️⃣ Crime Data (FGJ) Structure")
    st.write(f"**Total rows:** {len(df):,}")
    st.write("**Columns:**", df.columns.tolist())
    
    st.subheader("Sample of first 5 rows:")
    st.dataframe(df.head())
    
    st.subheader("Date/Time columns detail:")
    date_time_cols = [col for col in df.columns if any(x in col.lower() for x in ['fecha', 'anio', 'mes', 'hora', 'date', 'time'])]
    if date_time_cols:
        st.write("**Found date/time columns:**", date_time_cols)
        for col in date_time_cols:
            st.write(f"- **{col}**: Type = {df[col].dtype}")
            st.write("  Sample values:", df[col].dropna().head(5).tolist())
    
    st.subheader("Location columns:")
    location_cols = ['latitud', 'longitud', 'alcaldia_hecho']
    for col in location_cols:
        if col in df.columns:
            st.write(f"- **{col}**: Type = {df[col].dtype}")
            if col == 'alcaldia_hecho':
                st.write("  Unique values:", df[col].nunique())
                st.write("  Value counts:")
                st.dataframe(df[col].value_counts())
    
    # ==========================================
    # CUADRANTES DATA STRUCTURE
    # ==========================================
    st.header("2️⃣ Cuadrantes Data Structure")
    st.write(f"**Total cuadrantes:** {len(cuadrantes)}")
    st.write("**Columns:**", cuadrantes.columns.tolist())
    
    st.subheader("Sample of first 3 rows:")
    st.dataframe(cuadrantes.head(3))
    
    # ⭐ CHECK FOR ALCALDIA COLUMN
    st.subheader("🔍 Alcaldia Column Check")
    if 'alcaldia' in cuadrantes.columns:
        st.success("✅ **'alcaldia' column EXISTS in cuadrantes!**")
        st.write("**Unique alcaldías in cuadrantes:**", cuadrantes['alcaldia'].nunique())
        st.write("**Alcaldia value counts:**")
        st.dataframe(cuadrantes['alcaldia'].value_counts())
    else:
        st.error("❌ **No 'alcaldia' column found in cuadrantes**")
        st.write("This column is needed to map cuadrantes to boroughs")
        st.write("**Available columns:**", cuadrantes.columns.tolist())
    
    if 'geo_shape' in cuadrantes.columns:
        st.subheader("geo_shape structure:")
        sample_shape = cuadrantes['geo_shape'].dropna().iloc[0] if len(cuadrantes['geo_shape'].dropna()) > 0 else None
        if sample_shape:
            st.write("**Type:**", type(sample_shape))
            st.write("**Sample geo_shape (first 500 chars):**")
            st.json(sample_shape if isinstance(sample_shape, dict) else str(sample_shape)[:500])
    
    
    # ==========================================
    # DATA QUALITY CHECK
    # ==========================================
    st.header("3️⃣ Data Quality Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Valid Coordinates", f"{len(df):,}")
    with col2:
        st.metric("Unique Alcaldías (Crime)", df['alcaldia_hecho'].nunique() if 'alcaldia_hecho' in df.columns else 0)
    with col3:
        st.metric("Cuadrantes", len(cuadrantes))
# Add this section after the "3️⃣ Data Quality Summary" section in your data_checker.py

    # ==========================================
    # DELITO TYPES ANALYSIS
    # ==========================================
    st.header("4️⃣ Delito (Crime Type) Analysis")
    
    if 'delito' in df.columns:
        delito_counts = df['delito'].value_counts()
        
        st.subheader("📊 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Unique Crime Types", len(delito_counts))
        with col2:
            st.metric("Total Crime Records", len(df))
        with col3:
            most_common = delito_counts.index[0] if len(delito_counts) > 0 else "N/A"
            st.metric("Most Common Crime", most_common, f"{delito_counts.iloc[0]:,} times")
        
        st.subheader("📋 All Delito Types with Counts")
        
        # Create a dataframe for better display
        delito_df = pd.DataFrame({
            'Crime Type': delito_counts.index,
            'Count': delito_counts.values,
            'Percentage': (delito_counts.values / len(df) * 100).round(2)
        })
        delito_df['Percentage'] = delito_df['Percentage'].apply(lambda x: f"{x}%")
        
        st.dataframe(
            delito_df,
            use_container_width=True,
            height=400
        )
        
        # Download button for the data
        csv = delito_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Delito Types as CSV",
            data=csv,
            file_name="delito_types.csv",
            mime="text/csv"
        )
        
        st.subheader("🔍 Sample Delito Values")
        st.write("First 20 unique crime types:")
        for i, (delito, count) in enumerate(delito_counts.head(20).items(), 1):
            st.text(f"{i:2d}. [{count:>6,}] {delito}")
        
        # Show keywords analysis
        st.subheader("🔤 Keyword Analysis")
        st.write("Analyzing common patterns in crime descriptions...")
        
        keywords = {
            'VEHICULO/VEHÍCULO': 0,
            'MOTOCICLETA/MOTO': 0,
            'AUTOBUS/AUTOBÚS': 0,
            'CAMION/CAMIÓN': 0,
            'TAXI': 0,
            'CARGA': 0,
            'CON VIOLENCIA': 0,
            'SIN VIOLENCIA': 0
        }
        
        for delito in df['delito'].dropna():
            delito_upper = str(delito).upper()
            if 'VEHICULO' in delito_upper or 'VEHÍCULO' in delito_upper:
                keywords['VEHICULO/VEHÍCULO'] += 1
            if 'MOTOCICLETA' in delito_upper or 'MOTO' in delito_upper:
                keywords['MOTOCICLETA/MOTO'] += 1
            if 'AUTOBUS' in delito_upper or 'AUTOBÚS' in delito_upper:
                keywords['AUTOBUS/AUTOBÚS'] += 1
            if 'CAMION' in delito_upper or 'CAMIÓN' in delito_upper:
                keywords['CAMION/CAMIÓN'] += 1
            if 'TAXI' in delito_upper:
                keywords['TAXI'] += 1
            if 'CARGA' in delito_upper:
                keywords['CARGA'] += 1
            if 'CON VIOLENCIA' in delito_upper:
                keywords['CON VIOLENCIA'] += 1
            if 'SIN VIOLENCIA' in delito_upper:
                keywords['SIN VIOLENCIA'] += 1
        
        keyword_df = pd.DataFrame({
            'Keyword': keywords.keys(),
            'Count': keywords.values(),
            'Percentage': [(v / len(df) * 100) for v in keywords.values()]
        })
        keyword_df['Percentage'] = keyword_df['Percentage'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(keyword_df, use_container_width=True)
        
    else:
        st.error("❌ 'delito' column not found in dataset")
# ==========================================
    # AGENCIA ANALYSIS
    # ==========================================
    st.header("5️⃣ Agencia List")
    
    if 'agencia' in df.columns:
        # Get all unique agencias
        unique_agencias = sorted(df['agencia'].dropna().unique())
        
        st.subheader(f"📋 All Unique Agencias ({len(unique_agencias)} total)")
        
        # Display as a simple list
        for i, agencia in enumerate(unique_agencias, 1):
            st.text(f"{i:3d}. {agencia}")
        
        # Download button
        agencia_list_df = pd.DataFrame({'Agencia': unique_agencias})
        csv = agencia_list_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Agencias List as CSV",
            data=csv,
            file_name="agencias_list.csv",
            mime="text/csv",
            key="download_agencia"
        )
        
    else:
        st.error("❌ 'agencia' column not found in dataset")
        st.write("**Available columns:**", df.columns.tolist())