"""The dependency gate must reject incomplete reports and indirect vulnerabilities."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ops.check_mall_audit import fingerprints


class MallAuditTests(unittest.TestCase):
    def read_report(self, data, kind):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(data))
            return fingerprints(path, kind)

    def test_direct_and_indirect_high_findings_are_blocking(self):
        report = {"vulnerabilities": {
            "direct": {"severity": "high", "via": [{"source": 123}]},
            "indirect": {"severity": "critical", "via": ["direct"]},
            "moderate": {"severity": "moderate", "via": [{"source": 456}]},
        }}
        self.assertEqual(self.read_report(report, "npm"),
                         {("direct", "123"), ("indirect", "via:direct")})

    def test_incomplete_inventory_is_not_a_clean_scan(self):
        with self.assertRaises(ValueError):
            self.read_report({"error": {"code": "ENETUNREACH"}}, "npm")
        with self.assertRaises(ValueError):
            self.read_report({}, "pip")

    def test_python_findings_keep_package_and_advisory_identity(self):
        report = {"dependencies": [{"name": "package", "vulns": [{"id": "CVE-fixture"}]}]}
        self.assertEqual(self.read_report(report, "pip"), {("package", "CVE-fixture")})


if __name__ == "__main__":
    unittest.main()
