import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")

# --- LOGO ---
try:
    st.sidebar.image("unam_logo.png", use_container_width=True)
except:
    st.sidebar.write("### UNAM Engineering")

st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

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

# --- SIDEBAR NAVIGATION ---
role = st.sidebar.radio("Management Menu", ["Student Registration", "Student View (Results)", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE: STUDENT REGISTRATION ---
if role == "Student Registration":
    st.header("📝 Student Research Registration")
    with st.form("reg_form", clear_on_submit=True):
        n = st.text_input("Full Name")
        i = st.text_input("Student ID")
        e = st.text_input("Email")
        s = st.text_input("Supervisor")
        t = st.text_area("Research Title")
        if st.form_submit_button("Submit Registration"):
            sd = load_data("students")
            ci = clean_id(i)
            if not all([n, ci, e, s, t]):
                st.error("Please fill in all fields.")
            else:
                nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Successfully Registered!")

# --- ROLE: STUDENT VIEW ---
elif role == "Student View (Results)":
    st.header("📋 View Your Results")
    sid_input = st.text_input("Enter Student ID").strip()
    if sid_input:
        tid = clean_id(sid_input)
        m_df = load_data("marks")
        if not m_df.empty:
            student_results = m_df[m_df['student_id'] == tid].copy()
            if not student_results.empty:
                st.success(f"Viewing Results for: {student_results.iloc[0]['
