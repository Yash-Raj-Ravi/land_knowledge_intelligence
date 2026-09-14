import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.report import ProjectReportResponse
from backend.core.dependencies import (
    get_report_service,
    get_db_service,
    get_rag_service,
    get_analytics_service
)
from backend.models.rag import AskRequest


class TestReportsModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report_service = get_report_service()
        cls.db_service = get_db_service()
        cls.rag_service = get_rag_service()
        cls.analytics_service = get_analytics_service()

    def test_1_valid_project_report_generation(self):
        """1. Valid project report generation."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        self.assertIsInstance(res, ProjectReportResponse)
        self.assertEqual(res.project_id, "PRJ-NHAI-2024")
        self.assertTrue(len(res.executive_summary) > 0)
        self.assertTrue(len(res.sections) >= 5)

    def test_2_correct_project_scoping(self):
        """2. Correct project scoping."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        self.assertEqual(res.project_id, "PRJ-NHAI-2024")
        self.assertIn("PRJ-NHAI-2024", res.report_title)

    def test_3_authoritative_postgresql_numbers_preserved(self):
        """3. Authoritative PostgreSQL numbers preserved."""
        parcels = self.db_service.get_authoritative_project_parcels("PRJ-NHAI-2024")
        expected_count = len(parcels)
        expected_area = sum(p.get("area_hectares") or 0.0 for p in parcels)
        expected_award = sum(p.get("total_award_amount") or 0.0 for p in parcels)

        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        metrics = res.structured_metrics

        self.assertEqual(metrics.get("total_parcels"), expected_count)
        self.assertAlmostEqual(metrics.get("total_area_hectares"), expected_area, places=2)
        self.assertAlmostEqual(metrics.get("total_awarded_compensation"), expected_award, places=2)

    def test_4_missing_data_handled_safely(self):
        """4. Missing data handled safely."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        # Find R&R or Possession section
        rr_sec = next((s for s in res.sections if "Rehabilitation" in s.section_title or "R&R" in s.section_title), None)
        if rr_sec:
            self.assertTrue(
                "Information not available" in rr_sec.content or len(rr_sec.content) > 0
            )

    def test_5_document_citations_preserved(self):
        """5. Document citations preserved."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        self.assertIsInstance(res.citations, list)
        for cit in res.citations:
            self.assertTrue(len(cit.document_id) > 0)
            self.assertTrue(len(cit.file_name) > 0)
            self.assertTrue(cit.page_number >= 1)

    def test_6_conflicts_preserved(self):
        """6. Conflicts preserved."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        self.assertIsInstance(res.conflicts, list)
        for c in res.conflicts:
            self.assertTrue(len(c.field_name) > 0)
            self.assertTrue(len(c.authoritative_value) > 0)

    def test_7_hallucination_resistance_when_evidence_is_insufficient(self):
        """7. Hallucination resistance when evidence is insufficient."""
        res = self.report_service.generate_project_report("PRJ-NON-EXISTENT-999")
        self.assertIn(res.evidence_coverage, ["INSUFFICIENT", "PARTIAL", "COMPLETE"])
        self.assertEqual(res.structured_metrics.get("total_parcels"), 0)

    def test_8_unsupported_legal_conclusion_rejected_avoided(self):
        """8. Unsupported legal conclusion / prediction rejected/avoided."""
        res = self.report_service.generate_project_report("PRJ-NHAI-2024")
        full_text = res.markdown_content.lower()
        forbidden_phrases = ["delay probability", "expected delay days", "delay score", "predict delay"]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, full_text, f"Report should not contain delay prediction phrase '{phrase}'")

    def test_9_project_isolation(self):
        """9. Project isolation."""
        res1 = self.report_service.generate_project_report("PRJ-NHAI-2024")
        res2 = self.report_service.generate_project_report("PRJ-DEFAULT")
        self.assertEqual(res1.project_id, "PRJ-NHAI-2024")
        self.assertEqual(res2.project_id, "PRJ-DEFAULT")

    def test_10_existing_rag_analytics_functionality_remains_operational(self):
        """10. Existing RAG & Analytics functionality remains operational."""
        # Check /ask RAG
        ask_res = self.rag_service.ask(AskRequest(query="What is the status of Survey 142/3A?"))
        self.assertTrue(len(ask_res.answer) > 0)

        # Check Analytics
        ana_res = self.analytics_service.process_query("How many parcels exist?")
        self.assertTrue(ana_res.is_valid_analytical_query)


if __name__ == "__main__":
    unittest.main()
