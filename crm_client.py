import requests

API_BASE = "https://analyst-assessment-production.up.railway.app/api/v1"
TOKEN = "bh_lCSyghnRNXlOjPrHHEM--A"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def get_all_accounts():
    res = requests.get(f"{API_BASE}/accounts", headers=HEADERS)
    res.raise_for_status()
    return res.json()

def create_account(account_data):
    res = requests.post(f"{API_BASE}/accounts", headers=HEADERS, json=account_data)
    res.raise_for_status()
    return res.json()

def update_account(account_id, update_data):
    res = requests.patch(f"{API_BASE}/accounts/{account_id}", headers=HEADERS, json=update_data)
    res.raise_for_status()
    return res.json()

def fetch_and_save_snapshot():
    accounts = get_all_accounts()
    import json
    with open("crm_snapshot.json", "w") as f:
        json.dump(accounts, f, indent=2)
    print(f"Fetched {len(accounts)} accounts from CRM.")
    return accounts

if __name__ == "__main__":
    fetch_and_save_snapshot()