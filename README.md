# CRCE Companion

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-7C3AED?style=for-the-badge&logo=uv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A modern, fast, and insightful dashboard for CRCE Contineo student portal data.**

Register once, access your attendance and marks anytime — no more repetitive logins.

</div>

---

## The Problem

The official Contineo student portal is tedious to use every day:

- **Repetitive Login** — You must enter your PRN and full Date of Birth every single time you want to check your data.
- **No Insights** — The portal shows your attendance percentage, but doesn't tell you how many lectures you can safely miss or need to attend to stay above the 75% threshold.
- **No Comparison** — There's no way to see how you're performing compared to your classmates.
- **Odd/Even Separation** — Odd and even semester data lives on separate portals with different URLs, making it annoying to check both.

## Features

- **One-Time Registration** — Save your PRN and DOB once, linked to a username of your choice. Your credentials are validated against the live portal before saving.
- **Odd & Even Semester Support** — Automatically scrapes data from both the odd and even semester portals, so all your data is available in one place.
- **Smart Attendance Tracker**
  - Displays current attendance percentage for every subject.
  - Calculates exactly how many lectures you can **miss** while staying above 75%.
  - Tells you how many lectures you must **attend** to get back to 75% if you're below.
- **Detailed CIE Marks** — Clean breakdown of marks for MSE, ISE, ESE, and lab exams with per-subject totals.
- **SGPI Calculation** — Automatically computes your Semester Grade Point Index with a subject-wise grade breakdown.
- **Semester Leaderboards** — See how you rank against your classmates for any semester.
- **Live Data & Caching**
  - **Fetch Data** — Retrieves cached data from the database (instant).
  - **Get Live Data** — Scrapes the portal for the most up-to-the-minute information.
- **Feedback System** — Built-in feedback form with email notifications via Resend.


## Tech Stack

| Layer               | Technology                                                                                                      |
|---------------------|-----------------------------------------------------------------------------------------------------------------|
| Frontend            | [Streamlit](https://streamlit.io/)                                                                              |
| Web Scraping        | [Requests](https://requests.readthedocs.io/) & [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Database            | [PostgreSQL](https://www.postgresql.org/) via [Neon](https://neon.tech/)                                        |
| Email Notifications | [Resend](https://resend.com/)                                                                                   |
| Package Manager     | [uv](https://docs.astral.sh/uv/)                                                                                |
| Deployment          | Streamlit Community Cloud                                                                                       |

## Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Python 3.13+ (handled automatically by uv)
- A PostgreSQL database (recommended: [Neon](https://neon.tech/) free tier)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dsouza-shaun/crce-companion.git
   cd crce-companion
   ```

2. **Install dependencies with uv:**
   ```bash
   uv sync
   ```
   This creates a virtual environment automatically and installs all dependencies from `pyproject.toml` using the locked versions in `uv.lock`.

3. **Set up environment variables:**

   Create a `.env` file in the project root:

   ```ini
   NEON_DB_PASSWORD=your_db_password
   NEON_DB_URI=your_db_host
   PG_DBNAME=your_db_name
   PG_USER=your_db_user
   EMAIL_RECEIVER=your_email@gmail.com
   RESEND_API_KEY=your_resend_key
   ```

4. **Run the app:**
   ```bash
   uv run streamlit run app.py
   ```

## How to Use

1. **Register** — Click "Register New Student" in the sidebar. Enter your details *exactly* as they appear on the Contineo portal, along with a unique username. The app validates your credentials against the live portal before saving.

2. **Fetch Data** — Type your username and click **Fetch Data** for cached results, or **Get Live Data** to scrape the latest information from both odd and even semester portals.

3. **Explore** — Switch between semesters using the "Select Semester" dropdown. View attendance insights, CIE marks breakdown, SGPI, and leaderboard rankings.

## Project Structure

```
crce-companion/
├── app.py              # Streamlit dashboard (main entry point)
├── web_scraper.py      # Portal scraping & login logic
├── db_utils.py         # PostgreSQL database operations
├── config.py           # Portal URLs, subject mapping, DB config
├── update_all.py       # Batch update script for all users
├── main.py             # CLI version for quick lookups
├── pyproject.toml      # Project metadata & dependencies (uv)
├── static/             # PWA assets (icons, manifest)
├── uv.lock             # Locked dependency versions
└── .env                 # Environment variables (not committed)
```

## Disclaimer

> **This project is not affiliated with, endorsed by, or connected to CRCE (Fr. Conceicao Rodrigues College of Engineering) or Contineo Technologies in any way.**
>
> This tool was created solely for **educational and personal convenience purposes**. It accesses publicly available student data that the user themselves is authorized to view. No data is shared, sold, or misused.
>
> Use this software responsibly and in compliance with your institution's policies. The developers assume no liability for misuse.

---

<div align="center">

Based on [Mark Lopes' Contineo](https://github.com/MarkLopes11/Contineo) version

</div>
