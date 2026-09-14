# Frontend & GIS Integration Handoff Specification
## Phase 8 Unified AI Integration Layer

---

## 1. Overview & Architectural Guarantees

This document serves as the formal API contract and integration specification for Web application and GIS frontend developers interfacing with the Land Knowledge Intelligence backend.

### Key Architectural Rules
1. **Authoritative Structured Data**: PostgreSQL is the single source of truth for numerical aggregates, parcel metadata, compensation calculations, and project statistics.
2. **Deterministic Retrieval & Aggregation**: All counting, grouping, filtering, and conflict identification are computed deterministically prior to presentation.
3. **No Unbounded Semantic Search**: Parcel and project intelligence endpoints utilize strictly scoped SQL lookups and metadata-filtered vector searches.
4. **Abstract Anomaly Interface**: Anomaly detection uses a decoupled provider boundary (`BaseAnomalyProvider`). If the anomaly detection engine fails, the API gracefully returns `anomaly_service_status: "unavailable"` without causing HTTP 500 errors.
5. **No Delay Predictions**: Endpoints provide current-state factual attention categories (`DATA_CONFLICT`, `ANOMALY_DETECTED`, `COMPENSATION_PENDING`, etc.). Predictive delay percentages, predicted delay days, and future risk models are strictly excluded.
6. **Explicit Report Triggers**: `report_available: true` in project intelligence signals availability; it does NOT automatically trigger report generation.

---

## 2. Global Base URL & Configuration

```
Base URL: http://localhost:8000
Content-Type: application/json
```

---

## 3. Endpoints Specification

### 3.1 Parcel Intelligence Endpoint

Retrieves aggregated facts, scoped document evidence, conflicts, anomalies, and current-state attention flags for a single parcel.

- **HTTP Method**: `GET`
- **Path**: `/parcels/{parcel_id}/intelligence`
- **Path Parameter**: `parcel_id` (string, e.g., `PCL-VADADALA-142-3A` or `142/3A`)

#### Example Request
```http
GET /parcels/PCL-VADADALA-142-3A/intelligence HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Example Response (`200 OK`)
```json
{
  "parcel_id": "PCL-VADADALA-142-3A",
  "survey_number": "142/3A",
  "village": "Vadadala",
  "district": "Vadodara",
  "state": "Gujarat",
  "project_id": "PRJ-NHAI-2024",
  "area_hectares": 0.45,
  "land_category": "Agricultural",
  "acquisition_status": "Section 3C Objections Received",
  "total_award_amount": 1250000.0,
  "payment_status": "Calculated",
  "landowner": "Ramesh Patel",
  "evidence_count": 2,
  "evidence_summary": [
    {
      "document_id": "doc-7a8b9c",
      "file_name": "Vadadala_Land_Schedule.pdf",
      "page_number": 1,
      "excerpt": "Survey 142/3A area listed as 0.5200 Ha in schedule draft..."
    }
  ],
  "conflicts": [
    {
      "conflict_id": "cnf-101",
      "field_name": "area_hectares",
      "db_value": "0.45",
      "doc_value": "0.52",
      "document_id": "doc-7a8b9c",
      "file_name": "Vadadala_Land_Schedule.pdf",
      "severity": "high",
      "description": "Area discrepancy between 7/12 record (0.45 Ha) and document schedule (0.52 Ha)."
    }
  ],
  "anomalies": [
    {
      "parcel_id": "PCL-VADADALA-142-3A",
      "project_id": "PRJ-NHAI-2024",
      "anomaly_type": "Area Discrepancy",
      "severity": "high",
      "field": "area_hectares",
      "expected_value": "0.4500 Ha",
      "observed_value": "0.5200 Ha",
      "source": "Land Area Validation Model",
      "confidence": 0.92,
      "status": "open"
    }
  ],
  "anomaly_service_status": "online",
  "attention_categories": [
    "DATA_CONFLICT",
    "ANOMALY_DETECTED",
    "COMPENSATION_PENDING",
    "POSSESSION_PENDING",
    "VERIFICATION_REQUIRED"
  ],
  "source": "Authoritative PostgreSQL Database + Grounded RAG Documents"
}
```

---

### 3.2 Project Intelligence Endpoint

Retrieves aggregated project metrics, stage distributions, conflict counts, anomaly counts, and current-state attention categories.

- **HTTP Method**: `GET`
- **Path**: `/projects/{project_id}/intelligence`
- **Path Parameter**: `project_id` (string, e.g., `PRJ-NHAI-2024`)

#### Example Request
```http
GET /projects/PRJ-NHAI-2024/intelligence HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Example Response (`200 OK`)
```json
{
  "project_id": "PRJ-NHAI-2024",
  "project_name": "PRJ-NHAI-2024 - Land Acquisition Project",
  "state": "Gujarat",
  "district": "Vadodara",
  "total_parcels": 4,
  "total_area_hectares": 1.77,
  "total_awarded_compensation": 4650000.0,
  "acquisition_stage_counts": {
    "Section 3A Notification": 1,
    "Section 3C Objections": 1,
    "Section 3D Declaration": 1,
    "Possession Taken": 1
  },
  "payment_status_counts": {
    "Paid": 1,
    "Calculated": 1,
    "Pending": 2
  },
  "village_counts": {
    "Vadadala": 4
  },
  "evidence_count": 3,
  "conflict_count": 1,
  "anomaly_count": 1,
  "anomaly_service_status": "online",
  "report_available": true,
  "attention_categories": [
    "DATA_CONFLICT",
    "ANOMALY_DETECTED",
    "COMPENSATION_PENDING",
    "VERIFICATION_REQUIRED"
  ],
  "source": "Authoritative PostgreSQL Database + Grounded RAG Documents"
}
```

---

### 3.3 Existing Core Endpoints (Preserved Contracts)

#### Grounded RAG (`/ask`)
- **Method**: `POST`
- **Path**: `/ask`
- **Request Payload**:
  ```json
  {
    "question": "What is the compensation awarded for Survey 142/3A?",
    "project_id": "PRJ-NHAI-2024",
    "language": "hi"
  }
  ```

#### Natural-Language Analytics (`/analytics/query`)
- **Method**: `POST`
- **Path**: `/analytics/query`
- **Request Payload**:
  ```json
  {
    "query": "Show total compensation by village",
    "project_id": "PRJ-NHAI-2024"
  }
  ```

#### AI MIS Project Report (`/reports/project`)
- **Method**: `POST`
- **Path**: `/reports/project`
- **Request Payload**:
  ```json
  {
    "project_id": "PRJ-NHAI-2024"
  }
  ```

---

## 4. Grounded Evidence Coverage Semantics

When displaying report or retrieval summaries on the frontend UI:
- **`COMPLETE`**: Required evidence and authoritative DB metrics are fully present.
- **`PARTIAL`**: DB metrics exist, but secondary document evidence is incomplete.
- **`INSUFFICIENT`**: Critical DB metrics or primary notifications are missing.

Missing data fields are explicitly returned as `null` or `"Unknown"` and MUST NOT be interpolated or assumed.

---

## 5. Attention Flags & Conflict Indicators

Frontend UI components should render distinct visual indicators based on the `attention_categories` array:
- 🔴 **`DATA_CONFLICT`**: Mismatch between 7/12 record and gazette notification.
- ⚠️ **`ANOMALY_DETECTED`**: Flagged by rules engine or anomaly model.
- 🟡 **`COMPENSATION_PENDING`**: Award calculated but disbursement pending.
- 🔵 **`POSSESSION_PENDING`**: Section 3D declared; physical possession awaiting clearance.
- 📄 **`DOCUMENT_MISSING`**: No verified PDF evidence linked to parcel.
- 🔍 **`VERIFICATION_REQUIRED`**: Verification action needed prior to approval.

---

## 6. Multilingual Options (`language` Parameter)

The `/ask` endpoint accepts an optional `language` parameter:
- `"en"` (Default: English)
- `"hi"` (Hindi - standard land terminology e.g., 'मुआवजा', 'अधिग्रहण', 'खसरा')
- `"mr"` (Marathi - standard land terminology e.g., 'भूसंपादन', 'मोबदला', 'सातबारा')

---

## 7. Fault Tolerance & Service Status Handling

If the external Anomaly Detection Service is down or experiencing network degradation:
- The response returns HTTP `200 OK`.
- `anomaly_service_status` is set to `"unavailable"`.
- `anomalies` array is empty `[]`.
- All authoritative PostgreSQL facts, retrieval evidence, and conflict summaries continue to function without interruption.
