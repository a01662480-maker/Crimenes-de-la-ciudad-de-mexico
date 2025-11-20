import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

# ===============================
# Load environment variables
# ===============================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE")

# ===============================
# Create Supabase client
# ===============================
@st.cache_data
def load_data():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("❌ Missing Supabase credentials. Check your .env file.")
        return pd.DataFrame()

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        all_data = []
        batch_size = 1000
        offset = 0
        total_fetched = 0
        total_expected = 90000  # adjust to your dataset size

        progress_text = "Loading records..."
        progress_bar = st.progress(0, text=progress_text)

        while True:
            response = (
                supabase.table(SUPABASE_TABLE)
                .select("*")
                .range(offset, offset + batch_size - 1)
                .execute()
            )

            if not response.data:
                break

            all_data.extend(response.data)
            total_fetched += len(response.data)
            offset += batch_size

            pct = min(total_fetched / total_expected, 1.0)
            progress_bar.progress(pct, text=f"Loaded {total_fetched:,} records...")
            time.sleep(0.01)

        progress_bar.progress(1.0, text=f"✅ Load complete: {len(all_data):,} records")

        if not all_data:
            st.warning("No data found in the table.")
            return pd.DataFrame()

        df = pd.DataFrame(all_data)

        if "fecha_hecho" in df.columns:
            df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
            df["anio_hecho"] = df["fecha_hecho"].dt.year

        return df

    except Exception as e:
        st.error(f"Error connecting to Supabase: {e}")
        return pd.DataFrame()
