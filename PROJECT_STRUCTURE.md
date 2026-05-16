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
    ├── PROJECT_STRUCTURE.md
    ├── pyproject.toml          # Project metadata & dependencies (uv)
    ├── README.md
    ├── uv.lock                 # Locked dependency versions
    └── web_scraper.py          # Portal scraping & login logic
```