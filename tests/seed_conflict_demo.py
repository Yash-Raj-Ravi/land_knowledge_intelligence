"""
Seed Dedicated Conflict Demo Document into ChromaDB Collection.
Creates an explicit conflict document chunk for Survey 142/3A:
- Document ID: p2-doc-conflict-001
- File Name: Surveyor_Field_Inspection_Report.pdf
- Page: 4
- Text: Physical measurement on site for Survey 142/3A indicates area of 0.52 hectare instead of 0.45 hectare recorded in revenue records.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.vectorstore.chroma_store import ChromaStore
from backend.embedding.embedding_model import EmbeddingModel

logging.basicConfig(level=logging.INFO)

def seed_conflict_chunk():
    store = ChromaStore()
    embedding_model = EmbeddingModel()

    doc_id = "p2-doc-conflict-001"
    file_name = "Surveyor_Field_Inspection_Report.pdf"
    survey_number = "142/3A"
    page_number = 4
    text = "Physical measurement on site for Survey 142/3A indicates area of 0.52 hectare instead of 0.45 hectare recorded in revenue records."

    chunk_id_str = f"{doc_id}_{page_number}"
    vector = embedding_model.embed_texts([text])[0]

    meta_dict = {
        "document_id": doc_id,
        "source_file": file_name,
        "document_category": "Survey / Inspection Report",
        "page_number": page_number,
        "chunk_id": 4,
        "chunk_type": "prose",
        "section_heading": "Field Extent Verification",
        "raw_survey_number": survey_number,
        "normalized_survey_number": survey_number,
        "survey_number": survey_number,
        "survey_numbers_str": survey_number,
        "language": "English",
        "file_path": f"uploads/{file_name}",
        "project_id": "PRJ-NHAI-2024",
        "village": "Vadadala",
        "district": "Vadodara",
        "tehsil": "Savli",
        "state": "Gujarat",
        "acquisition_stage": "Inspection",
        "document_date": "2024-02-01",
        "authority": "SLAO Surveyor Team"
    }

    try:
        # Upsert into ChromaDB
        store.collection.upsert(
            ids=[chunk_id_str],
            documents=[text],
            embeddings=[vector],
            metadatas=[meta_dict]
        )
        print(f"Successfully seeded conflict chunk '{chunk_id_str}' for Survey 142/3A into ChromaDB!")
    except Exception as e:
        print(f"Error seeding conflict chunk: {e}")

if __name__ == "__main__":
    seed_conflict_chunk()
