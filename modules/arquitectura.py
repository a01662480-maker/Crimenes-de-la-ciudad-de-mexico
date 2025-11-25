import streamlit as st
from PIL import Image
import os
import pandas as pd
import json

def show():
    """Display the technical architecture documentation page"""
    
    # --- VARIABLES DE CONFIGURACIÓN ---
    CARPETA = "architecture"

    # Archivos de Arquitectura
    NOMBRE_ARCHIVO_MAIN = "DB_Diagram.png"  
    NOMBRE_ARCHIVO_N8N = "n8n_workflow.png" 

    # Imágenes de Resultados ML
    IMG_LOSS_NAME = "Curvas_de_Aprendizaje.jpeg"
    IMG_SCATTER_NAME = "Dispersión.jpeg"
    IMG_ZOOM_NAME = "Zoom_Detalle.jpeg"

    # Link de Colab
    LINK_COLAB = "https://colab.research.google.com/drive/1Ku7LLp4Oo1OaKSAnlmQNxQT1t1lAUUng?usp=sharing"

    # Construcción de Rutas Completas
    IMG_PATH_MAIN = os.path.join(CARPETA, NOMBRE_ARCHIVO_MAIN)
    IMG_PATH_N8N = os.path.join(CARPETA, NOMBRE_ARCHIVO_N8N)
    IMG_PATH_LOSS = os.path.join(CARPETA, IMG_LOSS_NAME)
    IMG_PATH_SCATTER = os.path.join(CARPETA, IMG_SCATTER_NAME)
    IMG_PATH_ZOOM = os.path.join(CARPETA, IMG_ZOOM_NAME)

    # ==========================================
    # DATOS JSON DE N8N (EMBEDDED)
    # ==========================================

    # 1. AGENTE PRINCIPAL
    N8N_MAIN_AGENT = """
{
  "name": "SQL Agente Thales",
  "nodes": [
    {
      "parameters": {
        "name": "query_sql",
        "description": "Call this tool to execute a query. Remember that it should be in a postgreSQL query structure.",
        "workflowId": {
          "__rl": true,
          "value": "A92Uq6DuuOY6iz08",
          "mode": "list",
          "cachedResultUrl": "/workflow/A92Uq6DuuOY6iz08",
          "cachedResultName": "Query SQL"
        },
        "specifyInputSchema": true,
        "schemaType": "manual",
        "inputSchema": "{\\n\\"type\\": \\"object\\",\\n\\"properties\\": {\\n\\t\\"sql\\": {\\n\\t\\t\\"type\\": \\"string\\",\\n\\t\\t\\"description\\": \\"A SQL query based on the users question and database schema.\\"\\n\\t\\t}\\n\\t}\\n}"
      },
      "id": "78fdae48-85b5-40af-88fd-8c122da013cf",
      "name": "Execute Query",
      "type": "@n8n/n8n-nodes-langchain.toolWorkflow",
      "typeVersion": 1.2,
      "position": [384, 320]
    },
    {
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.query || $json.chatInput }}",
        "options": {
          "systemMessage": "=## ABSOLUTE RULE FOR TABLE NAME\\nYou MUST ALWAYS reference the table EXACTLY as:\\n\\n*\\"FGJ\\"*\\n\\nRules:\\n- ALWAYS use: \\"FGJ\\"\\n- NEVER use: FGJ, fgj, 'FGJ', FGJ, or FGJ without quotes.\\n- Every SQL query MUST contain:\\n  sql\\n  FROM \\"FGJ\\"\\n  \\n\\nIf you ever generate a SQL query without double quotes around the table name, you MUST correct yourself and rewrite it properly before calling query_sql.\\n\\n---\\n\\n## Role\\nYou are a *Database Query Wizard* specialized in generating PostgreSQL queries for the table \\"FGJ\\", which contains ONLY *vehicle theft (robo de vehículo)* crime records.\\n\\nYour job:\\n- Interpret natural language questions about vehicle theft.\\n- Build SQL queries targeting ONLY the table \\"FGJ\\".\\n- Always perform schema retrieval and SQL execution using the provided tools.\\n- Provide clear, concise English answers.\\n- NEVER explain your reasoning unless asked.\\n\\n---\\n\\n## Tools\\n### 1. get_schema_supabase\\nRetrieves the schema of all tables.  \\n*MUST ALWAYS be executed before writing any SQL query.*\\n\\n### 2. query_sql\\nExecutes SQL queries in this format:\\njson\\n{ \\"sql\\": \\"YOUR SQL QUERY HERE\\" }\\n\\n\\n---\\n\\n## IMPORTANT RULES OF BEHAVIOR\\n- *ALWAYS* run get_schema_supabase first.\\n- *ALWAYS* run query_sql to execute the SQL you generate.\\n- *NEVER* show SQL unless you plan to send it to query_sql.\\n- Always answer in *English*, short and clear.\\n- For EACH new user question, you MUST re-run get_schema_supabase and query_sql.\\n- NEVER assume table names; ALWAYS use \\"FGJ\\".\\n\\n---\\n\\n## TABLE CONTEXT\\nThe table \\"FGJ\\" contains fields related exclusively to *vehicle theft incidents*, including:\\n\\n- anio_hecho  \\n- mes_hecho  \\n- fecha_hecho  \\n- hora_hecho  \\n- delito  \\n- categoria_delito  \\n- competencia  \\n- fiscalia  \\n- agencia  \\n\\nAll questions should be interpreted as related to vehicle theft or its subcategories (violent theft, non-violent theft, attempted theft, theft by modality, etc.).\\n\\n---\\n\\n## CRITICAL SEARCH TECHNIQUE\\nFor ANY search term, ALWAYS generate MULTIPLE variants, always using ILIKE:\\n\\nExample for vehicle theft:\\nsql\\nWHERE\\n  delito ILIKE '%rob%' OR\\n  delito ILIKE '%robo%' OR\\n  delito ILIKE '%vehic%' OR\\n  delito ILIKE '%vehículo%' OR\\n  categoria_delito ILIKE '%rob%' OR\\n  categoria_delito ILIKE '%vehic%'\\n\\n\\nRules:\\n- ALWAYS include stems.\\n- ALWAYS include versions with and without accents.\\n- NEVER rely on full exact words.\\n- ALWAYS use multiple variants.\\n\\n---\\n\\n## CRIME TYPE RULE\\nIf the user asks about variations of vehicle theft:\\n- violent\\n- non-violent\\n- attempted\\n- successful\\n- type of vehicle  \\n- circumstances  \\n\\nTHEN search ONLY in:\\n- delito\\n- categoria_delito\\n\\nExample:\\nsql\\nWHERE\\n  delito ILIKE '%rob%' OR\\n  categoria_delito ILIKE '%vehic%'\\n\\n\\n---\\n\\n## FISCALÍA & AGENCY RULE\\nIf the user asks about "where", "which fiscalía", "which agency":\\n\\nUse stems:\\nsql\\nWHERE\\n  fiscalia ILIKE '%izta%' OR\\n  fiscalia ILIKE '%cuauh%' OR\\n  agencia ILIKE '%izta%' OR\\n  agencia ILIKE '%cuauh%'\\n\\n\\n---\\n\\n## DATE & YEAR SEARCH PATTERNS\\n### Year:\\nsql\\nWHERE anio_hecho = 2023\\n\\n\\n### Date Range:\\nsql\\nWHERE fecha_hecho BETWEEN '2023-01-01' AND '2023-12-31'\\n\\n\\n### Month:\\nsql\\nWHERE mes_hecho ILIKE '%enero%'\\n\\n\\n---\\n\\n## QUERY GENERATION PROCESS\\n1. Read and interpret the user's question.  \\n2. ALWAYS call get_schema_supabase.  \\n3. Identify filters (year, date, fiscalía, agency, modality).  \\n4. Build a robust SQL query that ALWAYS uses \\"FGJ\\".  \\n5. ALWAYS include multiple ILIKE variants.  \\n6. Execute SQL using query_sql.  \\n7. Provide a clear English answer using the results.  \\n\\n---\\n\\n## REQUIRED\\n- ALWAYS use \\"FGJ\\" with double quotes.\\n- NEVER generate FGJ without quotes.\\n- ALWAYS use ILIKE with stems and variants.\\n- ALWAYS re-run both tools on every new user message.\\n- ALWAYS answer in English.\\n- If results are empty → broaden search stems.\\n- If results are too large → apply LIMIT 50.\\n\\n### Today's date: {{ $now }}\\n",
          "maxIterations": 5
        }
      },
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.8,
      "position": [256, 96],
      "id": "faa93a78-409c-496e-a7a7-0988d32e7a82",
      "name": "AI Agent1"
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "e8937f7a-17cc-4e17-970f-7c711fe88fb0",
              "name": "output",
              "value": "={{ $json.output }}",
              "type": "string"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [560, 112],
      "id": "614d053e-b442-4285-94c5-ff536957b647",
      "name": "Edit Fields"
    },
    {
      "parameters": {
        "name": "get_schema_supabase",
        "description": "=Call this tool to retrieve the schema of all the tables inside of the database. A string will be retrieved with the name of the table and its columns, each table is separated by \\\\n\\\\n.",
        "workflowId": {
          "__rl": true,
          "value": "40BiK2Q26VQGKpy2",
          "mode": "list",
          "cachedResultUrl": "/workflow/40BiK2Q26VQGKpy2",
          "cachedResultName": "Get Schema Supabase"
        },
        "workflowInputs": {
          "mappingMode": "defineBelow",
          "value": {},
          "matchingColumns": [],
          "schema": [],
          "attemptToConvertTypes": false,
          "convertFieldsToString": false
        }
      },
      "type": "@n8n/n8n-nodes-langchain.toolWorkflow",
      "typeVersion": 2,
      "position": [512, 320],
      "id": "616e033c-8ae7-43d0-9c01-218e8e376f8d",
      "name": "Get Schema"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
      "typeVersion": 1,
      "position": [128, 320],
      "id": "b1e22321-b51c-4107-acdc-60173d041c30",
      "name": "Google Gemini Chat Model",
      "credentials": {
        "googlePalmApi": {
          "id": "0z36BMsorCBFSAaD",
          "name": "Google Gemini(PaLM) Api account"
        }
      }
    },
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "thaleschat",
        "responseMode": "responseNode",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [96, 96],
      "id": "60fb9ce3-5ca0-4135-9c45-145fd9424e60",
      "name": "Webhook",
      "webhookId": "199e8e1e-ffde-4b36-9439-3ed6e490f002"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.4,
      "position": [704, 112],
      "id": "f567ee3e-059a-472b-b9ea-793fcc0b5607",
      "name": "Respond to Webhook"
    }
  ],
  "connections": {
    "Execute Query": {
      "ai_tool": [[{"node": "AI Agent1", "type": "ai_tool", "index": 0}]]
    },
    "AI Agent1": {
      "main": [[{"node": "Edit Fields", "type": "main", "index": 0}]]
    },
    "Get Schema": {
      "ai_tool": [[{"node": "AI Agent1", "type": "ai_tool", "index": 0}]]
    },
    "Google Gemini Chat Model": {
      "ai_languageModel": [[{"node": "AI Agent1", "type": "ai_languageModel", "index": 0}]]
    },
    "Webhook": {
      "main": [[{"node": "AI Agent1", "type": "main", "index": 0}]]
    },
    "Edit Fields": {
      "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
    }
  }
}
"""

    # 2. TOOL: QUERY SQL
    N8N_QUERY_TOOL = """
{
  "name": "Query SQL",
  "nodes": [
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "{{ $json.query.sql }}",
        "options": {}
      },
      "id": "845ca207-3876-4e8a-8a5a-ef62857dbee4",
      "name": "Postgres",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [240, 0],
      "credentials": {
        "postgres": {
          "id": "EMH2renzuERUyZXZ",
          "name": "Postgres account"
        }
      }
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "e2f94fb1-3deb-466a-a36c-e3476511d5f2",
              "name": "response",
              "value": "={{ $json }}",
              "type": "string"
            }
          ]
        },
        "options": {}
      },
      "id": "8f9f494b-c848-4c04-be89-6f7e6522ca51",
      "name": "Edit Fields",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [688, 0]
    },
    {
      "parameters": {},
      "id": "36633df7-41ff-490d-a9be-dd14bcb88185",
      "name": "Execute Workflow Trigger",
      "type": "n8n-nodes-base.executeWorkflowTrigger",
      "typeVersion": 1,
      "position": [0, 0]
    },
    {
      "parameters": {
        "jsCode": "// Obtener los items de entrada\\nconst items = $input.all();\\n\\n// Unir todos los elementos en un solo objeto\\nconst combinedItem = {\\n  resultado: items.map(item => ({\\n    ...item.json // Mantiene todos los parámetros dinámicamente\\n  }))\\n};\\n\\n// Retornar el nuevo array con un solo objeto\\nreturn [{ json: combinedItem }];\\n"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [464, 0],
      "id": "29b77025-173e-40bf-8573-9ef74b1ac37e",
      "name": "Code"
    }
  ],
  "connections": {
    "Postgres": {
      "main": [[{"node": "Code", "type": "main", "index": 0}]]
    },
    "Execute Workflow Trigger": {
      "main": [[{"node": "Postgres", "type": "main", "index": 0}]]
    },
    "Code": {
      "main": [[{"node": "Edit Fields", "type": "main", "index": 0}]]
    }
  }
}
"""

    # 3. TOOL: GET SCHEMA
    N8N_SCHEMA_TOOL = """
{
  "name": "Get Schema Supabase",
  "nodes": [
    {
      "parameters": {
        "jsCode": "function transformSchema(input) {\\n    const tables = {};\\n    \\n    input.forEach(({ json }) => {\\n        if (!json) return;\\n        \\n        const { tablename, schemaname, column_name, data_type } = json;\\n        \\n        if (!tables[tablename]) {\\n            tables[tablename] = { schema: schemaname, columns: [] };\\n        }\\n        tables[tablename].columns.push(${column_name} (${data_type}));\\n    });\\n    \\n    return Object.entries(tables)\\n        .map(([tablename, { schema, columns }]) => Table ${tablename} (Schema: ${schema}) has columns: ${columns.join(\", \")})\\n        .join(\"\\\\n\\\\n\");\\n}\\n\\n// Example usage\\nconst input = $input.all();\\nconsole.log(input);\\nconst transformedSchema = transformSchema(input);\\n\\nreturn { data: transformedSchema };"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [544, -96],
      "id": "07d16ab5-06cc-4202-a3e2-1e51e77ebfb2",
      "name": "Code"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT \\n    t.schemaname,\\n    t.tablename,\\n    c.column_name,\\n    c.data_type\\nFROM \\n    pg_catalog.pg_tables t\\nJOIN \\n    information_schema.columns c\\n    ON t.schemaname = c.table_schema\\n    AND t.tablename = c.table_name\\nWHERE \\n    t.schemaname = 'public'\\nORDER BY \\n    t.tablename, c.ordinal_position;",
        "options": {}
      },
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [320, -96],
      "id": "765a0e86-14f7-4b4a-aa94-188328b56bea",
      "name": "Postgres1",
      "alwaysOutputData": false,
      "executeOnce": false,
      "credentials": {
        "postgres": {
          "id": "EMH2renzuERUyZXZ",
          "name": "Postgres account"
        }
      }
    },
    {
      "parameters": {},
      "id": "e047346f-8051-4fe4-b5b9-d013a3b337cf",
      "name": "Execute Workflow Trigger",
      "type": "n8n-nodes-base.executeWorkflowTrigger",
      "typeVersion": 1,
      "position": [112, -96]
    }
  ],
  "connections": {
    "Postgres1": {
      "main": [[{"node": "Code", "type": "main", "index": 0}]]
    },
    "Execute Workflow Trigger": {
      "main": [[{"node": "Postgres1", "type": "main", "index": 0}]]
    }
  }
}
"""

    # --- ESTILOS CSS ---
    st.markdown("""
        <style>
        .main { background-color: #f9f9f9; }
        h1 { color: #B71C1C; font-family: 'Helvetica', sans-serif; font-weight: bold; }
        h3 { color: #1A2855; }
        .stExpander { background-color: white; border: 1px solid #ddd; border-radius: 8px; }
        .dataframe { font-size: 14px; }
        .stLinkButton a {
            background-color: #FF5722 !important;
            color: white !important;
            font-weight: bold;
        }
        .role-card {
            padding: 15px; border-radius: 10px; border: 1px solid #eee;
            text-align: center; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- TÍTULO ---
    st.title("🔴 The Button CDMX: Arquitectura Técnica")
    st.markdown("""
    *Documentación Oficial de Ingeniería de Datos*
    Flujo End-to-End para la predicción de criminalidad en la Ciudad de México, integrando modelos híbridos, gobierno de datos y agentes autónomos.
    """)
    st.divider()

    # --- 1. VISUALIZACIÓN DEL DIAGRAMA PRINCIPAL ---
    if os.path.exists(IMG_PATH_MAIN):
        image = Image.open(IMG_PATH_MAIN)
        st.image(image, caption="Blueprint de Arquitectura - The Button CDMX", use_container_width=True)
    else:
        st.error(f"⚠ No se encontró la imagen principal: {IMG_PATH_MAIN}")

    st.divider()

    # --- 2. EXPLICACIÓN DETALLADA ---
    st.header("🔍 Componentes del Sistema")

    # DEFINICIÓN DE PESTAÑAS (6 TABS)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📥 Ingesta & ETL", 
        "🗂 Taxonomía de Datos", 
        "🧠 Inteligencia Artificial", 
        "📊 Despliegue",
        "🔐 Seguridad (RBAC)",
        "🚀 Roadmap & Futuro"
    ])

    # --- TAB 1: INGESTA ---
    with tab1:
        st.subheader("Origen y Procesamiento")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.info("*Fuentes de Datos*")
        with col2:
            st.markdown("""
            * *Sistema Ajolote (Legacy):* Fuente primaria que exporta datos transaccionales en *CSV*.
            * *Fuentes Externas:* Datos geoespaciales y catálogos de la CDMX.
            * *ETL Engine:* Normalización, limpieza de nulos y estandarización de fechas.
            * *Data Fusion:* Etapa de Joins donde se enriquece la data histórica antes de persistir.
            """)

    # --- TAB 2: TAXONOMÍA ---
    with tab2:
        st.subheader("🗂 Modelo de Datos Completo")
        st.markdown("Esquema DDL detallado de *Supabase (PostgreSQL)*. Se visualizan todos los atributos disponibles por entidad.")

        # Diagrama Vertical Estilo Ficha (Card Style)
        st.graphviz_chart("""
        digraph ERD {
            rankdir=TB;
            node [shape=none, fontname="Helvetica", fontsize=10];
            edge [color="#999999"];

            # --- TABLA FGJ ---
            FGJ [label=<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">
                <tr><td bgcolor="#1A2855"><font color="white"><b>FGJ (Hechos)</b></font></td></tr>
                <tr><td align="left">🔹 anio_hecho: bigint</td></tr>
                <tr><td align="left">🔹 mes_hecho: text</td></tr>
                <tr><td align="left">🔹 fecha_hecho: date</td></tr>
                <tr><td align="left">🔹 hora_hecho: timestamptz</td></tr>
                <tr><td align="left">🔹 delito: text</td></tr>
                <tr><td align="left">🔹 categoria_delito: text</td></tr>
                <tr><td align="left">🔹 competencia: text</td></tr>
                <tr><td align="left">🔹 fiscalia: text</td></tr>
                <tr><td align="left">🔹 agencia: text</td></tr>
                <tr><td align="left">🔹 unidad_investigacion: text</td></tr>
                <tr><td align="left">🔹 colonia_hecho: text</td></tr>
                <tr><td align="left">🔹 colonia_catalogo: text</td></tr>
                <tr><td align="left">🔹 alcaldia_hecho: text</td></tr>
                <tr><td align="left">🔹 latitud: float8</td></tr>
                <tr><td align="left">🔹 longitud: float8</td></tr>
                <tr><td align="left">🔹 day_of_week: text</td></tr>
                <tr><td align="left">🔹 fecha_hora: timestamptz</td></tr>
                <tr><td align="left">🔹 hora: smallint</td></tr>
                <tr><td align="left">🔹 minuto: smallint</td></tr>
                <tr><td align="left">🔹 segundo: smallint</td></tr>
            </table>
            >];

            # --- TABLA CUADRANTES ---
            Cuadrantes [label=<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">
                <tr><td bgcolor="#2E7D32"><font color="white"><b>Cuadrantes (Geo)</b></font></td></tr>
                <tr><td align="left">🔑 id (PK): text</td></tr>
                <tr><td align="left">🔸 no_region: bigint</td></tr>
                <tr><td align="left">🔸 no_cuadran: bigint</td></tr>
                <tr><td align="left">🔸 zona: text</td></tr>
                <tr><td align="left">🔸 geo_shape: jsonb</td></tr>
                <tr><td align="left">🔸 geo_point_2d: text</td></tr>
                <tr><td align="left">🔸 alcaldia: text</td></tr>
                <tr><td align="left">🔸 sector: text</td></tr>
                <tr><td align="left">🔸 clave_sect: bigint</td></tr>
            </table>
            >];

            # --- TABLA CRIME PREDICTIONS ---
            Predictions [label=<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">
                <tr><td bgcolor="#EF6C00"><font color="white"><b>CrimePredictions</b></font></td></tr>
                <tr><td align="left">🔑 Cuadrante (FK): bigint</td></tr>
                <tr><td align="left">🔸 Fecha: date</td></tr>
                <tr><td align="left">🔸 Día Semana: text</td></tr>
                <tr><td align="left">🔸 Turno: text</td></tr>
                <tr><td align="left">🔸 HOLIDAY: text</td></tr>
                <tr><td align="left">🔸 PAY_DAY: text</td></tr>
                <tr><td align="left">🚀 Crímenes Predichos: bigint</td></tr>
            </table>
            >];
            
            # --- TABLA CHAT ---
            Chat [label=<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">
                <tr><td bgcolor="#6A1B9A"><font color="white"><b>n8n_chat_histories</b></font></td></tr>
                <tr><td align="left">🔑 id (PK): serial</td></tr>
                <tr><td align="left">🔸 session_id: varchar(255)</td></tr>
                <tr><td align="left">🔸 message: jsonb</td></tr>
            </table>
            >];

            # --- TABLA PROFILES ---
            Profiles [label=<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">
                <tr><td bgcolor="#455A64"><font color="white"><b>profiles (Auth)</b></font></td></tr>
                <tr><td align="left">🔑 id (PK): uuid</td></tr>
                <tr><td align="left">🔸 email: text</td></tr>
                <tr><td align="left">🔸 rol: text</td></tr>
            </table>
            >];

            FGJ -> Cuadrantes [style="invis"]; 
        }
        """)

        st.markdown("### 📋 Diccionario de Datos (DDL Completo)")
        
        with st.expander("1. Tabla 'FGJ' (Hechos Delictivos)", expanded=False):
            st.code("""
create table public."FGJ" (
  anio_hecho bigint not null,
  mes_hecho text null,
  fecha_hecho date not null,
  hora_hecho timestamp with time zone null,
  delito text null,
  categoria_delito text null,
  competencia text null,
  fiscalia text null,
  agencia text null,
  unidad_investigacion text null,
  colonia_hecho text null,
  colonia_catalogo text null,
  alcaldia_hecho text null,
  latitud double precision null,
  longitud double precision null,
  day_of_week text null,
  fecha_hora timestamp with time zone null,
  hora smallint null,
  minuto smallint null,
  segundo smallint null
) TABLESPACE pg_default;
            """, language="sql")
        
        with st.expander("2. Tabla 'Cuadrantes' (Geometría Policial)", expanded=False):
            st.code("""
create table public.cuadrantes (
  id text not null,
  no_region bigint null,
  no_cuadran bigint null,
  zona text null,
  geo_shape jsonb null,
  geo_point_2d text null,
  alcaldia text null,
  sector text null,
  clave_sect bigint null,
  constraint cuadrantes_pkey primary key (id)
) TABLESPACE pg_default;
            """, language="sql")

        with st.expander("3. Tabla 'CrimePredictions' (Salida ML)", expanded=False):
            st.code("""
create table public."CrimePredictions" (
  "Cuadrante" bigint null,
  "Fecha" date null,
  "Día Semana" text null,
  "Turno" text null,
  "HOLIDAY" text null,
  "PAY_DAY" text null,
  "Crímenes Predichos" bigint null
) TABLESPACE pg_default;
            """, language="sql")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            with st.expander("4. Tabla 'n8n_chat_histories'", expanded=False):
                st.code("""
create table public.n8n_chat_histories (
  id serial not null,
  session_id character varying(255) not null,
  message jsonb not null,
  constraint n8n_chat_histories_pkey primary key (id)
) TABLESPACE pg_default;
                """, language="sql")
        
        with col_d2:
            with st.expander("5. Tabla 'profiles' (Seguridad)", expanded=False):
                st.code("""
create table public.profiles (
  id uuid not null default auth.uid (),
  email text not null,
  rol text null,
  constraint profiles_pkey primary key (id)
) TABLESPACE pg_default;
                """, language="sql")

    # --- TAB 3: INTELIGENCIA ARTIFICIAL ---
    with tab3:
        st.subheader("🧠 Cerebro Digital: ML & Agentes")
        
        subtab_ml, subtab_n8n = st.tabs(["📊 Pipeline Predictivo (MLP+XGB)", "🤖 Agente SQL (GenAI)"])
        
        # --- SUBTAB ML ---
        with subtab_ml:
            c_head1, c_head2 = st.columns([3, 1])
            with c_head1:
                st.markdown("#### Arquitectura Híbrida: Deep Learning + Boosting")
            with c_head2:
                st.link_button("🚀 Ver Código (Colab)", LINK_COLAB)

            col1, col2 = st.columns([1.5, 1])
            with col1:
                st.markdown("*Paso A: Base Model (MLP)*")
                st.graphviz_chart("""
                digraph MLP {
                    rankdir=LR;
                    node [shape=record, style="filled", fontname="Helvetica", fontsize=10];
                    Input [label="{Input|Feat: 28}", fillcolor="#e3f2fd"];
                    Hidden [label="{Hidden Layers|Dense(256)|Dense(128)}", fillcolor="#fff9c4"];
                    Output [label="{Output|Predicción Base}", fillcolor="#c8e6c9"];
                    Input -> Hidden -> Output;
                }
                """)
            with col2:
                st.markdown("*Paso B: Corrección de Residuos*")
                st.info("XGBoost predice el error del MLP para ajustar el resultado final.")

            st.markdown("#### 📉 Evaluación Visual")
            v1, v2, v3 = st.tabs(["Curvas", "Dispersión", "Zoom"])
            with v1:
                if os.path.exists(IMG_PATH_LOSS): st.image(Image.open(IMG_PATH_LOSS), use_container_width=True)
            with v2:
                if os.path.exists(IMG_PATH_SCATTER): st.image(Image.open(IMG_PATH_SCATTER), use_container_width=True)
            with v3:
                if os.path.exists(IMG_PATH_ZOOM): st.image(Image.open(IMG_PATH_ZOOM), use_container_width=True)

            st.markdown("#### 🚀 KPIs Finales")
            m1, m2, m3 = st.columns(3)
            m1.metric("R²", "0.7851", "+2.6%")
            m2.metric("MAE", "1.44", "-0.12", delta_color="inverse")
            m3.metric("MAPE", "28.81%", "-7.8%", delta_color="inverse")

        # --- SUBTAB N8N (DESCARGABLES) ---
        with subtab_n8n:
            st.markdown("#### 🤖 Agente Autónomo de Base de Datos")
            
            col_n8n_1, col_n8n_2 = st.columns([1, 1])
            with col_n8n_1:
                st.markdown("""
                Orquestación mediante *N8N* que permite a los usuarios hacer preguntas en lenguaje natural.
                
                *Flujo Lógico:*
                1. *Trigger:* Webhook (Chat Input).
                2. *Schema Awareness:* El agente lee la estructura de FGJ.
                3. *SQL Gen:* Gemini genera la query.
                4. *Response:* Texto natural.
                """)
                
                # --- SECCIÓN DE DESCARGAS ---
                st.markdown("### 📥 Recursos Descargables (Workflow JSONs)")
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
                with col_dl1:
                    st.download_button(
                        label="📦 Agente Principal",
                        data=N8N_MAIN_AGENT,
                        file_name="SQL_Agente_Thales.json",
                        mime="application/json",
                        help="El flujo principal que orquesta la IA."
                    )
                with col_dl2:
                    st.download_button(
                        label="🛠 Tool: Query SQL",
                        data=N8N_QUERY_TOOL,
                        file_name="Query_SQL.json",
                        mime="application/json",
                        help="Sub-flujo para ejecutar consultas en Postgres."
                    )
                with col_dl3:
                    st.download_button(
                        label="🛠 Tool: Get Schema",
                        data=N8N_SCHEMA_TOOL,
                        file_name="Get_Schema_Supabase.json",
                        mime="application/json",
                        help="Sub-flujo para leer la estructura de la DB."
                    )

            with col_n8n_2:
                if os.path.exists(IMG_PATH_N8N):
                    st.image(Image.open(IMG_PATH_N8N), caption="Workflow N8N", use_container_width=True)
                else:
                    st.warning(f"Falta imagen N8N: {NOMBRE_ARCHIVO_N8N}")

    # --- TAB 4: DESPLIEGUE ---
    with tab4:
        st.subheader("Entrega de Valor")
        st.success("""
        *Flujo de CI/CD - The Button CDMX:*
        1. *Streamlit:* Framework de visualización conectado a Supabase.
        2. *GitHub:* Repositorio para control de versiones y despliegue continuo.
        3. *Dashboard Final:* Interfaz de usuario donde se consumen los KPIs y Predicciones.
        """)

    # --- TAB 5: SEGURIDAD ---
    with tab5:
        st.subheader("🔐 Seguridad y Control de Acceso (RBAC)")
        st.markdown("Sistema de autenticación basado en *Supabase Auth* con encriptación de credenciales.")
        
        st.graphviz_chart("""
        digraph Auth {
            rankdir=LR;
            node [shape=box, style="rounded,filled", fontname="Helvetica"];
            User [label="Usuario", fillcolor="#fff9c4"];
            Router [label="Role Router", shape=diamond, fillcolor="#e1bee7"];
            Views [label="{Vistas Seguras|Admin|FGJ|Thales}", shape=record, fillcolor="#b3e5fc"];
            User -> Router [label="Login"];
            Router -> Views [label="Token JWT"];
        }
        """)
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.markdown("<div class='role-card' style='background-color:#e3f2fd'><h4>🔵 FGJ</h4><small>Vista Operativa</small></div>", unsafe_allow_html=True)
        with col_r2:
            st.markdown("<div class='role-card' style='background-color:#ffebee'><h4>🔴 ADMIN</h4><small>Control Total</small></div>", unsafe_allow_html=True)
        with col_r3:
            st.markdown("<div class='role-card' style='background-color:#f3e5f5'><h4>🟣 THALES</h4><small>Vista Técnica</small></div>", unsafe_allow_html=True)

    # --- TAB 6: ROADMAP ---
    with tab6:
        st.subheader("🚀 Roadmap y Evolución del Proyecto")
        st.markdown("Estrategia de escalabilidad para convertir *The Button CDMX* en un sistema crítico de seguridad pública.")
        
        col_fut1, col_fut2 = st.columns(2)
        
        with col_fut1:
            st.markdown("### 🛠 Fase 2: Automatización")
            st.markdown("""
            * *Orquestación:* Implementación de *Apache Airflow* para reemplazar la ejecución manual de scripts ETL.
            * *Model Registry:* Versionado automático de modelos (.pkl) en Supabase Storage.
            * *Drift Monitoring:* Alertas automáticas si los patrones delictivos cambian drásticamente, sugiriendo reentrenamiento.
            """)
            
        with col_fut2:
            st.markdown("### 🔮 Fase 3: Real-Time & Feedback")
            st.markdown("""
            * *Ingesta Streaming:* Conexión a APIs del C5 para ingestión de eventos en tiempo real (Kafka).
            * *RLHF (Reinforcement Learning):* Botones de feedback ("👍/👎") en el dashboard para que los oficiales validen la utilidad de la predicción.
            * *Multimodal:* Integrar análisis de video para detección de incidentes.
            """)
        
        st.markdown("---")
        st.info("💡 *Visión:* Crear el sistema operativo central de prevención delictiva predictiva de México.")

    # --- FOOTER ---
    st.markdown("---")
    st.caption("🔴 *The Button CDMX* | Documentación generada para el equipo de Ingeniería de Datos.")