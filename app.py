import json
import streamlit as st
import crm_client

st.set_page_config(layout="wide")
st.title("CRM Reconciliation Review Dashboard")

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
    st.success("All proposals reviewed and processed!")
else:
    prop = pending[0]
    st.subheader(f"Proposal Type: {prop['action_type']}")
    st.info(f"Reasoning: {prop['reason']}")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Website Evidence")
        st.json(prop["scraped_data"])

    with col2:
        st.write("### Current CRM Record")
        st.json(prop.get("matched_account", {}))

    btn_approve, btn_reject = st.columns(2)

    if btn_approve.button("Approve & Write to CRM", type="primary"):
        action = prop["action_type"]
        scraped = prop["scraped_data"]
        p_id = prop["bellhaven_parent_id"]

        if action == "CREATE_NEW":
            crm_client.create_account({
                "name": scraped["facility_name"],
                "address": scraped["address"],
                "parent_id": p_id,
                "status": "Active"
            })
        elif action == "REPARENT_DIRECT":
            acc_id = prop["matched_account"]["id"]
            crm_client.update_account(acc_id, {
                "parent_id": p_id,
                "name": scraped["facility_name"],
                "status": "Active"
            })
        elif action == "CHOW_SOP":
            old_acc_id = prop["matched_account"]["id"]
            new_acc = crm_client.create_account({
                "name": scraped["facility_name"],
                "address": scraped["address"],
                "parent_id": p_id,
                "status": "Active"
            })
            crm_client.update_account(old_acc_id, {
                "chow_current_account": new_acc["id"]
            })

        save_decision({"proposal_id": prop["proposal_id"], "status": "APPROVED"})
        st.experimental_rerun()

    if btn_reject.button("Reject Proposal"):
        save_decision({"proposal_id": prop["proposal_id"], "status": "REJECTED"})
        st.experimental_rerun()