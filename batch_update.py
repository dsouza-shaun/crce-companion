# 1. Run manually (interactive)
# uv run batch_update.py
#
# 2. Run directly via CLI args
# uv run batch_update.py CE B
# uv run batch_update.py CSE A

import logging
import re
import sys
import time
from datetime import datetime

import pytz

import config
import db_utils
import web_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("batch_update")

# --- Core Scraping & Calculation Logic (Mirrors app.py, Streamlit-free) ---
def scrape_fresh_data(user_details, semester_types=None):
    if semester_types is None:
        semester_types = ["even"]
    all_organized_data = {}
    last_scraped_at = None

    def get_sem_for_subject(sub_code, default_sem):
        code = sub_code.strip().upper()
        if re.search(r"^(CSC|CSDC|CSDL|CSL)8", code):
            return 8
        return default_sem

    for sem_type in semester_types:
        login_url = config.get_login_url(sem_type)
        session, html = web_scraper.login_and_get_welcome_page(
            user_details["prn"], user_details["dob_day"],
            user_details["dob_month"], user_details["dob_year"],
            user_details["full_name"], login_url=login_url
        )
        if not html:
            logger.warning(f"Login failed for {user_details['full_name']} on {sem_type} portal.")
            continue

        dashboard_sem = web_scraper.extract_student_semester(html)
        if not dashboard_sem:
            dashboard_sem = 0

        raw_marks = web_scraper.extract_cie_marks(session, html, base_url=login_url)
        raw_att = web_scraper.extract_detailed_attendance_info(session, html, base_url=login_url)

        for sub, exams in raw_marks.items():
            sem = get_sem_for_subject(sub, dashboard_sem)
            if sem == 0: continue
            if sem not in all_organized_data:
                all_organized_data[sem] = {'cie': {}, 'att': {}}
            all_organized_data[sem]['cie'][sub] = exams

        for sub, details in raw_att.items():
            sem = get_sem_for_subject(sub, dashboard_sem)
            if sem == 0: continue
            if sem not in all_organized_data:
                all_organized_data[sem] = {'cie': {}, 'att': {}}
            all_organized_data[sem]['att'][sub] = details

        last_scraped_at = datetime.now(pytz.utc)

    if not all_organized_data:
        return None
    return {"semesters_data": all_organized_data, "scraped_at": last_scraped_at}

def calculate_grade_point(percentage):
    if percentage >= 85.00: return 10
    if 80.00 <= percentage <= 84.99: return 9
    if 70.00 <= percentage <= 79.99: return 8
    if 60.00 <= percentage <= 69.99: return 7
    if 50.00 <= percentage <= 59.99: return 6
    if 45.00 <= percentage <= 49.99: return 5
    if 40.00 <= percentage <= 44.99: return 4
    return 0

def _grade_letter(gp):
    return {10: "O", 9: "A", 8: "B", 7: "C", 6: "D", 5: "E", 4: "P", 0: "F"}.get(gp, "F")

def _resolve_credits(sub_code, sub_name):
    if sub_code in config.SUBJECT_CODE_TO_CREDITS_MAP:
        return config.SUBJECT_CODE_TO_CREDITS_MAP[sub_code], False
    if "project" in sub_name.lower(): return 3, True
    if "tools" in sub_name.lower(): return 2, True
    if "lab" in sub_name.lower(): return 1, True
    return 3, True

def compute_sgpa(cie_data):
    if not cie_data: return None
    total_credits = weighted_gp = 0
    db_details = []
    for sub_code, exams in cie_data.items():
        sub_name = config.SUBJECT_CODE_TO_NAME_MAP.get(sub_code, sub_code)
        cred, _ = _resolve_credits(sub_code, sub_name)
        obt_sum, max_sum = 0.0, 0.0
        for ex, val in exams.items():
            o, m = val.get('obtained', 0), val.get('max', 0)
            if isinstance(o, (int, float)):
                obt_sum += o
                max_sum += m if m > 0 else config.get_max_marks(sub_code, ex)
        if max_sum > 0:
            perc = (obt_sum / max_sum) * 100
            gp = calculate_grade_point(perc)
            weighted_gp += cred * gp
            total_credits += cred
            db_details.append({"subject_code": sub_code, "subject_name": sub_name, "percentage": float(f"{perc:.2f}"), "grade_point": gp, "grade_letter": _grade_letter(gp), "credits": cred})
    if total_credits == 0: return None
    return {"sgpa": weighted_gp / total_credits, "total_credits": total_credits, "db_details": db_details}

def compute_sgpa_separated(cie_data):
    if not cie_data: return None
    total_credits = weighted_gp = 0
    db_details = []
    for sub_code, exams in cie_data.items():
        sub_name = config.SUBJECT_CODE_TO_NAME_MAP.get(sub_code, sub_code)
        if sub_code not in config.SUBJECT_CREDIT_BREAKDOWN:
            cred, _ = _resolve_credits(sub_code, sub_name)
            obt_sum, max_sum = 0.0, 0.0
            for ex, val in exams.items():
                o, m = val.get('obtained', 0), val.get('max', 0)
                if isinstance(o, (int, float)):
                    obt_sum += o
                    max_sum += m if m > 0 else config.get_max_marks(sub_code, ex)
            if max_sum > 0:
                perc = (obt_sum / max_sum) * 100
                gp = calculate_grade_point(perc)
                weighted_gp += cred * gp
                total_credits += cred
                db_details.append({"subject_code": sub_code, "subject_name": sub_name, "component": "Total", "percentage": float(f"{perc:.2f}"), "grade_point": gp, "grade_letter": _grade_letter(gp), "credits": cred})
            continue

        credits_map = config.SUBJECT_CREDIT_BREAKDOWN[sub_code]
        components = {"TH": {"obt": 0.0, "max": 0.0}, "PR": {"obt": 0.0, "max": 0.0}, "TU": {"obt": 0.0, "max": 0.0}}
        for ex, val in exams.items():
            o, m = val.get('obtained', 0), val.get('max', 0)
            if isinstance(o, (int, float)):
                m_actual = m if m > 0 else config.get_max_marks(sub_code, ex)
                comp = "PR" if "PR-" in ex else ("TU" if "TU-" in ex else "TH")
                components[comp]["obt"] += o
                components[comp]["max"] += m_actual

        for comp in ["TH", "PR", "TU"]:
            cred = credits_map.get(comp, 0)
            if cred > 0 and components[comp]["max"] > 0:
                perc = (components[comp]["obt"] / components[comp]["max"]) * 100
                gp = calculate_grade_point(perc)
                weighted_gp += cred * gp
                total_credits += cred
                db_details.append({"subject_code": sub_code, "subject_name": sub_name, "component": comp, "percentage": float(f"{perc:.2f}"), "grade_point": gp, "grade_letter": _grade_letter(gp), "credits": cred})

    if total_credits == 0: return None
    return {"sgpa": weighted_gp / total_credits, "total_credits": total_credits, "db_details": db_details}

def calculate_and_save_sgpa(user_id, sem, cie_data):
    result = compute_sgpa(cie_data)
    result_sep = compute_sgpa_separated(cie_data)
    if result:
        db_utils.save_student_sgpi_pg(
            user_id, sem, result["sgpa"], result["db_details"],
            result_sep["sgpa"] if result_sep else None,
            result_sep["db_details"] if result_sep else None
        )

# --- Batch Runner ---
def run_batch_update(dept, division, delay=10):
    logger.info(f"Targeting: {dept}-{division}")
    all_users = db_utils.get_all_users_from_db_pg()
    target_users = [u for u in all_users if u.get("department", "").upper() == dept.upper() and u.get("division", "").upper() == division.upper()]

    if not target_users:
        logger.error(f"❌ No users found for {dept}-{division}. Check DB or spelling.")
        return

    logger.info(f"Found {len(target_users)} students. Starting batch scrape...")
    success, failed = 0, 0

    for idx, user in enumerate(target_users, 1):
        logger.info(f"[{idx}/{len(target_users)}] Processing: {user['full_name']} (PRN: {user['prn']})")
        try:
            result = scrape_fresh_data(user, semester_types=["even", "odd"])
            if not result:
                logger.warning(f"⚠️ No data returned for {user['full_name']}")
                failed += 1
                continue

            scraped_at = result.get("scraped_at", datetime.now(pytz.utc))
            for sem, data in result["semesters_data"].items():
                db_utils.update_student_marks_in_db_pg(user["id"], sem, data.get('cie', {}), scraped_at)
                db_utils.update_attendance_in_db_pg(user["id"], sem, data.get('att', {}))
                if data.get('cie'):
                    calculate_and_save_sgpa(user["id"], sem, data['cie'])

            logger.info(f"✅ Updated {user['full_name']}")
            success += 1
        except Exception as e:
            logger.error(f"❌ Failed {user['full_name']}: {e}")
            failed += 1

        if idx < len(target_users):
            time.sleep(delay) # To avoid IP bans

    logger.info(f"Batch complete. ✅ Success: {success} | ❌ Failed: {failed}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        dept_input = sys.argv[1].upper()
        div_input = sys.argv[2].upper()
    else:
        dept_input = input("Enter Department (CE/CSE/ECS/MECH): ").strip().upper()
        div_input = input("Enter Division (A/B/C): ").strip().upper()

    if dept_input not in ["CE", "CSE", "ECS", "MECH"]:
        logger.error("Invalid Department. Must be CE, CSE, ECS, or MECH.")
        sys.exit(1)
    if div_input not in ["A", "B", "C"]:
        logger.error("Invalid Division. Must be A, B, or C.")
        sys.exit(1)

    run_batch_update(dept_input, div_input)