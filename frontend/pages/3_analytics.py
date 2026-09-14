import streamlit as st
import pandas as pd
from api import query_analytics, get_projects
from components.sidebar import render_sidebar

render_sidebar()

st.title("📊 Land Acquisition Analytics")
st.caption("Authoritative natural-language analytical insights & metrics powered by PostgreSQL.")

# Fetch projects for optional scoping
projects_resp = get_projects()
projects_list = projects_resp.get("data", []) if projects_resp.get("success") else [
    {"project_id": "PRJ-NHAI-2024", "name": "NHAI Expressway Expansion 2024"}
]

col_proj, _ = st.columns([3, 2])
with col_proj:
    proj_options = {"All Projects": "All Projects"}
    for p in projects_list:
        proj_options[p["project_id"]] = f"{p['project_id']} - {p.get('name', 'Project')}"
    
    selected_proj_key = st.selectbox(
        "Scope Analytics by Project (Optional)",
        options=list(proj_options.keys()),
        format_func=lambda k: proj_options[k],
        index=1 if "PRJ-NHAI-2024" in proj_options else 0
    )
    
    selected_project_id = selected_proj_key if selected_proj_key != "All Projects" else None

st.divider()

# Preset Example Questions
st.markdown("##### 💡 Example Analytical Questions")
presets = [
    "How many parcels in this project have compensation pending?",
    "How many parcels are at Award Pending stage?",
    "What is the total awarded compensation for this project?",
    "Show parcels in Vadadala where possession is pending.",
    "Which villages have the most pending compensation cases?",
    "How many parcels have acquisition status Section 19 Notification Issued?"
]

selected_query = None
p_cols = st.columns(2)
for idx, preset in enumerate(presets):
    with p_cols[idx % 2]:
        if st.button(preset, use_container_width=True, key=f"analytics_preset_{idx}"):
            selected_query = preset

# Natural language chat input
typed_query = st.chat_input("Ask an analytical question about parcels, compensation, stages, or villages...")
active_query = typed_query or selected_query

if active_query:
    st.markdown(f"### ❓ Query: *\"{active_query}\"*")
    
    with st.spinner("Processing natural-language analytical request..."):
        res = query_analytics(active_query, project_id=selected_project_id)
        
    if res["success"]:
        data = res["data"]
        is_valid = data.get("is_valid_analytical_query", True)
        summary = data.get("summary_explanation", "")
        source_label = data.get("source", "Authoritative PostgreSQL Database")
        result_obj = data.get("result", {})
        
        # Source Badge
        if "PostgreSQL" in source_label:
            st.success(f"🏛️ **Source:** {source_label}")
        else:
            st.warning(f"🟡 **Source:** {source_label}")

        if not is_valid:
            st.error(f"⚠️ **Request Rejected / Ambiguous:** {summary}")
            if data.get("error_message"):
                st.caption(f"Details: {data.get('error_message')}")
        else:
            st.info(summary)
            
            # Metric Summary Cards
            op = result_obj.get("operation", "N/A")
            agg_val = result_obj.get("aggregate_value")
            row_count = result_obj.get("row_count", 0)
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Operation Intent", op)
            with m2:
                if agg_val is not None:
                    if op in ["SUM", "AVG"]:
                        st.metric("Metric Result", f"₹{agg_val:,.2f}")
                    else:
                        st.metric("Metric Result", f"{int(agg_val):,}")
                else:
                    st.metric("Total Rows", row_count)
            with m3:
                st.metric("Target Entity", result_obj.get("target_entity", "parcels"))

            # Applied Filters Display
            applied_filters = result_obj.get("applied_filters", {})
            if applied_filters:
                st.markdown("**Applied Scoping Filters:**")
                filter_tags = " &nbsp;|&nbsp; ".join([f"`{k}` = **{v}**" for k, v in applied_filters.items()])
                st.markdown(filter_tags)

            # Data Table View (if rows exist)
            rows = result_obj.get("rows", [])
            if rows and len(rows) > 0:
                st.markdown("#### 📋 Detailed Data Results")
                df = pd.DataFrame(rows)
                
                # Format currency columns if present
                if "total_award_amount" in df.columns:
                    df["total_award_amount"] = df["total_award_amount"].apply(
                        lambda x: f"₹{x:,.2f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                    )
                if "sum" in df.columns:
                    df["sum"] = df["sum"].apply(
                        lambda x: f"₹{x:,.2f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                    )
                    
                st.dataframe(df, use_container_width=True)
                
    else:
        st.error(f"❌ Error querying analytics service: {res.get('error', 'Unknown backend error.')}")
