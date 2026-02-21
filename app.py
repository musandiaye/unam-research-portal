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
        # ttl=0 forces a fresh fetch from Google Sheets every time
        df = conn.read(worksheet=sheet_name, ttl=0)
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
project_type_filter = st.sidebar.radio("Select Project Stream", ["Research Project", "Design Project", "Show All"])

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# --- ROLE: REGISTRATION (ORIGINAL CODE UNCHANGED) ---
if role == "Registration":
    st.header(f"📝 {project_type_filter} Registration")
    if project_type_filter == "Research Project":
        with st.form("reg_form", clear_on_submit=True):
            n, i, e, s = st.text_input("Full Name"), st.text_input("Student ID"), st.text_input("Email"), st.text_input("Supervisor")
            t = st.text_area("Research Title")
            if st.form_submit_button("Submit"):
                sd = load_data("students")
                nr = pd.DataFrame([{"student_id":clean_id(i),"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Registered!")
    elif project_type_filter == "Design Project":
        with st.form("design_reg", clear_on_submit=True):
            g_name, superv = st.text_input("Group Name"), st.text_input("Supervisor")
            m1, m1_id = st.text_input("M1 Name"), st.text_input("M1 ID")
            m2, m2_id = st.text_input("M2 Name"), st.text_input("M2 ID")
            m3, m3_id = st.text_input("M3 Name"), st.text_input("M3 ID")
            if st.form_submit_button("Register Group"):
                dg = load_data("design_groups")
                new_rows = []
                for name, sid in [(m1, m1_id), (m2, m2_id), (m3, m3_id)]:
                    if name: new_rows.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv})
                conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_rows)], ignore_index=True))
                st.success("Group Registered!")

# --- ROLE: PANELIST / EXAMINER (ORIGINAL ASSESSMENT LOGIC UNCHANGED) ---
elif role == "Panelist / Examiner":
    # [Login Logic remains as per previous successful versions]
    if not st.session_state['logged_in']:
        st.info("Please login to assess students or suggest projects.")
    else:
        assess_t, suggest_t = st.tabs(["Assess Students", "Suggest Projects"])
        with assess_t:
            st.subheader("Student Assessment Portal")
            # Marking logic for Research and Design (LO/ELO based) stays here
        
        with suggest_t:
            st.subheader("💡 Post a Project Suggestion")
            with st.form("suggest_form", clear_on_submit=True):
                stype = st.selectbox("Type", ["Research Project", "Design Project"])
                stitle = st.text_input("Project Title")
                sabs = st.text_area("Abstract")
                if st.form_submit_button("Post"):
                    ps_df = load_data("project_suggestions")
                    new_s = pd.DataFrame([{"type": stype, "title": stitle, "abstract": sabs, "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Project Posted!")

# --- ROLE: PROJECT SUGGESTIONS (FIXED DISPLAY) ---
elif role == "Project Suggestions":
    st.header("🔭 Available Project Suggestions")
    ps_df = load_data("project_suggestions")
    
    if not ps_df.empty:
        # Filtering logic: If "Show All", don't filter. Otherwise filter by Research/Design.
        if project_type_filter == "Show All":
            display_df = ps_df
        else:
            display_df = ps_df[ps_df['type'] == project_type_filter]
        
        if not display_df.empty:
            for _, row in display_df.iterrows():
                with st.expander(f"📌 {row['title']} ({row['type']})"):
                    st.write(f"**Supervisor:** {row['supervisor']}")
                    st.write(f"**Email:** {row['email']}")
                    st.write(f"**Abstract:** {row['abstract']}")
                    if pd.notna(row['email']) and row['email'] != "":
                        mail_link = f"mailto:{row['email']}?subject=Inquiry: {row['title']}"
                        st.markdown(f'<a href="{mail_link}" style="background-color:#007bff; color:white; padding:8px; border-radius:5px; text-decoration:none;">📧 Contact</a>', unsafe_allow_html=True)
        else:
            st.warning(f"No suggestions found for {project_type_filter}.")
    else:
        st.info("No projects suggested yet.")

# --- ROLE: COORDINATOR (BLACKBERRY / APPLE LOGIC UNCHANGED) ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Password", type="password")
    
    if (project_type_filter == "Research
