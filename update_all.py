# BATCH UPDATE SCRIPT
import re
import time
from datetime import datetime

import pytz
from dotenv import load_dotenv

load_dotenv()

import db_utils
import web_scraper
import config
from app import compute_sgpa

DELAY_BETWEEN_REQUESTS = 10  # Seconds to wait between students


def identify_target_semester(sub_code, default_sem):
    code = sub_code.strip().upper()
    if re.search(r"^(CSC|CSDC|CSDL|CSL)8", code):
        return 8
    return default_sem


def run_update():
    print("=" * 60)
    print("Starting BATCH UPDATE: Both Odd & Even Semesters")
    print("=" * 60)

    all_users = db_utils.get_all_users_from_db_pg()

    if not all_users:
        print("❌ No users found in the database. Exiting.")
        return

    total_users = len(all_users)
    print(f"✅ Found {total_users} users to process.\n")

    success_count = 0
    fail_count = 0

    for i, user in enumerate(all_users):
        user_id = user['id']
        full_name = user['full_name']
        prn = user['prn']

        print("-" * 50)
        print(f"[{i + 1}/{total_users}] Processing: {full_name} (PRN: {prn})")

        try:
            # Try both Even and Odd semester portals
            organized_data = {}

            for sem_type in ["even", "odd"]:
                login_url = config.get_login_url(sem_type)
                portal_label = "Odd" if sem_type == "odd" else "Even"
                print(f"   🔄 Trying {portal_label} semester portal...")

                session, html = web_scraper.login_and_get_welcome_page(
                    prn, user['dob_day'], user['dob_month'], user['dob_year'], full_name,
                    login_url=login_url
                )

                if not html:
                    print(f"   ⚠️ {portal_label} portal login failed. Skipping.")
                    continue

                raw_marks = web_scraper.extract_cie_marks(session, html, base_url=login_url)
                raw_att = web_scraper.extract_detailed_attendance_info(session, html, base_url=login_url)
                dashboard_sem = web_scraper.extract_student_semester(html) or 0

                for sub, exams in raw_marks.items():
                    sem = identify_target_semester(sub, dashboard_sem)
                    if sem == 0:
                        continue
                    if sem not in organized_data: organized_data[sem] = {'cie': {}, 'att': {}}
                    organized_data[sem]['cie'][sub] = exams

                for sub, details in raw_att.items():
                    sem = identify_target_semester(sub, dashboard_sem)
                    if sem == 0:
                        continue
                    if sem not in organized_data: organized_data[sem] = {'cie': {}, 'att': {}}
                    organized_data[sem]['att'][sub] = details

                print(f"   ✅ {portal_label} portal scraped successfully.")

            if not organized_data:
                print(f"   ❌ No data from either portal. Skipping.")
                fail_count += 1
                continue

            timestamp = datetime.now(pytz.utc)

            # 4. Process each semester found
            for sem, data in organized_data.items():
                print(f"   💾 Updating Semester {sem}...")

                # Save Marks & Attendance to DB
                if data['cie']:
                    db_utils.update_student_marks_in_db_pg(user_id, sem, data['cie'], timestamp)
                if data['att']:
                    db_utils.update_attendance_in_db_pg(user_id, sem, data['att'])

                if data['cie']:
                    sgpa_result = compute_sgpa(data['cie'])
                    if sgpa_result:
                        db_utils.save_student_sgpi_pg(user_id, sem, sgpa_result["sgpa"], sgpa_result["db_details"])
                        print(f"      Saved SGPA: {sgpa_result['sgpa']:.2f}")

            print(f"   ✅ {full_name} updated successfully.")
            success_count += 1

        except Exception as e:
            print(f"   Error processing {full_name}: {e}")
            fail_count += 1

        # Rate Limiting
        if i + 1 < total_users:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n" + "=" * 60)
    print("🎉 BATCH UPDATE COMPLETE")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    run_update()