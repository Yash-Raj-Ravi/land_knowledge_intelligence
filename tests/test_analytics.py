import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.analytics import AnalyticsResponse
from backend.core.dependencies import get_analytics_service
from backend.analytics.query_parser import AnalyticsQueryParser


class TestAnalyticsModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analytics_service = get_analytics_service()
        cls.query_parser = AnalyticsQueryParser()

    def test_1_count_parcels(self):
        """1. COUNT parcels"""
        res = self.analytics_service.process_query("How many parcels are in the project?", project_id="PRJ-NHAI-2024")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.operation, "COUNT")
        self.assertTrue(res.result.aggregate_value >= 0)

    def test_2_count_pending_compensation(self):
        """2. COUNT pending compensation"""
        res = self.analytics_service.process_query("How many parcels have compensation pending?", project_id="PRJ-NHAI-2024")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.operation, "COUNT")
        self.assertIn("payment_status", res.result.applied_filters)

    def test_3_sum_compensation(self):
        """3. SUM compensation"""
        res = self.analytics_service.process_query("What is the total awarded compensation for this project?", project_id="PRJ-NHAI-2024")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.operation, "SUM")
        self.assertIsNotNone(res.result.aggregate_value)

    def test_4_group_by_village(self):
        """4. GROUP BY village"""
        res = self.analytics_service.process_query("Which villages have the most pending compensation cases?", project_id="PRJ-NHAI-2024")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.operation, "GROUP_BY")
        self.assertEqual(res.result.group_by_field, "village")

    def test_5_filter_by_project(self):
        """5. FILTER by project"""
        res = self.analytics_service.process_query("How many parcels in PRJ-NHAI-2024 exist?")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.applied_filters.get("project_id"), "PRJ-NHAI-2024")

    def test_6_filter_by_acquisition_status(self):
        """6. FILTER by acquisition status"""
        res = self.analytics_service.process_query("How many parcels have acquisition status Section 19 Notification Issued?")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.applied_filters.get("acquisition_status"), "Section 19 Notification Issued")

    def test_7_no_matching_records(self):
        """7. No matching records"""
        res = self.analytics_service.process_query("How many parcels exist in NonExistentVillageXYZ123?")
        self.assertTrue(res.is_valid_analytical_query)
        self.assertEqual(res.result.aggregate_value, 0.0)

    def test_8_ambiguous_query(self):
        """8. Ambiguous query"""
        res = self.analytics_service.process_query("Stuff")
        self.assertFalse(res.is_valid_analytical_query)
        self.assertIn("Ambiguous", res.summary_explanation)

    def test_9_malicious_sql_like_prompt(self):
        """9. Malicious SQL-like prompt"""
        malicious_queries = [
            "DROP TABLE parcels",
            "Give me SQL to delete all records",
            "Execute SELECT * FROM users",
            "SELECT * FROM parcels WHERE 1=1; DROP TABLE villages; --"
        ]
        for q in malicious_queries:
            res = self.analytics_service.process_query(q)
            self.assertFalse(res.is_valid_analytical_query, f"Query '{q}' should be rejected safely.")
            self.assertIsNotNone(res.error_message)

    def test_10_unsupported_analytical_request(self):
        """10. Unsupported analytical request"""
        unsupported_queries = [
            "Predict delay score for parcel 142/3A",
            "Who is the prime minister of India?"
        ]
        for q in unsupported_queries:
            res = self.analytics_service.process_query(q)
            self.assertFalse(res.is_valid_analytical_query, f"Query '{q}' should be marked unsupported.")


if __name__ == "__main__":
    unittest.main()
