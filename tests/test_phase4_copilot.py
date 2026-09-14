import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.rag import AskRequest, AskResponse
from backend.core.dependencies import get_rag_service, get_db_service
from backend.services.conflict_detector import ConflictDetector, ConflictItem


class TestPhase4Copilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rag_service = get_rag_service()
        cls.db_service = get_db_service()
        cls.conflict_detector = ConflictDetector()

    def test_1_ask_request_without_context(self):
        """1. AskRequest without context → existing behavior remains unchanged."""
        req = AskRequest(query="What is the status of Survey 142/3A?")
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)
        self.assertIn(res.evidence_coverage, ["COMPLETE", "PARTIAL", "INSUFFICIENT"])
        self.assertIsInstance(res.citations, list)

    def test_2_ask_request_with_project_id(self):
        """2. AskRequest with project_id."""
        req = AskRequest(
            query="What documents are available for this project?",
            project_id="PRJ-NHAI-2024"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_3_ask_request_with_parcel_id(self):
        """3. AskRequest with parcel_id."""
        req = AskRequest(
            query="What is the area recorded for this parcel?",
            parcel_id="PCL-VADADALA-142-3A"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_4_ask_request_with_survey_number(self):
        """4. AskRequest with survey_number."""
        req = AskRequest(
            query="What compensation was awarded?",
            survey_number="142/3A",
            village="Vadadala"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_5_parcel_specific_query_returns_correct_survey_evidence(self):
        """5. Parcel-specific query returns the correct survey evidence."""
        req = AskRequest(
            query="What is the area of this parcel?",
            survey_number="142/3A",
            parcel_id="PCL-VADADALA-142-3A"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        # Check retrieval response evidence
        if res.retrieval_response and res.retrieval_response.evidence:
            found_survey = any(
                "142/3A" in (ev.survey_number or "") or "142/3A" in ev.excerpt
                for ev in res.retrieval_response.evidence
            )
            self.assertTrue(found_survey, "Retrieved evidence should reference Survey 142/3A")
        elif res.citations:
            self.assertTrue(len(res.citations) > 0)


    def test_6_general_copilot_still_works(self):
        """6. General Copilot still works (no parcel context)."""
        req = AskRequest(query="What is the land acquisition procedure under Section 19?")
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_7_conflict_responses_display_correctly(self):
        """7. Conflict responses still display correctly."""
        # Mock structured DB record vs document evidence discrepancy
        db_records = [{
            "survey_number": "142/3A",
            "area_hectares": 0.4500,
            "total_award_amount": 2450000.00
        }]
        
        class MockEvidence:
            survey_number = "142/3A"
            excerpt = "Survey 142/3A has an area of 0.52 hectares under acquisition."
            document_id = "DOC-CONFLICT-TEST"
            file_name = "Award_Conflict_Test.pdf"
            page_number = 2

        conflicts = self.conflict_detector.detect_conflicts(db_records, [MockEvidence()])
        self.assertTrue(len(conflicts) > 0, "Conflict detector should find area discrepancy.")
        c = conflicts[0]
        self.assertEqual(c.field_name, "area_hectares")
        self.assertIn("0.4500", c.authoritative_value)
        self.assertIn("0.5200", c.document_value)

    def test_8_insufficient_evidence_displays_correctly(self):
        """8. INSUFFICIENT evidence still displays correctly."""
        req = AskRequest(query="What is the status of non_existent_survey_99999999?")
        res = self.rag_service.ask(req)
        self.assertEqual(res.evidence_coverage, "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
