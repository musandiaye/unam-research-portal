import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")

# --- LOGO ---
LOGO_URL = "unam_logo.png" 
try:
    st.sidebar.image(LOGO_URL, use_container_width=True)
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
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

# --- AUTHENTICATION LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""

# --- SIDEBAR NAVIGATION ---
role = st.sidebar.radio("Management Menu", ["Student Registration", "Student View (Results)", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE 2: PANELIST / EXAMINER (WITH SELF-REGISTRATION) ---
if role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            st.subheader("Lecturer Login")
            login_user = st.text_input("Username", key="l_user")
            login_pw = st.text_input("Password", type="password", key="l_pw")
            if st.button("Login"):
                users_df = load_data("users")
                if not users_df.empty:
                    # Filter for user
                    user_row = users_df[users_df['username'] == login_user]
                    if not user_row.empty and user_row.iloc[0]['password'] == hash_password(login_pw):
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user_row.iloc[0]['full_name']
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")
        
        with tab2:
            st.subheader("New Lecturer Registration")
            new_fullname = st.text_input("Full Name (e.g., Dr. Smith)")
            new_user = st.text_input("Choose Username")
            new_pw = st.text_input("Choose Password", type="password")
            dept_key = st.text_input("Department Authorization Key", type="password")
            
            if st.button("Register Account"):
                if dept_key != "JEDSECE2026":
                    st.error("Incorrect Department Key. Account creation denied.")
                elif not new_fullname or not new_user or not new_pw:
                    st.error("All fields are required.")
                else:
                    users_df = load_data("users")
                    if not users_df.empty and new_user in users_df['username'].values:
                        st.error("Username already exists.")
                    else:
                        new_user_row = pd.DataFrame([{
                            "full_name": new_fullname,
                            "username": new_user,
                            "password": hash_password(new_pw)
                        }])
                        updated_users = pd.concat([users_df, new_user_row], ignore_index=True)
                        conn.update(worksheet="users", data=updated_users)
                        st.success("Account created! You can now login.")

    else:
        st.sidebar.success(f"Logged in as: {st.session_state['user_name']}")
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

        # --- SCORING INTERFACE (ONLY VISIBLE IF LOGGED IN) ---
        students_df = load_data("students")
        marks_df = load_data("marks")
        
        names_list = sorted(students_df['student_name'].unique().tolist()) if not students_df.empty else []
        s_name_sel = st.selectbox("Search Student Name", options=["[New Student]"] + names_list)
        
        selected_id, selected_title, selected_email = "", "", ""
        if s_name_sel != "[New Student]":
            row = students_df[students_df['student_name'] == s_name_sel].iloc[0]
            selected_id = clean_id(row['student_id'])
            selected_title = row.get('research_title', "")
            selected_email = row.get('email', "")

        with st.form("scoring_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value=s_name_sel if s_name_sel != "[New Student]" else "")
                final_id = st.text_input("Student Number", value=selected_id)
                final_email = st.text_input("Email", value=selected_email)
            with col2:
                final_title = st.text_area("Research Title", value=selected_title)
                p_type = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
                st.write(f"**Examiner:** {st.session_state['user_name']}")

            st.divider()
            st.markdown("#### A. Data Collection")
            st.caption("LO 1, 2 & 3 + ECN ELO 4 & 5")
            d_coll = st.slider("Mark", 0.0, 10.0, 0.0, 0.5, key="sc1")

            st.markdown("#### B. Data Analysis and Interpretation")
            st.caption("LO 1, 2 & 3 + ECN ELO 4 & 5")
            d_anal = st.slider("Mark", 0.0, 10.0, 0.0, 0.5, key="sc2")

            st.markdown("#### C. Professional Communication")
            st.caption("LO 5 + ECN ELO 6")
            d_comm = st.slider("Mark", 0.0, 10.0, 0.0, 0.5, key="sc3")

            remarks = st.text_area("Remarks")
            
            if st.form_submit_button("Submit Assessment"):
                cid = clean_id(final_id)
                total = float(d_coll + d_anal + d_comm)
                new_mark = pd.DataFrame([{
                    "student_id": cid, "student_name": final_name, "email": final_email,
                    "research_title": final_title, "assessment_type": p_type,
                    "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm,
                    "total_out_of_30": total, "examiner": st.session_state['user_name'], 
                    "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                conn.update(worksheet="marks", data=pd.concat([marks_df, new_mark], ignore_index=True))
                st.success("Marks Submitted!")

# --- (Other roles: Registration, Student View, Coordinator logic follows same clean_id logic) ---
elif role == "Student Registration":
    st.header("📝 Research Project Registration")
    with st.form("reg"):
        n = st.text_input("Full Name"); i = st.text_input("Student ID"); e = st.text_input("Email")
        s = st.text_input("Supervisor"); t = st.text_area("Title")
        if st.form_submit_button("Register"):
            sd = load_data("students"); ci = clean_id(i)
            if not all([n, ci, e, s, t]): st.error("Fill all fields")
            elif not sd.empty and ci in sd['student_id'].astype(str).values: st.error("Already registered")
            else:
                new_s = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, new_s], ignore_index=True))
                st.success("Registered!")

elif role == "Student View (Results)":
    st.header("📋 Student Grade Tracker")
    sid = st.text_input("Enter Student Number")
    if sid:
        m = load_data("marks"); tid = clean_id(sid)
        res = m[m['student_id'] == tid]
        if not res.empty:
            st.write(f"### Results for: {res.iloc[0]['student_name']}")
            avg = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
            avg['total_out_of_30'] = avg['total_out_of_30'].map('{:,.1f}'.format)
            st.table(avg)

elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    if st.sidebar.text_input("Password", type="password") == "Blackberry":
        sd = load_data("students"); md = load_data("marks")
        if not sd.empty:
            if not md.empty:
                # Merge logic
                md['student_id'] = md['student_id'].apply(clean_id)
                piv = md.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index()
                rep = pd.merge(sd, piv, on='student_id', how='left').fillna(0.0)
            else: rep = sd
            st.dataframe(rep, use_container_width=True)
