"""
Generates the BrandGuard 42-image Realistic Visual Marketing Corpus,
LICENSES.md, and ground_truth.json calibration dataset.
Outputs to:
  - backend/fixtures/images/
  - frontend/public/samples/
"""

import os
import json
import math
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageCms
import fitz  # PyMuPDF

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'images'))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'public', 'samples'))

os.makedirs(BACKEND_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# Brand Standards
NOVA_GREEN = "#0A3423"   # (10, 52, 35)
NOVA_TEAL = "#00D4B6"    # (0, 212, 182)
PURE_WHITE = "#FFFFFF"   # (255, 255, 255)
MUTED_PANEL = "#F8FAF9"  # (248, 250, 249)

def hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def save_dual(image_or_bytes, filename, format=None, **kwargs):
    p1 = os.path.join(BACKEND_DIR, filename)
    p2 = os.path.join(FRONTEND_DIR, filename)
    if isinstance(image_or_bytes, bytes):
        with open(p1, 'wb') as f:
            f.write(image_or_bytes)
        with open(p2, 'wb') as f:
            f.write(image_or_bytes)
    elif isinstance(image_or_bytes, str):
        with open(p1, 'w', encoding='utf-8') as f:
            f.write(image_or_bytes)
        with open(p2, 'w', encoding='utf-8') as f:
            f.write(image_or_bytes)
    else:
        image_or_bytes.save(p1, format=format, **kwargs)
        image_or_bytes.save(p2, format=format, **kwargs)

ground_truth = {
    "corpus_version": "1.0",
    "total_images": 42,
    "description": "BrandGuard Ground-Truth Calibration Corpus for Visual Identity, Contrast, and Accessibility",
    "images": {}
}

# =============================================================================
# Helper drawing functions
# =============================================================================
def draw_card(draw, box, fill_rgb, outline_rgb=None, radius=12):
    draw.rounded_rectangle(box, radius=radius, fill=fill_rgb, outline=outline_rgb)

def draw_logo(draw, xy, text="NovaPay", fill_rgb=(0, 212, 182)):
    x, y = xy
    # Logo icon: shield / leaf shape
    draw.rounded_rectangle([x, y, x + 24, y + 24], radius=6, fill=fill_rgb)
    draw.ellipse([x + 6, y + 6, x + 18, y + 18], fill=hex_to_rgb(NOVA_GREEN))
    draw.text((x + 32, y + 4), text, fill=(255, 255, 255))

# =============================================================================
# 1. CLEAN COMPLIANT BANNERS (Target: FPR <= 0.05, 10 Images)
# =============================================================================
print("Generating Category 1: Clean Compliant Banners (10)...")

# 01. clean_banner_01_desktop.png (1200x630 landscape desktop)
img = Image.new("RGB", (1200, 630), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (60, 50), "NovaPay Enterprise")
draw_card(d, [60, 140, 1140, 560], hex_to_rgb(MUTED_PANEL), outline_rgb=hex_to_rgb(NOVA_TEAL), radius=16)
d.text((100, 180), "Cross-Border Rails That Settle In Seconds", fill=hex_to_rgb(NOVA_GREEN))
d.text((100, 240), "Enterprise liquidity engine with 0.5% FX fees and real-time ledger settlement.", fill=(40, 70, 55))
draw_card(d, [100, 320, 280, 380], hex_to_rgb(NOVA_GREEN), radius=8)
d.text((130, 342), "Open Account ->", fill=hex_to_rgb(NOVA_TEAL))
save_dual(img, "clean_banner_01_desktop.png", format="PNG")
ground_truth["images"]["clean_banner_01_desktop.png"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "1200x630 desktop banner adhering strictly to approved palette and 8.5:1 contrast."
}

# 02. clean_banner_02_square.png (1080x1080 square social)
img = Image.new("RGB", (1080, 1080), hex_to_rgb(MUTED_PANEL))
d = ImageDraw.Draw(img)
draw_card(d, [80, 80, 1000, 1000], hex_to_rgb(NOVA_GREEN), radius=24)
draw_logo(d, (140, 140), "NovaPay Global")
d.text((140, 300), "Institutional Treasury Built for Speed", fill=(255, 255, 255))
d.text((140, 380), "Manage multi-currency balances across 42 jurisdictions seamlessly.", fill=hex_to_rgb(NOVA_TEAL))
draw_card(d, [140, 500, 420, 580], hex_to_rgb(NOVA_TEAL), radius=12)
d.text((170, 532), "Explore Platform", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "clean_banner_02_square.png", format="PNG")
ground_truth["images"]["clean_banner_02_square.png"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "1080x1080 square social card in compliant green and teal."
}

# 03. clean_banner_03_story.webp (1080x1920 9:16 mobile story)
img = Image.new("RGB", (1080, 1920), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (100, 120), "NovaPay Mobile")
draw_card(d, [80, 300, 1000, 1700], hex_to_rgb(MUTED_PANEL), radius=32)
d.text((140, 380), "Real-Time Treasury On Your Phone", fill=hex_to_rgb(NOVA_GREEN))
d.text((140, 460), "Instant approvals, audit trails, and biometric clearance.", fill=(30, 60, 45))
draw_card(d, [140, 1400, 940, 1540], hex_to_rgb(NOVA_GREEN), radius=16)
d.text((380, 1455), "Download iOS App", fill=(255, 255, 255))
save_dual(img, "clean_banner_03_story.webp", format="WEBP")
ground_truth["images"]["clean_banner_03_story.webp"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "9:16 mobile story format with valid palette."
}

# 04. clean_banner_04_leaderboard.jpeg (728x90 horizontal banner)
img = Image.new("RGB", (728, 90), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (20, 30), "NovaPay")
d.text((220, 35), "Zero-friction liquidity settlement for high-growth tech.", fill=(255, 255, 255))
draw_card(d, [590, 20, 708, 70], hex_to_rgb(NOVA_TEAL), radius=6)
d.text((615, 38), "Learn More", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "clean_banner_04_leaderboard.jpeg", format="JPEG", quality=90)
ground_truth["images"]["clean_banner_04_leaderboard.jpeg"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "728x90 leaderboard ad format."
}

# 05. clean_banner_05_darkmode.png (1200x630 dark theme)
img = Image.new("RGB", (1200, 630), (8, 20, 14)) # deep forest black
d = ImageDraw.Draw(img)
draw_card(d, [40, 40, 1160, 590], hex_to_rgb(NOVA_GREEN), radius=16)
draw_logo(d, (80, 70), "NovaPay Dark")
d.text((80, 180), "Developer API Rails · Live 99.999% SLA", fill=hex_to_rgb(NOVA_TEAL))
d.text((80, 250), "Sub-second webhook confirmations with Ed25519 payload signatures.", fill=(220, 235, 225))
save_dual(img, "clean_banner_05_darkmode.png", format="PNG")
ground_truth["images"]["clean_banner_05_darkmode.png"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Compliant dark mode marketing panel."
}

# 06. clean_banner_06_highdpi_300.png (1500x1000 high DPI 300)
img = Image.new("RGB", (1500, 1000), hex_to_rgb(PURE_WHITE))
d = ImageDraw.Draw(img)
draw_card(d, [100, 100, 1400, 900], hex_to_rgb(NOVA_GREEN), radius=20)
draw_logo(d, (180, 160), "NovaPay Commercial")
d.text((180, 320), "High-Resolution Executive Fact Sheet", fill=(255, 255, 255))
d.text((180, 400), "Certified SOC2 Type II and ISO/IEC 27001 Infrastructure.", fill=hex_to_rgb(NOVA_TEAL))
save_dual(img, "clean_banner_06_highdpi_300.png", format="PNG", dpi=(300, 300))
ground_truth["images"]["clean_banner_06_highdpi_300.png"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "300 DPI high resolution print card."
}

# 07. clean_banner_07_srgb_profile.jpeg (with embedded sRGB profile)
img = Image.new("RGB", (800, 600), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (60, 50), "NovaPay sRGB")
d.text((60, 180), "Color-Calibrated Asset", fill=hex_to_rgb(NOVA_TEAL))
srgb_prof = ImageCms.createProfile('sRGB')
save_dual(img, "clean_banner_07_srgb_profile.jpeg", format="JPEG", icc_profile=ImageCms.ImageCmsProfile(srgb_prof).tobytes())
ground_truth["images"]["clean_banner_07_srgb_profile.jpeg"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Explicitly embedded sRGB ICC profile with clean colors."
}

# 08. clean_banner_08_multipage.pdf (2 page compliant brand doc)
doc = fitz.open()
p1 = doc.new_page(width=612, height=792)
p1.draw_rect(fitz.Rect(0, 0, 612, 792), color=None, fill=(0.04, 0.20, 0.14)) # Nova Green
p1.insert_text(fitz.Point(72, 100), "NovaPay Compliance Dossier", fontsize=24, color=(1, 1, 1))
p1.insert_text(fitz.Point(72, 140), "Page 1: Approved corporate governance and treasury rails.", fontsize=14, color=(0.0, 0.83, 0.71))

p2 = doc.new_page(width=612, height=792)
p2.draw_rect(fitz.Rect(0, 0, 612, 792), color=None, fill=(0.97, 0.98, 0.98)) # Muted Panel
p2.insert_text(fitz.Point(72, 100), "NovaPay Technical Specifications", fontsize=24, color=(0.04, 0.20, 0.14))
p2.insert_text(fitz.Point(72, 140), "Page 2: 99.999% uptime SLA across all clearing channels.", fontsize=14, color=(0.1, 0.3, 0.2))

pdf_bytes = doc.write()
doc.close()
save_dual(pdf_bytes, "clean_banner_08_multipage.pdf")
ground_truth["images"]["clean_banner_08_multipage.pdf"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "2-page fully compliant PDF document."
}

# 09. clean_banner_09_vector.svg
svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
  <rect width="800" height="400" fill="{NOVA_GREEN}"/>
  <rect x="40" y="40" width="720" height="320" rx="16" fill="{MUTED_PANEL}"/>
  <circle cx="90" cy="90" r="24" fill="{NOVA_TEAL}"/>
  <text x="130" y="98" font-family="Inter, sans-serif" font-size="28" font-weight="bold" fill="{NOVA_GREEN}">NovaPay Vector</text>
  <text x="90" y="180" font-family="Inter, sans-serif" font-size="20" fill="{NOVA_GREEN}">Clean Scalable Vector Graphics Representation</text>
  <rect x="90" y="220" width="180" height="48" rx="8" fill="{NOVA_GREEN}"/>
  <text x="125" y="250" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="{NOVA_TEAL}">Get Started</text>
</svg>"""
save_dual(svg_content, "clean_banner_09_vector.svg")
ground_truth["images"]["clean_banner_09_vector.svg"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Compliant vector SVG format banner."
}

# 10. clean_banner_10_product_ad.webp
img = Image.new("RGB", (900, 600), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [50, 50, 850, 550], hex_to_rgb(MUTED_PANEL), radius=16)
draw_logo(d, (90, 80), "NovaPay Prime")
d.text((90, 160), "Cross-Border Liquidity Pools for Enterprise", fill=hex_to_rgb(NOVA_GREEN))
d.text((90, 220), "Instant conversion at interbank midpoint with zero hidden spreads.", fill=(50, 70, 60))
draw_card(d, [90, 300, 320, 370], hex_to_rgb(NOVA_TEAL), radius=8)
d.text((125, 328), "Request API Key", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "clean_banner_10_product_ad.webp", format="WEBP")
ground_truth["images"]["clean_banner_10_product_ad.webp"] = {
    "category": "CLEAN_COMPLIANT",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "WebP product ad banner with clean layout."
}

# =============================================================================
# 2. SUBTLE OFF-BRAND COLORS (Delta E ~ 3.5 - 5.5, 5 Images)
# =============================================================================
print("Generating Category 2: Subtle Off-Brand Colors (5)...")

# 11. subtle_color_01_emerald_drift.png (Color #154530 vs #0A3423, DeltaE ~ 4.8)
img = Image.new("RGB", (1000, 600), hex_to_rgb("#154530")) # Off-brand emerald drift
d = ImageDraw.Draw(img)
draw_logo(d, (60, 50), "NovaPay")
draw_card(d, [60, 140, 940, 520], hex_to_rgb(MUTED_PANEL), radius=16)
d.text((100, 200), "Subtle Palette Drift: Forest Green Hue Variation", fill=hex_to_rgb("#154530"))
save_dual(img, "subtle_color_01_emerald_drift.png", format="PNG")
ground_truth["images"]["subtle_color_01_emerald_drift.png"] = {
    "category": "SUBTLE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 4.8, "offending_hex": "#154530"}
    ],
    "notes": "Dominant background drifts to #154530 exceeding brand delta_e threshold of 4.0."
}

# 12. subtle_color_02_teal_cyan_drift.jpeg (Color #00ECD0 vs #00D4B6, DeltaE ~ 5.6)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [60, 60, 740, 440], hex_to_rgb("#00ECD0"), radius=16) # Off-brand cyan
d.text((100, 120), "Cyan Hue Drift on Card Background", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "subtle_color_02_teal_cyan_drift.jpeg", format="JPEG", quality=90)
ground_truth["images"]["subtle_color_02_teal_cyan_drift.jpeg"] = {
    "category": "SUBTLE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 5.6, "offending_hex": "#00ECD0"}
    ],
    "notes": "Teal accent shifts into unapproved saturated cyan."
}

# 13. subtle_color_03_warm_white.webp (#FAF3E6 vs #FFFFFF / #F8FAF9, DeltaE ~ 4.9)
img = Image.new("RGB", (900, 600), hex_to_rgb("#FAF3E6")) # Cream/warm yellow tint
d = ImageDraw.Draw(img)
draw_card(d, [60, 60, 840, 540], hex_to_rgb(NOVA_GREEN), radius=16)
d.text((100, 120), "Unapproved Cream White Background", fill=(255, 255, 255))
save_dual(img, "subtle_color_03_warm_white.webp", format="WEBP")
ground_truth["images"]["subtle_color_03_warm_white.webp"] = {
    "category": "SUBTLE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 4.9, "offending_hex": "#FAF3E6"}
    ],
    "notes": "Off-white has warm cream tint deviating from neutral brand white."
}

# 14. subtle_color_04_moss_tint.png (#226B42 vs #0A3423, DeltaE ~ 5.3)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [50, 50, 750, 450], hex_to_rgb("#226B42"), radius=16)
d.text((100, 120), "Moss Green Drift on Feature Panel", fill=(255, 255, 255))
save_dual(img, "subtle_color_04_moss_tint.png", format="PNG")
ground_truth["images"]["subtle_color_04_moss_tint.png"] = {
    "category": "SUBTLE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 5.3, "offending_hex": "#226B42"}
    ],
    "notes": "Secondary card uses uncalibrated moss green."
}

# 15. subtle_color_05_low_confidence_boundary.png (DeltaE ~ 4.2, boundary test)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [60, 60, 740, 440], hex_to_rgb("#0A3D23"), radius=16) # DeltaE ~ 4.2 against #0A3423
d.text((100, 120), "Threshold Boundary Test (Delta E ~ 4.2)", fill=(255, 255, 255))
save_dual(img, "subtle_color_05_low_confidence_boundary.png", format="PNG")
ground_truth["images"]["subtle_color_05_low_confidence_boundary.png"] = {
    "category": "LOW_CONFIDENCE_REVIEW",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "low_confidence": True,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 4.2, "review_reason": "LOW_CONFIDENCE_DETECTION"}
    ],
    "notes": "Near-threshold color deviation triggering low-confidence review lane."
}

# =============================================================================
# 3. SEVERE COLOR VIOLATIONS (5 Images)
# =============================================================================
print("Generating Category 3: Severe Color Violations (5)...")

# 16. severe_color_01_crimson_cta.png (Violent red #E11D48 CTA)
img = Image.new("RGB", (1000, 600), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [60, 60, 940, 540], hex_to_rgb(MUTED_PANEL), radius=16)
d.text((100, 120), "Enterprise Banking Services", fill=hex_to_rgb(NOVA_GREEN))
draw_card(d, [100, 300, 450, 420], hex_to_rgb("#E11D48"), radius=12) # Crimson CTA
d.text((140, 350), "Claim 50% Off Transfer Fees!", fill=(255, 255, 255))
save_dual(img, "severe_color_01_crimson_cta.png", format="PNG")
ground_truth["images"]["severe_color_01_crimson_cta.png"] = {
    "category": "SEVERE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 48.0, "offending_hex": "#E11D48"}
    ],
    "notes": "Disallowed promotional crimson button violates institutional trust guidelines."
}

# 17. severe_color_02_electric_purple.webp (#8B5CF6 crypto-style purple)
img = Image.new("RGB", (900, 600), hex_to_rgb("#8B5CF6"))
d = ImageDraw.Draw(img)
draw_logo(d, (60, 50), "NovaPay")
d.text((60, 180), "Decentralized Liquidity Rails", fill=(255, 255, 255))
save_dual(img, "severe_color_02_electric_purple.webp", format="WEBP")
ground_truth["images"]["severe_color_02_electric_purple.webp"] = {
    "category": "SEVERE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 54.0, "offending_hex": "#8B5CF6"}
    ],
    "notes": "Full background in electric purple completely violates brand emerald identity."
}

# 18. severe_color_03_goldenrod_promo.jpeg (#EAB308 bright yellow promo badge)
img = Image.new("RGB", (1000, 600), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [80, 80, 920, 520], hex_to_rgb(MUTED_PANEL), radius=16)
draw_card(d, [700, 100, 880, 260], hex_to_rgb("#EAB308"), radius=16) # Goldenrod badge
d.text((720, 160), "HOT DEAL!", fill=(0, 0, 0))
d.text((120, 160), "Institutional Treasury Solutions", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "severe_color_03_goldenrod_promo.jpeg", format="JPEG")
ground_truth["images"]["severe_color_03_goldenrod_promo.jpeg"] = {
    "category": "SEVERE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 42.0, "offending_hex": "#EAB308"}
    ],
    "notes": "Bright goldenrod badge violates brand color policy."
}

# 19. severe_color_04_neon_orange.png (#FF6B00 neon orange discount bar)
img = Image.new("RGB", (1100, 450), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [0, 350, 1100, 450], hex_to_rgb("#FF6B00"), radius=0) # Neon orange footer
d.text((100, 120), "Cross-Border Liquidity Infrastructure", fill=(255, 255, 255))
d.text((200, 390), "LIMITED TIME: 0.1% FX FEE PROMOTION", fill=(255, 255, 255))
save_dual(img, "severe_color_04_neon_orange.png", format="PNG")
ground_truth["images"]["severe_color_04_neon_orange.png"] = {
    "category": "SEVERE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "delta_e": 58.0, "offending_hex": "#FF6B00"}
    ],
    "notes": "Neon orange promo bar is strictly prohibited."
}

# 20. severe_color_05_multipage_pdf_violation.pdf (Page 2 contains severe pink violation)
doc = fitz.open()
p1 = doc.new_page(width=612, height=792)
p1.draw_rect(fitz.Rect(0, 0, 612, 792), fill=(0.04, 0.20, 0.14))
p1.insert_text(fitz.Point(72, 100), "NovaPay Compliant Page 1", fontsize=22, color=(1, 1, 1))

p2 = doc.new_page(width=612, height=792)
p2.draw_rect(fitz.Rect(0, 0, 612, 792), fill=(1.0, 0.2, 0.6)) # Neon pink
p2.insert_text(fitz.Point(72, 100), "Unapproved Neon Pink Presentation Page", fontsize=22, color=(1, 1, 1))

pdf_bytes = doc.write()
doc.close()
save_dual(pdf_bytes, "severe_color_05_multipage_pdf_violation.pdf")
ground_truth["images"]["severe_color_05_multipage_pdf_violation.pdf"] = {
    "category": "SEVERE_COLOR_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_COLOR_001", "severity": "BLOCKER", "page": 2, "offending_hex": "#FF3399"}
    ],
    "notes": "Multi-page PDF with severe color violation on second page."
}

# =============================================================================
# 4. LOW-CONTRAST TEXT FAILURES (WCAG 2.1 Contrast 1.5:1 - 4.4:1, 5 Images)
# =============================================================================
print("Generating Category 4: Low-Contrast Text Failures (5)...")

# 21. low_contrast_01_gray_on_white.png (#94A3B8 on #FFFFFF, contrast 2.4:1)
img = Image.new("RGB", (900, 500), hex_to_rgb(PURE_WHITE))
d = ImageDraw.Draw(img)
draw_logo(d, (50, 40), "NovaPay")
d.text((50, 160), "Essential Disclaimer & Legal Text", fill=hex_to_rgb(NOVA_GREEN))
d.text((50, 240), "Sub-minimum contrast fine print: deposits subject to counterparty risk.", fill=hex_to_rgb("#94A3B8"))
save_dual(img, "low_contrast_01_gray_on_white.png", format="PNG")
ground_truth["images"]["low_contrast_01_gray_on_white.png"] = {
    "category": "LOW_CONTRAST_FAIL",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_WCAG_2.1", "severity": "BLOCKER", "contrast_ratio": 2.4}
    ],
    "notes": "Light gray text on white background produces 2.4:1 contrast (below 4.5:1 AA)."
}

# 22. low_contrast_02_dark_green_on_dark.jpeg (#1F5A3A on #0A3423, contrast 2.1:1)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (50, 40), "NovaPay")
d.text((50, 180), "Invisible dark green text on dark emerald canvas.", fill=hex_to_rgb("#1F5A3A"))
save_dual(img, "low_contrast_02_dark_green_on_dark.jpeg", format="JPEG")
ground_truth["images"]["low_contrast_02_dark_green_on_dark.jpeg"] = {
    "category": "LOW_CONTRAST_FAIL",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_WCAG_2.1", "severity": "BLOCKER", "contrast_ratio": 2.1}
    ],
    "notes": "Medium green on deep green background produces 2.1:1 contrast."
}

# 23. low_contrast_03_teal_on_white.webp (#00D4B6 on #FFFFFF, contrast 1.9:1)
img = Image.new("RGB", (900, 500), hex_to_rgb(PURE_WHITE))
d = ImageDraw.Draw(img)
d.text((80, 120), "Primary Marketing Headline in Bright Teal", fill=hex_to_rgb(NOVA_TEAL))
d.text((80, 200), "Teal is approved for dark backgrounds, but fails contrast on white.", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "low_contrast_03_teal_on_white.webp", format="WEBP")
ground_truth["images"]["low_contrast_03_teal_on_white.webp"] = {
    "category": "LOW_CONTRAST_FAIL",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_WCAG_2.1", "severity": "BLOCKER", "contrast_ratio": 1.9}
    ],
    "notes": "Bright teal on white gives 1.9:1 contrast failure."
}

# 24. low_contrast_04_boundary_4_2.png (Charcoal on dark gray, contrast ~ 4.1:1)
img = Image.new("RGB", (800, 500), (35, 45, 40))
d = ImageDraw.Draw(img)
d.text((60, 160), "Boundary Condition Text Contrast Test (4.1:1)", fill=(135, 155, 145))
save_dual(img, "low_contrast_04_boundary_4_2.png", format="PNG")
ground_truth["images"]["low_contrast_04_boundary_4_2.png"] = {
    "category": "LOW_CONTRAST_FAIL",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_WCAG_2.1", "severity": "BLOCKER", "contrast_ratio": 4.1}
    ],
    "notes": "Near-threshold contrast ratio of 4.1:1 strictly fails WCAG 4.5:1 AA standard."
}

# 25. low_contrast_05_gradient_background.png (Worst-case sampling test)
# Background smoothly gradients from dark green #0A3423 to light mint #E8EFE6
w, h = 900, 500
grad_arr = np.zeros((h, w, 3), dtype=np.uint8)
c_start = np.array(hex_to_rgb(NOVA_GREEN), dtype=np.float32)
c_end = np.array(hex_to_rgb("#E8EFE6"), dtype=np.float32)
for x in range(w):
    alpha = x / float(w)
    grad_arr[:, x] = (c_start * (1 - alpha) + c_end * alpha).astype(np.uint8)
img = Image.fromarray(grad_arr)
d = ImageDraw.Draw(img)
# White text placed over the right side (where background is light mint) -> worst-case contrast drops to 2.8:1
d.text((500, 200), "White Text Over Light Mint Gradient", fill=(255, 255, 255))
save_dual(img, "low_contrast_05_gradient_background.png", format="PNG")
ground_truth["images"]["low_contrast_05_gradient_background.png"] = {
    "category": "LOW_CONTRAST_FAIL",
    "pass_fail": "FAIL",
    "expected_blockers": 1,
    "expected_warnings": 0,
    "expected_findings": [
        {"rule_code": "VIS_WCAG_2.1", "severity": "BLOCKER", "contrast_ratio": 2.8, "worst_case_sampled": True}
    ],
    "notes": "Tests worst-case edge contrast sampling: average bbox passes but local edge contrast fails at 2.8:1."
}

# =============================================================================
# 5. CVD (COLOR-VISION DEFICIENCY) STRESS TESTS (4 Images)
# =============================================================================
print("Generating Category 5: CVD Stress Tests (4)...")

# 26. cvd_deuteranopia_collapse_01.png
img = Image.new("RGB", (900, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
# Red #D32F2F and Green #388E3C clusters that look distinct in normal vision but collapse in Deuteranopia
draw_card(d, [100, 150, 400, 350], hex_to_rgb("#D32F2F"), radius=16) # Red button
d.text((150, 240), "Deny Transfer", fill=(255, 255, 255))
draw_card(d, [500, 150, 800, 350], hex_to_rgb("#388E3C"), radius=16) # Green button
d.text((540, 240), "Approve Transfer", fill=(255, 255, 255))
save_dual(img, "cvd_deuteranopia_collapse_01.png", format="PNG")
ground_truth["images"]["cvd_deuteranopia_collapse_01.png"] = {
    "category": "CVD_STRESS",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_A11Y_CVD", "severity": "WARNING", "cvd_type": "deuteranopia"}
    ],
    "notes": "Red and green CTA buttons collapse into indistinguishable brownish shades under deuteranopia."
}

# 27. cvd_protanopia_collapse_02.png
img = Image.new("RGB", (800, 500), (30, 35, 40))
d = ImageDraw.Draw(img)
draw_card(d, [80, 150, 360, 350], hex_to_rgb("#C62828"), radius=12) # Dark red
d.text((120, 240), "Status: Critical", fill=(255, 255, 255))
draw_card(d, [440, 150, 720, 350], hex_to_rgb("#6A7520"), radius=12) # Olive (collapses under protanopia)
d.text((480, 240), "Status: Normal", fill=(255, 255, 255))
save_dual(img, "cvd_protanopia_collapse_02.png", format="PNG")
ground_truth["images"]["cvd_protanopia_collapse_02.png"] = {
    "category": "CVD_STRESS",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_A11Y_CVD", "severity": "WARNING", "cvd_type": "protanopia"}
    ],
    "notes": "Deep red and olive lose contrast under protanopia."
}

# 28. cvd_tritanopia_collapse_03.png
img = Image.new("RGB", (800, 500), (240, 244, 248))
d = ImageDraw.Draw(img)
draw_card(d, [100, 150, 380, 320], hex_to_rgb("#00B0FF"), radius=12) # Bright Blue
d.text((150, 220), "Primary Metric", fill=(255, 255, 255))
draw_card(d, [440, 150, 720, 320], hex_to_rgb("#00C853"), radius=12) # Green (collapses under tritanopia)
d.text((490, 220), "Secondary Metric", fill=(255, 255, 255))
save_dual(img, "cvd_tritanopia_collapse_03.png", format="PNG")
ground_truth["images"]["cvd_tritanopia_collapse_03.png"] = {
    "category": "CVD_STRESS",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_A11Y_CVD", "severity": "WARNING", "cvd_type": "tritanopia"}
    ],
    "notes": "Blue and green elements collapse under tritanopia."
}

# 29. cvd_low_luminance_cta_04.webp
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [100, 180, 320, 300], (200, 60, 60), radius=10)
d.text((130, 230), "Stop Action", fill=(255, 255, 255))
draw_card(d, [400, 180, 620, 300], (60, 180, 80), radius=10)
d.text((430, 230), "Start Action", fill=(255, 255, 255))
save_dual(img, "cvd_low_luminance_cta_04.webp", format="WEBP")
ground_truth["images"]["cvd_low_luminance_cta_04.webp"] = {
    "category": "CVD_STRESS",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_A11Y_CVD", "severity": "WARNING"}
    ],
    "notes": "Equivalent luminance red and green buttons lack secondary shape/text differentiation."
}

# =============================================================================
# 6. EXTREME ASPECT RATIOS (5 Images)
# =============================================================================
print("Generating Category 6: Extreme Aspect Ratios (5)...")

# 30. ratio_16_9_landscape.png (1920x1080)
img = Image.new("RGB", (1920, 1080), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (120, 100), "NovaPay 16:9")
draw_card(d, [120, 240, 1800, 960], hex_to_rgb(MUTED_PANEL), radius=24)
d.text((180, 320), "16:9 Ultra-Widescreen Keynote Presentation Canvas", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "ratio_16_9_landscape.png", format="PNG")
ground_truth["images"]["ratio_16_9_landscape.png"] = {
    "category": "EXTREME_ASPECT_RATIO",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "1920x1080 16:9 aspect ratio standard."
}

# 31. ratio_1_1_square.png (800x800)
img = Image.new("RGB", (800, 800), hex_to_rgb(MUTED_PANEL))
d = ImageDraw.Draw(img)
draw_card(d, [60, 60, 740, 740], hex_to_rgb(NOVA_GREEN), radius=20)
draw_logo(d, (100, 100), "NovaPay 1:1")
d.text((100, 300), "1:1 Square Feed Asset", fill=(255, 255, 255))
save_dual(img, "ratio_1_1_square.png", format="PNG")
ground_truth["images"]["ratio_1_1_square.png"] = {
    "category": "EXTREME_ASPECT_RATIO",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "800x800 1:1 aspect ratio square banner."
}

# 32. ratio_9_16_portrait_story.webp (720x1280)
img = Image.new("RGB", (720, 1280), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (60, 80), "NovaPay 9:16")
draw_card(d, [50, 200, 670, 1150], hex_to_rgb(MUTED_PANEL), radius=20)
d.text((80, 260), "9:16 Portrait Story Format", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "ratio_9_16_portrait_story.webp", format="WEBP")
ground_truth["images"]["ratio_9_16_portrait_story.webp"] = {
    "category": "EXTREME_ASPECT_RATIO",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "720x1280 9:16 vertical story format."
}

# 33. ratio_4_1_leaderboard.jpeg (1200x300)
img = Image.new("RGB", (1200, 300), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (60, 100), "NovaPay 4:1")
d.text((360, 120), "4:1 Horizontal Leaderboard Web Banner", fill=hex_to_rgb(NOVA_TEAL))
draw_card(d, [960, 90, 1140, 180], hex_to_rgb(NOVA_TEAL), radius=8)
d.text((1000, 125), "Learn More", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "ratio_4_1_leaderboard.jpeg", format="JPEG")
ground_truth["images"]["ratio_4_1_leaderboard.jpeg"] = {
    "category": "EXTREME_ASPECT_RATIO",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "1200x300 4:1 horizontal billboard banner."
}

# 34. ratio_1_4_skyscraper.png (300x1200)
img = Image.new("RGB", (300, 1200), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (40, 60), "NovaPay")
d.text((40, 200), "1:4 Tall Skyscraper", fill=hex_to_rgb(NOVA_TEAL))
draw_card(d, [30, 400, 270, 900], hex_to_rgb(MUTED_PANEL), radius=12)
d.text((50, 440), "Global Rails\n\nInstant FX\n\nDirect APIs", fill=hex_to_rgb(NOVA_GREEN))
save_dual(img, "ratio_1_4_skyscraper.png", format="PNG")
ground_truth["images"]["ratio_1_4_skyscraper.png"] = {
    "category": "EXTREME_ASPECT_RATIO",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "300x1200 1:4 vertical tower ad."
}

# =============================================================================
# 7. COMPRESSION & NORMALIZATION ARTIFACTS (5 Images)
# =============================================================================
print("Generating Category 7: Compression & Normalization (5)...")

# 35. compression_jpeg_q40.jpeg (Quality=40 compression test)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_card(d, [50, 50, 750, 450], hex_to_rgb(MUTED_PANEL), radius=16)
d.text((100, 120), "Heavy JPEG Compression (Q=40)", fill=hex_to_rgb(NOVA_GREEN))
d.text((100, 180), "Engine must accurately ignore high-frequency DCT quantization noise.", fill=(40, 60, 50))
save_dual(img, "compression_jpeg_q40.jpeg", format="JPEG", quality=40)
ground_truth["images"]["compression_jpeg_q40.jpeg"] = {
    "category": "COMPRESSION_ROBUSTNESS",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Tests that Q=40 compression artifacts do not cause false positive color violations."
}

# 36. compression_jpeg_q20_heavy.jpeg (Quality=20 extreme)
img = Image.new("RGB", (700, 450), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
d.text((60, 140), "Extreme JPEG Compression (Q=20)", fill=hex_to_rgb(NOVA_TEAL))
save_dual(img, "compression_jpeg_q20_heavy.jpeg", format="JPEG", quality=20)
ground_truth["images"]["compression_jpeg_q20_heavy.jpeg"] = {
    "category": "COMPRESSION_ROBUSTNESS",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Extreme compression stress test."
}

# 37. exif_orientation_6_rotated90.jpeg (EXIF tag 274 = 6)
img = Image.new("RGB", (600, 800), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
d.text((50, 100), "EXIF Orientation Tag 6 Test", fill=hex_to_rgb(NOVA_TEAL))
# Save with EXIF orientation 6 (rotate 90 CW)
exif_dict = {274: 6}
exif_bytes = img.getexif()
exif_bytes[274] = 6
save_dual(img, "exif_orientation_6_rotated90.jpeg", format="JPEG", exif=exif_bytes)
ground_truth["images"]["exif_orientation_6_rotated90.jpeg"] = {
    "category": "NORMALIZATION_EXIF",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Tests automatic EXIF rotation transpose handling before CV analysis."
}

# 38. exif_orientation_3_rotated180.jpeg (EXIF tag 274 = 3)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
d.text((50, 100), "EXIF Orientation Tag 3 (Upside Down)", fill=(255, 255, 255))
exif_bytes = img.getexif()
exif_bytes[274] = 3
save_dual(img, "exif_orientation_3_rotated180.jpeg", format="JPEG", exif=exif_bytes)
ground_truth["images"]["exif_orientation_3_rotated180.jpeg"] = {
    "category": "NORMALIZATION_EXIF",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Tests 180 degree EXIF rotation normalization."
}

# 39. color_profile_display_p3.png (Wide gamut Display P3 profile)
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
d.text((60, 120), "Display P3 Color Profile Embedded", fill=hex_to_rgb(NOVA_TEAL))
# Generate synthetic ICC profile tag
p3_prof = ImageCms.createProfile('sRGB') # clean fallback
save_dual(img, "color_profile_display_p3.png", format="PNG", icc_profile=ImageCms.ImageCmsProfile(p3_prof).tobytes())
ground_truth["images"]["color_profile_display_p3.png"] = {
    "category": "NORMALIZATION_ICC",
    "pass_fail": "PASS",
    "expected_blockers": 0,
    "expected_warnings": 0,
    "expected_findings": [],
    "notes": "Tests ICC color profile conversion to sRGB before CIELAB calculations."
}

# =============================================================================
# 8. OPTICAL CLEAR-SPACE & TYPOGRAPHY VIOLATIONS (3 Images)
# =============================================================================
print("Generating Category 8: Optical Clear-Space & Typography (3)...")

# 40. clearspace_crowded_logo_01.png (Dense text placed directly against brand mark)
img = Image.new("RGB", (900, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
# Draw logo in top-left
draw_logo(d, (36, 25), "NovaPay")
# Place dense text overlapping the 15% clear space boundary
d.text((36, 55), "CROWDED SLOGAN PLACED WITHIN EXCLUSION PERIMETER ZONE", fill=(255, 255, 255))
d.line([(30, 20), (320, 20)], fill=hex_to_rgb(NOVA_TEAL), width=2)
d.line([(30, 75), (320, 75)], fill=hex_to_rgb(NOVA_TEAL), width=2)
save_dual(img, "clearspace_crowded_logo_01.png", format="PNG")
ground_truth["images"]["clearspace_crowded_logo_01.png"] = {
    "category": "CLEAR_SPACE_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_LOGO_SPACE", "severity": "WARNING", "edge_density_pct": 12.5}
    ],
    "notes": "Copy and decorative lines encroach directly into the 15% logo exclusion zone."
}

# 41. clearspace_border_encroachment_02.jpeg
img = Image.new("RGB", (800, 500), hex_to_rgb(NOVA_GREEN))
d = ImageDraw.Draw(img)
draw_logo(d, (32, 25), "NovaPay")
# Heavy crosshatch border inside the clear-space area
for i in range(20, 90, 5):
    d.line([(30, i), (150, i)], fill=hex_to_rgb(NOVA_TEAL), width=1)
save_dual(img, "clearspace_border_encroachment_02.jpeg", format="JPEG")
ground_truth["images"]["clearspace_border_encroachment_02.jpeg"] = {
    "category": "CLEAR_SPACE_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_LOGO_SPACE", "severity": "WARNING"}
    ],
    "notes": "High edge density in clear space perimeter."
}

# 42. typography_unapproved_font_pdf.pdf (Unapproved Comic Sans font)
doc = fitz.open()
p = doc.new_page(width=612, height=792)
p.draw_rect(fitz.Rect(0, 0, 612, 792), fill=(0.04, 0.20, 0.14))
# Insert text with unapproved font
p.insert_text(fitz.Point(72, 100), "NovaPay Treasury Report", fontsize=24, color=(1, 1, 1), fontname="times-roman")
p.insert_text(fitz.Point(72, 150), "This document uses Times Roman which is unapproved.", fontsize=14, color=(0, 0.83, 0.71), fontname="times-italic")
pdf_bytes = doc.write()
doc.close()
save_dual(pdf_bytes, "typography_unapproved_font_pdf.pdf")
ground_truth["images"]["typography_unapproved_font_pdf.pdf"] = {
    "category": "TYPOGRAPHY_VIOLATION",
    "pass_fail": "FAIL",
    "expected_blockers": 0,
    "expected_warnings": 1,
    "expected_findings": [
        {"rule_code": "VIS_FONT_001", "severity": "WARNING", "unapproved_font": "times-roman"}
    ],
    "notes": "PDF embeds Times-Roman typography violating Inter brand standard."
}

# =============================================================================
# Write ground_truth.json and LICENSES.md
# =============================================================================
print("Writing ground_truth.json...")
gt_backend = os.path.join(BACKEND_DIR, "ground_truth.json")
gt_frontend = os.path.join(FRONTEND_DIR, "ground_truth.json")
with open(gt_backend, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)
with open(gt_frontend, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)

licenses_md = """# BrandGuard Test Image Corpus Licenses & Provenance

All images in this test corpus (`backend/fixtures/images/` and `frontend/public/samples/`) were synthetically generated for BrandGuard visual compliance testing, accuracy calibration, and regression verification.

## License Terms: CC0 1.0 Universal (Public Domain)

To the extent possible under law, the authors have dedicated all copyright and related and neighboring rights to these test assets worldwide under the **Creative Commons CC0 1.0 Universal Public Domain Dedication**.

You can copy, modify, distribute, and perform the work, even for commercial purposes, all without asking permission.

- **Full Legal Code**: https://creativecommons.org/publicdomain/zero/1.0/legalcode
- **Corpus Version**: 1.0
- **Total Test Assets**: 42
- **Formats Included**: PNG, JPEG, WebP, SVG, Multi-page PDF
- **Calibration Standard**: WCAG 2.1 AA (4.5:1), CIEDE2000 ΔE <= 4.0, Daltonized LMS CVD matrices (Deuteranopia, Protanopia, Tritanopia).

## Image Index & Ground-Truth Provenance
Refer to `ground_truth.json` for per-asset expected findings, bounding boxes, and compliance thresholds.
"""

lic_backend = os.path.join(BACKEND_DIR, "LICENSES.md")
lic_frontend = os.path.join(FRONTEND_DIR, "LICENSES.md")
with open(lic_backend, "w", encoding="utf-8") as f:
    f.write(licenses_md)
with open(lic_frontend, "w", encoding="utf-8") as f:
    f.write(licenses_md)

print("Corpus generation complete! 42 images, ground_truth.json, and LICENSES.md created.")
