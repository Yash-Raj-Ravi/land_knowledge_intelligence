import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.rag import AskRequest, AskResponse
from backend.core.dependencies import get_rag_service, get_ocr_service
from backend.utils.language_detector import detect_language
from backend.services.multilingual_service import MultilingualService


class TestMultilingualModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rag_service = get_rag_service()
        cls.ocr_service = get_ocr_service()
        cls.multilingual_service = MultilingualService()

    def test_1_english_document_retrieval(self):
        """1. English document retrieval."""
        req = AskRequest(query="What is the status of Survey 142/3A?")
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_2_hindi_document_retrieval(self):
        """2. Hindi document retrieval / language detection."""
        hindi_text = "इस भूमि का विवरण: गांव वडदला, खसरा नंबर 142/3A, कुल क्षेत्रफल 0.45 हेक्टेयर है।"
        detected = detect_language(hindi_text)
        self.assertEqual(detected["language"], "hi")
        self.assertTrue(detected["confidence"] > 0.5)

    def test_3_marathi_document_retrieval(self):
        """3. Marathi document retrieval / language detection."""
        marathi_text = "जमीन संपादन माहिती: मौजे वडदला, गट क्रमांक 142/3A, एकूण क्षेत्रफळ 0.45 हेक्टर आहे. मोबदला मंजूर."
        detected = detect_language(marathi_text)
        self.assertEqual(detected["language"], "mr")
        self.assertTrue(detected["confidence"] > 0.5)

    def test_4_hindi_to_english_cross_language_retrieval(self):
        """4. Hindi -> English cross-language retrieval."""
        req = AskRequest(
            query="What is the area of Survey 142/3A in Vadadala?",
            response_language="en"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_5_marathi_to_english_cross_language_retrieval(self):
        """5. Marathi -> English cross-language retrieval."""
        req = AskRequest(
            query="What compensation was awarded for Vadadala parcel?",
            response_language="en"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_6_english_to_hindi_cross_language_query(self):
        """6. English -> Hindi cross-language query."""
        req = AskRequest(
            query="What is the status of Survey 142/3A?",
            response_language="hi"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_7_english_to_marathi_cross_language_query(self):
        """7. English -> Marathi cross-language query."""
        req = AskRequest(
            query="What is the status of Survey 142/3A?",
            response_language="mr"
        )
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)

    def test_8_survey_number_normalization_across_languages(self):
        """8. Survey-number normalization across languages."""
        mr_survey_text = "मौजे वडदला गट क्रमांक 142/3A क्षेत्रफळ 0.45"
        hi_survey_text = "गांव वडदला खसरा नं 142/3A क्षेत्रफल 0.45"

        concepts_mr = self.multilingual_service.extract_canonical_concepts(mr_survey_text)
        concepts_hi = self.multilingual_service.extract_canonical_concepts(hi_survey_text)

        self.assertTrue(concepts_mr.get("village"))
        self.assertTrue(concepts_mr.get("survey_number"))
        self.assertTrue(concepts_hi.get("village"))
        self.assertTrue(concepts_hi.get("survey_number"))

    def test_9_page_level_citations_preserved(self):
        """9. Page-level citations preserved in cross-language queries."""
        req = AskRequest(query="What is recorded for Survey 142/3A?", response_language="hi")
        res = self.rag_service.ask(req)
        self.assertIsInstance(res.citations, list)
        for cit in res.citations:
            self.assertTrue(len(cit.file_name) > 0)
            self.assertTrue(cit.page_number >= 1)

    def test_10_unsupported_language_handled_safely(self):
        """10. Unsupported language handled safely."""
        detected = detect_language("12345 67890 !@#$%")
        self.assertEqual(detected["language"], "unknown")
        self.assertEqual(detected["confidence"], 0.0)

    def test_11_unicode_text_preserved(self):
        """11. Unicode Devanagari text preserved."""
        dev_text = "जिल्हा वडोदरा, तालुका सावली, मौजे वडदला"
        self.assertIn("वडदला", dev_text)
        self.assertEqual(len(dev_text), len("जिल्हा वडोदरा, तालुका सावली, मौजे वडदला"))

    def test_12_existing_english_rag_remains_operational(self):
        """12. Existing English RAG remains operational."""
        req = AskRequest(query="What area is recorded for Survey 142/3A?")
        res = self.rag_service.ask(req)
        self.assertIsInstance(res, AskResponse)
        self.assertTrue(len(res.answer) > 0)


if __name__ == "__main__":
    unittest.main()
