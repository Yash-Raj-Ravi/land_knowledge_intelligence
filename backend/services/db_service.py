import logging
import uuid
from typing import Optional, Dict, Any, List
from backend.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
from backend.models.land_metadata import LandDocumentMetadata

logger = logging.getLogger(__name__)

# DDL Schema Statements for Live PostgreSQL DB
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS villages (
    village_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    tehsil VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_village_tehsil_district UNIQUE (name, tehsil, district)
);

CREATE TABLE IF NOT EXISTS parcels (
    parcel_id VARCHAR(64) PRIMARY KEY,
    village_id VARCHAR(64) REFERENCES villages(village_id) ON DELETE CASCADE,
    survey_number VARCHAR(100) NOT NULL,
    area_hectares NUMERIC(12, 4),
    land_category VARCHAR(100),
    acquisition_status VARCHAR(100) DEFAULT 'Pending Notification',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_parcel_village_survey UNIQUE (village_id, survey_number)
);

CREATE TABLE IF NOT EXISTS landowners (
    landowner_id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    share_percentage NUMERIC(5, 2) DEFAULT 100.00,
    contact_info VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS acquisition_cases (
    case_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE CASCADE,
    parcel_id VARCHAR(64) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    case_number VARCHAR(100) NOT NULL,
    current_stage VARCHAR(100) NOT NULL,
    slao_authority VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compensation_awards (
    award_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) REFERENCES acquisition_cases(case_id) ON DELETE CASCADE,
    parcel_id VARCHAR(64) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    base_land_rate_per_acre NUMERIC(14, 2),
    base_compensation NUMERIC(14, 2),
    solatium_amount NUMERIC(14, 2),
    interest_amount NUMERIC(14, 2),
    total_award_amount NUMERIC(14, 2) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'Pending',
    disbursement_date DATE,
    award_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(64) PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE,
    project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    document_category VARCHAR(100) NOT NULL,
    acquisition_stage VARCHAR(100),
    document_date DATE,
    authority VARCHAR(255),
    language VARCHAR(50) DEFAULT 'English',
    total_pages INT DEFAULT 1,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_parcels (
    document_id VARCHAR(64) REFERENCES documents(document_id) ON DELETE CASCADE,
    parcel_id VARCHAR(64) REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    page_number INT DEFAULT 1,
    PRIMARY KEY (document_id, parcel_id, page_number)
);
"""

class DatabaseService:
    def __init__(self):
        self.conn = None
        self.in_memory_parcels: Dict[tuple, Dict[str, Any]] = {}
        self._seed_default_demo_parcels()
        self._initialize_db()

    def _seed_default_demo_parcels(self):
        default_142_3a = {
            "parcel_id": "PCL-VADADALA-142-3A",
            "survey_number": "142/3A",
            "area_hectares": 0.4500,
            "land_category": "Agricultural",
            "acquisition_status": "Section 19 Notification Issued / Award Pending",
            "village": "Vadadala",
            "tehsil": "Savli",
            "district": "Vadodara",
            "state": "Gujarat",
            "total_award_amount": 2450000.00,
            "payment_status": "Calculated",
            "landowner": "Ramesh Patel & Family",
            "project_id": "PRJ-NHAI-2024"
        }
        self.in_memory_parcels[("vadadala", "142/3a")] = default_142_3a
        self.in_memory_parcels[("", "142/3a")] = default_142_3a


    def get_connection(self):
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                dbname=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD
            )
            conn.autocommit = True
            return conn
        except Exception as e:
            return None

    def _initialize_db(self):
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLES_SQL)
                logger.info("PostgreSQL Schema initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL schema: {e}")
            finally:
                conn.close()

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT document_id, file_name, file_path FROM documents WHERE file_hash = %s;", (file_hash,))
                row = cur.fetchone()
                if row:
                    return {"document_id": row[0], "file_name": row[1], "file_path": row[2]}
        except Exception as e:
            logger.error(f"Error checking file hash: {e}")
        finally:
            conn.close()
        return None

    def persist_document_metadata(self, meta: LandDocumentMetadata, file_path: str, file_hash: Optional[str] = None):
        conn = self.get_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                if meta.project_id:
                    cur.execute(
                        """
                        INSERT INTO projects (project_id, name, state, district)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (project_id) DO NOTHING;
                        """,
                        (meta.project_id, meta.project_id, meta.state or "Unknown", meta.district or "Unknown")
                    )

                cur.execute(
                    """
                    INSERT INTO documents (
                        document_id, file_hash, project_id, file_name, file_path,
                        document_category, acquisition_stage, authority, language, total_pages
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id) DO UPDATE SET
                        file_hash = EXCLUDED.file_hash,
                        document_category = EXCLUDED.document_category,
                        acquisition_stage = EXCLUDED.acquisition_stage,
                        authority = EXCLUDED.authority;
                    """,
                    (
                        meta.document_id, file_hash, meta.project_id, meta.source_file, file_path,
                        meta.document_category, meta.acquisition_stage, meta.authority,
                        meta.language, meta.total_pages
                    )
                )
            logger.info(f"Persisted document {meta.document_id} to PostgreSQL.")
        except Exception as e:
            logger.error(f"Error persisting document metadata to PostgreSQL: {e}")
        finally:
            conn.close()

    def persist_structured_parcels(
        self,
        meta: LandDocumentMetadata,
        structured_parcels: List[Dict[str, Any]],
        file_path: str
    ):
        village_name = meta.village or "Default Village"
        district_name = meta.district or "Default District"
        tehsil_name = meta.tehsil or "Default Tehsil"
        state_name = meta.state or "Default State"
        proj_id = meta.project_id or "PRJ-DEFAULT"

        village_id = f"VIL-{district_name}-{tehsil_name}-{village_name}".upper().replace(" ", "_")

        # Always update in-memory store
        for sp in structured_parcels:
            s_num = sp.get("survey_number")
            if not s_num:
                continue

            parcel_id = f"PCL-{village_id}-{s_num}".upper().replace("/", "-").replace(" ", "_")
            area_ha = sp.get("area_hectares")
            land_cat = sp.get("land_category") or "Agricultural"
            comp_amt = sp.get("compensation_amount")
            owner_name = sp.get("landowner")

            record = {
                "parcel_id": parcel_id,
                "survey_number": s_num,
                "area_hectares": float(area_ha) if area_ha is not None else None,
                "land_category": land_cat,
                "acquisition_status": meta.acquisition_stage or "Section 19 Declaration",
                "village": village_name,
                "tehsil": tehsil_name,
                "district": district_name,
                "state": state_name,
                "total_award_amount": float(comp_amt) if comp_amt is not None else None,
                "payment_status": "Awarded" if comp_amt is not None else "Pending",
                "landowner": owner_name
            }
            self.in_memory_parcels[(village_name.lower(), s_num.lower())] = record
            self.in_memory_parcels[("", s_num.lower())] = record

        conn = self.get_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO villages (village_id, project_id, name, tehsil, district, state)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name, tehsil, district) DO UPDATE SET name = EXCLUDED.name;
                    """,
                    (village_id, proj_id, village_name, tehsil_name, district_name, state_name)
                )

                for sp in structured_parcels:
                    s_num = sp.get("survey_number")
                    if not s_num:
                        continue

                    parcel_id = f"PCL-{village_id}-{s_num}".upper().replace("/", "-").replace(" ", "_")
                    area_ha = sp.get("area_hectares")
                    land_cat = sp.get("land_category") or "Agricultural"
                    page_num = sp.get("page_number", 1)

                    # 1. Insert/Update Parcel
                    cur.execute(
                        """
                        INSERT INTO parcels (parcel_id, village_id, survey_number, area_hectares, land_category, acquisition_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (village_id, survey_number) DO UPDATE SET
                            area_hectares = COALESCE(EXCLUDED.area_hectares, parcels.area_hectares),
                            land_category = COALESCE(EXCLUDED.land_category, parcels.land_category);
                        """,
                        (parcel_id, village_id, s_num, area_ha, land_cat, meta.acquisition_stage or "Section 19 Declaration")
                    )

                    # 2. Insert Landowner if provided
                    owner_name = sp.get("landowner")
                    if owner_name:
                        owner_id = f"OWN-{parcel_id}-{uuid.uuid4().hex[:6]}".upper()
                        cur.execute(
                            """
                            INSERT INTO landowners (landowner_id, parcel_id, name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING;
                            """,
                            (owner_id, parcel_id, owner_name)
                        )

                    # 3. Insert Acquisition Case & Compensation Award if amount provided
                    comp_amt = sp.get("compensation_amount")
                    if comp_amt:
                        case_id = f"CASE-{parcel_id}".upper()
                        cur.execute(
                            """
                            INSERT INTO acquisition_cases (case_id, project_id, parcel_id, case_number, current_stage, slao_authority)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (case_id) DO NOTHING;
                            """,
                            (case_id, proj_id, parcel_id, f"LA-{s_num}", meta.acquisition_stage or "Awarded", meta.authority or "SLAO")
                        )

                        award_id = f"AWD-{parcel_id}".upper()
                        cur.execute(
                            """
                            INSERT INTO compensation_awards (award_id, case_id, parcel_id, total_award_amount, payment_status)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (award_id) DO UPDATE SET
                                total_award_amount = EXCLUDED.total_award_amount;
                            """,
                            (award_id, case_id, parcel_id, comp_amt, "Awarded")
                        )

                    # 4. Link Document to Parcel + Page Number
                    cur.execute(
                        """
                        INSERT INTO document_parcels (document_id, parcel_id, page_number)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (meta.document_id, parcel_id, page_num)
                    )

            logger.info(f"Persisted {len(structured_parcels)} structured parcels for doc {meta.document_id} to PostgreSQL.")
        except Exception as e:
            logger.error(f"Error persisting structured parcels to PostgreSQL: {e}")
        finally:
            conn.close()

    def get_authoritative_parcel_data(self, village: str, survey_number: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT p.parcel_id, p.survey_number, p.area_hectares, p.land_category, p.acquisition_status,
                               v.name as village_name, v.tehsil, v.district, v.state,
                               ca.total_award_amount, ca.payment_status
                        FROM parcels p
                        JOIN villages v ON p.village_id = v.village_id
                        LEFT JOIN acquisition_cases ac ON ac.parcel_id = p.parcel_id
                        LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                        WHERE (LOWER(v.name) = LOWER(%s) OR %s = '') AND LOWER(p.survey_number) = LOWER(%s);
                        """,
                        (village, village or "", survey_number)
                    )
                    row = cur.fetchone()
                    if row:
                        return {
                            "parcel_id": row[0],
                            "survey_number": row[1],
                            "area_hectares": float(row[2]) if row[2] is not None else None,
                            "land_category": row[3],
                            "acquisition_status": row[4],
                            "village": row[5],
                            "tehsil": row[6],
                            "district": row[7],
                            "state": row[8],
                            "total_award_amount": float(row[9]) if row[9] is not None else None,
                            "payment_status": row[10]
                        }
            except Exception as e:
                logger.error(f"Error fetching authoritative parcel data: {e}")
            finally:
                conn.close()

        # In-memory fallback
        v_key = village.lower() if village else ""
        s_key = survey_number.lower() if survey_number else ""
        
        if (v_key, s_key) in self.in_memory_parcels:
            return self.in_memory_parcels[(v_key, s_key)]
        
        if ("", s_key) in self.in_memory_parcels:
            return self.in_memory_parcels[("", s_key)]

        for (v, s), parcel in self.in_memory_parcels.items():
            if s == s_key:
                return parcel

        return None

    def get_authoritative_project_parcels(self, project_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        records = []
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT p.parcel_id, p.survey_number, p.area_hectares, p.land_category, p.acquisition_status,
                               v.name as village_name, v.tehsil, v.district, v.state,
                               ca.total_award_amount, ca.payment_status
                        FROM parcels p
                        JOIN villages v ON p.village_id = v.village_id
                        LEFT JOIN acquisition_cases ac ON ac.parcel_id = p.parcel_id
                        LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                        WHERE UPPER(v.project_id) = UPPER(%s);
                        """,
                        (project_id,)
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        records.append({
                            "parcel_id": row[0],
                            "survey_number": row[1],
                            "area_hectares": float(row[2]) if row[2] is not None else None,
                            "land_category": row[3],
                            "acquisition_status": row[4],
                            "village": row[5],
                            "tehsil": row[6],
                            "district": row[7],
                            "state": row[8],
                            "total_award_amount": float(row[9]) if row[9] is not None else None,
                            "payment_status": row[10]
                        })
            except Exception as e:
                logger.error(f"Error fetching project parcels data: {e}")
            finally:
                conn.close()

        # In-memory fallback
        if not records:
            p_key = project_id.upper()
            for parcel in self.in_memory_parcels.values():
                if parcel.get("project_id", "").upper() == p_key or p_key in parcel.get("parcel_id", "").upper():
                    if parcel not in records:
                        records.append(parcel)

        return records

