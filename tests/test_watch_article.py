import importlib.util
import plistlib
import re
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from scripts.build_site import FORBIDDEN

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "content/systems/watchos-ble-central-background"
spec = importlib.util.spec_from_file_location("watch_audit", ARTICLE / "examples/audit_watch_bundle.py")
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


class WatchArticleTests(unittest.TestCase):
    def fixture(self):
        return {"CFBundleSupportedPlatforms": ["WatchOS"],
                "NSBluetoothAlwaysUsageDescription": "Connect to the selected phone.",
                "NSHealthShareUsageDescription": "Read workout data.",
                "NSHealthUpdateUsageDescription": "Save the chosen workout.",
                "UIBackgroundModes": ["bluetooth-central"],
                "WKBackgroundModes": ["workout-processing"]}, {"com.apple.developer.healthkit": True}

    def test_configuration_pass_is_never_runtime_verification(self):
        info, rights = self.fixture()
        report = auditor.audit(info, rights)
        self.assertTrue(report["static_checks_passed"])
        self.assertFalse(report["runtime_verified"])

    def test_missing_background_ble_flag_is_reported(self):
        info, rights = self.fixture()
        info["UIBackgroundModes"] = ["audio"]
        report = auditor.audit(info, rights)
        self.assertFalse(report["static_checks_passed"])
        self.assertTrue(any("Audio mode" in note for note in report["notes"]))

    def test_observer_entitlement_is_not_a_workout_entitlement(self):
        info, _ = self.fixture()
        report = auditor.audit(info, {"com.apple.developer.healthkit.background-delivery": True})
        self.assertFalse(report["static_checks_passed"])
        self.assertTrue(any("observer queries" in note for note in report["notes"]))

    def test_only_one_extended_category_and_correct_platform(self):
        info, rights = self.fixture()
        info["WKBackgroundModes"] += ["mindfulness", "alarm"]
        self.assertFalse(auditor.audit(info, rights)["static_checks_passed"])
        info["WKBackgroundModes"] = ["workout-processing"]
        info["CFBundleSupportedPlatforms"] = ["iPhoneOS"]
        self.assertFalse(auditor.audit(info, rights)["static_checks_passed"])

    def test_document_xml_examples_are_well_formed_and_consistent(self):
        text = (ARTICLE / "README.md").read_text()
        samples = re.findall(r"```xml\n(.*?)\n```", text, re.S)
        self.assertEqual(len(samples), 4)
        workout, rights, extended, phone = [plistlib.loads(s.encode()) for s in samples]
        workout["CFBundleSupportedPlatforms"] = ["WatchOS"]
        extended["CFBundleSupportedPlatforms"] = ["WatchOS"]
        self.assertTrue(auditor.audit(workout, rights)["static_checks_passed"])
        self.assertTrue(auditor.audit(extended, {}, "mindfulness")["static_checks_passed"])
        self.assertEqual(phone["UIBackgroundModes"], ["bluetooth-peripheral"])
        self.assertNotIn("audio", phone["UIBackgroundModes"])

    def test_signed_bundle_with_no_entitlements_is_distinct_from_codesign_failure(self):
        with patch.object(auditor.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"", stderr=b"Executable=example")):
            self.assertEqual(auditor.signed_entitlements(Path("example.app")), {})
        with patch.object(auditor.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout=b"", stderr=b"not signed")):
            with self.assertRaises(ValueError):
                auditor.signed_entitlements(Path("example.app"))

    def test_signed_xml_entitlements_are_read_without_exposing_other_metadata(self):
        expected = {"com.apple.developer.healthkit": True}
        raw = plistlib.dumps(expected)
        with patch.object(auditor.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=raw, stderr=b"warning")):
            self.assertEqual(auditor.signed_entitlements(Path("example.app")), expected)

    def test_packet_size_examples(self):
        self.assertEqual(struct.calcsize("<dfffb"), 21)
        payload = 8 + 10 * 21
        self.assertEqual(payload, 218)
        self.assertEqual((payload + 4 - 1) // 4, 55)
        self.assertEqual((payload + 169 - 1) // 169, 2)

    def test_public_article_and_example_have_no_private_identifiers(self):
        for path in ARTICLE.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py", ".json", ".svg"}:
                text = path.read_text()
                self.assertIsNone(FORBIDDEN.search(text), path.name)
                self.assertNotIn("/Users/", text)
                self.assertNotIn("-----BEGIN PRIVATE KEY", text)


if __name__ == "__main__":
    unittest.main()
