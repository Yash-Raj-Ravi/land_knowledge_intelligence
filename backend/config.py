from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"

ALLOWED_TYPES = {"application/pdf",

                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX

                 "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX

                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX

                 "text/plain",

                 "text/csv",

                 "image/png",

                 "image/jpeg"
                 }
# Chunking 
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Embedding Configuration
EMBEDDING_MODEL = "mxbai-embed-large:latest"
OLLAMA_BASE_URL = "http://localhost:11434"

# Vector database
CHROMA_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "land_acquisition_documents"

# LLM
LLM_MODEL = "llama3.1:8b"

# OCR
TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

MAX_CHUNKS_PER_DOCUMENT = 3

OCR_SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
}

EMBEDDING_BATCH_SIZE = 16

# Structure-Aware Chunking Defaults
CHUNK_TARGET_MIN = 800
CHUNK_TARGET_MAX = 1200
MAX_TABLE_ROWS_PER_CHUNK = 10

# PostgreSQL Configuration
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "land_acquisition_db"
PG_USER = "postgres"
PG_PASSWORD = "postgres_password"

# Land Acquisition Document Categories
DOCUMENT_CATEGORIES = [
    "Land Record / Revenue Record",
    "Acquisition Notification",
    "Award",
    "Compensation Record",
    "R&R Record",
    "Possession Record",
    "Government Order / Approval",
    "Survey / Inspection Report",
    "Legal / Dispute Document"
]