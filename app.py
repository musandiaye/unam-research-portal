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
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

# --- SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = ""

# --- LOGIN / SIGNUP SCREEN ---
if not st.session_state['authenticated']:
    st.title("UNAM Engineering Portal")
    auth_tab1, auth_tab2 = st.tabs(["Login", "Register Account"])
    
    with auth_tab1:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                u_df = load_data("users")
                # Check credentials and get role
                user_match = u_df[(u_df['username'] == u) & (u_df['password'] == hash_password(p))]
                if not user_match.empty:
                    st.session_state['authenticated'] = True
                    st.session_state['user_role'] = user_match.iloc[0]['role']
                    st.session_state['user_name'] = user_match.iloc[0]['full_name']
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

    with auth_tab2:
        with st.form("signup"):
            new_n = st.text_input("Full Name")
            new_u = st.text_input("Username")
            new_p = st.text_input("Password", type="password")
            # This is where the user picks their level
            new_r = st.selectbox("I am a:", ["Student", "Examiner", "Coordinator"])
            key = st.text_input("Access Key (Required for Examiner/Coordinator)", type="password")
            
            if st.form_submit_button("Sign Up"):
                # Security Check
                if new_r in ["Examiner", "Coordinator"] and key != "JEDSECE2026":
                    st.error("Invalid Access Key for this role.")
                else:
                    u_df = load_data("users")
                    new_user = pd.DataFrame([{"full_name": new_n, "username": new_u, "password": hash_password(new_p), "role": new_r}])
                    conn.update(worksheet="users", data=pd.concat([u_df, new_user], ignore_index=True))
                    st.success("Account created! Please Login.")

# --- AUTHENTICATED VIEW ---
else:
    st.sidebar.title(f"Welcome, {st.session_state['user_name']}")
    st.sidebar.info(f"Role: {st.session_state['user_role']}")
    
    # Define Menu based on Role
    menu_options = ["Project Suggestions", "Registration"]
    if st.session_state['user_role'] in ["Examiner", "Coordinator"]:
        menu_options.append("Panelist / Examiner")
    if st.session_state['user_role'] == "Coordinator":
        menu_options.append("Coordinator")
    
    choice = st.sidebar.radio("Menu", menu_options)
    
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.rerun()

    # --- REST OF YOUR LOGIC (Registration, Examiner, Coordinator) ---
    # The 'choice' variable now controls the flow just like 'role' did before.
    if choice == "Registration":
        st.header("Project Registration")
        # [Insert existing registration code here]
    
    elif choice == "Project Suggestions":
        st.header("Project Dashboard")
        # [Insert existing suggestions code here]
    
    # ... and so on for Examiner and Coordinator tabs
