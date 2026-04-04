#!/usr/bin/env python3
"""
Tests for SAAF-oriented 78207 chatbot intents and legacy behavior.
"""

import unittest

from app.integrated import get_groq_response
from app.saaf_handlers import try_handle_saaf_question


class TestSaafChatbot(unittest.TestCase):
    def _extract_text(self, result):
        if isinstance(result, tuple):
            return result[0]
        return result

    def test_available_community_need(self):
        result = try_handle_saaf_question(
            "What are the most common health issues in ZIP 78207?"
        )
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("community need signals", text.lower())
        self.assertIn("health_places", text)

    def test_available_311_conditions(self):
        result = try_handle_saaf_question(
            "Are there patterns of mold, pests, or sanitation complaints in 78207?"
        )
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("311 health-related signals", text)
        self.assertIn("mold/sanitation/pests", text.lower())

    def test_service_landscape_proxy(self):
        result = try_handle_saaf_question(
            "What mental health services are available in ZIP 78207?"
        )
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("service landscape proxy", text.lower())

    def test_gap_detection(self):
        result = try_handle_saaf_question(
            "Where are community needs highest but services limited in 78207?"
        )
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("gap score", text.lower())
        self.assertIn("need evidence", text.lower())

    def test_context_question(self):
        result = try_handle_saaf_question("What are the demographics of ZIP 78207?")
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("context metrics", text.lower())
        self.assertIn("population", text.lower())

    def test_unavailable_data_strict_response(self):
        result = try_handle_saaf_question(
            "Which areas show higher ER visits or crisis response concerns?"
        )
        self.assertIsNotNone(result)
        text = self._extract_text(result)
        self.assertIn("cannot provide a data-backed answer", text.lower())
        self.assertIn("currently available datasets", text.lower())

    def test_legacy_question_still_works(self):
        result = get_groq_response("How many potholes have been found this month?")
        text = self._extract_text(result)
        self.assertTrue(isinstance(text, str) and len(text) > 0)

    def test_mental_health_medication_question_is_strict(self):
        result = get_groq_response(
            "What percentage of residents in ZIP code 78207 use anxiety, depression, or sleep medications based only on available ZIP-level data?"
        )
        text = self._extract_text(result)
        self.assertIn("does not report", text.lower())
        self.assertIn("no valid percentage can be given", text.lower())
        self.assertIn("health_places.csv", text)

    def test_mental_health_national_comparison_requires_benchmark(self):
        result = get_groq_response(
            "How does mental health treatment usage in ZIP code 78207 compare to national averages, and what data sources support this comparison?"
        )
        text = self._extract_text(result)
        self.assertIn("cannot make a data-backed comparison to national averages", text.lower())
        self.assertIn("brfss / places", text.lower())

    def test_living_arrangements_no_longer_falls_into_potholes_dataset(self):
        result = get_groq_response("Do most people live by themselves or with others?")
        text = self._extract_text(result)
        self.assertIn("living arrangements in san antonio", text.lower())
        self.assertNotIn("311/potholes_cleaned.csv", text.lower())

    def test_pci_response_keeps_demo_style(self):
        result = get_groq_response("PCI for Zip code 78259?")
        text = self._extract_text(result)
        self.assertIn("Pavement Condition Index (PCI) for zip code 78259:", text)
        self.assertIn("Breakdown:", text)
        self.assertNotIn("Notes:", text)

    def test_history_response_keeps_year_groups(self):
        result = get_groq_response("History of repeated pothole complaints along San Pedro Ave?")
        text = self._extract_text(result)
        self.assertIn("Complaint History for San Pedro Ave", text)
        self.assertIn("2022", text)
        self.assertNotIn("Notes:", text)


if __name__ == "__main__":
    unittest.main()
