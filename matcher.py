import json
from thefuzz import fuzz

def load_json(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_account_id(acc):
    """Helper to safely retrieve account ID regardless of key naming."""
    if not isinstance(acc, dict):
        return None
    return acc.get("id") or acc.get("account_id") or acc.get("_id")

def parse_crm_accounts(crm_raw):
    """Normalizes CRM raw data into a standard list of account dictionaries with 'id' fields."""
    accounts = []
    
    if isinstance(crm_raw, list):
        for item in crm_raw:
            if isinstance(item, dict):
                accounts.append(item)
    elif isinstance(crm_raw, dict):
        # Case 1: Dict with a list key like {"accounts": [...]}
        for list_key in ["accounts", "data", "items", "results"]:
            if list_key in crm_raw and isinstance(crm_raw[list_key], list):
                return [item for item in crm_raw[list_key] if isinstance(item, dict)]
        
        # Case 2: Dict keyed by account IDs like {"acc_101": {"name": "Bellhaven"}}
        for k, v in crm_raw.items():
            if isinstance(v, dict):
                if "id" not in v and "account_id" not in v:
                    v["id"] = k
                accounts.append(v)

    return accounts

def run_matching():
    scraped = load_json("scraped_facilities.json")
    crm_raw = load_json("crm_snapshot.json")
    decisions = load_json("decisions.json")
    decided_ids = {d["proposal_id"] for d in decisions}

    crm = parse_crm_accounts(crm_raw)
    scraped = [f for f in scraped if isinstance(f, dict)]

    print(f"Loaded {len(crm)} CRM accounts and {len(scraped)} scraped facilities.")

    # Identify Bellhaven Parent Account
    parent_account = next(
        (a for a in crm if "bellhaven" in a.get("name", "").lower() and not a.get("parent_id")),
        None
    )
    
    parent_id = get_account_id(parent_account)
    if parent_id:
        print(f"Found Bellhaven Parent ID: {parent_id}")
    else:
        print("Warning: Bellhaven parent account not found or has no ID.")

    proposals = []

    for idx, facility in enumerate(scraped):
        facility_name = facility.get("facility_name", "")
        p_id = f"prop_{idx}_{abs(hash(facility_name))}"
        
        if p_id in decided_ids:
            continue

        best_match = None
        highest_score = 0

        for acc in crm:
            acc_name = acc.get("name", "")
            score = fuzz.token_set_ratio(facility_name, acc_name)
            if score > highest_score:
                highest_score = score
                best_match = acc

        if highest_score > 80 and best_match:
            rev = best_match.get("lifetime_revenue", 0) or 0
            ar = best_match.get("outstanding_ar", 0) or 0
            matched_id = get_account_id(best_match)

            # Ensure 'id' key exists in matched_account dict for UI downstream
            best_match["id"] = matched_id

            if best_match.get("parent_id") != parent_id:
                if rev > 0 and ar > 0:
                    # CHOW SOP Trigger
                    proposals.append({
                        "proposal_id": p_id,
                        "action_type": "CHOW_SOP",
                        "scraped_data": facility,
                        "matched_account": best_match,
                        "bellhaven_parent_id": parent_id,
                        "reason": f"CHOW Required: Revenue (${rev}) and AR (${ar}) exist on old account."
                    })
                else:
                    # Direct Re-parent
                    proposals.append({
                        "proposal_id": p_id,
                        "action_type": "REPARENT_DIRECT",
                        "scraped_data": facility,
                        "matched_account": best_match,
                        "bellhaven_parent_id": parent_id,
                        "reason": "No outstanding AR with revenue; safe to direct re-parent."
                    })
        else:
            # New Account Creation
            proposals.append({
                "proposal_id": p_id,
                "action_type": "CREATE_NEW",
                "scraped_data": facility,
                "bellhaven_parent_id": parent_id,
                "reason": "Location not found in CRM."
            })

    with open("proposals.json", "w") as f:
        json.dump(proposals, f, indent=2)
    print(f"Successfully generated {len(proposals)} proposals in proposals.json.")

if __name__ == "__main__":
    run_matching()