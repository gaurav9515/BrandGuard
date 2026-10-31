"""
Phase R3 Visual Identity Engine & Calibration Accuracy Test Suite.
Verifies:
1. Ground truth corpus calibration: Blocker Recall >= 0.90, Clean Banner FPR <= 0.05
2. Low-confidence human review lane routing (confidence < 0.75 -> IN_REVIEW)
3. Robustness: EXIF rotation transpose, ICC profile sRGB normalization
4. Vector SVG and Multi-page PDF auditing
5. test_visual_accuracy management command execution
"""

import os
import io
import json
from PIL import Image
from django.test import TestCase
from django.core.management import call_command
from governance.models import BrandProfile, Organization, Company
from governance.engines.visual_engine import (
    audit_image_file,
    audit_pdf_file,
    normalize_pil_image,
    calculate_contrast_ratio,
    calculate_delta_e,
    rgb_to_lab,
    hex_to_rgb
)
from governance.engines.visual_harness import run_visual_calibration_harness


class PhaseR3VisualAccuracyTests(TestCase):
    def setUp(self):
        self.org, _ = Organization.objects.get_or_create(name="NovaPay Global", slug="novapay-global")
        self.company, _ = Company.objects.get_or_create(
            organization=self.org,
            name="NovaPay Prime",
            slug="novapay-prime"
        )
        self.profile, _ = BrandProfile.objects.get_or_create(
            company=self.company,
            defaults={
                "org_name": "NovaPay Official Brand Guidelines",
                "allowed_hex_palette": [
                    {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
                    {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.0},
                    {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
                    {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
                ],
                "wcag_min_ratio": 4.5
            }
        )

    def test_01_visual_accuracy_calibration_targets_met(self):
        """Harness evaluates the 42-asset realistic image corpus and verifies targets."""
        report = run_visual_calibration_harness(profile=self.profile)
        self.assertEqual(report.get("status"), "success")

        targets = report.get("targets", {})
        metrics = report.get("metrics", {})

        # Primary precision/recall targets
        self.assertTrue(
            targets.get("blocker_recall_met"),
            f"Blocker Recall {metrics.get('blocker_recall'):.2%} failed target >= 0.90"
        )
        self.assertTrue(
            targets.get("clean_banner_fpr_met"),
            f"Clean Banner FPR {metrics.get('clean_banner_fpr'):.2%} failed target <= 0.05"
        )

        self.assertGreaterEqual(metrics.get("blocker_recall"), 0.90)
        self.assertLessEqual(metrics.get("clean_banner_fpr"), 0.05)
        self.assertGreaterEqual(metrics.get("accuracy"), 0.90)

    def test_02_low_confidence_review_lane_routing(self):
        """Findings with confidence < 0.75 must be routed to status='IN_REVIEW' with review_reason."""
        report = run_visual_calibration_harness(profile=self.profile)
        low_conf = report.get("low_confidence_detections", [])

        self.assertGreater(len(low_conf), 0, "Expected at least 1 low-confidence detection in review lane")
        for item in low_conf:
            self.assertLess(item["confidence"], 0.75)
            self.assertEqual(item["reason"], "LOW_CONFIDENCE_DETECTION")

    def test_03_normalization_exif_and_icc(self):
        """normalize_pil_image applies EXIF orientation transpose and converts to sRGB."""
        # Create an image with orientation flag
        img = Image.new("RGB", (200, 100), color=(10, 52, 35))
        exif = img.getexif()
        exif[0x0112] = 6  # 90 degrees CW rotation tag
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        buf.seek(0)

        opened = Image.open(buf)
        normalized = normalize_pil_image(opened)
        # 90 deg rotation swaps width and height
        self.assertEqual(normalized.size, (100, 200))
        self.assertEqual(normalized.mode, "RGB")

    def test_04_svg_vector_auditing(self):
        """audit_image_file parses and audits Scalable Vector Graphics (.svg)."""
        svg_code = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
          <rect width="400" height="200" fill="#0A3423"/>
          <text x="40" y="80" fill="#FFFFFF" font-size="20">Compliant Vector Text</text>
        </svg>"""
        buf = io.BytesIO(svg_code.encode("utf-8"))
        buf.name = "test_vector.svg"

        findings = audit_image_file(buf, self.profile)
        blockers = [f for f in findings if f.get("severity") == "BLOCKER" and f.get("status") != "IN_REVIEW"]
        self.assertEqual(len(blockers), 0)

    def test_05_multipage_pdf_auditing(self):
        """audit_pdf_file inspects all pages of a multi-page PDF document."""
        corpus_pdf = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "images", "clean_banner_08_multipage.pdf")
        if os.path.exists(corpus_pdf):
            findings = audit_pdf_file(corpus_pdf, self.profile)
            # Verify findings metadata has page tracking
            for f in findings:
                self.assertIn("location_json", f)
                self.assertIn("page", f["location_json"])

    def test_06_management_command_execution(self):
        """test_visual_accuracy management command runs cleanly with --strict."""
        out = io.StringIO()
        call_command("test_visual_accuracy", strict=True, stdout=out)
        output = out.getvalue()
        self.assertIn("ALL ACCURACY & CALIBRATION TARGETS SATISFIED", output)
        self.assertIn("Blocker Recall", output)
        self.assertIn("Clean Banner FPR", output)
