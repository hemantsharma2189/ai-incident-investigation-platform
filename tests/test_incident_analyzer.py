import json
import unittest
from pathlib import Path

from incident_analyzer import analyze_incident, create_report


class TestIncidentAnalyzer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        incident_path = Path(
            "examples/deployment-failure.json"
        )

        with incident_path.open("r", encoding="utf-8") as file:
            cls.data = json.load(file)

        cls.findings = analyze_incident(cls.data)

    def test_detects_deployment_correlation(self):
        titles = [
            finding["title"]
            for finding in self.findings
        ]

        self.assertIn(
            "Recent deployment correlates with service degradation",
            titles,
        )

    def test_detects_http_errors(self):
        titles = [
            finding["title"]
            for finding in self.findings
        ]

        self.assertIn(
            "Elevated HTTP error rate",
            titles,
        )

    def test_detects_container_restarts(self):
        titles = [
            finding["title"]
            for finding in self.findings
        ]

        self.assertIn(
            "Repeated container restarts: checkout-api",
            titles,
        )

    def test_detects_resource_saturation(self):
        titles = [
            finding["title"]
            for finding in self.findings
        ]

        self.assertIn("CPU saturation", titles)
        self.assertIn("High application latency", titles)

    def test_report_requires_human_approval(self):
        report = create_report(
            self.data,
            self.findings,
        )

        self.assertIn(
            "Recovery actions require human approval",
            report,
        )
        self.assertIn(
            "INC-2026-001",
            report,
        )


if __name__ == "__main__":
    unittest.main()
