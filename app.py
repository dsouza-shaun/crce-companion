import math
import os
import re
from datetime import datetime

import pytz
import streamlit as st
from dotenv import load_dotenv
from streamlit_local_storage import LocalStorage

try:
    _localS = LocalStorage()
except Exception:
    class MockLocalStorage:
        def getItem(self, key): return None

        def setItem(self, key, value): pass


    _localS = MockLocalStorage()


def get_item(key): return _localS.getItem(key)

def set_item(key, value): _localS.setItem(key, value)

load_dotenv()
import config
import db_utils
import web_scraper

# For emails
import resend

def send_email_notification(user, user_email, message, rating):
    api_key = os.getenv("RESEND_API_KEY")
    receiver_email = os.getenv("EMAIL_RECEIVER")

    if not api_key:
        return

    resend.api_key = api_key

    # If user didn't provide email, reply-to defaults to my own email (so i don't lose the thread)
    reply_to_address = user_email if user_email else receiver_email

    html_content = f"""
    <h3>🔔 New User Feedback</h3>
    <p><strong>User:</strong> {user}</p>
    <p><strong>Email:</strong> {user_email if user_email else "Not provided"}</p>
    <p><strong>Rating:</strong> {rating}/5 ⭐</p>
    <p><strong>Message:</strong><br>{message}</p>
    <hr>
    <p><em>To reply to the student, simply click "Reply" in your email client.</em></p>
    """

    try:
        resend.Emails.send({
            "from": "Student App <onboarding@resend.dev>",
            "to": receiver_email,
            "reply_to": reply_to_address,  # <--- THIS IS THE MAGIC LINE
            "subject": f"New Feedback from {user} ({rating} Stars)",
            "html": html_content
        })
        print("Email sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")


# --- Helper Functions ---

def identify_semester(subject_code):
    """Extracts semester from subject code (CSC701 -> 7)."""
    match = re.search(r'\d', subject_code)
    return int(match.group()) if match else 0


def scrape_fresh_data(user_details, semester_types=None):
    """
    Scrapes data and organizes it.
    - semester_types: list of "even" and/or "odd" — determines which portal(s) to scrape.
    - Default: Uses the Semester found on the Welcome Page (e.g., 7).
    - Exception: Moves 'CSC8...', 'CSDC8...', 'CSDL8...' subjects to Semester 8.
    """
    if semester_types is None:
        semester_types = ["even"]

    all_organized_data = {}
    last_scraped_at = None

    def get_sem_for_subject(sub_code, default_sem):
        """Checks if subject is explicitly Sem 8, otherwise returns default."""
        code = sub_code.strip().upper()

        # RULE: If code starts with CSC8, CSDC8, or CSDL8 -> Force Sem 8
        if re.search(r"^(CSC|CSDC|CSDL|CSL)8", code):
            return 8

        # Otherwise, stick to what the dashboard says (e.g., Sem 7)
        return default_sem

    for sem_type in semester_types:
        login_url = config.get_login_url(sem_type)
        portal_label = "Odd" if sem_type == "odd" else "Even"

        # 1. Login and get the Dashboard HTML
        session, html = web_scraper.login_and_get_welcome_page(
            user_details["prn"], user_details["dob_day"],
            user_details["dob_month"], user_details["dob_year"],
            user_details["full_name"],
            login_url=login_url
        )
        if not html:
            print(f"Login failed for {portal_label} semester portal.")
            continue

        # 2. Extract the Default Semester from the Dashboard
        dashboard_sem = web_scraper.extract_student_semester(html)
        if not dashboard_sem:
            dashboard_sem = 0

        # 3. Scrape Raw Data
        raw_marks = web_scraper.extract_cie_marks(session, html, base_url=login_url)
        raw_att = web_scraper.extract_detailed_attendance_info(session, html, base_url=login_url)

        # 4. Organize Data (Hybrid Logic) — merge into all_organized_data
        for sub, exams in raw_marks.items():
            sem = get_sem_for_subject(sub, dashboard_sem)
            if sem == 0:
                continue
            if sem not in all_organized_data:
                all_organized_data[sem] = {'cie': {}, 'att': {}}
            all_organized_data[sem]['cie'][sub] = exams

        for sub, details in raw_att.items():
            sem = get_sem_for_subject(sub, dashboard_sem)
            if sem == 0:
                continue
            if sem not in all_organized_data:
                all_organized_data[sem] = {'cie': {}, 'att': {}}
            all_organized_data[sem]['att'][sub] = details

        last_scraped_at = datetime.now(pytz.utc)

    if not all_organized_data:
        return None

    return {
        "semesters_data": all_organized_data,
        "scraped_at": last_scraped_at
    }


def calculate_grade_point(percentage):
    if percentage >= 85.00: return 10
    if 80.00 <= percentage <= 84.99: return 9
    if 70.00 <= percentage <= 79.99: return 8
    if 60.00 <= percentage <= 69.99: return 7
    if 55.00 <= percentage <= 59.99: return 6
    if 50.00 <= percentage <= 54.99: return 5
    if 45.00 <= percentage <= 49.99: return 4
    return 0


# --- Init ---
if 'db_initialized' not in st.session_state:
    db_utils.create_db_and_table_pg()
    db_utils.create_feedback_table_pg()
    st.session_state.db_initialized = True

if 'first_name' not in st.session_state:
    st.session_state.first_name = get_item(key="last_username") or ""
if 'show_add_user_form' not in st.session_state:
    st.session_state.show_add_user_form = False
if 'student_data_result' not in st.session_state:
    st.session_state.student_data_result = None
if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None  # username string when logged in
if 'show_toast' not in st.session_state:
    st.session_state.show_toast = None

st.set_page_config(page_title="CRCE Companion", page_icon="static/contineo.png", layout="wide")
st.header("🎓 CRCE Companion Dashboard")

if not st.session_state.authenticated_user:
    st.markdown("""
<style>
.welcome-card {
    border: 1px solid var(--border-color, rgba(128,128,128,0.2));
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 10px;
}
.welcome-card h4 {
    margin: 0 0 14px 0;
    font-size: 1.1rem;
    font-weight: 600;
}
.welcome-steps {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}
.step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    border: 1px solid var(--border-color, rgba(128,128,128,0.15));
    border-radius: 8px;
    padding: 12px 15px;
    flex: 1 1 180px;
}
.step-num {
    font-size: 0.85rem;
    font-weight: 700;
    opacity: 0.45;
    flex-shrink: 0;
    margin-top: 2px;
    letter-spacing: 0.03em;
}
.step-text strong {
    display: block;
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 4px;
}
.step-text span {
    font-size: 0.9rem;
    opacity: 0.8;
    line-height: 1.5;
}
.mobile-tip {
    margin-top: 15px;
    padding: 10px 15px;
    border-left: 4px solid #FF4B4B;
    background-color: rgba(255, 75, 75, 0.05);
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-color);
}
@media (max-width: 480px) {
    .welcome-steps { flex-direction: column; }
    .step { flex: 1 1 auto; }
}
</style>
<div class="welcome-card">
    <h4>Getting Started</h4>
    <div class="welcome-steps">
        <div class="step">
            <div class="step-num">01</div>
            <div class="step-text">
                <strong>Register</strong>
                <span>Click <em>Register New Student</em> in the sidebar. Choose a username and password, then enter your PRN and date of birth exactly as they appear on the Contineo portal.</span>
            </div>
        </div>
        <div class="step">
            <div class="step-num">02</div>
            <div class="step-text">
                <strong>Log In</strong>
                <span>Enter your username and password in the sidebar and click <em>Login</em>. You only need to do this once per session.</span>
            </div>
        </div>
        <div class="step">
            <div class="step-num">03</div>
            <div class="step-text">
                <strong>View Your Data</strong>
                <span>Use <em>Fetch Data</em> for cached results or <em>Get Live Data</em> to pull the latest information directly from the portal.</span>
            </div>
        </div>
    </div>
    <div class="mobile-tip">
        <strong>Mobile User?</strong> The sidebar is hidden by default. Tap the <strong>&#10095;&#10095;</strong> arrow icon at the top-left corner to open it.
    </div>
</div>
""", unsafe_allow_html=True)

# Injecting the PWA links pointing to local static folder
st.markdown(
    """
    <link rel="manifest" href="/app/static/manifest.json">
    <link rel="apple-touch-icon" href="/app/static/contineo.png">
    <meta name="theme-color" content="#0e1117">
    """,
    unsafe_allow_html=True
)


def on_user_change():
    # When username changes, clear auth and data
    st.session_state.authenticated_user = None
    st.session_state.student_data_result = None


st.sidebar.header("Student Lookup")

# Username, password and login button are always visible when not authenticated
if not st.session_state.authenticated_user:
    st.sidebar.text_input("Username:", key="first_name", on_change=on_user_change)
    sidebar_password = st.sidebar.text_input(
        "Password:", type="password", key="sidebar_password_input"
    )
    login_clicked = st.sidebar.button("Login", type="primary", width="stretch")
else:
    # Already logged in — just read the stored username, no inputs needed
    sidebar_password = ""
    login_clicked = False

first_name_input = st.session_state.first_name.strip()

# Handle Login button click
if login_clicked and first_name_input:
    lookup = db_utils.get_user_from_db_pg(first_name_input)
    if not lookup:
        st.sidebar.error("Username not found.")
    else:
        pw_ok = db_utils.verify_user_password(first_name_input, sidebar_password)
        if pw_ok:
            st.session_state.authenticated_user = first_name_input
            st.session_state.student_data_result = None
            if not db_utils.user_has_password(first_name_input):
                st.session_state.show_toast = ("warning", "⚠️ Account has no password set. Please re-register.")
            else:
                st.session_state.show_toast = ("success", f"Logged in as {first_name_input}!")
            st.rerun()
        else:
            st.sidebar.error("Incorrect password.")

is_authenticated = (st.session_state.authenticated_user == first_name_input) if first_name_input else False

# Show login/logout toast
if st.session_state.get("show_toast"):
    st.toast(st.session_state.show_toast[1])
    st.session_state.show_toast = None

# i have commented the below functionality
# because it was redundant but i have kept it for backward comaptibility
# --- Semester Portal Selector ---
# SEM_TYPE_OPTIONS = {"Even Semester": "even", "Odd Semester": "odd", "Both Semesters": "both"}
# selected_sem_type_label = st.sidebar.selectbox(
#     "Semester Portal",
#     list(SEM_TYPE_OPTIONS.keys()),
#     index=2,  # Default: Both Semesters
#     help="Select which semester portal to scrape from. Use 'Both' to fetch from odd and even portals together."
# )
# selected_sem_type = SEM_TYPE_OPTIONS[selected_sem_type_label]
selected_sem_type = "both"
selected_sem_type_label = "Both Semesters"

# Fetch buttons and logout — only shown when authenticated
fetch_button = False
force_refresh_button = False
if is_authenticated:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        fetch_button = st.button("Fetch Data", type="primary", width='stretch')
        st.caption("**From DB**\n(Cached Data)")
    with col2:
        force_refresh_button = st.button("Get Live Data", width='stretch')
        st.caption("**From Portal**\n(Current Data)")
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", width="stretch"):
        st.session_state.authenticated_user = None
        st.session_state.student_data_result = None
        st.session_state.show_toast = ("success", f"Logged out.")
        st.rerun()
else:
    st.sidebar.markdown("---")

# Add User Form
if st.sidebar.button("➕ Register New Student", type="primary", width='stretch'):
    st.session_state.show_add_user_form = not st.session_state.show_add_user_form

if st.session_state.show_add_user_form:
    with st.sidebar.expander("Add New Student Form", expanded=True):
        with st.form("new_user_form"):
            st.markdown("##### Enter New Student Details:")
            st.info("Please provide details exactly as they appear in the Contineo Portal.")

            new_first_name = st.text_input(
                "App Username (e.g. 'gamer709'):",
                help="Choose a strong unique username. "
                     "This username will be used to log in to CRCE Companion."
            ).strip()
            new_password = st.text_input(
                "Password:",
                type="password",
                help="Choose a strong password and do not share it with anyone. You will need this to log in."
            )
            new_password_confirm = st.text_input(
                "Confirm Password:",
                type="password"
            )
            new_full_name = st.text_input("Full Name (as on Portal):").strip().upper()
            new_prn = st.text_input("Roll no. (Or PRN if you use that):").strip()

            new_dob_day = st.text_input(
                "Date (DD)",
                max_chars=2,
                placeholder="DD"
            ).strip()

            new_dob_month = st.text_input(
                "Month (MM)",
                max_chars=2,
                placeholder="MM"
            ).strip()

            new_dob_year = st.text_input(
                "Year (YYYY)",
                max_chars=4,
                placeholder="YYYY"
            ).strip()

            # Keep only numeric input
            new_dob_day = re.sub(r"\D", "", new_dob_day)
            new_dob_month = re.sub(r"\D", "", new_dob_month)
            new_dob_year = re.sub(r"\D", "", new_dob_year)

            submitted_add_user = st.form_submit_button("Validate & Save Student")

            if submitted_add_user:
                # 1. Local Validation: Check for empty fields
                if not all([new_first_name, new_password, new_password_confirm, new_full_name, new_prn, new_dob_day, new_dob_month, new_dob_year]):
                    st.error("❌ All fields are required.")
                elif new_password != new_password_confirm:
                    st.error("❌ Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                else:
                    # 2. Remote Validation: Attempt to Log in to the Portal
                    with st.spinner("Attempting login to Contineo Portal..."):
                        try:
                            # Use the currently selected semester portal for validation
                            validation_login_url = config.get_login_url(selected_sem_type if selected_sem_type != "both" else "even")
                            session, validation_html = web_scraper.login_and_get_welcome_page(
                                new_prn,
                                new_dob_day,
                                new_dob_month,
                                new_dob_year,
                                new_full_name,
                                login_url=validation_login_url
                            )
                        except Exception as e:
                            session, validation_html = None, None
                            st.error(f"Connection Error: {e}")

                    # 3. Verify Result
                    if validation_html:
                        st.success("Credentials Validated Successfully!\nPlease Wait...")

                        # 4. Save to Database (Only happens if validation passed)
                        save_success = db_utils.add_user_to_db_pg(
                            new_first_name,
                            new_full_name,
                            new_prn,
                            new_dob_day,
                            new_dob_month,
                            new_dob_year,
                            password=new_password
                        )

                        if save_success:
                            st.balloons()
                            st.success(f"User '{new_first_name}' saved to database.")
                            st.session_state.show_add_user_form = False
                            st.rerun()
                        else:
                            st.warning("⚠️ Validation passed, but Username or PRN already exists in the database.")
                    else:
                        # 5. Validation Failed - Do NOT Save
                        st.error("❌ Validation Failed.")
                        st.markdown("""
                        **Possible causes:**
                        1. Incorrect PRN or Date of Birth.
                        2. **Full Name** does not match the portal exactly (check spelling/spacing).
                        3. Portal is currently down.
                        4. Wrong semester portal selected — try switching between **Odd/Even Semester** above.
                        """)
# Fetch Logic — only allowed when authenticated
should_fetch = (
    is_authenticated and
    (fetch_button or force_refresh_button or (first_name_input and not st.session_state.student_data_result))
)

if not is_authenticated and (fetch_button or force_refresh_button) and first_name_input:
    st.sidebar.warning("Please log in first.")

if should_fetch and first_name_input:
    set_item("last_username", first_name_input)
    user_details = db_utils.get_user_from_db_pg(first_name_input)

    if user_details:
        result = None
        source = "Database"

        # 1. Try DB Cache
        if not force_refresh_button:
            with st.spinner("Checking cache..."):
                result = db_utils.get_student_data_from_db(user_details["id"])

        # 2. Scrape if needed
        if not result or force_refresh_button:
            source = "Live Portal"
            # Determine which portal(s) to scrape based on sidebar selection
            if selected_sem_type == "both":
                sem_types_to_scrape = ["even", "odd"]
            else:
                sem_types_to_scrape = [selected_sem_type]
            spinner_msg = f"Fetching from {selected_sem_type_label.lower()} portal..."
            with st.spinner(spinner_msg):
                scrape_res = scrape_fresh_data(user_details, semester_types=sem_types_to_scrape)
                if scrape_res:
                    result = scrape_res
                    # Save to DB (Marks & Attendance linked to Current Semester)
                    for sem, data in result["semesters_data"].items():
                        db_utils.update_student_marks_in_db_pg(
                            user_details["id"], sem, data['cie'], result["scraped_at"]
                        )
                        db_utils.update_attendance_in_db_pg(
                            user_details["id"], sem, data['att']
                        )

                    # Add latest_sem logic for display
                    latest = max(result["semesters_data"].keys()) if result["semesters_data"] else None
                    result["latest_sem"] = latest

        if result:
            st.session_state.student_data_result = {"user_details": user_details, "data_pkg": result, "source": source}
        else:
            st.error("Login Failed or No Data.")
            st.session_state.student_data_result = None
    else:
        st.error("User not found.")

# Display Logic
if st.session_state.student_data_result:
    pkg = st.session_state.student_data_result
    user = pkg["user_details"]
    data = pkg["data_pkg"]
    source = pkg["source"]

    st.subheader(f"Student: {user['full_name']}")

    if data and data.get("scraped_at"):
        ts = data["scraped_at"].astimezone(pytz.timezone('Asia/Kolkata')).strftime('%d-%b %I:%M %p')
        if source == "Database":
            st.info(f"Cached: {ts}")
        else:
            st.success(f"Live: {ts}")

    all_sem_data = data.get("semesters_data", {})
    latest_sem = data.get("latest_sem")

    if all_sem_data:
        # Semester Selector
        sem_options = sorted(all_sem_data.keys(), reverse=True)
        selected_sem = st.selectbox("Select Semester", sem_options, index=0)

        # Get data for selected semester
        current_data = all_sem_data[selected_sem]
        marks_data = current_data.get('cie', {})
        att_data = current_data.get('att', {})

        # SGPA Calculation
        st.markdown(f"### Semester {selected_sem} Performance")

        total_credits = 0
        weighted_gp = 0
        breakdown = []
        db_details = []  # For saving

        if marks_data:
            for sub_code, exams in marks_data.items():
                sub_name = config.SUBJECT_CODE_TO_NAME_MAP.get(sub_code, sub_code)

                if "lab" in sub_name.lower():
                    cred = 1
                elif "project" in sub_name.lower():
                    cred = 3
                else:
                    cred = 3

                obt_sum = 0.0
                max_sum = 0.0

                for ex, val in exams.items():
                    o = val.get('obtained', 0)
                    m = val.get('max', 0)
                    if isinstance(o, (int, float)):
                        obt_sum += o
                        max_sum += m if m > 0 else config.get_max_marks(sub_code, ex)

                if max_sum > 0:
                    perc = (obt_sum / max_sum) * 100
                    rnd_perc = math.floor(perc + 0.5)
                    gp = calculate_grade_point(rnd_perc)

                    weighted_gp += (cred * gp)
                    total_credits += cred

                    grade = "F"
                    if gp == 10:
                        grade = "O"
                    elif gp == 9:
                        grade = "A"
                    elif gp == 8:
                        grade = "B"
                    elif gp == 7:
                        grade = "C"
                    elif gp == 6:
                        grade = "D"
                    elif gp == 5:
                        grade = "E"
                    elif gp == 4:
                        grade = "P"

                    breakdown.append(f"**{sub_name}**: {perc:.1f}% → {grade} ({gp})")
                    db_details.append({
                        "subject_code": sub_code, "subject_name": sub_name,
                        "percentage": float(f"{perc:.2f}"), "grade_point": gp, "grade_letter": grade, "credits": cred
                    })

            if total_credits > 0:
                sgpa = weighted_gp / total_credits

                # Save SGPA if from Live Source
                if source == "Live Portal":
                    db_utils.save_student_sgpi_pg(user["id"], selected_sem, sgpa, db_details)

                c1, c2 = st.columns([2, 3])
                c1.metric("SGPA", f"{sgpa:.2f}")
                with c2:
                    with st.expander("Subject Breakdown"):
                        for b in breakdown: st.markdown(f"- {b}")
                if st.button(f"🏆 Sem {selected_sem} Leaderboard"):
                    lb = db_utils.get_semester_leaderboard_pg(selected_sem)
                    if lb:
                        RANK_STYLES = {
                            1: ("🥇", "#FFD700", "#3d2e00"),
                            2: ("🥈", "#C0C0C0", "#2a2a2a"),
                            3: ("🥉", "#CD7F32", "#2e1a00"),
                        }
                        rows_html = ""
                        for i, (name, score) in enumerate(lb):
                            rank = i + 1
                            medal, bg_light, bg_dark = RANK_STYLES.get(rank, ("", "transparent", "transparent"))
                            is_you = name == user["full_name"]
                            you_badge = ' <span style="font-size:0.7rem;padding:1px 6px;border-radius:4px;background:rgba(128,128,128,0.15);font-weight:600;">You</span>' if is_you else ""
                            rank_cell = f"{medal} {rank}" if medal else str(rank)
                            rows_html += f"""
                            <tr style="background:linear-gradient(90deg,{bg_light}18,transparent);font-weight:{'700' if rank<=3 else '400'};">
                                <td style="padding:8px 12px;text-align:center;font-size:0.9rem;opacity:0.6;">{rank_cell}</td>
                                <td style="padding:8px 12px;font-size:0.88rem;">{name}{you_badge}</td>
                                <td style="padding:8px 12px;text-align:right;font-size:0.9rem;font-variant-numeric:tabular-nums;">{score:.2f}</td>
                            </tr>"""
                        st.markdown(f"""
<style>
.lb-table{{width:100%;border-collapse:collapse;margin-top:8px;}}
.lb-table thead tr{{border-bottom:1px solid rgba(128,128,128,0.25);}}
.lb-table th{{padding:6px 12px;font-size:0.75rem;opacity:0.5;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;}}
.lb-table th:last-child,.lb-table td:last-child{{text-align:right;}}
.lb-table tbody tr{{border-bottom:1px solid rgba(128,128,128,0.08);}}
.lb-table tbody tr:hover{{background:rgba(128,128,128,0.05)!important;}}
</style>
<table class="lb-table">
  <thead><tr><th>#</th><th>Student</th><th>SGPA</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)
                    else:
                        st.caption("No leaderboard data.")
        else:
            st.info("No marks available for this semester.")

        st.divider()

        # --- Attendance & Marks Columns ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Attendance")
            if att_data:
                att_display = []
                for sub, det in att_data.items():
                    # --- Formatting: Name (Code) ---
                    subject_name = config.SUBJECT_CODE_TO_NAME_MAP.get(sub, sub)
                    display_name = f"{subject_name} ({sub})"

                    att = det.get('attended', 0)
                    cond = det.get('conducted', 0)

                    if cond > 0:
                        p = (att / cond) * 100
                        status = "N/A"
                        if p >= 75:
                            miss = math.floor((att / 0.75) - cond)
                            status = f"✅ Safe by {int(miss)} class(es)"
                        else:
                            need = math.ceil(((0.75 * cond) - att) / 0.25)
                            status = f"⚠️ Low. Attend {int(need)} class(es)"

                        att_display.append(
                            {"Subject": display_name, "Attendance": f"{p:.1f}%", "Status(For 75%)": status})
                st.dataframe(att_display, width='stretch', hide_index=True)
            else:
                st.info("No attendance records.")

        with col2:
            st.subheader("Marks")
            if marks_data:
                for sub, exams in marks_data.items():
                    # --- Formatting: Name (Code) ---
                    subject_name = config.SUBJECT_CODE_TO_NAME_MAP.get(sub, sub)
                    display_name = f"{subject_name} ({sub})"

                    # Initialize totals for this subject
                    sub_total_obt = 0
                    sub_total_max = 0

                    with st.expander(f"{display_name}"):
                        for ex, val in exams.items():
                            if isinstance(val, dict):
                                o = val.get('obtained', 0)
                                m = val.get('max', 0)

                                # Display the individual exam line
                                st.write(f"**{ex}:** {o} / {m}")

                                # Add to running total
                                sub_total_obt += float(o)
                                sub_total_max += float(m)
                            else:
                                # Fallback for old data formats
                                st.write(f"**{ex}:** {val}")

                        # Display the Total at the very end
                        st.markdown("---")
                        st.markdown(f"**Total:** {sub_total_obt} / {sub_total_max}")

            else:
                st.info("No marks records.")
    else:
        st.warning("No data found for any semester.")

elif (fetch_button or force_refresh_button) and not first_name_input:
    st.sidebar.warning("Please enter a username to fetch data.")

# Sticky Bottom Sidebar Footer
st.sidebar.markdown(
    """
    <style>
    [data-testid="stSidebarContent"] {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }

    .sidebar-footer {
        margin-top: auto;
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <div class="sidebar-footer">
        <hr>
        <p style="font-size: 1rem; color: gray; margin-bottom: 0.5rem;">
            Created by 
            <a href="https://github.com/dsouza-shaun" target="_blank" style="color: #4F8BF9; text-decoration: none; font-weight: bold;">
                Shaun Dsouza
            </a>
        </p>
        <p style="font-size: 0.85rem; color: gray; line-height: 1.2;">
            Inspired by 
            <a href="https://github.com/MarkLopes11/Contineo" target="_blank" style="color: #4F8BF9;">
                Mark Lopes' Contineo
            </a> version
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()
st.subheader("💬 Feedback & Support")

with st.expander("Report a bug or leave a suggestion", expanded=True):
    with st.form("feedback_form_main"):
        current_user = st.session_state.first_name.strip() if st.session_state.first_name else "Anonymous"

        c1, c2 = st.columns([1, 4])

        with c1:
            st.write("**Rate your experience:**")
            selected_sentiment = st.feedback("stars")

        with c2:
            # New Email Input
            fb_email = st.text_input("Your Email:")
            fb_msg = st.text_area("Message", placeholder="Tell us what you think...")

        submitted_fb = st.form_submit_button("Submit Feedback")

        if submitted_fb:
            final_rating = (selected_sentiment + 1) if selected_sentiment is not None else 0

            if final_rating == 0:
                st.warning("⚠️ Please select a Star Rating.")
            elif not fb_msg.strip():
                st.warning("⚠️ Please write a message.")
            else:
                # 1. Save to Database (Pass email now)
                if db_utils.save_feedback_pg(current_user, fb_email, fb_msg, final_rating):

                    # 2. Send Email Notification (Pass email now)
                    send_email_notification(current_user, fb_email, fb_msg, final_rating)

                    st.success("Thank you! Your feedback has been recorded. ❤️")
                    st.balloons()
                else:
                    st.error("Internal Error: Could not save feedback.")