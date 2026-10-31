"""
Visual Accuracy & Precision/Recall Calibration Harness.
Evaluates BrandGuard Visual Engine against the 42-image ground_truth.json corpus.
Calculates:
- Blocker Recall (Target: >= 0.90)
- Clean Banner False Positive Rate (Target: <= 0.05)
- Per-rule Precision, Recall, F1 score
- Confusion Matrix (TP, FP, TN, FN)
- Low-confidence detections routed to human review lane
"""

import os
import json
import csv
import io
from datetime import datetime
from django.conf import settings
from .visual_engine import audit_image_file, audit_pdf_file


def run_visual_calibration_harness(profile=None):
    """
    Executes the accuracy calibration harness across the corpus.
    Returns structured results dict.
    """
    if profile is None:
        from governance.models import BrandProfile
        profile = BrandProfile.objects.first()
        if not profile:
            from governance.views import get_active_profile
            profile = get_active_profile()

    corpus_dir = os.path.join(settings.BASE_DIR, 'fixtures', 'images')
    gt_path = os.path.join(corpus_dir, 'ground_truth.json')

    if not os.path.exists(gt_path):
        return {
            "error": "Ground truth file not found at " + gt_path,
            "status": "failed"
        }

    with open(gt_path, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    images_dict = ground_truth.get("images", {})
    total_images = len(images_dict)

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    per_rule_stats = {
        "VIS_COLOR_001": {"name": "Off-Brand Color Palette", "tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "VIS_WCAG_2.1": {"name": "WCAG 2.1 Contrast Failure", "tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "VIS_A11Y_CVD": {"name": "Color-Vision Deficiency Ambiguity", "tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "VIS_LOGO_SPACE": {"name": "Optical Clear-Space Crowding", "tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "VIS_FONT_001": {"name": "Unapproved Typography", "tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }

    low_confidence_queue = []
    asset_results = []

    for filename, gt in images_dict.items():
        file_path = os.path.join(corpus_dir, filename)
        if not os.path.exists(file_path):
            continue

        # Run engine based on format
        if filename.lower().endswith('.pdf'):
            findings = audit_pdf_file(file_path, profile)
        else:
            findings = audit_image_file(file_path, profile)

        # Separate blockers vs warnings
        blocker_findings = [f for f in findings if f.get('severity') == 'BLOCKER' and f.get('status') != 'IN_REVIEW']
        warning_findings = [f for f in findings if f.get('severity') == 'WARNING']
        low_conf_findings = [f for f in findings if f.get('confidence', 1.0) < 0.75 or f.get('review_reason') == 'LOW_CONFIDENCE_DETECTION']

        for lc in low_conf_findings:
            low_confidence_queue.append({
                "filename": filename,
                "category": gt.get("category", "UNKNOWN"),
                "rule_code": lc.get("rule_citation_code"),
                "rule_title": lc.get("rule_citation_title"),
                "confidence": lc.get("confidence", 0.70),
                "reason": lc.get("review_reason", "LOW_CONFIDENCE_DETECTION"),
                "source_excerpt": lc.get("source_excerpt", ""),
                "suggested_fixes": lc.get("suggested_fixes", [])
            })

        expected_pass = gt.get("pass_fail") == "PASS"
        expected_blockers = gt.get("expected_blockers", 0)
        has_actual_blockers = len(blocker_findings) > 0

        # Classification
        if expected_pass:
            if not has_actual_blockers:
                tn += 1
                classification = "TN (Clean Pass)"
            else:
                fp += 1
                classification = "FP (False Alarm)"
        else:
            if has_actual_blockers or (expected_blockers == 0 and len(warning_findings) > 0):
                tp += 1
                classification = "TP (Violation Caught)"
            else:
                fn += 1
                classification = "FN (Violation Missed)"

        # Per-rule breakdown
        actual_rule_codes = {f.get("rule_citation_code") for f in findings}
        expected_rule_codes = {ef.get("rule_code") for ef in gt.get("expected_findings", [])}

        for rule_code in per_rule_stats:
            exp = rule_code in expected_rule_codes
            act = rule_code in actual_rule_codes
            if exp and act:
                per_rule_stats[rule_code]["tp"] += 1
            elif not exp and act:
                per_rule_stats[rule_code]["fp"] += 1
            elif exp and not act:
                per_rule_stats[rule_code]["fn"] += 1
            else:
                per_rule_stats[rule_code]["tn"] += 1

        asset_results.append({
            "filename": filename,
            "category": gt.get("category"),
            "expected_pass_fail": gt.get("pass_fail"),
            "classification": classification,
            "actual_findings_count": len(findings),
            "blockers_count": len(blocker_findings),
            "warnings_count": len(warning_findings),
            "findings": findings,
            "notes": gt.get("notes", "")
        })

    # Overall metrics
    total_samples = tp + fp + tn + fn
    accuracy = (tp + tn) / max(1, total_samples)

    blocker_recall = tp / max(1, (tp + fn))
    clean_banner_fpr = fp / max(1, (fp + tn))
    precision = tp / max(1, (tp + fp))
    f1_score = 2 * (precision * blocker_recall) / max(1e-5, (precision + blocker_recall))

    # Compile per-rule precision/recall/F1 table
    rule_table = []
    for r_code, stats in per_rule_stats.items():
        r_tp = stats["tp"]
        r_fp = stats["fp"]
        r_fn = stats["fn"]
        r_prec = r_tp / max(1, (r_tp + r_fp))
        r_rec = r_tp / max(1, (r_tp + r_fn))
        r_f1 = 2 * (r_prec * r_rec) / max(1e-5, (r_prec + r_rec)) if (r_prec + r_rec) > 0 else 0.0
        rule_table.append({
            "rule_code": r_code,
            "rule_name": stats["name"],
            "tp": r_tp,
            "fp": r_fp,
            "fn": r_fn,
            "tn": stats["tn"],
            "precision": round(r_prec, 3),
            "recall": round(r_rec, 3),
            "f1_score": round(r_f1, 3),
        })

    report = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_images_evaluated": total_samples,
        "targets": {
            "blocker_recall_target": ">= 0.90",
            "clean_banner_fpr_target": "<= 0.05",
            "blocker_recall_met": blocker_recall >= 0.90,
            "clean_banner_fpr_met": clean_banner_fpr <= 0.05
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "blocker_recall": round(blocker_recall, 4),
            "clean_banner_fpr": round(clean_banner_fpr, 4),
            "precision": round(precision, 4),
            "f1_score": round(f1_score, 4),
        },
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        },
        "per_rule_breakdown": rule_table,
        "low_confidence_detections": low_confidence_queue,
        "low_confidence_count": len(low_confidence_queue),
        "asset_results": asset_results
    }

    return report


def generate_calibration_csv_report(report_data):
    """Generates a downloadable CSV summary of the calibration run."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Summary Header
    writer.writerow(["BrandGuard Visual Calibration & Accuracy Report"])
    writer.writerow(["Generated At", report_data.get("timestamp")])
    writer.writerow(["Total Corpus Images Evaluated", report_data.get("total_images_evaluated")])
    writer.writerow([])

    # 2. Executive Metrics
    m = report_data.get("metrics", {})
    t = report_data.get("targets", {})
    writer.writerow(["Metric", "Score", "Target", "Status"])
    writer.writerow(["Blocker Recall", f"{round(m.get('blocker_recall', 0) * 100, 1)}%", ">= 90.0%", "PASS" if t.get("blocker_recall_met") else "FAIL"])
    writer.writerow(["Clean Banner FPR", f"{round(m.get('clean_banner_fpr', 0) * 100, 1)}%", "<= 5.0%", "PASS" if t.get("clean_banner_fpr_met") else "FAIL"])
    writer.writerow(["Overall Accuracy", f"{round(m.get('accuracy', 0) * 100, 1)}%", "-", "-"])
    writer.writerow(["Precision", f"{round(m.get('precision', 0) * 100, 1)}%", "-", "-"])
    writer.writerow(["F1 Score", round(m.get('f1_score', 0), 3), "-", "-"])
    writer.writerow([])

    # 3. Confusion Matrix
    cm = report_data.get("confusion_matrix", {})
    writer.writerow(["Confusion Matrix"])
    writer.writerow(["True Positives (TP)", cm.get("true_positives", 0)])
    writer.writerow(["False Positives (FP)", cm.get("false_positives", 0)])
    writer.writerow(["True Negatives (TN)", cm.get("true_negatives", 0)])
    writer.writerow(["False Negatives (FN)", cm.get("false_negatives", 0)])
    writer.writerow([])

    # 4. Per-Rule Breakdown
    writer.writerow(["Rule Code", "Rule Name", "Precision", "Recall", "F1 Score", "TP", "FP", "FN"])
    for rb in report_data.get("per_rule_breakdown", []):
        writer.writerow([
            rb.get("rule_code"),
            rb.get("rule_name"),
            rb.get("precision"),
            rb.get("recall"),
            rb.get("f1_score"),
            rb.get("tp"),
            rb.get("fp"),
            rb.get("fn")
        ])
    writer.writerow([])

    # 5. Asset Results
    writer.writerow(["Filename", "Category", "Expected", "Classification", "Blockers", "Warnings", "Notes"])
    for ar in report_data.get("asset_results", []):
        writer.writerow([
            ar.get("filename"),
            ar.get("category"),
            ar.get("expected_pass_fail"),
            ar.get("classification"),
            ar.get("blockers_count"),
            ar.get("warnings_count"),
            ar.get("notes")
        ])

    return output.getvalue()

