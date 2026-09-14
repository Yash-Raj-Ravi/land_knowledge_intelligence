import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.anomaly_service import AnomalyService, FailingAnomalyProvider, LocalAnomalyProvider
from backend.services.attention_service import AttentionService
from backend.services.intelligence_service import IntelligenceService
from backend.core import dependencies

class TestIntegrationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Reset default dependencies before each test
        dependencies._anomaly_service = AnomalyService(LocalAnomalyProvider())
        dependencies._attention_service = AttentionService()
        dependencies._intelligence_service = IntelligenceService(
            db_service=dependencies._db_service,
            retrieval_service=dependencies._retrieval_service,
            conflict_detector=dependencies._conflict_detector,
            anomaly_service=dependencies._anomaly_service,
            attention_service=dependencies._attention_service
        )

    def test_01_parcel_intelligence_contract(self):
        """1. GET /parcels/{parcel_id}/intelligence returns valid structure and facts."""
        response = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("parcel_id", data)
        self.assertIn("survey_number", data)
        self.assertIn("village", data)
        self.assertIn("acquisition_status", data)
        self.assertIn("evidence_summary", data)
        self.assertIn("conflicts", data)
        self.assertIn("anomalies", data)
        self.assertIn("attention_categories", data)
        self.assertEqual(data["anomaly_service_status"], "online")

    def test_02_project_intelligence_contract(self):
        """2. GET /projects/{project_id}/intelligence returns aggregates and counts."""
        response = self.client.get("/projects/PRJ-NHAI-2024/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project_id"], "PRJ-NHAI-2024")
        self.assertIn("total_parcels", data)
        self.assertIn("total_area_hectares", data)
        self.assertIn("acquisition_stage_counts", data)
        self.assertIn("payment_status_counts", data)
        self.assertTrue(data["report_available"])

    def test_03_anomaly_integration(self):
        """3. Anomaly Integration: Verify anomaly payload structure when provider returns anomalies."""
        response = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        anomalies = data.get("anomalies", [])
        self.assertGreaterEqual(len(anomalies), 1)
        first = anomalies[0]
        self.assertIn("anomaly_type", first)
        self.assertIn("severity", first)
        self.assertIn("confidence", first)

    def test_04_fault_tolerance(self):
        """4. Fault Tolerance: Simulate anomaly service failure, ensure HTTP 200 returned with status 'unavailable'."""
        failing_service = AnomalyService(FailingAnomalyProvider())
        dependencies._anomaly_service = failing_service
        dependencies._intelligence_service = IntelligenceService(
            db_service=dependencies._db_service,
            retrieval_service=dependencies._retrieval_service,
            conflict_detector=dependencies._conflict_detector,
            anomaly_service=failing_service,
            attention_service=dependencies._attention_service
        )

        response = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["anomaly_service_status"], "unavailable")
        self.assertEqual(data["anomalies"], [])
        self.assertIsNotNone(data["parcel_id"])

    def test_05_existing_ask_contract(self):
        """5. Existing /ask Contract: Ensure /ask contract is preserved and returns grounded answer."""
        payload = {
            "query": "What is the status of Section 3A notification?",
            "project_id": "PRJ-NHAI-2024"
        }
        response = self.client.post("/ask", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("citations", data)

    def test_06_existing_analytics_query_contract(self):
        """6. Existing /analytics/query Contract: Ensure /analytics/query returns structured response."""
        payload = {
            "query": "Show total compensation by village",
            "project_id": "PRJ-NHAI-2024"
        }
        response = self.client.post("/analytics/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("summary_explanation", data)
        self.assertIn("result", data)

    def test_07_existing_reports_project_contract(self):
        """7. Existing /reports/project Contract: Ensure /reports/project returns project report."""
        payload = {
            "project_id": "PRJ-NHAI-2024"
        }
        response = self.client.post("/reports/project", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project_id"], "PRJ-NHAI-2024")
        self.assertIn("markdown_content", data)
        self.assertIn("evidence_coverage", data)

    def test_08_multilingual_options(self):
        """8. Multilingual Options: Test /ask with response_language='hi' and response_language='mr'."""
        for lang in ["hi", "mr"]:
            payload = {
                "query": "What is the compensation status?",
                "project_id": "PRJ-NHAI-2024",
                "response_language": lang
            }
            response = self.client.post("/ask", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("answer", data)


    def test_09_conflict_detection_preservation(self):
        """9. Conflict Detection Preservation: Ensure conflict detector identifies data conflicts."""
        response = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("conflicts", data)

    def test_10_scoped_retrieval(self):
        """10. Scoped Retrieval: Verify retrieval filters by parcel_id / project_id."""
        response = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("evidence_summary", data)

    def test_11_no_predictive_delay_contract(self):
        """11. No Predictive Delay Contract: Verify no predictive delay fields exist in responses."""
        res_parcel = self.client.get("/parcels/PCL-VADADALA-142-3A/intelligence").json()
        res_project = self.client.get("/projects/PRJ-NHAI-2024/intelligence").json()

        forbidden_keys = ["delay_probability", "predicted_delay_days", "future_delay_risk", "predicted_delay"]
        for key in forbidden_keys:
            self.assertNotIn(key, res_parcel, f"Forbidden key '{key}' found in parcel intelligence!")
            self.assertNotIn(key, res_project, f"Forbidden key '{key}' found in project intelligence!")

    def test_12_safety_handling_nonexistent_parcel(self):
        """12. Safety Handling: Non-existent parcel lookup returns safe fallback structure instead of crashing."""
        response = self.client.get("/parcels/PCL-NONEXISTENT-999-99/intelligence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["parcel_id"], "PCL-NONEXISTENT-999-99")
        self.assertIn("attention_categories", data)
        self.assertEqual(data["anomaly_service_status"], "online")


if __name__ == "__main__":
    unittest.main()
