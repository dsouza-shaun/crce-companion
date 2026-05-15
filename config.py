import os

NEON_DB_PASSWORD = os.environ.get("NEON_DB_PASSWORD")

if NEON_DB_PASSWORD is None:
    import sys
    sys.exit("Database password not configured. Exiting.")

# Construct the connection string using the password
PG_HOST = os.environ.get("NEON_DB_URI")
PG_DBNAME = os.environ.get("PG_DBNAME", "neondb")
PG_USER = os.environ.get("PG_USER", "neondb_owner")

NEON_CONNECTION_STRING = f"postgresql://{PG_USER}:{NEON_DB_PASSWORD}@{PG_HOST}/{PG_DBNAME}?sslmode=require"


# Portal Configuration
LOGIN_URL_EVEN = "https://crce-students.contineo.in/parents/index.php?option=com_studentdashboard&controller=studentdashboard&task=dashboard"
LOGIN_URL_ODD = "https://crce-students.contineo.in/parentsodd/index.php?option=com_studentdashboard&controller=studentdashboard&task=dashboard"

# Default (kept for backward compatibility)
LOGIN_URL = LOGIN_URL_EVEN
FORM_ACTION_URL = LOGIN_URL


def get_login_url(semester_type="even"):
    """Returns the appropriate login URL based on semester type ('odd' or 'even')."""
    if semester_type == "odd":
        return LOGIN_URL_ODD
    return LOGIN_URL_EVEN

# --- Form Field Names ---
PRN_FIELD_NAME = "username"
DAY_FIELD_NAME = "dd"
MONTH_FIELD_NAME = "mm"
YEAR_FIELD_NAME = "yyyy"
PASSWORD_FIELD_NAME = "passwd"

# --- Subject Code Mapping ---
SUBJECT_CODE_TO_NAME_MAP = {
    # Semester 1
    "25BSC11CE01" : "MATRICES AND DIFFERENTIAL CALCULUS",
    "25BSC11CE04" : "ENGINEERING CHEMISTRY",
    "25ESC11CE03": "PROGRAMMING FUNDAMENTALS",
    "25PCC11CE03": "DIGITAL ELECTRONICS",
    "25PCC11CE01": "INNOVATION AND DESIGN THINKING",
    "25PCC11CE04": "ESSENTIAL PSYCHOMOTOR SKILLS FOR ENGINEERS",
    "25PCC11CE02": "ESSENTIAL COMPUTING SKILLS FOR ENGINEERS",
    "25IKS11CE01": "INDIAN KNOWLEDGE SYSTEM",

    # Semester 2
    "25BSC11CE03" : "INTEGRAL CALCULUS AND PROBABILITY THEORY",
    "25ESC11CE04" : "HUMAN HEALTH SYSTEMS",
    "25ESC11CE02": "BASIC ELECTRICAL AND ELECTRONICS ENGINEERING",
    "25VSE11CE02": "CREATIVE CODING IN PYTHON",
    "25BSC11CE02": "ENGINEERING PHYSICS",
    "25ESC11CE01": "ENGINEERING GRAPHICS",
    "25VSE11CE01": "MEASURING INSTRUMENTS AND TESTING TOOLS",
    "25AEC11CE01": "ART OF COMMUNICATION"
}

SUBJECT_CODE_TO_CREDITS_MAP = {
    # Semester 1
    "25BSC11CE01" : 3,
    "25BSC11CE04" : 3,
    "25ESC11CE03": 4,
    "25PCC11CE03": 3,
    "25PCC11CE01": 1,
    "25PCC11CE04": 2,
    "25PCC11CE02": 2,
    "25IKS11CE01": 2,

    # Semester 2
    "25BSC11CE03" : 3,
    "25ESC11CE04" : 1,
    "25ESC11CE02": 4,
    "25VSE11CE02": 2,
    "25BSC11CE02": 3,
    "25ESC11CE01": 3,
    "25VSE11CE01": 2,
    "25AEC11CE01": 2
}

MAX_MARKS_CONFIG = {
    # A. DEFAULTS (Applied if no specific subject rule exists)
    "DEFAULT": {
        "MSE": 30,
        "TH-ISE1": 20,
        "TH-ISE2": 20,
        "ESE": 30,
        "PR-ISE1": 20,
        "PR-ISE2": 30,
    },

    # B. SUBJECT SPECIFIC OVERRIDES
    # Format: "SUBJECT_CODE": { "EXAM_NAME": MAX_MARKS }
    
    # "CSL701": {         # Example: Machine Learning Lab
    #     "PR-ISE1": 10,  # <--- HERE: You specify this is out of 10
    #     "PR-ISE2": 10   # <--- HERE: You specify this is out of 10
    # }

    # INTEGRAL CALCULUS AND PROBABILITY THEORY
    "25BSC11CE03": {
        "MSE": 30,
        "TH-ISE1": 20,
        "TH-ISE2": 20,
        "ESE": 30,
        "TU-ISE1": 20,
        "TU-ISE2": 30,
    },

    # HUMAN HEALTH SYSTEMS
    "25ESC11CE04": {
        "TH-ISE1": 20,
        "TH-ISE2": 30
    },

    # CREATIVE CODING IN PYTHON
    "25VSE11CE02": {
        "PR-ISE1": 50,
        "PR-ISE2": 50
    },

    # MEASURING INSTRUMENTS AND TESTING TOOLS
    "25VSE11CE01": {
        "PR-ISE1": 50,
        "PR-ISE2": 50
    },
}

def get_max_marks(subject_code, exam_type):
    """
    Returns the max marks for a specific subject and exam.
    Prioritizes specific subject rules, falls back to defaults.
    """
    # 1. Check if there are special rules for this Subject Code
    if subject_code in MAX_MARKS_CONFIG:
        if exam_type in MAX_MARKS_CONFIG[subject_code]:
            return MAX_MARKS_CONFIG[subject_code][exam_type]

    # 2. Fallback to Default values
    return MAX_MARKS_CONFIG["DEFAULT"].get(exam_type, 20)