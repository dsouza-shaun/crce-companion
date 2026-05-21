"""
Standalone database migration/setup script.

Run this manually for:
  - Initial setup of a new database
  - Local development environment setup
  - Disaster recovery / re-creating tables

Usage:
    python migrate.py
"""

import db_utils

db_utils.create_db_and_table_pg()
db_utils.create_feedback_table_pg()

print("Database migration/setup completed.")
