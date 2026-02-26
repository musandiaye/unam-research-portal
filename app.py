import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas  # Requires: pip install streamlit-drawable-canvas
import pandas as pd
from datetime import datetime
import hashlib
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Engineering Portal", layout="wide")

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

mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""
    st.session_state['user_email'] = ""

# --- SIDEBAR ---
st.sidebar.header("Navigation")
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator", "Project Suggestions"])
project_type = st.sidebar.radio("Select Stream", ["Research Project", "Design Project"])

# --- REGISTRATION (Includes Abstract) ---
if role == "Registration":
    if project_type == "Research Project":
        st.header("📝 Student Research Registration")
        with st.form("reg_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            i = st.text_input("Student ID")
            e = st.text_input("Email")
            s = st.text_input("Supervisor")
            t = st.text_area("Research Title")
            abst = st.text_area("Research Abstract (Max 250 words)")
            if st.form_submit_button("Submit Registration"):
                sd = load_data("students")
                word_count = len(abst.split())
                if not all([n, i, e, s, t, abst]): st.error("Fill all fields.")
                elif word_count > 250: st.error("Abstract exceeds 250 words.")
                else:
                    nr = pd.DataFrame([{"student_id":clean_id(i),"student_name":n,"email":e,"supervisor":s,"research_title":t, "abstract":abst}])
                    conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                    st.success("Registered!")
    else:
        st.header("👥 Design Group Registration")
        with st.form("design_reg", clear_on_submit=True):
            g_name = st.text_input("Group Name")
            superv = st.text_input("Supervisor")
            g_abst = st.text_area("Abstract (Max 250 words)")
            m1_n = st.text_input("M1 Name"); m1_id = st.text_input("M1 ID")
            m2_n = st.text_input("M2 Name"); m2_id = st.text_input("M2 ID")
            m3_n = st.text_input("M3 Name"); m3_id = st.text_input("M3 ID")
            if st.form_submit_button("Submit Group"):
                word_count = len(g_abst.split())
                if word_count > 250: st.error("Abstract too long.")
                else:
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id)]:
                        if name and sid: new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv, "abstract": g_abst})
                    conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                    st.success("Group Registered!")

# --- PANELIST / EXAMINER (Includes E-Signature) ---
elif role == "Panelist / Examiner":
    if not st.session_state['logged_in']:
        # [Login/Signup code remains same as stable release]
        pass 
    else:
        st.header(f"🧑‍🏫 Examiner Portal ({project_type})")
        assess_tab, suggest_tab = st.tabs(["Assess Students", "Suggest Projects"])
        
        with assess_tab:
            ws = "design_marks" if project_type == "Design Project" else "marks"
            m_df = load_data(ws)
            
            if project_type == "Research Project":
                s_df = load_data("students")
                target = st.selectbox("Select Student", options=[""] + sorted(s_df['student_name'].tolist()) if not s_df.empty else [""])
                f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target = st.selectbox("Select Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            # RUBRICS (Mapping criteria from PDF Guidelines)
            m_c1 = m_c2 = m_c3 = m_c4 = m_c5 = 0.0
            if "Report" in f_stage:
                raw_mark = st.number_input("Final Mark (0-100)", 0.0, 100.0)
            elif project_type == "Research Project":
                if "Presentation 1" in f_stage:
                    m_c1 = st.select_slider("1. Problem Statement (LO 1, 2)", mark_options)
                    st.caption("Guidelines: WHAT/WHERE/WHEN/HOW/WHY, objectives, and environmental impact.")
                    m_c2 = st.select_slider("2. Literature Review (LO 6)", mark_options)
                    st.caption("Guidelines: Referencing style, critique of gaps in previous work.")
                    m_c3 = st.select_slider("3. Methodology (LO 2, 3)", mark_options)
                    st.caption("Guidelines: Valid methodology and specified ICT instruments.")
                    m_c4 = st.select_slider("4. Project Planning (LO 1)", mark_options)
                    st.caption("Guidelines: Valid milestones and resource consideration.")
                    m_c5 = st.select_slider("5. Communication (LO 5)", mark_options)
                    st.caption("Guidelines: Terminology, illustrations, and Q&A defense.")
                    raw_mark = float(m_c1 + m_c2 + m_c3 + m_c4 + m_c5)
                # [Other research stages 2 & 3 follow same pattern...]

            remarks = st.text_area("Examiner Remarks")

            # --- E-SIGNATURE OPTION ---
            st.subheader("🖋️ Examiner Authorization")
            st.write("Please sign in the box below to validate these marks.")
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#eeeeee",
                height=150,
                width=400,
                drawing_mode="freedraw",
                key="canvas",
            )

            if st.button("Submit Verified Assessment"):
                if not target:
                    st.error("Please select a student/group.")
                elif canvas_result.json_data is None or len(canvas_result.json_data["objects"]) == 0:
                    st.error("Mark validity error: Digital signature is required before submission.")
                else:
                    id_col = "student_id" if project_type == "Research Project" else "group_name"
                    new_row = pd.DataFrame([{
                        id_col: target, 
                        "assessment_type": f_stage, 
                        "raw_mark": raw_mark, 
                        "examiner": st.session_state['user_name'], 
                        "remarks": remarks,
                        "signature_status": "Verified-Digital",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                    st.success("Assessment submitted and signed successfully!")

# --- COORDINATOR ---
# [Coordinator code remains same as stable release]
