# It lets Frontend communicate with Backend
from asyncio import timeout
from pathlib import Path
import requests
from config import BACKEND_URL, REQUEST_TIMEOUT, UPLOAD_ENDPOINT, EMBED_ENDPOINT, ASK_ENDPOINT, EXTRACT_ENTITIES_ENDPOINT


def get_url(endpoint:str) -> str:
    return f"{BACKEND_URL}{endpoint}"

# Check if the backend API is reachable
def check_backend() -> bool:
    """
       Checks whether the backend API is reachable and healthy.

       Returns:
           bool: True if backend is online, otherwise False.
       """


    try:
            response = requests.get(
                get_url("/"),
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code != 200:
                return False
            data = response.json()

            return data.get("status") == "success"
    except requests.RequestException:
            return False

def upload_document(uploaded_file) -> dict:
    """
    Uploads a document to the backend and indexes it.

    Returns:
        dict: {
            "success": bool,
            "data": dict | None,
            "error": str | None
        }
    """
    try:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
            )
        }

        upload_response = requests.post(
            get_url(UPLOAD_ENDPOINT),
            files=files,
            timeout=REQUEST_TIMEOUT
        )

        if upload_response.status_code != 200:
            return {
                "success": False,
                "error": upload_response.json().get(
                    "detail",
                    "Failed to upload document."
                )
            }

        upload_data = upload_response.json()
        file_path = Path(upload_data["path"])

        embed_response = requests.post(
            get_url(EMBED_ENDPOINT),
            json={
                "file_path": str(file_path)
            },
            timeout=REQUEST_TIMEOUT
        )
        # print("Status:", embed_response.status_code)
        # print("Body:", embed_response.text)

        if embed_response.status_code != 200:
            return {
                "success": False,
                "error": embed_response.json().get(
                    "detail",
                    "Failed to index document."
                )
            }

        return {
            "success": True,
            "data": embed_response.json()
        }

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to the backend."
        }
def extract_entities(document_id: str) -> dict:
    try:
        response = requests.post(
            get_url(EXTRACT_ENTITIES_ENDPOINT),
            json={"document_id": document_id},
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": response.json().get(
                    "detail",
                    "Failed to extract entities."
                )
            }

        return {
            "success": True,
            "data": response.json()
        }

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to backend."
        }

def ask_question(
    question: str,
    project_id: str = None,
    parcel_id: str = None,
    survey_number: str = None,
    village: str = None,
    district: str = None,
    response_language: str = None
) -> dict:
    """
    Sends a question to the RAG backend with optional contextual scoping parameters.
    """
    try:
        payload = {
            "query": question,
            "top_k": 10
        }
        if project_id:
            payload["project_id"] = project_id
        if parcel_id:
            payload["parcel_id"] = parcel_id
        if survey_number:
            payload["survey_number"] = survey_number
        if village:
            payload["village"] = village
        if district:
            payload["district"] = district
        if response_language and response_language != "auto":
            payload["response_language"] = response_language

        ask_response = requests.post(
            get_url(ASK_ENDPOINT),
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        if ask_response.status_code != 200:
            return {
                "success": False,
                "error": ask_response.json().get("detail", "Failed to retrieve an answer.")
            }

        return {"success": True, "data": ask_response.json()}

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to the backend."
        }


def get_documents() -> dict:
    try:
        response = requests.get(
            get_url("/documents"),
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": response.json().get(
                    "detail",
                    "Failed to fetch repository."
                )
            }

        return {
            "success": True,
            "data": response.json()
        }

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to backend."
        }

def reset_database() -> dict:
    try:
        response = requests.post(
            get_url("/reset"),
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            return {
                "success": False,
                "error": response.json().get(
                    "detail",
                    "Failed to reset database."
                )
            }

        return {
            "success": True,
            "data": response.json()
        }

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to backend."
        }

def delete_document(document_id: str) -> dict:
    try:
        response = requests.delete(
            get_url(f"/documents/{document_id}"),
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": response.json().get(
                    "detail",
                    "Failed to delete document."
                )
            }

        return {
            "success": True,
            "data": response.json()
        }

    except requests.RequestException:
        return {
            "success": False,
            "error": "Unable to connect to backend."
        }


def get_projects() -> dict:
    try:
        response = requests.get(get_url("/projects"), timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "Failed to fetch projects.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def get_parcels(project_id: str = None, village: str = None) -> dict:
    try:
        params = {}
        if project_id:
            params["project_id"] = project_id
        if village:
            params["village"] = village
        response = requests.get(get_url("/parcels"), params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "Failed to fetch parcels.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def query_analytics(query: str, project_id: str = None) -> dict:
    try:
        payload = {"query": query}
        if project_id:
            payload["project_id"] = project_id
        response = requests.post(get_url("/analytics/query"), json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "Failed to query analytics.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def generate_project_report(project_id: str) -> dict:
    try:
        response = requests.post(get_url("/reports/project"), json={"project_id": project_id}, timeout=REQUEST_TIMEOUT * 2)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "Failed to generate project report.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def transcribe_audio(file_bytes: bytes, filename: str = "audio.wav", language: str = "auto") -> dict:
    try:
        files = {"file": (filename, file_bytes, "audio/wav")}
        data = {"language": language or "auto"}
        response = requests.post(get_url("/voice/transcribe"), files=files, data=data, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "STT transcription failed.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def synthesize_speech(text: str, language: str = "en") -> dict:
    try:
        payload = {"text": text, "language": language}
        response = requests.post(get_url("/voice/synthesize"), json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "TTS synthesis failed.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}


def ask_voice(
    file_bytes: bytes,
    filename: str = "audio.wav",
    language: str = "auto",
    project_id: str = None,
    parcel_id: str = None,
    survey_number: str = None,
    village: str = None,
    district: str = None
) -> dict:
    try:
        audio_mime = "audio/wav"
        audio_filename = filename or "audio.wav"
        if file_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            audio_mime = "audio/webm"
            audio_filename = f"{Path(audio_filename).stem}.webm"
        elif file_bytes.startswith(b"OggS"):
            audio_mime = "audio/ogg"
            audio_filename = f"{Path(audio_filename).stem}.ogg"
        elif len(file_bytes) >= 8 and file_bytes[4:8] == b"ftyp":
            audio_mime = "audio/mp4"
            audio_filename = f"{Path(audio_filename).stem}.m4a"
        elif not file_bytes.startswith(b"RIFF"):
            audio_mime = "application/octet-stream"

        files = {"file": (audio_filename, file_bytes, audio_mime)}
        data = {"language": language or "auto"}
        if project_id:
            data["project_id"] = project_id
        if parcel_id:
            data["parcel_id"] = parcel_id
        if survey_number:
            data["survey_number"] = survey_number
        if village:
            data["village"] = village
        if district:
            data["district"] = district

        response = requests.post(get_url("/voice/ask"), files=files, data=data, timeout=REQUEST_TIMEOUT * 2)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("detail", "Voice query processing failed.")}
        return {"success": True, "data": response.json()}
    except requests.RequestException:
        return {"success": False, "error": "Unable to connect to backend."}






