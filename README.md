# Bellhaven Senior Living - CRM Ownership Synchronization

## Architectural Summary
This system automates ownership reconciliation between Bellhaven's web directory and our CRM sandbox.

### 1. Web Scraper (`scraper.py`)
Parses active locations, addresses, and offerings from the public site using BeautifulSoup.

### 2. Matching Engine & CHOW SOP (`matcher.py`)
Compares scraped web locations against existing CRM records using fuzzy name matching (`thefuzz`).

- **CHOW SOP Compliance:** Before moving an account to the Bellhaven parent, the pipeline checks `lifetime_revenue` and `outstanding_ar`. 
  - If `lifetime_revenue > 0` **AND** `outstanding_ar > 0`, the existing account remains intact to preserve billing history. A new account is created under Bellhaven, and `chow_current_account` on the old account is updated to reference the new ID.
  - If `lifetime_revenue == 0` **OR** `outstanding_ar == 0`, the existing account is directly re-parented to Bellhaven.
- **Duplicates & Orphans:** Inactive duplicate accounts are marked with `status = "Inactive"` and linked via `duplicate_of_account`. CRM accounts missing from the website are marked `status = "Needs Review"`.

### 3. Human Review Application (`app.py`)
A Streamlit dashboard displays side-by-side evidence comparing scraped data against CRM records. No write operations occur without manual approval. Decisions are recorded in `decisions.json` to ensure safe, idempotent re-runs.

### 4. Scheduled Execution (`.github/workflows/daily_sync.yml`)
Configured to execute daily at midnight UTC via GitHub Actions.