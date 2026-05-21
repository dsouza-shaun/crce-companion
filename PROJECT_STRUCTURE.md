```
└── 📁crce-companion
    └── 📁.streamlit
        └── config.toml
    └── 📁assets
        ├── logo.png
        ├── mockup-1.png
        ├── mockup-2.png
        └── mockup-3.png
    └── 📁static                # PWA assets (icons, manifest)
        ├── contineo.png
        └── manifest.json
    ├── .env                    # Environment variables
    ├── .gitignore
    ├── app.py                  # Streamlit dashboard (main entry point)
    ├── batch_update.py         # Batch update script
    ├── config.py               # Portal URLs, subject mapping, DB config
    ├── db_utils.py             # PostgreSQL database operations
    ├── LICENSE
    ├── PROJECT_STRUCTURE.md
    ├── pyproject.toml          # Project metadata & dependencies (uv)
    ├── README.md
    ├── uv.lock                 # Locked dependency versions
    └── web_scraper.py          # Portal scraping & login logic
```