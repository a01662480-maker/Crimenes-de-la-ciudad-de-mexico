import streamlit as st
import json
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client
import ast

def show():
    """Display the interactive crime map"""
    st.title("🗺️ Mapa de la Ciudad de México")

    # -------------------------
    # Configuration
    # -------------------------
    SUPABASE_URL = "https://xzeycsqwynjxnzgctydr.supabase.co"
    SUPABASE_KEY = "sb_publishable_wSTGdAAY_IIuYKNpr6N6GA_rGZy-y29"
    SUPABASE_TABLE = "FGJ"
    SUPABASE_TABLE_CUADRANTS = "cuadrantes"

    CDMX_CENTER = [19.4326, -99.1332]

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # -------------------------
    # Helper Functions
    # -------------------------
    def normalize_alcaldia_name(name):
        """Normalize alcaldia names for matching"""
        if pd.isna(name):
            return None
        import unicodedata
        
        name = str(name).upper().strip()
        name = ''.join(c for c in unicodedata.normalize('NFD', name) 
                    if unicodedata.category(c) != 'Mn')
        name = name.replace('.', '')
        name = name.replace(' DE MORELOS', '')
        if name.startswith('LA '):
            name = name[3:]
        name = ' '.join(name.split())
        
        return name


    def match_alcaldia_name(alcaldia_name, cuadrantes_alcaldia_name):
        """Check if two alcaldia names match"""
        norm1 = normalize_alcaldia_name(alcaldia_name)
        norm2 = normalize_alcaldia_name(cuadrantes_alcaldia_name)
        return norm1 == norm2

    # -------------------------
    # Data Loading Functions
    # -------------------------
    @st.cache_data(show_spinner=False)
    def load_alcaldias():
        """Load alcaldías GeoJSON"""
        try:
            with open('alcaldias.json', 'r', encoding='utf-8') as f:
                geojson = json.load(f)
            
            # Calculate bounds for each alcaldía
            alcaldia_bounds = {}
            for feature in geojson['features']:
                name = feature['properties'].get('NOMGEO', 'Unknown')
                feature['properties']['name'] = name
                feature['properties']['name_normalized'] = normalize_alcaldia_name(name)
                
                # Calculate bounds
                if feature['geometry']['type'] == 'Polygon':
                    coords = feature['geometry']['coordinates'][0]
                else:  # MultiPolygon
                    coords = []
                    for polygon in feature['geometry']['coordinates']:
                        coords.extend(polygon[0])
                
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                
                alcaldia_bounds[name] = {
                    'center': [sum(lats) / len(lats), sum(lons) / len(lons)],
                    'bounds': [[min(lons), min(lats)], [max(lons), max(lats)]]
                }
            
            return geojson, alcaldia_bounds
        except FileNotFoundError:
            st.error("❌ alcaldias.json not found")
            return None, {}

    @st.cache_data(show_spinner=False)
    def load_population_data():
        """Load population data from JSON"""
        try:
            with open('caractersticas-demogrficas-nivel-ageb.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract features and create DataFrame
            if 'features' in data:
                # GeoJSON format
                records = [f['properties'] for f in data['features']]
            else:
                # Direct JSON array
                records = data
            
            df = pd.DataFrame(records)
            
            # Group by alcaldía and sum population
            pop_df = df.groupby('alc')['pob'].sum().reset_index()
            pop_df.columns = ['alcaldia', 'population']
            pop_df['alcaldia_normalized'] = pop_df['alcaldia'].apply(normalize_alcaldia_name)
            
            # Create dictionary for easy lookup
            pop_dict = dict(zip(pop_df['alcaldia_normalized'], pop_df['population']))
            
            return pop_dict
        except FileNotFoundError:
            st.warning("⚠️ Population data file not found")
            return {}
        except Exception as e:
            st.warning(f"⚠️ Error loading population data: {str(e)}")
            return {}

    @st.cache_data(show_spinner=False, ttl=3600)
    def load_cuadrantes():
        """Load cuadrantes from Supabase and organize by alcaldía"""
        res = supabase.table(SUPABASE_TABLE_CUADRANTS).select("*").execute()
        cuadrantes_df = pd.DataFrame(res.data)
        
        if "geo_shape" in cuadrantes_df.columns:
            def parse_shape(v):
                try:
                    return ast.literal_eval(v) if isinstance(v, str) else v
                except:
                    return None
            cuadrantes_df["geo_shape"] = cuadrantes_df["geo_shape"].apply(parse_shape)
        
        cuadrantes_df['alcaldia_normalized'] = cuadrantes_df['alcaldia'].apply(normalize_alcaldia_name)
        
        # Organize cuadrantes by alcaldía
        cuadrantes_by_alcaldia = {}
        
        for alcaldia in cuadrantes_df['alcaldia'].unique():
            matched_df = cuadrantes_df[cuadrantes_df['alcaldia'] == alcaldia]
            
            features = []
            for idx, row in matched_df.iterrows():
                if row['geo_shape'] and isinstance(row['geo_shape'], dict) and 'coordinates' in row['geo_shape']:
                    feature = {
                        'type': 'Feature',
                        'geometry': row['geo_shape'],
                        'properties': {
                            'id': str(row['id']),
                            'no_cuadran': str(row['no_cuadran']),
                            'alcaldia': row['alcaldia'],
                            'sector': str(row.get('sector', '')),
                            'zona': str(row.get('zona', '')),
                            'crime_count': 0  # Will be filled later
                        }
                    }
                    features.append(feature)
            
            if features:
                normalized_name = normalize_alcaldia_name(alcaldia)
                cuadrantes_by_alcaldia[normalized_name] = {
                    'type': 'FeatureCollection',
                    'features': features
                }
        
        return cuadrantes_by_alcaldia, cuadrantes_df

    @st.cache_data(show_spinner=False)
    def perform_spatial_join_optimized(crime_points_df, cuadrantes_by_alcaldia):
        """
        Optimized spatial join using GeoPandas with spatial indexing.
        Returns the same cuadrante_crime_data structure as the original implementation.
        """
        import geopandas as gpd
        from shapely.geometry import shape
        
        # Step 1: Convert cuadrantes to GeoDataFrame
        # Extract all cuadrante features from the nested dict
        cuadrante_records = []
        for alcaldia_norm, cuadrante_geojson in cuadrantes_by_alcaldia.items():
            for feature in cuadrante_geojson['features']:
                cuadrante_records.append({
                    'cuadrante_id': feature['properties']['id'],
                    'alcaldia_normalized': alcaldia_norm,
                    'geometry': shape(feature['geometry']),
                    'no_cuadran': feature['properties']['no_cuadran'],
                    'alcaldia': feature['properties']['alcaldia'],
                    'sector': feature['properties']['sector'],
                    'zona': feature['properties']['zona']
                })
        
        cuadrantes_gdf = gpd.GeoDataFrame(cuadrante_records, crs='EPSG:4326')
        
        # Step 2: Convert crimes to GeoDataFrame
        crimes_gdf = gpd.GeoDataFrame(
            crime_points_df,
            geometry=gpd.points_from_xy(
                crime_points_df['longitud'], 
                crime_points_df['latitud']
            ),
            crs='EPSG:4326'
        )
        
        # Step 3: Perform spatial join with GeoPandas (uses spatial index automatically)
        joined = gpd.sjoin(crimes_gdf, cuadrantes_gdf, how='left', predicate='within')
        
        # Step 4: Initialize cuadrante_crime_data structure
        cuadrante_crime_data = {}
        for cuadrante_id in cuadrantes_gdf['cuadrante_id'].unique():
            cuadrante_crime_data[cuadrante_id] = {
                'crimes': [],
                'crime_types': {}
            }
        
        # Step 5: Process joined results and populate cuadrante_crime_data
        for idx, row in joined[joined['cuadrante_id'].notna()].iterrows():
            cuadrante_id = row['cuadrante_id']
            crime_type = row['delito'] if pd.notna(row['delito']) else 'Unknown'
            
            cuadrante_crime_data[cuadrante_id]['crimes'].append({
                'type': crime_type,
                'date': row['fecha_hecho'].strftime('%Y-%m-%d') if pd.notna(row['fecha_hecho']) else 'N/A',
                'agencia': row['agencia'] if pd.notna(row['agencia']) else 'N/A'
            })
            
            if crime_type not in cuadrante_crime_data[cuadrante_id]['crime_types']:
                cuadrante_crime_data[cuadrante_id]['crime_types'][crime_type] = 0
            cuadrante_crime_data[cuadrante_id]['crime_types'][crime_type] += 1
        
        return cuadrante_crime_data

    @st.cache_data(show_spinner=True, ttl=3600)
    def load_crime_data(selected_years):
        """Load crime data from Supabase filtered by years"""
        st.info(f"📡 Loading crime data for {', '.join(map(str, selected_years))}...")
        
        all_data = []
        batch_size = 1000
        
        # Get data for selected years plus the previous year for comparison
        latest_year = max(selected_years)
        years_to_load = list(set(selected_years + [latest_year - 1]))
        
        for year in years_to_load:
            offset = 0
            while True:
                res = supabase.table(SUPABASE_TABLE)\
                    .select("alcaldia_hecho, anio_hecho, fecha_hecho, latitud, longitud, delito, agencia")\
                    .eq("anio_hecho", year)\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not res.data:
                    break
                all_data.extend(res.data)
                offset += batch_size
        
        df = pd.DataFrame(all_data)
        df['alcaldia_normalized'] = df['alcaldia_hecho'].apply(normalize_alcaldia_name)
        
        # Parse fecha_hecho and extract month and day of week
        df['fecha_hecho'] = pd.to_datetime(df['fecha_hecho'], errors='coerce')
        df['month'] = df['fecha_hecho'].dt.month  # 1-12
        df['day_of_week'] = df['fecha_hecho'].dt.dayofweek  # 0=Monday, 6=Sunday
        
        # Convert lat/lon to numeric
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        
        st.success(f"✅ Loaded {len(df):,} crime records")
        return df, latest_year

    def calculate_crime_counts(crime_df, alcaldias_geojson, selected_years, population_data):
        """Calculate crime counts and crimes per capita per alcaldía"""
        # Filter to only selected years for the main count
        selected_df = crime_df[crime_df['anio_hecho'].isin(selected_years)]
        
        # Get crime counts by normalized alcaldía name
        crime_counts = selected_df.groupby('alcaldia_normalized').size().to_dict()
        
        # Match to alcaldías in geojson and add crime count property
        all_crime_counts = []
        all_per_capita = []
        
        for feature in alcaldias_geojson['features']:
            alcaldia_norm = feature['properties']['name_normalized']
            crime_count = crime_counts.get(alcaldia_norm, 0)
            population = population_data.get(alcaldia_norm, None)
            
            # Calculate crimes per capita
            if population and population > 0:
                crimes_per_capita = (crime_count / population) * 1000
            else:
                crimes_per_capita = 0
            
            feature['properties']['crime_count'] = crime_count
            feature['properties']['crimes_per_capita'] = round(crimes_per_capita, 2)
            feature['properties']['population'] = int(population) if population else 0
            
            all_crime_counts.append(crime_count)
            all_per_capita.append(crimes_per_capita)
        
        # Get min/max for both metrics
        min_crimes = min(all_crime_counts) if all_crime_counts else 0
        max_crimes = max(all_crime_counts) if all_crime_counts else 0
        min_per_capita = min(all_per_capita) if all_per_capita else 0
        max_per_capita = max(all_per_capita) if all_per_capita else 0
        
        return alcaldias_geojson, {
            'total': {'min': min_crimes, 'max': max_crimes},
            'per_capita': {'min': min_per_capita, 'max': max_per_capita}
        }

    def prepare_alcaldia_analytics(crime_df, alcaldia_normalized, selected_years, latest_year, population_data):
        """Prepare all analytics data for a specific alcaldía"""
        
        # Filter data for this alcaldía
        alcaldia_df = crime_df[crime_df['alcaldia_normalized'] == alcaldia_normalized]
        
        # Get population
        population = population_data.get(alcaldia_normalized, None)
        
        # 1. Total crimes for selected years
        selected_df = alcaldia_df[alcaldia_df['anio_hecho'].isin(selected_years)]
        total_crimes = len(selected_df)
        
        # Calculate crimes per capita (per 1,000 people)
        crimes_per_capita = (total_crimes / population * 1000) if population and population > 0 else None
        
        # 2. Year-over-year change (latest year vs previous year)
        latest_crimes = len(alcaldia_df[alcaldia_df['anio_hecho'] == latest_year])
        previous_crimes = len(alcaldia_df[alcaldia_df['anio_hecho'] == latest_year - 1])
        
        if previous_crimes > 0:
            yoy_change = ((latest_crimes - previous_crimes) / previous_crimes) * 100
        else:
            yoy_change = 0 if latest_crimes == 0 else 100
        
        # 3. Monthly trend data (separate lines for each year)
        # Month is already extracted from fecha_hecho as numeric (1-12)
        monthly_data = []
        for year in selected_years:
            year_df = alcaldia_df[alcaldia_df['anio_hecho'] == year].copy()
            # Filter out rows with invalid months
            year_df = year_df[year_df['month'].notna()]
            
            if len(year_df) > 0:
                monthly_counts = year_df.groupby('month').size().reset_index()
                monthly_counts.columns = ['month', 'crimes']
                monthly_counts['month'] = monthly_counts['month'].astype(int)
                monthly_counts['year'] = year
                monthly_data.append(monthly_counts)
        
        monthly_df = pd.concat(monthly_data, ignore_index=True) if monthly_data else pd.DataFrame()
        
        # 4. Day of week data (aggregated across all selected years)
        # Day of week is already extracted from fecha_hecho as numeric (0=Mon, 6=Sun)
        dow_df = selected_df[selected_df['day_of_week'].notna()].copy()
        
        if len(dow_df) > 0:
            dow_counts = dow_df.groupby('day_of_week').size().reset_index()
            dow_counts.columns = ['day', 'crimes']
            dow_counts['day'] = dow_counts['day'].astype(int)
            dow_counts = dow_counts.sort_values('day')
            dow_df = dow_counts
        else:
            # No valid day of week data
            dow_df = pd.DataFrame()
        
        # 5. Ranking among all alcaldías
        all_alcaldias_df = crime_df[crime_df['anio_hecho'].isin(selected_years)]
        ranking_df = all_alcaldias_df.groupby('alcaldia_normalized').size().reset_index()
        ranking_df.columns = ['alcaldia', 'crimes']
        ranking_df = ranking_df.sort_values('crimes', ascending=False).reset_index(drop=True)
        ranking_df['rank'] = ranking_df.index + 1
        
        current_rank = ranking_df[ranking_df['alcaldia'] == alcaldia_normalized]['rank'].values
        rank = int(current_rank[0]) if len(current_rank) > 0 else 0
        total_alcaldias = len(ranking_df)
        
        return {
            'total_crimes': total_crimes,
            'population': int(population) if population else None,
            'crimes_per_capita': round(crimes_per_capita, 2) if crimes_per_capita else None,
            'yoy_change': yoy_change,
            'latest_year': latest_year,
            'monthly_trend': monthly_df.to_dict('records'),
            'day_of_week': dow_df.to_dict('records'),
            'rank': rank,
            'total_alcaldias': total_alcaldias
        }

    # -------------------------
    # Sidebar - Year Filter
    # -------------------------
    st.sidebar.header("📅 Periodo de tiempo")

    # Get available years (you can adjust this range)
    available_years = list(range(2015,2025))

    selected_years = st.sidebar.multiselect(
        "años seleccionados:",
        options=available_years,
        default=[2024]
    )

    if not selected_years:
        st.warning("⚠️ Please select at least one year")
        st.stop()

    # Map coloring metric selector
    st.sidebar.header("🗺️ Resultados del mapa")
    map_metric = st.sidebar.radio(
        "Mostrar alcaldías por:",
        options=["Total Crímenes", "Crímenes per ápita"],
        index=0,
        help="Elige cómo colorear el mapa: por el total de delitos o por la tasa de delitos por cada 1,000 habitantes."
    )

    # -------------------------
    # Load Data
    # -------------------------
    with st.spinner("Loading map data..."):
        alcaldias_geojson, alcaldia_bounds = load_alcaldias()
        cuadrantes_by_alcaldia, cuadrantes_df = load_cuadrantes()
        crime_df, latest_year = load_crime_data(selected_years)
        population_data = load_population_data()

    if not alcaldias_geojson:
        st.stop()

    # -------------------------
    # Prepare Crime Points and Cuadrante Stats
    # -------------------------
    # Filter to selected years only for points display
    selected_crime_df = crime_df[crime_df['anio_hecho'].isin(selected_years)]

    # Remove rows with invalid coordinates
    crime_points_df = selected_crime_df[
        (selected_crime_df['latitud'].notna()) & 
        (selected_crime_df['longitud'].notna()) &
        (selected_crime_df['latitud'] != 0) &
        (selected_crime_df['longitud'] != 0)
    ].copy()

    # Get unique crime types and assign colors based on violence
    crime_type_colors = {}
    crime_violence_categories = {}

    # Define colors for violence categories
    VIOLENCE_COLORS = {
        'con_violencia': '#dc3545',      # Red for with violence
        'sin_violencia': '#28a745',      # Green for without violence
        'unknown': '#6c757d'             # Gray for unknown
    }

    def categorize_crime_by_violence(delito_text):
        """Categorize crime by violence level"""
        if pd.isna(delito_text):
            return 'unknown'
        
        delito_lower = str(delito_text).lower()
        
        if 'con violencia' in delito_lower:
            return 'con_violencia'
        elif 'sin violencia' in delito_lower:
            return 'sin_violencia'
        else:
            return 'unknown'

    # Categorize each crime
    crime_points_df['violence_category'] = crime_points_df['delito'].apply(categorize_crime_by_violence)

    # Assign colors based on violence category
    for _, row in crime_points_df.iterrows():
        delito = row['delito'] if pd.notna(row['delito']) else 'Unknown'
        violence_cat = row['violence_category']
        crime_type_colors[delito] = VIOLENCE_COLORS[violence_cat]
        crime_violence_categories[delito] = violence_cat

    # Count crimes by violence category for legend
    violence_counts = crime_points_df['violence_category'].value_counts().to_dict()

    # Spatial join: match crimes to cuadrantes using optimized GeoPandas
    st.info("🔄 Performing spatial join to match crimes to cuadrantes...")

    # Use optimized spatial join function
    cuadrante_crime_data = perform_spatial_join_optimized(crime_points_df, cuadrantes_by_alcaldia)

    # Update cuadrante features with crime counts and top crime types
    for alcaldia_norm, cuadrante_geojson in cuadrantes_by_alcaldia.items():
        for feature in cuadrante_geojson['features']:
            cuadrante_id = feature['properties']['id']
            crime_count = len(cuadrante_crime_data[cuadrante_id]['crimes'])
            
            # Get top 5 crime types
            crime_types = cuadrante_crime_data[cuadrante_id]['crime_types']
            top_crimes = sorted(crime_types.items(), key=lambda x: x[1], reverse=True)[:5]
            
            feature['properties']['crime_count'] = crime_count
            feature['properties']['top_crimes'] = [
                {'type': crime_type, 'count': count} 
                for crime_type, count in top_crimes
            ]

    # Organize crime points by alcaldía
    crime_points_by_alcaldia = {}
    for alcaldia_norm in crime_points_df['alcaldia_normalized'].unique():
        alcaldia_crimes = crime_points_df[crime_points_df['alcaldia_normalized'] == alcaldia_norm]
        
        features = []
        for _, row in alcaldia_crimes.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(row['longitud']), float(row['latitud'])]
                },
                'properties': {
                    'delito': str(row['delito']) if pd.notna(row['delito']) else 'Unknown',
                    'agencia': str(row['agencia']) if pd.notna(row['agencia']) else 'N/A',
                    'fecha': row['fecha_hecho'].strftime('%Y-%m-%d') if pd.notna(row['fecha_hecho']) else 'N/A',
                    'color': crime_type_colors.get(row['delito'], '#999999')
                }
            }
            features.append(feature)
        
        crime_points_by_alcaldia[alcaldia_norm] = {
            'type': 'FeatureCollection',
            'features': features
        }

    # Calculate min/max for cuadrante coloring
    all_cuadrante_counts = []
    for cuadrante_geojson in cuadrantes_by_alcaldia.values():
        for feature in cuadrante_geojson['features']:
            all_cuadrante_counts.append(feature['properties']['crime_count'])

    cuadrante_min = min(all_cuadrante_counts) if all_cuadrante_counts else 0
    cuadrante_max = max(all_cuadrante_counts) if all_cuadrante_counts else 0

    st.success("✅ Spatial join complete!")

    # Calculate crime counts and add to alcaldías
    alcaldias_geojson, metric_ranges = calculate_crime_counts(crime_df, alcaldias_geojson, selected_years, population_data)

    # Determine which metric to use for map coloring
    map_metric_key = 'per_capita' if map_metric == "Crimes per Capita" else 'total'
    min_value = metric_ranges[map_metric_key]['min']
    max_value = metric_ranges[map_metric_key]['max']

    # -------------------------
    # Prepare Analytics Data for Panel
    # -------------------------
    # Prepare analytics for all alcaldías
    analytics_data = {}
    for feature in alcaldias_geojson['features']:
        alcaldia_norm = feature['properties']['name_normalized']
        analytics_data[alcaldia_norm] = prepare_alcaldia_analytics(
            crime_df, alcaldia_norm, selected_years, latest_year, population_data
        )

    # -------------------------
    # Create HTML Map
    # -------------------------
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8' />
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <script src='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js'></script>
        <link href='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css' rel='stylesheet' />
        <style>
            body {{ margin: 0; padding: 0; }}
            #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
            #back-button {{
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 1000;
                background: #007bff;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                cursor: pointer;
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                border: none;
                display: none;
            }}
            #back-button:hover {{
                background: #0056b3;
            }}
            #info {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: white;
                padding: 10px 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
                font-size: 14px;
                display: none;
            }}
            #side-panel {{
                position: absolute;
                top: 0;
                right: -350px;
                width: 350px;
                height: 100%;
                background: white;
                box-shadow: -2px 0 10px rgba(0,0,0,0.3);
                z-index: 1001;
                transition: right 0.3s ease-in-out;
                overflow-y: auto;
                font-family: Arial, sans-serif;
            }}
            #side-panel.open {{
                right: 0;
            }}
            #side-panel-content {{
                padding: 20px;
            }}
            #side-panel-close {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 5px 10px;
            }}
            #side-panel-close:hover {{
                color: #000;
            }}
            .panel-title {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #333;
                padding-right: 30px;
            }}
            .panel-stat {{
                margin-bottom: 15px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }}
            .panel-stat.positive {{
                border-left-color: #28a745;
            }}
            .panel-stat.negative {{
                border-left-color: #dc3545;
            }}
            .panel-stat-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                margin-bottom: 5px;
            }}
            .panel-stat-value {{
                font-size: 28px;
                font-weight: bold;
                color: #333;
            }}
            .panel-stat-subvalue {{
                font-size: 14px;
                margin-top: 5px;
                font-weight: normal;
            }}
            .change-positive {{
                color: #28a745;
            }}
            .change-negative {{
                color: #dc3545;
            }}
            .chart-container {{
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 5px;
            }}
            .chart-title {{
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
                color: #333;
            }}
            .chart-svg {{
                width: 100%;
                height: 200px;
            }}
            .bar {{
                fill: #007bff;
            }}
            .bar:hover {{
                fill: #0056b3;
            }}
            .line {{
                fill: none;
                stroke-width: 2;
            }}
            .axis {{
                font-size: 10px;
            }}
            .axis-label {{
                font-size: 11px;
                fill: #666;
            }}
            .panel-hint {{
                margin-top: 20px;
                padding: 10px;
                background: #e7f3ff;
                border-radius: 5px;
                font-size: 12px;
                color: #0066cc;
            }}
            #legend {{
                position: absolute;
                bottom: 30px;
                right: 10px;
                z-index: 1000;
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
                font-size: 12px;
                transition: right 0.3s ease-in-out;
            }}
            #legend.panel-open {{
                right: 360px;
            }}
            #crime-type-legend {{
                position: absolute;
                bottom: 30px;
                left: 10px;
                z-index: 1000;
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
                font-size: 11px;
                max-width: 200px;
                max-height: 400px;
                overflow-y: auto;
                display: none;
            }}
            .crime-type-item {{
                display: flex;
                align-items: center;
                margin-bottom: 5px;
            }}
            .crime-type-color {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
                flex-shrink: 0;
            }}
            .crime-type-label {{
                font-size: 10px;
                line-height: 1.2;
            }}
            .legend-title {{
                font-weight: bold;
                margin-bottom: 10px;
                font-size: 13px;
            }}
            .legend-scale {{
                display: flex;
                align-items: center;
                margin-top: 5px;
            }}
            .legend-gradient {{
                width: 150px;
                height: 15px;
                background: linear-gradient(to right, 
                    rgb(173, 216, 230), 
                    rgb(100, 149, 237), 
                    rgb(65, 105, 225), 
                    rgb(255, 140, 0), 
                    rgb(255, 69, 0), 
                    rgb(220, 20, 60));
                border: 1px solid #ccc;
                margin: 0 5px;
            }}
            .legend-labels {{
                display: flex;
                justify-content: space-between;
                width: 150px;
                margin: 5px 5px 0 5px;
                font-size: 11px;
            }}
        </style>
    </head>
    <body>
        <div id='map'></div>
        <button id='back-button'>⬅️ Back to City View</button>
        <div id='info'></div>
        
        <!-- Side Panel -->
        <div id='side-panel'>
            <button id='side-panel-close'>×</button>
            <div id='side-panel-content'>
                <!-- Content will be populated by JavaScript -->
            </div>
        </div>
        
        <div id='legend'>
            <div class='legend-title'>{map_metric} ({', '.join(map(str, selected_years))})</div>
            <div class='legend-gradient'></div>
            <div class='legend-labels'>
                <span>{min_value:.1f}</span>
                <span>{max_value:.1f}</span>
            </div>
        </div>
        
        <div id='crime-type-legend'>
            <div class='legend-title'>Crime Types</div>
            <div id='crime-type-list'></div>
        </div>

        <script>
            // Data from Python
            const alcaldiasData = {json.dumps(alcaldias_geojson)};
            const alcaldiaBounds = {json.dumps(alcaldia_bounds)};
            const cuadrantesData = {json.dumps(cuadrantes_by_alcaldia)};
            const crimePointsData = {json.dumps(crime_points_by_alcaldia)};
            const crimeTypeColors = {json.dumps(crime_type_colors)};
            const violenceCounts = {json.dumps(violence_counts)};
            const cuadranteMin = {cuadrante_min};
            const cuadranteMax = {cuadrante_max};
            const analyticsData = {json.dumps(analytics_data)};
            const mapMetric = {json.dumps(map_metric_key)};
            const minValue = {min_value};
            const maxValue = {max_value};
            const selectedYears = {json.dumps(selected_years)};
            
            // State
            let currentView = 'city';
            let selectedAlcaldia = null;
            let clickTimeout = null;
            let hoveredCuadranteId = null;
            
            // Get the appropriate value based on selected metric
            function getMetricValue(properties) {{
                if (mapMetric === 'per_capita') {{
                    return properties.crimes_per_capita || 0;
                }} else {{
                    return properties.crime_count || 0;
                }}
            }}
            
            // Color interpolation for cuadrantes
            function getCuadranteColor(count) {{
                if (cuadranteMax === cuadranteMin) return 'rgb(173, 216, 230)';
                
                const normalized = (count - cuadranteMin) / (cuadranteMax - cuadranteMin);
                
                if (normalized < 0.2) {{
                    const t = normalized / 0.2;
                    return `rgb(${{173 + (100-173)*t}}, ${{216 + (149-216)*t}}, ${{230 + (237-230)*t}})`;
                }} else if (normalized < 0.4) {{
                    const t = (normalized - 0.2) / 0.2;
                    return `rgb(${{100 + (65-100)*t}}, ${{149 + (105-149)*t}}, ${{237 + (225-237)*t}})`;
                }} else if (normalized < 0.6) {{
                    const t = (normalized - 0.4) / 0.2;
                    return `rgb(${{65 + (255-65)*t}}, ${{105 + (140-105)*t}}, ${{225 + (0-225)*t}})`;
                }} else if (normalized < 0.8) {{
                    const t = (normalized - 0.6) / 0.2;
                    return `rgb(255, ${{140 + (69-140)*t}}, 0)`;
                }} else {{
                    const t = (normalized - 0.8) / 0.2;
                    return `rgb(${{255 + (220-255)*t}}, ${{69 + (20-69)*t}}, ${{0 + (60-0)*t}})`;
                }}
            }}
            
            // Color interpolation function (Blue → Red)
            function getCrimeColor(value) {{
                if (maxValue === minValue) return 'rgb(173, 216, 230)';
                
                const normalized = (value - minValue) / (maxValue - minValue);
                
                // Color stops: Light Blue → Cornflower Blue → Royal Blue → Orange → Red-Orange → Crimson
                if (normalized < 0.2) {{
                    const t = normalized / 0.2;
                    return `rgb(${{173 + (100-173)*t}}, ${{216 + (149-216)*t}}, ${{230 + (237-230)*t}})`;
                }} else if (normalized < 0.4) {{
                    const t = (normalized - 0.2) / 0.2;
                    return `rgb(${{100 + (65-100)*t}}, ${{149 + (105-149)*t}}, ${{237 + (225-237)*t}})`;
                }} else if (normalized < 0.6) {{
                    const t = (normalized - 0.4) / 0.2;
                    return `rgb(${{65 + (255-65)*t}}, ${{105 + (140-105)*t}}, ${{225 + (0-225)*t}})`;
                }} else if (normalized < 0.8) {{
                    const t = (normalized - 0.6) / 0.2;
                    return `rgb(255, ${{140 + (69-140)*t}}, 0)`;
                }} else {{
                    const t = (normalized - 0.8) / 0.2;
                    return `rgb(${{255 + (220-255)*t}}, ${{69 + (20-69)*t}}, ${{0 + (60-0)*t}})`;
                }}
            }}
            
            // Side panel functions
            function openSidePanel(alcaldiaName, crimeCount, alcaldiaNormalized) {{
                const panel = document.getElementById('side-panel');
                const legend = document.getElementById('legend');
                const content = document.getElementById('side-panel-content');
                
                // Get analytics data for this alcaldía
                const analytics = analyticsData[alcaldiaNormalized];
                
                if (!analytics) {{
                    console.error('No analytics data found for:', alcaldiaNormalized);
                    content.innerHTML = `
                        <div class="panel-title">${{alcaldiaName}}</div>
                        <div class="panel-stat">
                            <div class="panel-stat-label">Error</div>
                            <div class="panel-stat-value">No data available</div>
                        </div>
                    `;
                    panel.classList.add('open');
                    legend.classList.add('panel-open');
                    return;
                }}
                
                // Count cuadrantes for this alcaldía
                const cuadranteCount = cuadrantesData[alcaldiaNormalized] ? 
                    cuadrantesData[alcaldiaNormalized].features.length : 0;
                
                // Format year-over-year change
                const yoyClass = analytics.yoy_change >= 0 ? 'change-positive' : 'change-negative';
                const yoySymbol = analytics.yoy_change >= 0 ? '↑' : '↓';
                const yoyText = Math.abs(analytics.yoy_change).toFixed(1);
                
                // Create monthly trend chart
                const monthlyChart = createMonthlyTrendChart(analytics.monthly_trend);
                
                // Create day of week chart
                const dowChart = createDayOfWeekChart(analytics.day_of_week);
                
                content.innerHTML = `
                    <div class="panel-title">${{alcaldiaName}}</div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Total Crimes</div>
                        <div class="panel-stat-value">${{analytics.total_crimes.toLocaleString()}}</div>
                        <div class="panel-stat-subvalue">Across selected years</div>
                    </div>
                    
                    ${{analytics.population ? `
                    <div class="panel-stat">
                        <div class="panel-stat-label">Population</div>
                        <div class="panel-stat-value">${{analytics.population.toLocaleString()}}</div>
                    </div>
                    ` : ''}}
                    
                    ${{analytics.crimes_per_capita ? `
                    <div class="panel-stat">
                        <div class="panel-stat-label">Crime Rate</div>
                        <div class="panel-stat-value">${{analytics.crimes_per_capita}}</div>
                        <div class="panel-stat-subvalue">per 1,000 people</div>
                    </div>
                    ` : ''}}
                    
                    <div class="panel-stat ${{analytics.yoy_change >= 0 ? 'positive' : 'negative'}}">
                        <div class="panel-stat-label">Year-over-Year Change</div>
                        <div class="panel-stat-value ${{yoyClass}}">
                            ${{yoySymbol}} ${{yoyText}}%
                        </div>
                        <div class="panel-stat-subvalue">
                            ${{analytics.latest_year}} vs ${{analytics.latest_year - 1}}
                        </div>
                    </div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Crime Ranking</div>
                        <div class="panel-stat-value">#${{analytics.rank}}</div>
                        <div class="panel-stat-subvalue">out of ${{analytics.total_alcaldias}} alcaldías</div>
                    </div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Cuadrantes</div>
                        <div class="panel-stat-value">${{cuadranteCount}}</div>
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-title">Monthly Crime Trend</div>
                        ${{monthlyChart}}
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-title">Crimes by Day of Week</div>
                        ${{dowChart}}
                    </div>
                    
                    <div class="panel-hint">
                        💡 <strong>Tip:</strong> Double-click on the alcaldía to zoom in and view cuadrantes
                    </div>
                `;
                
                panel.classList.add('open');
                legend.classList.add('panel-open');
            }}
            
            function openCuadrantePanel(cuadranteProps, alcaldiaName) {{
                const panel = document.getElementById('side-panel');
                const legend = document.getElementById('legend');
                const content = document.getElementById('side-panel-content');
                
                const crimeCount = cuadranteProps.crime_count || 0;
                const topCrimes = cuadranteProps.top_crimes || [];
                
                // Create top crimes chart
                const topCrimesChart = createTopCrimesChart(topCrimes, crimeCount);
                
                content.innerHTML = `
                    <div style="font-size: 12px; color: #666; margin-bottom: 10px;">
                        ${{alcaldiaName}} > Cuadrante ${{cuadranteProps.no_cuadran}}
                    </div>
                    <div class="panel-title">Cuadrante ${{cuadranteProps.no_cuadran}}</div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Total Crimes</div>
                        <div class="panel-stat-value">${{crimeCount.toLocaleString()}}</div>
                        <div class="panel-stat-subvalue">In selected years</div>
                    </div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Sector</div>
                        <div class="panel-stat-value" style="font-size: 20px;">${{cuadranteProps.sector || 'N/A'}}</div>
                    </div>
                    
                    <div class="panel-stat">
                        <div class="panel-stat-label">Zona</div>
                        <div class="panel-stat-value" style="font-size: 20px;">${{cuadranteProps.zona || 'N/A'}}</div>
                    </div>
                    
                    ${{topCrimes.length > 0 ? `
                    <div class="chart-container">
                        <div class="chart-title">Top Crime Types</div>
                        ${{topCrimesChart}}
                    </div>
                    ` : '<div style="padding: 20px; text-align: center; color: #999;">No crime data available</div>'}}
                    
                    <div class="panel-hint">
                        💡 <strong>Tip:</strong> Click on individual crime points to see details
                    </div>
                `;
                
                panel.classList.add('open');
                legend.classList.add('panel-open');
            }}
            
            function closeSidePanel() {{
                const panel = document.getElementById('side-panel');
                const legend = document.getElementById('legend');
                panel.classList.remove('open');
                legend.classList.remove('panel-open');
            }}
            
            function createMonthlyTrendChart(monthlyData) {{
                if (!monthlyData || monthlyData.length === 0) {{
                    return '<div style="padding: 20px; text-align: center; color: #999;">No data available</div>';
                }}
                
                const width = 310;
                const height = 180;
                const margin = {{ top: 10, right: 30, bottom: 30, left: 40 }};
                const chartWidth = width - margin.left - margin.right;
                const chartHeight = height - margin.top - margin.bottom;
                
                // Group by year
                const yearGroups = {{}};
                monthlyData.forEach(d => {{
                    if (!yearGroups[d.year]) yearGroups[d.year] = [];
                    yearGroups[d.year].push(d);
                }});
                
                // Get scales
                const maxCrimes = Math.max(...monthlyData.map(d => d.crimes));
                const xScale = (month) => margin.left + ((month - 1) / 11) * chartWidth;
                const yScale = (crimes) => margin.top + chartHeight - (crimes / maxCrimes) * chartHeight;
                
                // Colors for different years
                const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8'];
                
                let svg = `<svg class="chart-svg" viewBox="0 0 ${{width}} ${{height}}">`;
                
                // Y axis
                svg += `<line x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{margin.top + chartHeight}}" stroke="#ccc" />`;
                
                // X axis
                svg += `<line x1="${{margin.left}}" y1="${{margin.top + chartHeight}}" x2="${{margin.left + chartWidth}}" y2="${{margin.top + chartHeight}}" stroke="#ccc" />`;
                
                // Month labels
                for (let i = 1; i <= 12; i++) {{
                    const x = xScale(i);
                    if (i % 3 === 1) {{
                        const monthNames = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
                        svg += `<text x="${{x}}" y="${{margin.top + chartHeight + 15}}" class="axis" text-anchor="middle">${{monthNames[i-1]}}</text>`;
                    }}
                }}
                
                // Y axis labels
                const yTicks = [0, maxCrimes / 2, maxCrimes];
                yTicks.forEach(tick => {{
                    const y = yScale(tick);
                    svg += `<text x="${{margin.left - 5}}" y="${{y}}" class="axis" text-anchor="end" dominant-baseline="middle">${{Math.round(tick)}}</text>`;
                }});
                
                // Draw lines for each year
                Object.keys(yearGroups).forEach((year, idx) => {{
                    const data = yearGroups[year].sort((a, b) => a.month - b.month);
                    const color = colors[idx % colors.length];
                    
                    let pathD = '';
                    data.forEach((d, i) => {{
                        const x = xScale(d.month);
                        const y = yScale(d.crimes);
                        pathD += i === 0 ? `M ${{x}} ${{y}}` : ` L ${{x}} ${{y}}`;
                    }});
                    
                    svg += `<path d="${{pathD}}" class="line" stroke="${{color}}" />`;
                    
                    // Add dots
                    data.forEach(d => {{
                        const x = xScale(d.month);
                        const y = yScale(d.crimes);
                        svg += `<circle cx="${{x}}" cy="${{y}}" r="3" fill="${{color}}" />`;
                    }});
                }});
                
                // Legend
                let legendY = 15;
                Object.keys(yearGroups).forEach((year, idx) => {{
                    const color = colors[idx % colors.length];
                    svg += `<rect x="${{width - margin.right - 50}}" y="${{legendY}}" width="15" height="3" fill="${{color}}" />`;
                    svg += `<text x="${{width - margin.right - 30}}" y="${{legendY + 2}}" class="axis" dominant-baseline="middle">${{year}}</text>`;
                    legendY += 12;
                }});
                
                svg += '</svg>';
                return svg;
            }}
            
            function createTopCrimesChart(topCrimes, totalCount) {{
                if (!topCrimes || topCrimes.length === 0) {{
                    return '<div style="padding: 20px; text-align: center; color: #999;">No crime data available</div>';
                }}
                
                const width = 310;
                const height = Math.max(150, topCrimes.length * 35);
                const margin = {{ top: 10, right: 40, bottom: 10, left: 10 }};
                const chartWidth = width - margin.left - margin.right;
                const chartHeight = height - margin.top - margin.bottom;
                
                const maxCount = Math.max(...topCrimes.map(d => d.count));
                
                // Function to determine color based on violence
                function getViolenceColor(crimeType) {{
                    const typeLower = crimeType.toLowerCase();
                    if (typeLower.includes('con violencia')) {{
                        return '#dc3545'; // Red
                    }} else if (typeLower.includes('sin violencia')) {{
                        return '#28a745'; // Green
                    }} else {{
                        return '#6c757d'; // Gray
                    }}
                }}
                
                let svg = `<svg class="chart-svg" viewBox="0 0 ${{width}} ${{height}}" style="height: ${{height}}px;">`;
                
                topCrimes.forEach((crime, i) => {{
                    const y = margin.top + (i * 35);
                    const barWidth = (crime.count / maxCount) * (chartWidth - 100);
                    const percentage = ((crime.count / totalCount) * 100).toFixed(1);
                    const color = getViolenceColor(crime.type);
                    
                    // Crime type label
                    const crimeLabel = crime.type.length > 25 ? crime.type.substring(0, 25) + '...' : crime.type;
                    svg += `<text x="${{margin.left}}" y="${{y + 12}}" class="axis" text-anchor="start" font-size="10">${{crimeLabel}}</text>`;
                    
                    // Bar
                    svg += `<rect x="${{margin.left}}" y="${{y + 15}}" width="${{barWidth}}" height="15" fill="${{color}}" opacity="0.8" />`;
                    
                    // Count and percentage
                    svg += `<text x="${{margin.left + barWidth + 5}}" y="${{y + 26}}" class="axis" text-anchor="start" font-size="10">${{crime.count}} (${{percentage}}%)</text>`;
                }});
                
                svg += '</svg>';
                return svg;
            }}
            
            function createDayOfWeekChart(dowData) {{
                if (!dowData || dowData.length === 0) {{
                    return '<div style="padding: 20px; text-align: center; color: #999;">No day of week data available</div>';
                }}
                
                const width = 310;
                const height = 180;
                const margin = {{ top: 10, right: 10, bottom: 50, left: 40 }};
                const chartWidth = width - margin.left - margin.right;
                const chartHeight = height - margin.top - margin.bottom;
                
                const maxCrimes = Math.max(...dowData.map(d => d.crimes));
                const barWidth = chartWidth / dowData.length - 5;
                
                let svg = `<svg class="chart-svg" viewBox="0 0 ${{width}} ${{height}}">`;
                
                // Y axis
                svg += `<line x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{margin.top + chartHeight}}" stroke="#ccc" />`;
                
                // X axis
                svg += `<line x1="${{margin.left}}" y1="${{margin.top + chartHeight}}" x2="${{margin.left + chartWidth}}" y2="${{margin.top + chartHeight}}" stroke="#ccc" />`;
                
                // Y axis labels
                const yTicks = [0, maxCrimes / 2, maxCrimes];
                yTicks.forEach(tick => {{
                    const y = margin.top + chartHeight - (tick / maxCrimes) * chartHeight;
                    svg += `<text x="${{margin.left - 5}}" y="${{y}}" class="axis" text-anchor="end" dominant-baseline="middle">${{Math.round(tick)}}</text>`;
                }});
                
                // Bars
                dowData.forEach((d, i) => {{
                    const x = margin.left + (i * (barWidth + 5)) + 2.5;
                    const barHeight = (d.crimes / maxCrimes) * chartHeight;
                    const y = margin.top + chartHeight - barHeight;
                    
                    svg += `<rect x="${{x}}" y="${{y}}" width="${{barWidth}}" height="${{barHeight}}" class="bar" />`;
                    svg += `<text x="${{x + barWidth/2}}" y="${{y - 5}}" class="axis" text-anchor="middle" font-size="9">${{d.crimes}}</text>`;
                    
                    // Day labels - handle both string and numeric formats
                    let dayLabel = '';
                    if (typeof d.day === 'number') {{
                        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                        dayLabel = dayNames[d.day] || d.day;
                    }} else {{
                        dayLabel = String(d.day).substring(0, 3);
                    }}
                    
                    svg += `<text x="${{x + barWidth/2}}" y="${{margin.top + chartHeight + 15}}" class="axis" text-anchor="middle" transform="rotate(-45, ${{x + barWidth/2}}, ${{margin.top + chartHeight + 15}})">${{dayLabel}}</text>`;
                }});
                
                svg += '</svg>';
                return svg;
            }}
            
            // Initialize map
            const map = new maplibregl.Map({{
                container: 'map',
                style: {{
                    'version': 8,
                    'sources': {{
                        'osm': {{
                            'type': 'raster',
                            'tiles': ['https://a.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
                            'tileSize': 256,
                            'attribution': '© OpenStreetMap contributors'
                        }}
                    }},
                    'layers': [{{
                        'id': 'osm',
                        'type': 'raster',
                        'source': 'osm'
                    }}]
                }},
                center: {json.dumps(CDMX_CENTER[::-1])},
                zoom: 9.5
            }});
            
            map.on('load', function() {{
                // Add alcaldías source
                map.addSource('alcaldias', {{
                    'type': 'geojson',
                    'data': alcaldiasData
                }});
                
                // Create color expression for data-driven styling
                const colorExpression = ['case'];
                alcaldiasData.features.forEach(function(feature) {{
                    const value = getMetricValue(feature.properties);
                    const color = getCrimeColor(value);
                    colorExpression.push(['==', ['get', 'name'], feature.properties.name]);
                    colorExpression.push(color);
                }});
                colorExpression.push('rgb(173, 216, 230)'); // fallback
                
                // Add alcaldías fill layer with crime-based colors
                map.addLayer({{
                    'id': 'alcaldias-fill',
                    'type': 'fill',
                    'source': 'alcaldias',
                    'paint': {{
                        'fill-color': colorExpression,
                        'fill-opacity': 0.7
                    }}
                }});
                
                map.addLayer({{
                    'id': 'alcaldias-outline',
                    'type': 'line',
                    'source': 'alcaldias',
                    'paint': {{
                        'line-color': 'darkblue',
                        'line-width': 2
                    }}
                }});
                
                // Add cuadrantes sources and layers (initially hidden)
                Object.keys(cuadrantesData).forEach(function(alcaldiaNormalized) {{
                    const sourceId = 'cuadrantes-' + alcaldiaNormalized;
                    
                    map.addSource(sourceId, {{
                        'type': 'geojson',
                        'data': cuadrantesData[alcaldiaNormalized]
                    }});
                    
                    // Create color expression for cuadrantes based on crime count
                    const cuadranteColorExpression = ['case'];
                    cuadrantesData[alcaldiaNormalized].features.forEach(function(feature) {{
                        const count = feature.properties.crime_count;
                        const color = getCuadranteColor(count);
                        cuadranteColorExpression.push(['==', ['get', 'no_cuadran'], feature.properties.no_cuadran]);
                        cuadranteColorExpression.push(color);
                    }});
                    cuadranteColorExpression.push('rgb(173, 216, 230)'); // fallback
                    
                    map.addLayer({{
                        'id': sourceId + '-fill',
                        'type': 'fill',
                        'source': sourceId,
                        'paint': {{
                            'fill-color': cuadranteColorExpression,
                            'fill-opacity': 0.6
                        }},
                        'layout': {{
                            'visibility': 'none'
                        }}
                    }});
                    
                    map.addLayer({{
                        'id': sourceId + '-outline',
                        'type': 'line',
                        'source': sourceId,
                        'paint': {{
                            'line-color': 'darkblue',
                            'line-width': 1.5
                        }},
                        'layout': {{
                            'visibility': 'none'
                        }}
                    }});
                }});
                
                // Add crime points sources and layers (initially hidden)
                Object.keys(crimePointsData).forEach(function(alcaldiaNormalized) {{
                    const sourceId = 'crime-points-' + alcaldiaNormalized;
                    
                    map.addSource(sourceId, {{
                        'type': 'geojson',
                        'data': crimePointsData[alcaldiaNormalized]
                    }});
                    
                    map.addLayer({{
                        'id': sourceId,
                        'type': 'circle',
                        'source': sourceId,
                        'paint': {{
                            'circle-radius': 4,
                            'circle-color': ['get', 'color'],
                            'circle-opacity': 0.7,
                            'circle-stroke-width': 1,
                            'circle-stroke-color': '#fff'
                        }},
                        'layout': {{
                            'visibility': 'none'
                        }}
                    }});
                }});
                
                // Add hover effect for alcaldías
                map.on('mouseenter', 'alcaldias-fill', function() {{
                    map.getCanvas().style.cursor = 'pointer';
                }});
                
                map.on('mousemove', 'alcaldias-fill', function(e) {{
                    if (e.features.length > 0) {{
                        const props = e.features[0].properties;
                        const metricLabel = mapMetric === 'per_capita' ? 'Crime Rate' : 'Crimes';
                        const metricValue = mapMetric === 'per_capita' ? 
                            props.crimes_per_capita.toFixed(2) + ' per 1K' : 
                            props.crime_count.toLocaleString();
                        
                        document.getElementById('info').innerHTML = 
                            '<strong>' + props.name + '</strong><br>' +
                            metricLabel + ': ' + metricValue;
                        document.getElementById('info').style.display = 'block';
                    }}
                }});
                
                map.on('mouseleave', 'alcaldias-fill', function() {{
                    map.getCanvas().style.cursor = '';
                    if (currentView === 'city') {{
                        document.getElementById('info').style.display = 'none';
                    }}
                }});
                
                // Single click handler - open side panel
                map.on('click', 'alcaldias-fill', function(e) {{
                    if (currentView === 'city' && e.features.length > 0) {{
                        // Clear any existing timeout
                        if (clickTimeout) {{
                            clearTimeout(clickTimeout);
                        }}
                        
                        // CRITICAL: Store the feature properties OUTSIDE the timeout
                        // because the event object becomes invalid
                        const alcaldiaName = e.features[0].properties.name;
                        const crimeCount = e.features[0].properties.crime_count;
                        const alcaldiaNormalized = e.features[0].properties.name_normalized;
                        
                        // Set a timeout to handle single click
                        clickTimeout = setTimeout(function() {{
                            openSidePanel(alcaldiaName, crimeCount, alcaldiaNormalized);
                            clickTimeout = null;
                        }}, 300); // 300ms delay to detect double-click
                    }}
                }});
                
                // Double-click handler - zoom in to alcaldía
                map.on('dblclick', 'alcaldias-fill', function(e) {{
                    if (currentView === 'city' && e.features.length > 0) {{
                        // Clear the single-click timeout
                        if (clickTimeout) {{
                            clearTimeout(clickTimeout);
                            clickTimeout = null;
                        }}
                        
                        const alcaldiaName = e.features[0].properties.name;
                        const alcaldiaNormalized = e.features[0].properties.name_normalized;
                        closeSidePanel(); // Close panel before drilling down
                        
                        // Small delay to ensure panel closes first
                        setTimeout(function() {{
                            drillDown(alcaldiaName, alcaldiaNormalized);
                        }}, 100);
                    }}
                }});
                
                // Click on map background to close panel
                map.on('click', function(e) {{
                    // Check if click was on an alcaldía
                    const features = map.queryRenderedFeatures(e.point, {{
                        layers: ['alcaldias-fill']
                    }});
                    
                    // If no alcaldía was clicked, close the panel
                    if (features.length === 0) {{
                        closeSidePanel();
                    }}
                }});
                
                // Add hover tooltips and click handlers for cuadrantes
                Object.keys(cuadrantesData).forEach(function(alcaldiaNormalized) {{
                    const layerId = 'cuadrantes-' + alcaldiaNormalized + '-fill';
                    
                    map.on('mouseenter', layerId, function(e) {{
                        map.getCanvas().style.cursor = 'pointer';
                    }});
                    
                    map.on('mousemove', layerId, function(e) {{
                        if (e.features.length > 0) {{
                            const currentId = e.features[0].properties.id;
                            
                            // Only update if we moved to a different cuadrante
                            if (hoveredCuadranteId !== currentId) {{
                                hoveredCuadranteId = currentId;
                                const props = e.features[0].properties;
                                document.getElementById('info').innerHTML = 
                                    '<strong>Cuadrante:</strong> ' + props.no_cuadran + '<br>' +
                                    '<strong>Sector:</strong> ' + props.sector + '<br>' +
                                    '<strong>Alcaldía:</strong> ' + props.alcaldia + '<br>' +
                                    '<strong>Crimes:</strong> ' + props.crime_count;
                                document.getElementById('info').style.display = 'block';
                            }}
                        }}
                    }});
                    
                    map.on('mouseleave', layerId, function() {{
                        map.getCanvas().style.cursor = '';
                        hoveredCuadranteId = null;
                        document.getElementById('info').style.display = 'none';
                    }});
                    
                    // Click handler for cuadrantes - open side panel
                    map.on('click', layerId, function(e) {{
                        if (e.features.length > 0) {{
                            const props = e.features[0].properties;
                            
                            // Parse top_crimes if it's a string
                            let topCrimes = [];
                            try {{
                                if (typeof props.top_crimes === 'string') {{
                                    topCrimes = JSON.parse(props.top_crimes);
                                }} else if (Array.isArray(props.top_crimes)) {{
                                    topCrimes = props.top_crimes;
                                }}
                            }} catch (err) {{
                                console.error('Error parsing top_crimes:', err);
                            }}
                            
                            const cuadranteProps = {{
                                no_cuadran: props.no_cuadran,
                                crime_count: props.crime_count,
                                sector: props.sector,
                                zona: props.zona,
                                top_crimes: topCrimes
                            }};
                            
                            openCuadrantePanel(cuadranteProps, props.alcaldia);
                        }}
                    }});
                }});
                
                // Add hover and click handlers for crime points
                Object.keys(crimePointsData).forEach(function(alcaldiaNormalized) {{
                    const layerId = 'crime-points-' + alcaldiaNormalized;
                    
                    map.on('mouseenter', layerId, function() {{
                        map.getCanvas().style.cursor = 'pointer';
                    }});
                    
                    map.on('mouseleave', layerId, function() {{
                        map.getCanvas().style.cursor = '';
                    }});
                    
                    map.on('click', layerId, function(e) {{
                        if (e.features.length > 0) {{
                            const props = e.features[0].properties;
                            
                            // Create popup
                            new maplibregl.Popup({{
                                closeButton: true,
                                closeOnClick: true
                            }})
                            .setLngLat(e.lngLat)
                            .setHTML(`
                                <div style="font-family: Arial, sans-serif; font-size: 12px;">
                                    <strong style="font-size: 13px;">${{props.delito}}</strong><br>
                                    <strong>Date:</strong> ${{props.fecha}}<br>
                                    <strong>Agency:</strong> ${{props.agencia}}
                                </div>
                            `)
                            .addTo(map);
                        }}
                    }});
                }});
            }});
            
            function drillDown(alcaldiaName, alcaldiaNormalized) {{
                currentView = 'alcaldia';
                selectedAlcaldia = alcaldiaName;
                
                // Hide only the selected alcaldía (keep others visible)
                map.setFilter('alcaldias-fill', ['!=', ['get', 'name'], alcaldiaName]);
                map.setFilter('alcaldias-outline', ['!=', ['get', 'name'], alcaldiaName]);
                
                // Show cuadrantes for selected alcaldía
                const sourceId = 'cuadrantes-' + alcaldiaNormalized;
                if (map.getLayer(sourceId + '-fill')) {{
                    map.setLayoutProperty(sourceId + '-fill', 'visibility', 'visible');
                    map.setLayoutProperty(sourceId + '-outline', 'visibility', 'visible');
                }}
                
                // Show crime points for selected alcaldía
                const crimePointsId = 'crime-points-' + alcaldiaNormalized;
                if (map.getLayer(crimePointsId)) {{
                    map.setLayoutProperty(crimePointsId, 'visibility', 'visible');
                }}
                
                // Show crime type legend and populate it
                const crimeTypeLegend = document.getElementById('crime-type-legend');
                const crimeTypeList = document.getElementById('crime-type-list');
                crimeTypeList.innerHTML = '';
                
                // Create simplified legend with just 3 categories
                const categories = [
                    {{ 
                        label: 'With Violence (Con Violencia)', 
                        color: '#dc3545',
                        count: violenceCounts['con_violencia'] || 0
                    }},
                    {{ 
                        label: 'Without Violence (Sin Violencia)', 
                        color: '#28a745',
                        count: violenceCounts['sin_violencia'] || 0
                    }},
                    {{ 
                        label: 'Unknown', 
                        color: '#6c757d',
                        count: violenceCounts['unknown'] || 0
                    }}
                ];
                
                categories.forEach(function(cat) {{
                    if (cat.count > 0) {{
                        const item = document.createElement('div');
                        item.className = 'crime-type-item';
                        item.innerHTML = `
                            <div class="crime-type-color" style="background-color: ${{cat.color}}"></div>
                            <div class="crime-type-label">${{cat.label}} (${{cat.count.toLocaleString()}})</div>
                        `;
                        crimeTypeList.appendChild(item);
                    }}
                }});
                
                crimeTypeLegend.style.display = 'block';
                
                // Fit bounds to alcaldía with padding
                const bounds = alcaldiaBounds[alcaldiaName];
                if (bounds && bounds.bounds) {{
                    map.fitBounds(bounds.bounds, {{
                        padding: 80,
                        duration: 1500,
                        maxZoom: 13
                    }});
                }}
                
                // Show back button
                document.getElementById('back-button').style.display = 'block';
            }}
            
            function zoomOut() {{
                currentView = 'city';
                selectedAlcaldia = null;
                
                // Show all alcaldías layers (remove filter)
                map.setFilter('alcaldias-fill', null);
                map.setFilter('alcaldias-outline', null);
                
                // Hide all cuadrantes layers and crime points
                Object.keys(cuadrantesData).forEach(function(alcaldiaNormalized) {{
                    const sourceId = 'cuadrantes-' + alcaldiaNormalized;
                    if (map.getLayer(sourceId + '-fill')) {{
                        map.setLayoutProperty(sourceId + '-fill', 'visibility', 'none');
                        map.setLayoutProperty(sourceId + '-outline', 'visibility', 'none');
                    }}
                    
                    const crimePointsId = 'crime-points-' + alcaldiaNormalized;
                    if (map.getLayer(crimePointsId)) {{
                        map.setLayoutProperty(crimePointsId, 'visibility', 'none');
                    }}
                }});
                
                // Hide crime type legend
                document.getElementById('crime-type-legend').style.display = 'none';
                
                // Zoom back to city view
                map.flyTo({{
                    center: {json.dumps(CDMX_CENTER[::-1])},
                    zoom: 9.5,
                    duration: 1500
                }});
                
                // Hide back button and info
                document.getElementById('back-button').style.display = 'none';
                document.getElementById('info').style.display = 'none';
            }}
            
            // Back button click handler
            document.getElementById('back-button').addEventListener('click', zoomOut);
            
            // Side panel close button
            document.getElementById('side-panel-close').addEventListener('click', closeSidePanel);
        </script>
    </body>
    </html>
    """

    # -------------------------
    # Render Map
    # -------------------------
    # Make the map wider and adjust height
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 95%;
        }
        iframe {
            display: block;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

    components.html(html_content, height=550, scrolling=False)

    # -------------------------
    # Stats
    # -------------------------
    total_alcaldias = len(alcaldias_geojson['features'])
    total_cuadrantes = sum(len(geojson['features']) for geojson in cuadrantes_by_alcaldia.values())
    total_crimes = len(crime_df[crime_df['anio_hecho'].isin(selected_years)])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Alcaldías", total_alcaldias)
    col2.metric("Total Cuadrantes", total_cuadrantes)
    col3.metric("Total Crímenes", f"{total_crimes:,}")

    # Show top 5 alcaldías by crime
    st.subheader("📊 Top 5 Alcaldías por conteo de crimen")
    selected_crime_df = crime_df[crime_df['anio_hecho'].isin(selected_years)]
    crime_by_alcaldia = selected_crime_df.groupby('alcaldia_hecho').size().sort_values(ascending=False).head(5)
    st.bar_chart(crime_by_alcaldia)