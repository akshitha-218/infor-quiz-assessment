import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- 1. SETTINGS, STYLING & CUSTOM INFOR SPINNER ---
st.set_page_config(page_title="INFOR GBS Assessment", layout="wide", page_icon="🎯")

# SECRET ADMIN CODE - Change this to your secure token
ADMIN_SECRET_KEY = "InforAdmin2026"

# Injecting Custom Infor Crimson Branding & Interface Stripping Rules
st.markdown("""
    <style>
    /* 🚫 HIDES STREAMLIT LOGOS, GITHUB ICONS, AND FLOATING TOP HEADER MENUS */
    header, [data-testid="stHeader"] {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* 🚫 HIDES THE FOOTER AND REDUCES BOTTOM HOSTING WATERMARKS */
    footer {
        visibility: hidden !important;
    }
    
    /* Adjust page margins to compensate for the removed top toolbar */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Infor Brand Primary Button Theme Override */
    div.stButton > button:first-child {
        background-color: #E32229 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.5rem 1rem !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #B31B20 !important;
        color: white !important;
    }
    
    /* Clean Underlined Text Links for Secondary Navigation */
    .infor-link-container {
        display: flex;
        justify-content: space-between;
        margin-top: 15px;
    }
    .infor-text-link {
        color: #E32229 !important;
        text-decoration: underline !important;
        font-weight: 500;
        font-size: 14px;
    }
    .infor-text-link:hover {
        color: #B31B20 !important;
    }

    /* --- CUSTOM CENTRAL LOADING SPINNER OVERRIDE --- */
    div[data-testid="stLoadingElement"] {
        position: fixed !important;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255, 255, 255, 0.85) !important;
        z-index: 999999 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    div[data-testid="stLoadingElement"]::after {
        content: "" !important;
        width: 60px !important;
        height: 60px !important;
        border: 5px solid #f3f3f3 !important;
        border-top: 5px solid #E32229 !important;
        border-radius: 50% !important;
        animation: inforPulseSpinner 1s linear infinite !important;
        box-shadow: 0 0 15px rgba(227, 34, 41, 0.2) !important;
    }
    div[data-testid="stLoadingElement"] > div {
        display: none !important;
    }
    @keyframes inforPulseSpinner {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
""", unsafe_allow_html=True)

# Folder Path Routing Configuration
USER_ACCESS_FOLDER = "UserAccess"
QUESTIONS_FOLDER = "Questions"
OUTPUT_FOLDER = "Completed_Assessments"

WHITELIST_FILE = os.path.join(USER_ACCESS_FOLDER, "AccessTokens.xlsx")
DATABASE_FILE = os.path.join(USER_ACCESS_FOLDER, "User_Database.xlsx")
QUIZ_FILE = os.path.join(QUESTIONS_FOLDER, "Quiz_Worksheet.xlsx")
LOGO_FILE = "infor_logo.webp"

for folder in [OUTPUT_FOLDER, USER_ACCESS_FOLDER, QUESTIONS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def has_already_taken_test(email):
    clean_email_name = email.strip().lower().replace("@", "_").replace(".", "_")
    if os.path.exists(OUTPUT_FOLDER):
        for filename in os.listdir(OUTPUT_FOLDER):
            if filename.startswith(clean_email_name):
                return True
    return False


# --- 💾 CREDENTIAL DATABASE CONTROLLERS ---
def get_user_credentials():
    if not os.path.exists(DATABASE_FILE):
        pd.DataFrame(columns=["Email", "Password"]).to_excel(DATABASE_FILE, index=False)
    try:
        return pd.read_excel(DATABASE_FILE)
    except Exception:
        return pd.DataFrame(columns=["Email", "Password"])

def verify_whitelist_key(email, access_code):
    if not os.path.exists(WHITELIST_FILE):
        return False, f"Missing master configuration file: '{WHITELIST_FILE}'"
    try:
        df = pd.read_excel(WHITELIST_FILE)
        df.columns = df.columns.str.strip()
        clean_email = email.strip().lower()
        clean_code = str(access_code).strip()
        
        if 'Email' not in df.columns:
            return False, "Expected column 'Email' not found in AccessTokens.xlsx"
            
        matched = df[df['Email'].str.strip().str.lower() == clean_email]
        if matched.empty:
            return False, "This email address is not whitelisted for registration."
        if str(matched.iloc[0]['Access_Code']).strip() == clean_code:
            return True, "Valid"
        return False, "Invalid corporate token combination."
    except Exception as e:
        return False, f"Error reading tracking index sheet: {str(e)}"

def register_user_profile(email, password):
    df = get_user_credentials()
    clean_email = email.strip().lower()
    if not df.empty:
        df = df[df['Email'].str.strip().str.lower() != clean_email]
    new_row = pd.DataFrame([{"Email": clean_email, "Password": str(password).strip()}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(DATABASE_FILE, index=False)

def authenticate_login(email, password):
    df = get_user_credentials()
    if df.empty:
        return False
    clean_email = email.strip().lower()
    clean_password = str(password).strip()
    matched = df[df['Email'].str.strip().str.lower() == clean_email]
    if matched.empty:
        return False
    return str(matched.iloc[0]['Password']).strip() == clean_password


# --- 💾 ASSESSMENT EXCEL OUTPUT GENERATOR ---
def save_report_locally(user_email, report_dataframe):
    try:
        clean_email_name = user_email.replace("@", "_").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_email_name}_{timestamp}.xlsx"
        full_filepath = os.path.join(OUTPUT_FOLDER, filename)
        
        summary = report_dataframe.groupby('Domain').agg(Correct=('Raw_Result', 'sum')).reset_index()
        
        strengths = []
        focus_areas = []
        depth_profile = []

        for _, row in summary.iterrows():
            d_name, score = row['Domain'], row['Correct']
            domain_history = report_dataframe[report_dataframe['Domain'] == d_name]
            
            if score >= 4:
                strengths.append(f"{d_name}: Strong grasp ({score}/5)")
            elif score <= 2:
                focus_areas.append(f"{d_name}: Needs improvement ({score}/5)")
            
            if score >= 3:
                correct_questions = domain_history[domain_history['Raw_Result'] == True]
                if not correct_questions.empty:
                    correct_levels = correct_questions['Level'].tolist()
                    if "Hard" in correct_levels:
                        final_proficiency = "Hard"
                    elif "Medium" in correct_levels:
                        final_proficiency = "Medium"
                    else:
                        final_proficiency = "Easy"
                else:
                    final_proficiency = "None"
                
                if final_proficiency != "None":
                    depth_profile.append(f"Demonstrated {final_proficiency} proficiency in {d_name}.")

        max_len = max(len(strengths), len(focus_areas), len(depth_profile), 1)
        strengths += [""] * (max_len - len(strengths))
        focus_areas += [""] * (max_len - len(focus_areas))
        depth_profile += [""] * (max_len - len(depth_profile))
        
        analysis_df = pd.DataFrame({
            "Strengths (Score >= 4/5)": strengths,
            "Focus Areas (Score <= 2/5)": focus_areas,
            "Proficiency Depth (Score >= 3/5)": depth_profile
        })

        clean_report = report_dataframe.drop(columns=['Raw_Result'])

        with pd.ExcelWriter(full_filepath, engine='openpyxl') as writer:
            clean_report.to_excel(writer, index=False, sheet_name="Assessment Summary")
            analysis_df.to_excel(writer, index=False, sheet_name="Performance Analysis")
            
        return True, full_filepath
    except Exception as e:
        return False, str(e)


# --- 2. ASSESSMENT POOL HANDLING ---
@st.cache_data
def load_quiz_data():
    if not os.path.exists(QUIZ_FILE):
        st.error(f"Excel Error: Could not find '{QUIZ_FILE}'. Please verify it exists inside your Questions folder.")
        return None
    try:
        return pd.read_excel(QUIZ_FILE, sheet_name=None)
    except Exception as e:
        st.error(f"Excel Error: '{QUIZ_FILE}' could not be evaluated: {e}")
        return None

def generate_fixed_questions():
    with st.spinner():
        all_data = load_quiz_data()
        if not all_data:
            return []
        domains = sorted(list(all_data.keys()))
        question_pool = []
        for domain in domains:
            df = all_data[domain]
            for difficulty in ["Easy", "Easy", "Medium", "Medium", "Hard"]:
                diff_pool = df[df['Difficulty'] == difficulty]
                if diff_pool.empty: 
                    diff_pool = df
                existing_questions = [q['Question'] for q in question_pool]
                available_pool = diff_pool[~diff_pool['Question'].isin(existing_questions)]
                if available_pool.empty:
                    available_pool = df[~df['Question'].isin(existing_questions)]
                if not available_pool.empty:
                    selected_q = available_pool.sample(n=1).iloc[0].to_dict()
                    selected_q['domain'] = domain
                    question_pool.append(selected_q)
        return question_pool[:25]


# --- 💡 SUBMISSION VALIDATION DIALOG BOX ---
@st.dialog("⚠️ Confirm Early Exam Submission")
def show_early_submission_popup(filled_count):
    unanswered_count = 25 - filled_count
    st.write(f"You have only answered **{filled_count}/25** questions.")
    st.write(f"Submitting now means **{unanswered_count}** remaining questions will be scored as empty/incorrect.")
    st.markdown("---")
    col_cancel, col_confirm = st.columns(2)
    with col_cancel:
        if st.button("🛑 Cancel & Resume", use_container_width=True):
            st.rerun() 
    with col_confirm:
        if st.button("💥 Confirm & Submit", type="primary", use_container_width=True):
            with st.spinner():
                state['complete'] = True
                time.sleep(0.6)
            st.rerun()


# --- 3. PERSISTENT STATE ARCHITECTURE ---
if 'quiz_state' not in st.session_state:
    st.session_state.quiz_state = {
        'questions': [],           
        'active_idx': 0,           
        'user_answers': {},        
        'submitted_questions': {}, 
        'complete': False,
        'celebrated': False,  
        'file_saved': False,
        'saved_filepath': "",
        'is_logged_in': False,  
        'user_email': "",
        'auth_mode': "Login"
    }

state = st.session_state.quiz_state

# --- 🔎 URL ROUTING CAPTURE ENGINE ---
current_view = st.query_params.get("view", "user")

if "action" in st.query_params:
    requested_action = st.query_params["action"]
    if requested_action in ["Login", "SignUp", "ForgotPassword"]:
        state['auth_mode'] = requested_action
    st.query_params.clear()


# --- ⚙️ ROUTE 1: HIDDEN ADMIN PANEL (Only accessible via ?view=admin) ---
if current_view == "admin":
    col_l, col_admin_card, col_r = st.columns([1, 2, 1])
    with col_admin_card:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=110)
        st.write("## 🔐 Corporate Administrative Terminal")
        st.caption("Manual authorization portal for managing log sessions and clear locks.")
        st.markdown("<hr style='border: 1px solid #E32229; margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)
        
        admin_pass = st.text_input("Enter Master Admin Key", type="password", placeholder="Provide secure credentials")
        
        if admin_pass == ADMIN_SECRET_KEY:
            st.success("Authorized: Directory Connection Established.")
            files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith('.xlsx')] if os.path.exists(OUTPUT_FOLDER) else []
            
            if not files:
                st.info("No logs or completed submission sheets found in directory.")
            else:
                st.write(f"### Total Active System Records: ({len(files)})")
                st.divider()
                for file in files:
                    col_file_name, col_del_btn = st.columns([3, 1])
                    with col_file_name:
                        st.text(f"📄 {file}")
                    with col_del_btn:
                        if st.button("❌ Delete & Reset", key=f"del_{file}"):
                            os.remove(os.path.join(OUTPUT_FOLDER, file))
                            st.success("Log cleared! Account unlocked.")
                            time.sleep(0.5)
                            st.rerun()
        elif admin_pass != "":
            st.error("Invalid Administrative Key.")


# --- 🎯 ROUTE 2: REGULAR ASSESSMENT APPLICATION ---
else:
    if not state['is_logged_in']:
        col_left, col_card, col_right = st.columns([1.2, 1.5, 1.2])
        
        with col_card:
            if os.path.exists(LOGO_FILE):
                st.image(LOGO_FILE, width=110)
            else:
                st.title("Infor")
                
            st.write("### INFOR GBS Assessment")
            st.caption("Sign in with your enterprise credentials to begin your assessment.")
            st.markdown("<hr style='border: 1px solid #E32229; margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

            # --- VIEWPORT MODE A: SIGN IN INTERFACE ---
            if state['auth_mode'] == "Login":
                login_email = st.text_input("Corporate Email Address (@infor.com)", key="li_email", placeholder="name@infor.com").strip().lower()
                login_pass = st.text_input("Enter Password", type="password", key="li_pass", placeholder="••••••••")
                
                st.write("<br>", unsafe_allow_html=True)
                
                if has_already_taken_test(login_email):
                    st.error("🚫 Blocked: This corporate account profile has already submitted an assessment.")
                    st.info("ℹ️ **Notice for Re-attempts:** If you submitted your assessment prematurely by mistake, please contact your **Test Administrator/HR** to clear your previous session log.")
                
                if st.button("🔓 Sign In", use_container_width=True):
                    if not login_email.endswith("@infor.com"):
                        st.error("❌ Access Denied: Only valid @infor.com addresses are permitted.")
                    elif has_already_taken_test(login_email):
                        st.error("❌ Sign In Restricted: This profile is locked out. Please consult your administrator.")
                    elif authenticate_login(login_email, login_pass):
                        with st.spinner():
                            state['is_logged_in'] = True
                            state['user_email'] = login_email
                            state['questions'] = generate_fixed_questions()
                            time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Invalid Email or Password configuration mismatch.")
                
                st.markdown("""
                    <div class='infor-link-container' style='justify-content: center;'>
                        <a href='?action=ForgotPassword' target='_self' class='infor-text-link'>Forgot Password?</a>
                        <span style='margin: 0 10px; color: #ccc;'>|</span>
                        <a href='?action=SignUp' target='_self' class='infor-text-link'>Create an Account</a>
                    </div>
                """, unsafe_allow_html=True)

            # --- VIEWPORT MODE B: SIGN UP INTERFACE ---
            elif state['auth_mode'] == "SignUp":
                reg_email = st.text_input("Corporate Email Address (@infor.com)", key="su_email", placeholder="name@infor.com").strip().lower()
                reg_code = st.text_input("Access Key", type="password", key="su_code", placeholder="Received from HR/Admin")
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    reg_pass1 = st.text_input("Define Access Password", type="password", key="su_pass1", placeholder="Min 4 characters")
                with col_p2:
                    reg_pass2 = st.text_input("Confirm Chosen Password", type="password", key="su_pass2", placeholder="Repeat password")
                    
                st.write("<br>", unsafe_allow_html=True)
                if st.button("✨ Register Profile Account", use_container_width=True):
                    existing_records = get_user_credentials()
                    is_already_registered = False if existing_records.empty else reg_email in existing_records['Email'].str.lower().values
                    
                    if not reg_email.endswith("@infor.com"):
                        st.error("❌ Access Restriction: Custom accounts require verified @infor.com profiles.")
                    elif is_already_registered:
                        st.warning("⚠️ This account profile is already registered.")
                    elif reg_pass1 != reg_pass2:
                        st.error("❌ Operational Error: Passwords do not match.")
                    elif len(reg_pass1) < 4:
                        st.error("❌ Security Error: Passwords must contain at least 4 characters.")
                    else:
                        with st.spinner():
                            key_ok, error_msg = verify_whitelist_key(reg_email, reg_code)
                            if key_ok:
                                register_user_profile(reg_email, reg_pass1)
                                st.success("🎉 Registration complete! You can now sign in.")
                                state['auth_mode'] = "Login"
                                time.sleep(0.4)
                                st.rerun()
                            else:
                                st.error(f"❌ Verification Failure: {error_msg}")
                            
                st.markdown("""
                    <div style='text-align: center; margin-top: 15px;'>
                        <a href='?action=Login' target='_self' class='infor-text-link'>⬅️ Back to Existing Login</a>
                    </div>
                """, unsafe_allow_html=True)

            # --- VIEWPORT MODE C: FORGOT PASSWORD INTERFACE ---
            elif state['auth_mode'] == "ForgotPassword":
                st.write("#### Reset Password Credentials")
                reset_email = st.text_input("Corporate Email Address (@infor.com)", key="rst_email", placeholder="name@infor.com").strip().lower()
                reset_code = st.text_input("Your Original Verification Token Code", type="password", key="rst_code", placeholder="Token from AccessTokens.xlsx")
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    reset_pass1 = st.text_input("Define New Password", type="password", key="rst_pass1")
                with col_r2:
                    reset_pass2 = st.text_input("Confirm New Password", type="password", key="rst_pass2")
                    
                st.write("<br>", unsafe_allow_html=True)
                if st.button("🔄 Rewrite Profile Password", use_container_width=True):
                    if reset_pass1 != reset_pass2:
                        st.error("❌ Mismatch: Passwords do not match.")
                    elif len(reset_pass1) < 4:
                        st.error("❌ Passwords must contain at least 4 characters.")
                    else:
                        with st.spinner():
                            key_ok, error_msg = verify_whitelist_key(reset_email, reset_code)
                            if key_ok:
                                register_user_profile(reset_email, reset_pass1)
                                st.success("🔄 Password updated successfully! Moving to login...")
                                state['auth_mode'] = "Login"
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"❌ Token Check Mismatch: {error_msg}")
                                
                st.markdown("""
                    <div style='text-align: center; margin-top: 15px;'>
                        <a href='?action=Login' target='_self' class='infor-text-link'>⬅️ Back to Existing Login</a>
                    </div>
                """, unsafe_allow_html=True)

    # PHASE 2: Navigation & Question Engine
    elif not state['complete']:
        st.title("⚖️ NextGen Assessment")
        st.info(f"Signed In As: **{state['user_email']}**")
        st.divider()

        idx = state['active_idx']
        q = state['questions'][idx]
        
        has_been_submitted = state['submitted_questions'].get(idx, False)
        current_saved_selection = state['user_answers'].get(idx, None)
        
        st.write(f"### Question **{idx + 1} of 25**")
        
        progress_status = ""
        total_filled_out = 0
        for i in range(25):
            if state['submitted_questions'].get(i, False): 
                progress_status += "🔒 "
                total_filled_out += 1
            elif state['user_answers'].get(i, None) is not None: 
                progress_status += "📝 "
                total_filled_out += 1
            else: 
                progress_status += "⬜ "
                
        st.markdown(f"**Exam Map:** {progress_status}")
        st.caption("🔒 Submitted/Locked | 📝 Answered (unlocked draft) | ⬜ Unanswered")
        st.divider()

        st.write(f"### {q['Question']}")
        options = [q['Opt_A'], q['Opt_B'], q['Opt_C'], q['Opt_D']]
        
        radio_index = options.index(current_saved_selection) if current_saved_selection in options else None
        
        selected_option = st.radio(
            "Select the correct answer:", 
            options, 
            index=radio_index, 
            key=f"radio_{idx}", 
            disabled=has_been_submitted
        )
        
        if not has_been_submitted and selected_option is not None:
            state['user_answers'][idx] = selected_option

        if has_been_submitted:
            st.success("🔒 Answer submitted and locked. This question can no longer be edited.")

        st.divider()
        
        nav_col1, nav_col2, action_col, submit_exam_col = st.columns([1, 1, 2, 2])
        
        with nav_col1:
            if st.button("⬅️ Previous", use_container_width=True, disabled=(idx == 0)):
                state['active_idx'] -= 1
                st.rerun()
                
        with nav_col2:
            if st.button("Next ➡️", use_container_width=True, disabled=(idx == 24)):
                state['active_idx'] += 1
                st.rerun()

        with action_col:
            if not has_been_submitted:
                if st.button("🔒 Submit & Advance", type="primary", use_container_width=True):
                    if selected_option is None:
                        st.error("Please select an option before submitting.")
                    else:
                        state['submitted_questions'][idx] = True
                        if state['active_idx'] < 24:
                            state['active_idx'] += 1
                        st.rerun()
            else:
                st.button("🔒 Answer Saved", disabled=True, use_container_width=True)

        with submit_exam_col:
            if st.button("🏁 End & Submit Test", type="secondary", use_container_width=True):
                if total_filled_out < 25:
                    show_early_submission_popup(total_filled_out)
                else:
                    state['complete'] = True
                    st.rerun()

    # PHASE 3: Clean Submission Confirm Screen
    else:
        if not state.get('celebrated', False):
            st.balloons()
            state['celebrated'] = True

        st.write("## ✨ Test submitted successfully!")
        st.divider()
        
        history_records = []
        for i, q in enumerate(state['questions']):
            if i in state['user_answers']:
                user_ans = state['user_answers'][i]
                is_correct = (user_ans == q['Correct'])
                result_tag = "✅" if is_correct else "❌"
            else:
                user_ans = "No Answer Given"
                is_correct = False
                result_tag = "⚪ Not Attempted"
                
            history_records.append({
                "No": i + 1,
                "Domain": q['domain'],
                "Level": q['Difficulty'],
                "User_Selection": user_ans,
                "Result": result_tag,
                "Raw_Result": is_correct
            })
            
        report_df = pd.DataFrame(history_records)
        
        if not report_df.empty:
            if not state['file_saved']:
                success, filepath = save_report_locally(state['user_email'], report_df)
                state['file_saved'] = True
                state['saved_filepath'] = filepath

        st.write("Thank you for completing the INFOR GBS assessment portal. Your responses and skill depth calculations have been safely recorded on our servers.")
        st.write("<br>", unsafe_allow_html=True)
        
        if st.button("Log Out & Close App", type="primary"):
            st.session_state.clear()
            st.rerun()