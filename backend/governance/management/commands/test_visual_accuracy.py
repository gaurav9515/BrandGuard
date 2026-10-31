import json
import sys
from django.core.management.base import BaseCommand
from governance.engines.visual_harness import (
    run_visual_calibration_harness,
    generate_calibration_csv_report
)


class Command(BaseCommand):
    help = "Runs the Visual Engine Accuracy & Calibration Harness across the 42-image test corpus."

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='console',
            choices=['console', 'json', 'csv'],
            help="Output format: console, json, or csv"
        )
        parser.add_argument(
            '--strict',
            action='store_true',
            help="Exit with non-zero status if target thresholds (Recall >= 0.90, FPR <= 0.05) are not met."
        )

    def handle(self, *args, **options):
        output_format = options.get('format', 'console')
        strict = options.get('strict', False)

        report = run_visual_calibration_harness()

        if report.get("status") == "failed":
            self.stderr.write(self.style.ERROR(f"Harness failed: {report.get('error')}"))
            sys.exit(1)

        targets = report.get("targets", {})
        metrics = report.get("metrics", {})
        cm = report.get("confusion_matrix", {})

        recall_met = targets.get("blocker_recall_met", False)
        fpr_met = targets.get("clean_banner_fpr_met", False)
        all_passed = recall_met and fpr_met

        if output_format == 'json':
            self.stdout.write(json.dumps(report, indent=2))
        elif output_format == 'csv':
            csv_str = generate_calibration_csv_report(report)
            self.stdout.write(csv_str)
        else:
            self.stdout.write("\n" + "=" * 68)
            self.stdout.write(self.style.SUCCESS("  BRANDGUARD VISUAL ENGINE ACCURACY & CALIBRATION HARNESS"))
            self.stdout.write("=" * 68)
            self.stdout.write(f"Evaluated Assets : {report.get('total_images_evaluated')} files across 8 test categories")
            self.stdout.write(f"Timestamp        : {report.get('timestamp')}")
            self.stdout.write("-" * 68)

            self.stdout.write(self.style.MIGRATE_HEADING("CALIBRATION TARGET METRICS:"))
            rec_color = self.style.SUCCESS if recall_met else self.style.ERROR
            fpr_color = self.style.SUCCESS if fpr_met else self.style.ERROR

            rec_val = f"{metrics.get('blocker_recall', 0):.2%}"
            fpr_val = f"{metrics.get('clean_banner_fpr', 0):.2%}"
            self.stdout.write(f"  * Blocker Recall        : {rec_color(rec_val)}  [Target: {targets.get('blocker_recall_target')}] {'[PASS]' if recall_met else '[FAIL]'}")
            self.stdout.write(f"  * Clean Banner FPR      : {fpr_color(fpr_val)}  [Target: {targets.get('clean_banner_fpr_target')}] {'[PASS]' if fpr_met else '[FAIL]'}")
            self.stdout.write(f"  * Overall Accuracy      : {metrics.get('accuracy', 0):.2%}")
            self.stdout.write(f"  * Overall Precision     : {metrics.get('precision', 0):.2%}")
            self.stdout.write(f"  * F1 Score              : {metrics.get('f1_score', 0):.2%}")

            self.stdout.write("\n" + self.style.MIGRATE_HEADING("CONFUSION MATRIX:"))
            self.stdout.write(f"  True Positives  (TP) : {cm.get('true_positives', 0)}")
            self.stdout.write(f"  False Positives (FP) : {cm.get('false_positives', 0)}")
            self.stdout.write(f"  True Negatives  (TN) : {cm.get('true_negatives', 0)}")
            self.stdout.write(f"  False Negatives (FN) : {cm.get('false_negatives', 0)}")

            self.stdout.write("\n" + self.style.MIGRATE_HEADING("PER-RULE CLASSIFICATION PERFORMANCE:"))
            self.stdout.write(f"  {'Rule Code':<16} {'Rule Name':<34} {'TP':<4} {'FP':<4} {'FN':<4} {'Prec':<6} {'Rec':<6} {'F1':<6}")
            self.stdout.write("  " + "-" * 76)
            for r in report.get("per_rule_breakdown", []):
                self.stdout.write(f"  {r['rule_code']:<16} {r['rule_name']:<34} {r['tp']:<4} {r['fp']:<4} {r['fn']:<4} {r['precision']:<6.2f} {r['recall']:<6.2f} {r['f1_score']:<6.2f}")

            self.stdout.write("\n" + self.style.MIGRATE_HEADING("LOW-CONFIDENCE HUMAN REVIEW QUEUE:"))
            self.stdout.write(f"  Routed to human review: {report.get('low_confidence_count', 0)} item(s)")
            for lc in report.get("low_confidence_detections", []):
                self.stdout.write(f"    - {lc['filename']} [{lc['rule_code']}] conf={lc['confidence']} -> reason: {lc['reason']}")

            self.stdout.write("=" * 68)
            if all_passed:
                self.stdout.write(self.style.SUCCESS("  ALL ACCURACY & CALIBRATION TARGETS SATISFIED."))
            else:
                self.stdout.write(self.style.WARNING("  ONE OR MORE CALIBRATION TARGETS NOT MET."))
            self.stdout.write("=" * 68 + "\n")

        if strict and not all_passed:
            sys.exit(1)
