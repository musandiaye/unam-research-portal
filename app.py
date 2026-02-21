import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Engineering Portal", layout="wide")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPERS ---
def clean_id(val):
    if pd.isna(val) or val == "": return ""
    return str(val).split('.')[0].strip()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data(sheet_name):
    try:
        # Using ttl=0 to ensure we get the latest data from your sheet
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).apply(clean_id)
        return df
    except:
        return pd.DataFrame()

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""
    st.session_state['user_email'] = ""

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator", "Project Suggestions"])
project_type = st.sidebar.radio("Select Stream Filter", ["Research Project", "Design Project", "Show All"])

# --- [REGISTRATION & EXAMINER CODE REMAINS UNCHANGED] ---
# ... (Keeping your existing registration and marking logic exactly as is)

# --- ROLE: PROJECT SUGGESTIONS (REFINED) ---
if role == "Project Suggestions":
    st.header("🔭 Available Project Suggestions")
    st.info("Students: If you are interested, contact the supervisor via the blue button.")
    
    # Reloading data with no cache to ensure the new entry shows
    ps_df = load_data("project_suggestions")
    
    if not ps_df.empty:
        # Apply filtering logic
        if project_type == "Show All":
            display_df = ps_df
        else:
            display_df = ps_df[ps_df['type'] == project_type]
        
        if not display_df.empty:
            for _, row in display_df.iterrows():
                # Handling the 'nan' or empty values for display
                title = row['title'] if pd.notna(row['title']) else "Untitled Project"
                supervisor = row['supervisor'] if pd.notna(row['supervisor']) else "Unknown"
                email_val = row['email'] if pd.notna(row['email']) and str(row['email']).strip() != "" else ""
                abstract = row['abstract'] if pd.notna(row['abstract']) else "No abstract provided."
                p_type = row['type'] if pd.notna(row['type']) else "General"

                with st.expander(f"📌 {title} ({p_type})"):
                    st.write(f"**Supervisor:** {supervisor}")
                    if email_val:
                        st.write(f"**Email:** {email_val}")
                    st.write(f"**Abstract:** {abstract}")
                    
                    if email_val and email_val != "nan":
                        mail_link = f"mailto:{email_val}?subject=Interest in {p_type}: {title}"
                        st.markdown(f'<a href="{mail_link}" style="padding:10px; background-color:#007bff; color:white; text-decoration:none; border-radius:5px; font-size:14px;">📧 Contact Supervisor</a>', unsafe_allow_html=True)
                    else:
                        st.warning("No contact email available for this supervisor.")
        else:
            st.warning(f"No projects found matching the category: {project_type}")
    else:
        st.info("The suggestions list is currently empty. Examiners can add projects in the 'Panelist / Examiner' tab.")

# --- [COORDINATOR CODE REMAINS UNCHANGED] ---
# ... (Keeping your existing Blackberry/Apple dashboard logic exactly as is)
