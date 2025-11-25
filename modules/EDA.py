import streamlit as st
import os
import json

def show():
    """Main EDA display function"""
    
    # ==========================
    #   CSS PARA ANIMACIONES Y TARJETA
    # ==========================
    st.markdown("""
    <style>

    .fade-in {
        animation: fadeIn 1s ease-in-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    .card-desc {
        background: #ffffff;
        padding: 20px;
        margin-top: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.12);
        font-size: 19px;
        font-weight: 300;
        font-family: 'Segoe UI', sans-serif;
        color: #444;
        line-height: 1.55;
    }

    .dot-container {
        text-align: center;
        margin-top: 15px;
    }

    .dot {
        font-size: 22px;
        margin: 0 4px;
        color: #bbb;
    }

    .dot.active {
        color: #333;
    }

    </style>
    """, unsafe_allow_html=True)

    # ==========================
    #   TÍTULO
    # ==========================
    st.markdown("""
    <div style="text-align:center; padding: 20px 0;">
        <h1 style="font-size: 42px; margin-bottom:5px;">
            🚗📊 Radiografía del Robo de Vehículos en la CDMX
        </h1>
        <h3 style="color:gray; margin-top:0;">
            Un recorrido visual por patrones, tendencias y zonas críticas
        </h3>
        <hr style="margin-top:20px;">
    </div>
    """, unsafe_allow_html=True)


    # ==========================
    #   LEER DESCRIPCIONES
    # ==========================
    DESC_FILE = "descriptions.json"
    descripciones = {}

    if os.path.exists(DESC_FILE):
        try:
            with open(DESC_FILE, "r", encoding="utf-8") as f:
                descripciones = json.load(f)
        except:
            st.warning("⚠ No se pudo leer descriptions.json, revisa su formato.")
    else:
        st.warning("⚠ No se encontró descriptions.json. Se usarán descripciones por nombre.")


    # ==========================
    #   CARGAR IMÁGENES
    # ==========================
    GRAPH_FOLDER = "graphs"
    valid_ext = (".png", ".jpg", ".jpeg")

    imagenes = []
    
    # Check if graphs folder exists
    if not os.path.exists(GRAPH_FOLDER):
        st.error(f"⚠ La carpeta '{GRAPH_FOLDER}/' no existe. Por favor créala y agrega imágenes.")
        st.stop()
    
    for file in sorted(os.listdir(GRAPH_FOLDER)):
        if file.lower().endswith(valid_ext):
            path = os.path.join(GRAPH_FOLDER, file)
            desc = descripciones.get(
                file,
                file.replace("_", " ").rsplit(".", 1)[0].capitalize()
            )
            imagenes.append((file, path, desc))

    if not imagenes:
        st.error("⚠ No hay imágenes dentro de la carpeta 'graphs/'.")
        st.stop()


    # ==========================
    #   SESSION STATE INDEX
    # ==========================
    if "eda_index" not in st.session_state:
        st.session_state.eda_index = 0


    # ==========================
    #   FUNCIONES DE NAVEGACIÓN
    # ==========================
    def next_image():
        st.session_state.eda_index = (st.session_state.eda_index + 1) % len(imagenes)

    def prev_image():
        st.session_state.eda_index = (st.session_state.eda_index - 1) % len(imagenes)


    # ==========================
    #   MOSTRAR IMAGEN CON ANIMACIÓN
    # ==========================
    filename, img_path, desc = imagenes[st.session_state.eda_index]

    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.image(img_path, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


    # ==========================
    #   DESCRIPCIÓN — AHORA CON MARKDOWN
    # ==========================
    st.markdown('<div class="card-desc fade-in">', unsafe_allow_html=True)
    st.markdown(desc, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


    # ==========================
    #   INDICADORES TIPO "•••"
    # ==========================
    dots_html = '<div class="dot-container">'
    for i in range(len(imagenes)):
        dots_html += (
            f"<span class='dot {'active' if i == st.session_state.eda_index else ''}'>•</span>"
        )
    dots_html += "</div>"

    st.markdown(dots_html, unsafe_allow_html=True)


    # ==========================
    #   BOTONES DE NAVEGACIÓN
    # ==========================
    col1, col2, col3 = st.columns([1,2,1])

    with col1:
        if st.button("⬅ Anterior", use_container_width=True, key="eda_prev"):
            prev_image()
            st.rerun()

    with col3:
        if st.button("Siguiente ➡", use_container_width=True, key="eda_next"):
            next_image()
            st.rerun()


    # ==========================
    #   CONTADOR
    # ==========================
    st.markdown(
        f"<p style='text-align:center; opacity:0.6;'>Imagen {st.session_state.eda_index + 1} de {len(imagenes)}</p>",
        unsafe_allow_html=True
    )