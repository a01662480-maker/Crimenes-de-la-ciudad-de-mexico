"""
CDMX Crime Analytics Dashboard
Main application entry point with authentication and "Remember Me" functionality
"""

import streamlit as st
from supabase import create_client
import pandas as pd
import os
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
import json

# ===============================
# Load Environment Variables
# ===============================
load_dotenv()

# ===============================
# Configuration
# ===============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "FGJ")
SUPABASE_TABLE_CUADRANTS = os.getenv("SUPABASE_TABLE_CUADRANTS", "cuadrantes")

# Cookie password for encryption (MUST be set in .env for security)
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD", "my-super-secret-password-change-this-in-production")

# ===============================
# App Configuration (MUST BE FIRST)
# ===============================
st.set_page_config(
    page_title="Panel de Análisis de Delitos CDMX",
    layout="wide",
    page_icon="📊"
)

# ===============================
# Cookie Manager Initialization
# ===============================
# Initialize cookie manager with 7-day expiry
cookies = EncryptedCookieManager(
    prefix="cdmx_crime_app_",
    password=COOKIE_PASSWORD
)

# Wait for cookies to be ready
if not cookies.ready():
    st.stop()

# ===============================
# Authentication Functions
# ===============================
def login_user(email, password):
    """Authenticate user and retrieve role from profiles table"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = auth_response.user
        session = auth_response.session
        
        if not user or not session:
            return None, None, None
        
        # Fetch user role from profiles table
        user_data = supabase.table("profiles").select("rol").eq("id", user.id).single().execute()
        rol = user_data.data["rol"] if user_data.data else None
        
        return user, rol, session
    except Exception as e:
        st.error(f"❌ Error al iniciar sesión: {e}")
        return None, None, None


def save_session_to_cookies(session, email, rol, remember_me=False):
    """Save session tokens to encrypted cookies"""
    if remember_me:
        # Store refresh token for 7 days
        cookies["refresh_token"] = session.refresh_token
        cookies["user_email"] = email
        cookies["user_rol"] = rol
        cookies["remember_me"] = "true"
        cookies.save()


def auto_login_from_cookies():
    """Attempt to auto-login using stored refresh token"""
    try:
        # Check if remember_me cookie exists
        if cookies.get("remember_me") != "true":
            return False
        
        refresh_token = cookies.get("refresh_token")
        user_email = cookies.get("user_email")
        user_rol = cookies.get("user_rol")
        
        if not refresh_token:
            return False
        
        # Try to refresh session with Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Set the refresh token and get new session
        auth_response = supabase.auth.set_session(refresh_token, refresh_token)
        
        if auth_response and auth_response.user:
            # Successfully refreshed - update session state
            st.session_state.logged_in = True
            st.session_state.rol = user_rol
            st.session_state.user_email = user_email
            
            # Update cookies with new refresh token if available
            if auth_response.session and auth_response.session.refresh_token:
                cookies["refresh_token"] = auth_response.session.refresh_token
                cookies.save()
            
            return True
        else:
            # Token expired or invalid - clear cookies
            clear_cookies()
            return False
            
    except Exception as e:
        # If auto-login fails, clear cookies and return False
        clear_cookies()
        return False


def clear_cookies():
    """Clear all authentication cookies"""
    cookies["refresh_token"] = ""
    cookies["user_email"] = ""
    cookies["user_rol"] = ""
    cookies["remember_me"] = ""
    cookies.save()


def logout_user():
    """Clear session state, cookies, and log out user"""
    try:
        # Revoke Supabase session if possible
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.auth.sign_out()
    except:
        pass
    
    # Clear cookies
    clear_cookies()
    
    # Clear session state
    st.session_state.clear()
    st.rerun()


def get_allowed_pages(rol):
    """Return list of pages accessible to each role"""
    role_pages = {
        "ADMIN": [
            "🏠 Inicio",
            "🗺️ Mapa Interactivo",
            "📈 Panorama de la Ciudad",
            "🏛️ Panel de Alcaldías",
            "🔍 Verificador de Datos",
            "📊 EDA",
            "🔮 Predicciones",
            "🏗️ Arquitectura"
        ],
        "FGJ": [
            "🏠 Inicio",
            "🗺️ Mapa Interactivo",
            "📈 Panorama de la Ciudad",
            "🏛️ Panel de Alcaldías",
            "🔮 Predicciones"
        ],
        "THALES": [
            "🏠 Inicio",
            "🗺️ Mapa Interactivo",
            "📈 Panorama de la Ciudad",
            "🏛️ Panel de Alcaldías",
            "🔍 Verificador de Datos",
            "📊 EDA",
            "🔮 Predicciones",
            "🏗️ Arquitectura"
        ]
    }
    return role_pages.get(rol, ["🏠 Inicio"])

# ===============================
# Session State Initialization
# ===============================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.rol = None
    st.session_state.user_email = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Inicio"

# ===============================
# AUTO-LOGIN CHECK
# ===============================
# Try to auto-login before showing login page
if not st.session_state.logged_in:
    auto_login_successful = auto_login_from_cookies()
    if auto_login_successful:
        st.rerun()

# ===============================
# LOGIN PAGE
# ===============================
if not st.session_state.logged_in:
    # Custom CSS for login page
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .login-header {
            text-align: center;
            color: #0066CC;
            margin-bottom: 2rem;
        }
        .login-box {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Display CDMX logo
        if os.path.exists("CDMX.png"):
            st.image("CDMX.png", use_container_width=True)
        
        st.markdown("""
            <div class="login-header">
                <h2>Panel de Análisis de Delitos CDMX</h2>
                <p>Iniciar Sesión</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            email = st.text_input("📧 Correo electrónico", key="login_email")
            password = st.text_input("🔒 Contraseña", type="password", key="login_password")
            
            # Remember Me checkbox
            remember_me = st.checkbox("🔐 Recordarme por 7 días", value=False)
            
            if st.button("Iniciar sesión", use_container_width=True, type="primary"):
                if email and password:
                    with st.spinner("Verificando credenciales..."):
                        user, rol, session = login_user(email, password)
                        if user and rol and session:
                            # Set session state
                            st.session_state.logged_in = True
                            st.session_state.rol = rol
                            st.session_state.user_email = email
                            
                            # Save to cookies if remember_me is checked
                            if remember_me:
                                save_session_to_cookies(session, email, rol, remember_me=True)
                            
                            st.success("✅ Inicio de sesión exitoso")
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas o usuario no encontrado.")
                else:
                    st.warning("⚠️ Por favor ingresa correo y contraseña.")
    
    st.stop()

# ===============================
# MAIN APPLICATION (After Login)
# ===============================

# Import all pages
from modules import EDA, data_checker, alcaldias_dashboard, interactive_map, city_overview, predictions_page, arquitectura

# ===============================
# Data Loading Functions
# ===============================
@st.cache_data(ttl=3600)
def load_summary_stats():
    """Load summary statistics for landing page"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get total crime count
        crime_response = supabase.table(SUPABASE_TABLE).select("fecha_hecho, alcaldia_hecho", count="exact").execute()
        total_crimes = crime_response.count if hasattr(crime_response, 'count') else len(crime_response.data)
        
        # Get most recent date
        recent_response = supabase.table(SUPABASE_TABLE).select("fecha_hecho").order("fecha_hecho", desc=True).limit(1).execute()
        most_recent_date = recent_response.data[0]['fecha_hecho'] if recent_response.data else "N/A"
        
        # Get unique alcaldías count
        alcaldias_response = supabase.table(SUPABASE_TABLE).select("alcaldia_hecho").execute()
        df_temp = pd.DataFrame(alcaldias_response.data)
        unique_alcaldias = df_temp['alcaldia_hecho'].nunique() if not df_temp.empty else 0
        
        # Get total cuadrantes
        cuadrantes_response = supabase.table(SUPABASE_TABLE_CUADRANTS).select("*", count="exact").execute()
        total_cuadrantes = cuadrantes_response.count if hasattr(cuadrantes_response, 'count') else len(cuadrantes_response.data)
        
        return {
            'total_crimes': total_crimes,
            'most_recent_date': most_recent_date,
            'unique_alcaldias': unique_alcaldias,
            'total_cuadrantes': total_cuadrantes
        }
    except Exception as e:
        st.error(f"Error loading summary stats: {e}")
        return {
            'total_crimes': 0,
            'most_recent_date': "N/A",
            'unique_alcaldias': 0,
            'total_cuadrantes': 0
        }

# ===============================
# Landing Page
# ===============================
def show_landing_page():
    """Display the enhanced landing/home page with role-based navigation"""
    
    # Custom CSS for landing page
    st.markdown("""
        <style>
        /* Hero Section */
        .hero-section {
            background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 102, 204, 0.2);
        }
        
        .hero-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .hero-subtitle {
            font-size: 1.2rem;
            opacity: 0.95;
            margin-bottom: 0;
        }
        
        /* KPI Cards */
        .kpi-card {
            background: linear-gradient(135deg, #F8F9FA 0%, #ffffff 100%);
            border-left: 4px solid #0066CC;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
            text-align: center;
        }
        
        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            color: #0066CC;
            margin: 0.5rem 0;
        }
        
        .kpi-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Navigation Card Buttons */
        .stButton > button {
            background: white !important;
            border: 2px solid #E0E0E0 !important;
            border-radius: 12px !important;
            padding: 2rem 1.5rem !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
            height: 220px !important;
            width: 100% !important;
            color: #666 !important;
            font-size: 0.95rem !important;
            line-height: 1.6 !important;
            box-shadow: none !important;
            white-space: pre-line !important;
        }
        
        .stButton > button:hover {
            border-color: #0066CC !important;
            box-shadow: 0 8px 24px rgba(0, 102, 204, 0.15) !important;
            transform: translateY(-4px) !important;
            background: white !important;
        }
        
        .stButton > button:focus:not(:active) {
            border-color: #E0E0E0 !important;
            box-shadow: none !important;
        }
        
        /* Footer */
        .landing-footer {
            text-align: center;
            color: #888;
            font-size: 0.85rem;
            padding: 2rem 0 1rem 0;
            border-top: 1px solid #E0E0E0;
            margin-top: 3rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">📊 Panel de Análisis de Delitos CDMX</h1>
            <p class="hero-subtitle">Plataforma integral para el análisis de patrones delictivos relacionados con vehículos en la Ciudad de México</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Load summary statistics
    stats = load_summary_stats()
    
    # Format date
    from datetime import datetime
    if stats['most_recent_date'] != "N/A":
        try:
            date_obj = datetime.strptime(stats['most_recent_date'][:10], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except:
            formatted_date = stats['most_recent_date']
    else:
        formatted_date = "N/A"
    
    # KPI Stats Section
    st.markdown("### 📈 Estadísticas Generales")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Total de Delitos</div>
                <div class="kpi-value">{stats['total_crimes']:,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi_col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Última Actualización</div>
                <div class="kpi-value" style="font-size: 1.5rem;">{formatted_date}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi_col3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Alcaldías</div>
                <div class="kpi-value">{stats['unique_alcaldias']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi_col4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Cuadrantes</div>
                <div class="kpi-value">{stats['total_cuadrantes']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Navigation Cards Section
    st.markdown("### 🧭 Explorar el Dashboard")
    st.markdown("Selecciona una sección para comenzar tu análisis:")
    
    # Get allowed pages for current user (excluding Inicio)
    allowed_pages = get_allowed_pages(st.session_state.rol)
    display_pages = [p for p in allowed_pages if p != "🏠 Inicio"]
    
    # Define page metadata (icon, title, description)
    page_metadata = {
        "🗺️ Mapa Interactivo": {
            "icon": "🗺️",
            "title": "Mapa Interactivo",
            "description": "Explora incidentes delictivos geográficamente con filtrado interactivo y capacidad de exploración por Alcaldía y Cuadrante."
        },
        "📈 Panorama de la Ciudad": {
            "icon": "📈",
            "title": "Panorama de la Ciudad",
            "description": "Visualiza tendencias, estadísticas e indicadores clave de rendimiento en toda la Ciudad de México."
        },
        "🏛️ Panel de Alcaldías": {
            "icon": "🏛️",
            "title": "Panel de Alcaldías",
            "description": "Profundiza en análisis detallados a nivel de Alcaldía con desgloses y comparaciones detalladas."
        },
        "🔍 Verificador de Datos": {
            "icon": "🔍",
            "title": "Verificador de Datos",
            "description": "Inspecciona y verifica conjuntos de datos, calidad de datos y estado del sistema (herramienta administrativa)."
        },
        "📊 EDA": {
            "icon": "📊",
            "title": "Análisis Exploratorio (EDA)",
            "description": "Radiografía visual del robo de vehículos: patrones, tendencias y zonas críticas con gráficos interactivos."
        },
        "🔮 Predicciones": {
            "icon": "🔮",
            "title": "Predicciones",
            "description": "Visualiza los resultados del modelo predictivo de delitos y análisis de patrones futuros basados en Machine Learning."
        },
        "🏗️ Arquitectura": {
            "icon": "🏗️",
            "title": "Arquitectura Técnica",
            "description": "Documentación técnica completa del sistema: base de datos, modelos ML, pipelines y agentes de IA."
        }
    }
    
    # Create cards dynamically in rows of 2
    for i in range(0, len(display_pages), 2):
        cols = st.columns(2)
        
        for j, col in enumerate(cols):
            if i + j < len(display_pages):
                page = display_pages[i + j]
                metadata = page_metadata.get(page, {
                    "icon": "📄",
                    "title": page.replace("🏠 ", "").replace("🗺️ ", "").replace("📈 ", "").replace("🏛️ ", "").replace("🔍 ", "").replace("🔮 ", "").replace("🏗️ ", "").replace("📊 ", ""),
                    "description": "Página del dashboard"
                })
                
                with col:
                    # Create button with plain text (no HTML)
                    button_label = f"{metadata['icon']}\n\n{metadata['title']}\n\n{metadata['description']}"
                    
                    if st.button(button_label, key=f"nav_btn_{i}_{j}", use_container_width=True):
                        st.session_state.current_page = page
                        st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
        <div class="landing-footer">
            <p><strong>Panel de Análisis de Delitos CDMX</strong> v1.0</p>
            <p>Datos proporcionados por la Fiscalía General de Justicia de la Ciudad de México</p>
            <p style="margin-top: 1rem; font-size: 0.75rem; color: #AAA;">
                Los datos mostrados son de carácter informativo. Para consultas oficiales, favor de dirigirse a las autoridades competentes.
            </p>
        </div>
    """, unsafe_allow_html=True)

# ===============================
# Sidebar Navigation
# ===============================
st.sidebar.title("🔍 Navegación")

# User info and logout button
st.sidebar.markdown(f"**👤 Usuario:** {st.session_state.rol}")
st.sidebar.markdown(f"**📧:** {st.session_state.user_email}")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout_user()

st.sidebar.markdown("---")

# Get allowed pages for current role
allowed_pages = get_allowed_pages(st.session_state.rol)

# Update sidebar selection based on session state
page = st.sidebar.radio(
    "Selecciona una página:",
    allowed_pages,
    index=allowed_pages.index(st.session_state.current_page) if st.session_state.current_page in allowed_pages else 0
)

# Update session state if sidebar selection changes
if page != st.session_state.current_page:
    st.session_state.current_page = page
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; color: #888; font-size: 12px; padding: 10px;'>
    <p>Panel de Análisis de Delitos CDMX v1.0</p>
    <p>Datos de la Fiscalía General de Justicia</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# Page Routing with Access Control
# ===============================
current_page = st.session_state.current_page

# Check if user has access to current page
if current_page not in allowed_pages:
    st.error("⚠️ No tienes acceso a esta página.")
    st.info("Por favor selecciona una página del menú de navegación.")
    st.stop()

# Route to appropriate page
if current_page == "🏠 Inicio":
    show_landing_page()

elif current_page == "🗺️ Mapa Interactivo":
    interactive_map.show()

elif current_page == "📈 Panorama de la Ciudad":
    city_overview.show()

elif current_page == "🏛️ Panel de Alcaldías":
    alcaldias_dashboard.show()

elif current_page == "🔍 Verificador de Datos":
    data_checker.show()

elif current_page == "📊 EDA":
    EDA.show()

elif current_page == "🔮 Predicciones":
    predictions_page.show()

elif current_page == "🏗️ Arquitectura":
    arquitectura.show()