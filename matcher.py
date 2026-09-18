import json
from thefuzz import fuzz

def load_json(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_account_id(acc):
    if not isinstance(acc, dict):
        return None
    return acc.get("id") or acc.get("account_id") or acc.get("_id")

def parse_crm_accounts(crm_raw):
    accounts = []
    if isinstance(crm_raw, list):
        for item in crm_raw:
            if isinstance(item, dict):
                accounts.append(item)
    elif isinstance(crm_raw, dict):
        for list_key in ["accounts", "data", "items", "results"]:
            if list_key in crm_raw and isinstance(crm_raw[list_key], list):
                return [item for item in crm_raw[list_key] if isinstance(item, dict)]
        for k, v in crm_raw.items():
            if isinstance(v, dict):
                if "id" not in v:
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

    parent_account = next(
        (a for a in crm if "bellhaven" in a.get("name", "").lower() and not a.get("parent_id")),
        None
    )
    parent_id = get_account_id(parent_account)

    proposals = []
    matched_crm_ids = set()

    # 1. Match Scraped Locations to CRM Accounts
    for idx, facility in enumerate(scraped):
        facility_name = facility.get("facility_name", "")
        p_id = f"prop_{idx}_{facility_name.lower().replace(' ', '_')}"
        
        if p_id in decided_ids:
            continue

        # Rank all CRM matches
        matches = []
        for acc in crm:
            acc_name = acc.get("name", "")
            score = fuzz.token_set_ratio(facility_name, acc_name)
            if score > 80:
                matches.append((score, acc))

        matches.sort(key=lambda x: x[0], reverse=True)

        if matches:
            best_match = matches[0][1]
            matched_id = get_account_id(best_match)
            best_match["id"] = matched_id
            matched_crm_ids.add(matched_id)

            # Handle Duplicate CRM entries if multiple match
            if len(matches) > 1:
                for _, dup_acc in matches[1:]:
                    dup_id = get_account_id(dup_acc)
                    matched_crm_ids.add(dup_id)
                    proposals.append({
                        "proposal_id": f"dup_{dup_id}",
                        "action_type": "MARK_DUPLICATE",
                        "matched_account": dup_acc,
                        "surviving_account_id": matched_id,
                        "reason": f"Duplicate of primary account {matched_id}."
                    })

            rev = best_match.get("lifetime_revenue", 0) or 0
            ar = best_match.get("outstanding_ar", 0) or 0

            if best_match.get("parent_id") != parent_id:
                if rev > 0 and ar > 0:
                    proposals.append({
                        "proposal_id": p_id,
                        "action_type": "CHOW_SOP",
                        "scraped_data": facility,
                        "matched_account": best_match,
                        "bellhaven_parent_id": parent_id,
                        "reason": f"CHOW Required: Rev (${rev}) & AR (${ar}) exist."
                    })
                else:
                    proposals.append({
                        "proposal_id": p_id,
                        "action_type": "REPARENT_DIRECT",
                        "scraped_data": facility,
                        "matched_account": best_match,
                        "bellhaven_parent_id": parent_id,
                        "reason": "Safe to re-parent directly (No outstanding AR)."
                    })
        else:
            proposals.append({
                "proposal_id": p_id,
                "action_type": "CREATE_NEW",
                "scraped_data": facility,
                "bellhaven_parent_id": parent_id,
                "reason": "New location not found in CRM."
            })

    # 2. Detect Orphan CRM Accounts (Under Bellhaven parent but missing from website)
    for acc in crm:
        acc_id = get_account_id(acc)
        if acc.get("parent_id") == parent_id and acc_id not in matched_crm_ids:
            orphan_pid = f"orphan_{acc_id}"
            if orphan_pid not in decided_ids:
                proposals.append({
                    "proposal_id": orphan_pid,
                    "action_type": "ORPHAN_NEEDS_REVIEW",
                    "matched_account": acc,
                    "reason": "Account currently listed under Bellhaven but missing from public website."
                })

    with open("proposals.json", "w") as f:
        json.dump(proposals, f, indent=2)
    print(f"Generated {len(proposals)} proposals in proposals.json.")

if __name__ == "__main__":
    run_matching()