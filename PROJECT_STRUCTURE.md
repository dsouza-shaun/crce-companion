```
└── 📁crce-companion
    └── 📁.streamlit
        ├── config.toml
    └── 📁static                # PWA assets (icons, manifest)
        ├── contineo.png
        ├── manifest.json
    ├── .env                    # Environment variables
    ├── .gitignore
    ├── app.py                  # Streamlit dashboard (main entry point)
    ├── config.py               # Portal URLs, subject mapping, DB config
    ├── db_utils.py             # PostgreSQL database operations
    ├── LICENSE
    ├── main.py                 # CLI version for quick lookups
    ├── PROJECT_STRUCTURE.md
    ├── pyproject.toml          # Project metadata & dependencies (uv)
    ├── README.md
    ├── update_all.py           # Batch update script for all users
    ├── uv.lock                 # Locked dependency versions
    ├── web_scraper.py          # Portal scraping & login logic
    └── ws.py
```