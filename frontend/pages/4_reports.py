import streamlit as st
from api import generate_project_report, get_projects
from components.sidebar import render_sidebar
from datetime import datetime

render_sidebar()

st.title("📑 AI MIS & Project Report Generation")
st.caption("Generate grounded, multi-section Land Acquisition MIS status reports synthesizing PostgreSQL facts and document evidence.")

# Fetch projects
projects_resp = get_projects()
projects_list = projects_resp.get("data", []) if projects_resp.get("success") else [
    {"project_id": "PRJ-NHAI-2024", "name": "NHAI Expressway Expansion 2024"}
]

col_proj, col_btn = st.columns([3, 2])

with col_proj:
    proj_options = {p["project_id"]: f"{p['project_id']} - {p.get('name', 'Project')}" for p in projects_list}
    proj_keys = list(proj_options.keys())
    default_idx = proj_keys.index("PRJ-NHAI-2024") if "PRJ-NHAI-2024" in proj_keys else 0
    
    selected_project_id = st.selectbox(
        "Select Project for Report Generation",
        options=proj_keys,
        format_func=lambda k: proj_options[k],
        index=default_idx,
        key="report_project_id"
    )

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    generate_clicked = st.button("🚀 Generate Project Report", type="primary", use_container_width=True)

st.divider()

if "current_report" not in st.session_state:
    st.session_state.current_report = None

if generate_clicked:
    with st.spinner(f"Generating authoritative MIS report for project {selected_project_id}..."):
        res = generate_project_report(selected_project_id)
        if res["success"]:
            st.session_state.current_report = res["data"]
        else:
            st.error(f"❌ Failed to generate report: {res.get('error', 'Unknown backend error')}")

report_data = st.session_state.current_report

if report_data and report_data.get("project_id") == selected_project_id:
    # Title & Metadata
    title = report_data.get("report_title", "Project Report")
    generated_at = report_data.get("generated_at", "")
    coverage = report_data.get("evidence_coverage", "INSUFFICIENT")
    metrics = report_data.get("structured_metrics", {})
    markdown_content = report_data.get("markdown_content", "")
    
    # Download Button Top Right
    d_col1, d_col2 = st.columns([4, 1])
    with d_col1:
        st.subheader(title)
        st.caption(f"Generated at: `{generated_at}` &nbsp;|&nbsp; Source: `Authoritative PostgreSQL Database + Grounded RAG Documents`")
    with d_col2:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            "📥 Export (.md)",
            data=markdown_content,
            file_name=f"MIS_Report_{selected_project_id}_{timestamp_str}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # Coverage Badge
    if coverage == "COMPLETE":
        st.success("🟢 Evidence Coverage: COMPLETE")
    elif coverage == "PARTIAL":
        st.warning("🟡 Evidence Coverage: PARTIAL")
    else:
        st.warning("🟠 Evidence Coverage: INSUFFICIENT — Document evidence limited.")

    # Executive Summary Card
    st.markdown("### 📌 Executive Summary")
    st.info(report_data.get("executive_summary", "Summary not available."))

    # KPI Metric Grid
    st.markdown("### 📊 Key Project Statistics")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Parcels", metrics.get("total_parcels", 0))
    with k2:
        st.metric("Total Area", f"{metrics.get('total_area_hectares', 0.0):.4f} Ha")
    with k3:
        tot_comp = metrics.get("total_awarded_compensation", 0.0)
        st.metric("Total Awarded", f"₹{tot_comp:,.2f}")
    with k4:
        stage_map = metrics.get("acquisition_stage_breakdown", {})
        top_stage = max(stage_map, key=stage_map.get) if stage_map else "N/A"
        st.metric("Primary Stage", top_stage)

    st.divider()

    # Detailed Sections Tabs
    st.markdown("### 📑 Detailed MIS Report Sections")
    sections = report_data.get("sections", [])
    
    if sections:
        tab_titles = [sec["section_title"] for sec in sections]
        tabs = st.tabs(tab_titles)
        for idx, tab in enumerate(tabs):
            with tab:
                st.markdown(f"### {sections[idx]['section_title']}")
                st.markdown(sections[idx]["content"])

    # Document Citations Card
    citations = report_data.get("citations", [])
    if citations:
        st.divider()
        st.markdown("### 📚 Supporting Document Citations")
        for cit in citations:
            with st.container(border=True):
                st.markdown(f"📌 **[Source: {cit.get('file_name', 'Doc')}, Page {cit.get('page_number', 1)}]** (`{cit.get('document_id')}`)")
                if cit.get("excerpt"):
                    st.caption(f"\"{cit.get('excerpt')}\"")

    # Conflicts Card
    conflicts = report_data.get("conflicts", [])
    if conflicts:
        st.divider()
        st.error("### ⚠️ Data Quality & Detected Discrepancies")
        for conf in conflicts:
            with st.container(border=True):
                st.markdown(
                    f"**{conf.get('conflict_type')}** for `{conf.get('field_name')}`:\n"
                    f"- 🏛️ **Database Fact:** `{conf.get('authoritative_value')}`\n"
                    f"- 📄 **Document Evidence:** `{conf.get('document_value')}` (Source: `{conf.get('file_name')}`, p.{conf.get('page_number')})"
                )

elif not report_data:
    st.info("👋 Select a project above and click **'🚀 Generate Project Report'** to build an authoritative MIS status report.")
