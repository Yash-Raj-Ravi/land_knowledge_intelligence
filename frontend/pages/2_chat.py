import streamlit as st
import base64
from api import ask_question, get_documents, get_projects, get_parcels, ask_voice
from components.sidebar import render_sidebar
from pathlib import Path
import time
from datetime import datetime
from utils.chat_export import generate_chat_markdown


render_sidebar()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Title & Export Button
col_header, col_export = st.columns([5, 1])
with col_header:
    st.title("🗺️ Land Acquisition Copilot")
    st.caption("Contextual AI assistant for Land Acquisition Projects, Parcels & Survey Records.")

with col_export:
    if st.session_state.messages:
        markdown = generate_chat_markdown(st.session_state.messages)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            "📥 Export",
            markdown,
            file_name=f"land_copilot_chat_{timestamp}.md",
            mime="text/markdown"
        )

# Mode & Language Selector
st.markdown("---")
col_m1, col_m2 = st.columns([3, 2])
with col_m1:
    copilot_mode = st.radio(
        "Select Copilot Mode",
        ["📌 Contextual Parcel Copilot", "🌐 General Land Acquisition Copilot"],
        horizontal=True,
        key="copilot_mode"
    )
with col_m2:
    lang_map = {
        "auto": "Auto (Query Language)",
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "mr": "Marathi (मराठी)"
    }
    selected_lang_code = st.selectbox(
        "Response Language",
        options=list(lang_map.keys()),
        format_func=lambda k: lang_map[k],
        index=0,
        key="selected_response_lang"
    )


# Fetch Available Projects & Parcels
projects_resp = get_projects()
projects_list = projects_resp.get("data", []) if projects_resp.get("success") else [
    {"project_id": "PRJ-NHAI-2024", "name": "NHAI Expressway Expansion 2024", "state": "Gujarat", "district": "Vadodara"}
]

selected_project_id = None
selected_parcel = None

if copilot_mode == "📌 Contextual Parcel Copilot":
    st.subheader("📍 Parcel / Survey Context Explorer")
    
    col_proj, col_vil, col_pcl = st.columns([2, 2, 3])
    
    with col_proj:
        proj_options = {p["project_id"]: f"{p['project_id']} - {p.get('name', 'Project')}" for p in projects_list}
        proj_keys = list(proj_options.keys())
        default_proj_idx = proj_keys.index("PRJ-NHAI-2024") if "PRJ-NHAI-2024" in proj_keys else 0
        selected_project_id = st.selectbox(
            "Select Project",
            options=proj_keys,
            format_func=lambda k: proj_options[k],
            index=default_proj_idx,
            key="selected_project_id"
        )
    
    parcels_resp = get_parcels(project_id=selected_project_id)
    parcels_list = parcels_resp.get("data", []) if parcels_resp.get("success") else [
        {
            "parcel_id": "PCL-VADADALA-142-3A",
            "survey_number": "142/3A",
            "village": "Vadadala",
            "district": "Vadodara",
            "state": "Gujarat",
            "area_hectares": 0.4500,
            "land_category": "Agricultural",
            "acquisition_status": "Section 19 Notification Issued / Award Pending",
            "total_award_amount": 2450000.00,
            "payment_status": "Calculated",
            "landowner": "Ramesh Patel & Family",
            "project_id": "PRJ-NHAI-2024"
        }
    ]

    # Extract unique villages for optional filtering
    villages = sorted(list({p.get("village") for p in parcels_list if p.get("village")}))
    village_options = ["All Villages"] + villages
    
    with col_vil:
        selected_village_filter = st.selectbox(
            "Filter Village",
            options=village_options,
            index=0,
            key="selected_village_filter"
        )
    
    # Filter parcels by village if selected
    if selected_village_filter != "All Villages":
        filtered_parcels = [p for p in parcels_list if p.get("village") == selected_village_filter]
    else:
        filtered_parcels = parcels_list
        
    if not filtered_parcels and parcels_list:
        filtered_parcels = parcels_list

    with col_pcl:
        pcl_options = {
            i: f"Survey {p.get('survey_number', 'N/A')} ({p.get('village', 'Village')}) - ID: {p.get('parcel_id', 'N/A')}"
            for i, p in enumerate(filtered_parcels)
        }
        # Find 142/3A index as default
        default_pcl_idx = 0
        for i, p in enumerate(filtered_parcels):
            if p.get("survey_number") == "142/3A":
                default_pcl_idx = i
                break
                
        selected_pcl_idx = st.selectbox(
            "Select Parcel / Survey Number",
            options=list(pcl_options.keys()),
            format_func=lambda k: pcl_options[k],
            index=default_pcl_idx if pcl_options else 0,
            key="selected_pcl_idx"
        )
        if filtered_parcels:
            selected_parcel = filtered_parcels[selected_pcl_idx]

    # Render Parcel Summary Card
    if selected_parcel:
        st.markdown("### 📋 Selected Parcel Summary")
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Survey Number", selected_parcel.get("survey_number", "N/A"))
                st.metric("Parcel ID", selected_parcel.get("parcel_id", "N/A"))
            with m2:
                st.metric("Village", selected_parcel.get("village", "N/A"))
                st.metric("District / State", f"{selected_parcel.get('district', 'N/A')}, {selected_parcel.get('state', 'N/A')}")
            with m3:
                area_val = selected_parcel.get("area_hectares")
                area_str = f"{area_val:.4f} Ha" if area_val is not None else "N/A"
                st.metric("Area", area_str)
                st.metric("Land Category", selected_parcel.get("land_category", "Agricultural"))
            with m4:
                award_val = selected_parcel.get("total_award_amount")
                award_str = f"₹{award_val:,.2f}" if award_val is not None else "Pending / N/A"
                st.metric("Award / Compensation", award_str)
                st.metric("Landowner", selected_parcel.get("landowner", "N/A"))
            
            st.info(f"**Acquisition Status:** {selected_parcel.get('acquisition_status', 'N/A')} &nbsp;|&nbsp; **Payment Status:** {selected_parcel.get('payment_status', 'Pending')}")

else:
    st.info("🌐 **General Land Acquisition Copilot Mode**: Ask queries across the entire knowledge base or scoped by Project ID without selecting a specific parcel.")
    col_g1, col_g2 = st.columns([2, 2])
    with col_g1:
        proj_options = {"All Projects": "All Projects"}
        for p in projects_list:
            proj_options[p["project_id"]] = f"{p['project_id']} - {p.get('name', 'Project')}"
        sel_g_proj = st.selectbox("Scope by Project (Optional)", options=list(proj_options.keys()), format_func=lambda k: proj_options[k])
        if sel_g_proj != "All Projects":
            selected_project_id = sel_g_proj

st.divider()

# Suggested Questions / Presets
preset_question = None
if copilot_mode == "📌 Contextual Parcel Copilot" and selected_parcel:
    st.markdown("##### 💡 Ask AI about this parcel")
    p_cols = st.columns(3)
    preset_list = [
        "What is pending for this parcel?",
        "What compensation was awarded?",
        "What does the award say about possession?",
        "Are there any conflicting records?",
        "Summarize all documents for this parcel."
    ]
    for idx, preset in enumerate(preset_list):
        with p_cols[idx % 3]:
            if st.button(preset, use_container_width=True, key=f"ctx_preset_{idx}"):
                preset_question = preset
else:
    st.markdown("##### 💡 General Copilot Presets")
    g_cols = st.columns(2)
    g_presets = [
        "What documents are available for Project PRJ-NHAI-2024?",
        "What is the status of Survey 142/3A?",
        "Summarize all land acquisition notifications.",
        "List all parcels with awards above ₹2,000,000."
    ]
    for idx, preset in enumerate(g_presets):
        with g_cols[idx % 2]:
            if st.button(preset, use_container_width=True, key=f"gen_preset_{idx}"):
                preset_question = preset

# Render Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("is_voice") and message["role"] == "assistant":
            st.markdown("### 🎙️ Transcript")
            st.markdown(message.get("transcript", ""))
            st.markdown("### 🤖 Grounded Answer")
        st.markdown(message["content"])

        if message.get("is_voice") and message["role"] == "assistant":
            audio_b64 = message.get("audio_base64")
            if message.get("audio_available") and audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    st.markdown("### 🔊 Voice Response")
                    st.audio(audio_bytes, format="audio/wav")
                except Exception:
                    st.info("Voice output unavailable")
            else:
                st.info("Voice output unavailable")
        
        if message["role"] == "assistant":
            # 1. Coverage Badge
            coverage = message.get("evidence_coverage")
            if coverage:
                if coverage == "COMPLETE":
                    st.success("🟢 Evidence Coverage: COMPLETE")
                elif coverage == "PARTIAL":
                    st.warning("🟡 Evidence Coverage: PARTIAL")
                else:
                    st.warning("🟠 Evidence Coverage: INSUFFICIENT — Response may lack supporting document evidence.")
            
            # 2. Conflicts Alert Card
            conflicts = message.get("conflicts", [])
            if conflicts:
                with st.container(border=True):
                    st.error("⚠️ **CONFLICT DETECTED BETWEEN DATABASE FACT AND DOCUMENT EVIDENCE**")
                    for conf in conflicts:
                        field_name = conf.get("field_name", "field")
                        auth_val = conf.get("authoritative_value", "N/A")
                        doc_val = conf.get("document_value", "N/A")
                        doc_file = conf.get("file_name", "document.pdf")
                        pg_num = conf.get("page_number", 1)
                        c_type = conf.get("conflict_type", "Discrepancy")
                        st.markdown(
                            f"- **{c_type}** for `{field_name}`:\n"
                            f"  - 🏛️ **Database Fact:** `{auth_val}`\n"
                            f"  - 📄 **Document Evidence:** `{doc_val}` (Source: `{doc_file}`, p.{pg_num})"
                        )
            
            # 3. Citations
            citations = message.get("citations", [])
            if citations:
                st.markdown("##### 📚 Source Citations")
                for cit in citations:
                    st.caption(f"📌 `[Source: {cit.get('file_name', 'Doc')}, p.{cit.get('page_number', 1)}]`")

# Multilingual Native Voice Copilot Component (Sarvam AI)
with st.expander("🎙️ Ask by Voice", expanded=False):
    st.caption("Record voice using your microphone or upload an audio file (English, Hindi, Marathi <= 30s).")

    col_mic, col_file = st.tabs(["🎤 Microphone Recording", "📁 Audio File Upload"])

    audio_value = None
    audio_filename = "recorded_voice.wav"

    with col_mic:
        recorded_audio = st.audio_input("Record your voice question", key="mic_audio_input")
        if recorded_audio is not None:
            audio_value = recorded_audio.getvalue()
            audio_filename = recorded_audio.name or "recorded_voice.webm"

    with col_file:
        uploaded_voice = st.file_uploader("Upload Voice Recording", type=["wav", "mp3", "m4a", "ogg", "webm"], key="voice_file_uploader")
        if uploaded_voice is not None:
            audio_value = uploaded_voice.getvalue()
            audio_filename = uploaded_voice.name

    if audio_value is not None:
        if st.button("🗣️ Process Voice Query", key="btn_process_voice", use_container_width=True):
            v_kwargs = {
                "file_bytes": audio_value,
                "filename": audio_filename,
                "language": selected_lang_code
            }
            if copilot_mode == "📌 Contextual Parcel Copilot" and selected_parcel:
                v_kwargs["project_id"] = selected_parcel.get("project_id") or selected_project_id
                v_kwargs["parcel_id"] = selected_parcel.get("parcel_id")
                v_kwargs["survey_number"] = selected_parcel.get("survey_number")
                v_kwargs["village"] = selected_parcel.get("village")
                v_kwargs["district"] = selected_parcel.get("district")
            elif selected_project_id:
                v_kwargs["project_id"] = selected_project_id

            with st.spinner("Processing voice query via Sarvam STT -> Grounded RAG -> Sarvam TTS..."):
                v_res = ask_voice(**v_kwargs)

            if v_res["success"]:
                v_data = v_res["data"]
                user_transcript = f"🎙️ **[Voice Input]**: {v_data.get('transcript', '')}"
                st.session_state.messages.append({"role": "user", "content": user_transcript})

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": v_data.get("answer", ""),
                    "is_voice": True,
                    "transcript": v_data.get("transcript", ""),
                    "language": v_data.get("language", selected_lang_code),
                    "evidence_coverage": v_data.get("evidence_coverage", "INSUFFICIENT"),
                    "conflicts": v_data.get("conflicts", []),
                    "citations": v_data.get("citations", []),
                    "audio_base64": v_data.get("audio_base64"),
                    "audio_available": v_data.get("audio_available", False)
                })
                st.rerun()
            else:
                st.error(f"❌ Voice Error: {v_res.get('error', 'Voice processing failed.')}")


# Chat Input & Form Handling
user_typed = st.chat_input("Ask a question about land acquisition, parcels, awards, or documents...")

question_to_ask = user_typed or preset_question

if question_to_ask:
    st.session_state.messages.append({"role": "user", "content": question_to_ask})
    with st.chat_message("user"):
        st.markdown(question_to_ask)

    # Prepare backend request parameters
    kwargs = {"question": question_to_ask}
    if selected_lang_code and selected_lang_code != "auto":
        kwargs["response_language"] = selected_lang_code

    if copilot_mode == "📌 Contextual Parcel Copilot" and selected_parcel:
        kwargs["project_id"] = selected_parcel.get("project_id") or selected_project_id
        kwargs["parcel_id"] = selected_parcel.get("parcel_id")
        kwargs["survey_number"] = selected_parcel.get("survey_number")
        kwargs["village"] = selected_parcel.get("village")
        kwargs["district"] = selected_parcel.get("district")
    elif selected_project_id:
        kwargs["project_id"] = selected_project_id

    with st.spinner("Retrieving evidence & generating contextual response..."):
        res = ask_question(**kwargs)

    if res["success"]:
        resp_data = res["data"]
        answer_text = resp_data.get("answer", "")
        coverage = resp_data.get("evidence_coverage", "INSUFFICIENT")
        conflicts = resp_data.get("conflicts", [])
        citations = resp_data.get("citations", [])

        with st.chat_message("assistant"):
            st.markdown(answer_text)
            
            if coverage == "COMPLETE":
                st.success("🟢 Evidence Coverage: COMPLETE")
            elif coverage == "PARTIAL":
                st.warning("🟡 Evidence Coverage: PARTIAL")
            else:
                st.warning("🟠 Evidence Coverage: INSUFFICIENT — Insufficient evidence retrieved from document store to answer with complete certainty.")
                
            if conflicts:
                with st.container(border=True):
                    st.error("⚠️ **CONFLICT DETECTED BETWEEN DATABASE FACT AND DOCUMENT EVIDENCE**")
                    for conf in conflicts:
                        field_name = conf.get("field_name", "field")
                        auth_val = conf.get("authoritative_value", "N/A")
                        doc_val = conf.get("document_value", "N/A")
                        doc_file = conf.get("file_name", "document.pdf")
                        pg_num = conf.get("page_number", 1)
                        c_type = conf.get("conflict_type", "Discrepancy")
                        st.markdown(
                            f"- **{c_type}** for `{field_name}`:\n"
                            f"  - 🏛️ **Database Fact:** `{auth_val}`\n"
                            f"  - 📄 **Document Evidence:** `{doc_val}` (Source: `{doc_file}`, p.{pg_num})"
                        )
            
            if citations:
                st.markdown("##### 📚 Source Citations")
                for cit in citations:
                    st.caption(f"📌 `[Source: {cit.get('file_name', 'Doc')}, p.{cit.get('page_number', 1)}]`")

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_text,
            "evidence_coverage": coverage,
            "conflicts": conflicts,
            "citations": citations
        })
    else:
        err_msg = f"❌ Error: {res.get('error', 'Unknown error occurred.')}"
        with st.chat_message("assistant"):
            st.error(err_msg)
        st.session_state.messages.append({"role": "assistant", "content": err_msg})
    
    st.rerun()
