import json
import streamlit as st
import crm_client

st.set_page_config(layout="wide")
st.title("CRM Reconciliation Dashboard")

def load_data(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_decision(decision):
    decisions = load_data("decisions.json")
    decisions.append(decision)
    with open("decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)

proposals = load_data("proposals.json")
decisions = load_data("decisions.json")
decided_ids = {d["proposal_id"] for d in decisions}

pending = [p for p in proposals if p["proposal_id"] not in decided_ids]

st.sidebar.metric("Pending Proposals", len(pending))

if not pending:
    st.success("All proposals reviewed! Your CRM is fully up to date.")
else:
    prop = pending[0]
    st.subheader(f"Proposed Action: {prop['action_type']}")
    st.info(f"Reason: {prop['reason']}")

    col1, col2 = st.columns(2)
    with col1:
        st.write("### Website Evidence")
        st.json(prop.get("scraped_data", {}))
    with col2:
        st.write("### CRM Record")
        st.json(prop.get("matched_account", {}))

    c1, c2 = st.columns(2)
    if c1.button("Approve & Update CRM", type="primary"):
        action = prop["action_type"]
        scraped = prop.get("scraped_data", {})
        p_id = prop.get("bellhaven_parent_id")

        if action == "CREATE_NEW":
            crm_client.create_account({
                "name": scraped.get("facility_name", ""),
                "address": scraped.get("address", ""),
                "parent_id": p_id,
                "status": "Active"
            })
        elif action == "REPARENT_DIRECT":
            acc_id = prop["matched_account"].get("id") or prop["matched_account"].get("account_id")
            crm_client.update_account(acc_id, {
                "parent_id": p_id,
                "status": "Active"
            })
        elif action == "CHOW_SOP":
            old_acc_id = prop["matched_account"].get("id") or prop["matched_account"].get("account_id")
            new_acc = crm_client.create_account({
                "name": scraped.get("facility_name", ""),
                "address": scraped.get("address", ""),
                "parent_id": p_id,
                "status": "Active"
            })
            new_acc_id = new_acc.get("id") or new_acc.get("account_id")
            crm_client.update_account(old_acc_id, {
                "chow_current_account": new_acc_id
            })
        elif action == "MARK_DUPLICATE":
            acc_id = prop["matched_account"].get("id") or prop["matched_account"].get("account_id")
            crm_client.update_account(acc_id, {
                "status": "Inactive",
                "duplicate_of_account": prop["surviving_account_id"]
            })
        elif action == "ORPHAN_NEEDS_REVIEW":
            acc_id = prop["matched_account"].get("id") or prop["matched_account"].get("account_id")
            crm_client.update_account(acc_id, {
                "status": "Needs Review"
            })

        save_decision({"proposal_id": prop["proposal_id"], "status": "APPROVED"})
        st.rerun()

    if c2.button("Reject Proposal"):
        save_decision({"proposal_id": prop["proposal_id"], "status": "REJECTED"})
        st.rerun()