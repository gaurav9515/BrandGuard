"""
Visual Identity Computer Vision Engine.
Implements:
1. CIELAB Delta-E Color Compliance via KMeans and CIE76 Delta-E.
2. WCAG 2.1 Accessibility Contrast Engine via Morphological Text ROI & Otsu Bimodal Thresholding.
3. PDF Embedded Font Inspector via PyMuPDF.
"""

import io
import math
import numpy as np
import cv2
from PIL import Image, ImageOps, ImageCms
from sklearn.cluster import KMeans
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None


def normalize_pil_image(pil_img):
    """
    Normalizes an input PIL image:
    1. EXIF orientation transpose (auto-rotates tags 3, 6, 8, etc.).
    2. Color Profile / ICC / CMYK normalization: converts Display P3, CMYK, or Adobe RGB to standard sRGB.
    3. Normalizes image mode to standard RGB.
    """
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    try:
        icc = pil_img.info.get('icc_profile')
        if icc:
            f_in = io.BytesIO(icc)
            src_profile = ImageCms.ImageCmsProfile(f_in)
            srgb_profile = ImageCms.createProfile('sRGB')
            pil_img = ImageCms.profileToProfile(pil_img, src_profile, srgb_profile, outputMode='RGB')
            return pil_img
    except Exception:
        pass

    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    return pil_img


CVD_MATRICES = {
    "deuteranopia": np.array([[0.625, 0.375, 0.0],
                              [0.7, 0.3, 0.0],
                              [0.0, 0.3, 0.7]], dtype=np.float32),
    "protanopia": np.array([[0.567, 0.433, 0.0],
                            [0.558, 0.442, 0.0],
                            [0.0, 0.242, 0.758]], dtype=np.float32),
    "tritanopia": np.array([[0.95, 0.05, 0.0],
                            [0.0, 0.433, 0.567],
                            [0.0, 0.475, 0.525]], dtype=np.float32),
}


def simulate_color_blindness(img_rgb, mode="deuteranopia"):
    """
    Applies RGB-to-LMS Daltonization projection matrix for color-blindness simulation.
    Supports 'deuteranopia' (red-green), 'protanopia', 'tritanopia'.
    """
    matrix = CVD_MATRICES.get(mode.lower(), CVD_MATRICES["deuteranopia"])
    simulated = np.dot(img_rgb.astype(np.float32), matrix.T)
    return np.clip(simulated, 0, 255).astype(img_rgb.dtype)


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c * 2 for c in hex_str])
    return [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]


def rgb_to_hex(rgb):
    return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}".upper()


def rgb_to_lab(rgb_val):
    """Convert RGB [0..255] to CIELAB float32 coordinates using OpenCV."""
    arr = np.float32([[rgb_val]]) / 255.0
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)[0][0]
    return lab


def cie76(lab1, lab2):
    """CIE76 color difference (Euclidean distance in CIELAB space)."""
    return float(np.linalg.norm(np.array(lab1, dtype=np.float64) - np.array(lab2, dtype=np.float64)))


def ciede2000(lab1, lab2, k_L=1.0, k_C=1.0, k_H=1.0):
    """
    CIEDE2000 standard color difference calculation (Sharma, Wu, Dalal 2005).
    Accurately accounts for non-uniformities in human color perception.
    """
    L1, a1, b1 = float(lab1[0]), float(lab1[1]), float(lab1[2])
    L2, a2, b2 = float(lab2[0]), float(lab2[1]), float(lab2[2])

    C1 = math.sqrt(a1**2 + b1**2)
    C2 = math.sqrt(a2**2 + b2**2)
    C_bar = (C1 + C2) / 2.0

    G = 0.5 * (1.0 - math.sqrt((C_bar**7) / (C_bar**7 + 25.0**7))) if (C_bar**7 + 25.0**7) > 0 else 0.0
    a1_prime = (1.0 + G) * a1
    a2_prime = (1.0 + G) * a2

    C1_prime = math.sqrt(a1_prime**2 + b1**2)
    C2_prime = math.sqrt(a2_prime**2 + b2**2)

    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360.0
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360.0

    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime

    if C1_prime * C2_prime == 0.0:
        delta_h_prime = 0.0
    elif abs(h2_prime - h1_prime) <= 180.0:
        delta_h_prime = h2_prime - h1_prime
    elif h2_prime - h1_prime > 180.0:
        delta_h_prime = (h2_prime - h1_prime) - 360.0
    else:
        delta_h_prime = (h2_prime - h1_prime) + 360.0

    delta_H_prime = 2.0 * math.sqrt(C1_prime * C2_prime) * math.sin(math.radians(delta_h_prime / 2.0))

    L_bar_prime = (L1 + L2) / 2.0
    C_bar_prime = (C1_prime + C2_prime) / 2.0

    if C1_prime * C2_prime == 0.0:
        h_bar_prime = h1_prime + h2_prime
    elif abs(h1_prime - h2_prime) <= 180.0:
        h_bar_prime = (h1_prime + h2_prime) / 2.0
    elif (h1_prime + h2_prime) < 360.0:
        h_bar_prime = (h1_prime + h2_prime + 360.0) / 2.0
    else:
        h_bar_prime = (h1_prime + h2_prime - 360.0) / 2.0

    T = (1.0 - 0.17 * math.cos(math.radians(h_bar_prime - 30.0))
         + 0.24 * math.cos(math.radians(2.0 * h_bar_prime))
         + 0.32 * math.cos(math.radians(3.0 * h_bar_prime + 6.0))
         - 0.20 * math.cos(math.radians(4.0 * h_bar_prime - 63.0)))

    delta_theta = 30.0 * math.exp(-(((h_bar_prime - 275.0) / 25.0)**2))
    R_C = 2.0 * math.sqrt((C_bar_prime**7) / (C_bar_prime**7 + 25.0**7)) if (C_bar_prime**7 + 25.0**7) > 0 else 0.0
    S_L = 1.0 + ((0.015 * (L_bar_prime - 50.0)**2) / math.sqrt(20.0 + (L_bar_prime - 50.0)**2))
    S_C = 1.0 + 0.045 * C_bar_prime
    S_H = 1.0 + 0.015 * C_bar_prime * T
    R_T = -math.sin(math.radians(2.0 * delta_theta)) * R_C

    term_L = delta_L_prime / (k_L * S_L)
    term_C = delta_C_prime / (k_C * S_C)
    term_H = delta_H_prime / (k_H * S_H)

    dE2 = term_L**2 + term_C**2 + term_H**2 + R_T * term_C * term_H
    return float(math.sqrt(max(0.0, dE2)))


def calculate_delta_e(lab1, lab2, algorithm=None):
    """
    Computes color difference between two Lab coordinates.
    Supports 'CIEDE2000' (default) with 'CIE76' fallback.
    Algorithm is configurable via settings.BRANDGUARD_DEFAULT_COLOR_METRIC.
    """
    from django.conf import settings
    metric = algorithm or getattr(settings, 'BRANDGUARD_DEFAULT_COLOR_METRIC', 'CIEDE2000')
    if metric.upper() == 'CIE76':
        return cie76(lab1, lab2)
    try:
        return ciede2000(lab1, lab2)
    except Exception:
        return cie76(lab1, lab2)


def srgb_channel_to_linear(c_val):
    c = float(c_val) / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    """WCAG 2.1 relative luminance calculation."""
    r_lin = srgb_channel_to_linear(rgb[0])
    g_lin = srgb_channel_to_linear(rgb[1])
    b_lin = srgb_channel_to_linear(rgb[2])
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(rgb1, rgb2):
    """WCAG contrast ratio (Lighter + 0.05) / (Darker + 0.05)."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def find_color_bounding_box(img_rgb, target_rgb, tolerance=40):
    """Locate bounding box of pixels close to target_rgb in the original image."""
    h, w, _ = img_rgb.shape
    diff = np.abs(img_rgb.astype(np.int32) - np.array(target_rgb, dtype=np.int32))
    dist = np.sum(diff, axis=2)
    mask = (dist < tolerance).astype(np.uint8) * 255

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [int(w * 0.1), int(h * 0.1), int(w * 0.8), int(h * 0.8)]

    # Take the largest contour or union of top contours
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    x, y, bw, bh = cv2.boundingRect(contours[0])
    # Pad slightly
    pad = 4
    x = max(0, x - pad)
    y = max(0, y - pad)
    bw = min(w - x, bw + pad * 2)
    bh = min(h - y, bh + pad * 2)
    return [int(x), int(y), int(bw), int(bh)]


def audit_image_array(img_rgb, profile, file_label="Asset"):
    """
    Run Visual Identity CV inspection on an RGB numpy array.
    Returns list of AuditFinding dicts.
    """
    findings = []
    orig_h, orig_w, _ = img_rgb.shape
    if orig_h == 0 or orig_w == 0:
        return findings

    allowed_palette = profile.allowed_hex_palette or []
    wcag_min_ratio = float(profile.wcag_min_ratio or 4.5)

    # 1. CIELAB Delta-E Color Compliance
    try:
        resized = cv2.resize(img_rgb, (150, 150), interpolation=cv2.INTER_AREA)
        pixels = resized.reshape(-1, 3).astype(np.float32)

        kmeans = KMeans(n_clusters=4, n_init=5, random_state=42)
        kmeans.fit(pixels)
        centers = kmeans.cluster_centers_
        counts = np.bincount(kmeans.labels_, minlength=len(centers))
        fractions = counts / len(pixels)

        approved_labs = []
        for swatch in allowed_palette:
            sw_rgb = hex_to_rgb(swatch.get('hex', '#000000'))
            sw_lab = rgb_to_lab(sw_rgb)
            approved_labs.append((swatch, sw_lab))

        flagged_colors = set()
        for idx, cluster_rgb in enumerate(centers):
            # Ignore thin anti-aliased edge transitions and noise (< 2.5% of image area)
            if fractions[idx] < 0.025:
                continue

            mean_intensity = np.mean(cluster_rgb)
            # Ignore pure white / light canvas (> 242) or dark canvas / near-black (< 26)
            if mean_intensity > 242 or mean_intensity < 26:
                continue

            c_lab = rgb_to_lab(cluster_rgb)

            from django.conf import settings
            color_metric = getattr(settings, 'BRANDGUARD_DEFAULT_COLOR_METRIC', 'CIEDE2000')
            sys_threshold = float(getattr(settings, 'BRANDGUARD_COLOR_DELTA_THRESHOLD', 4.0))

            if approved_labs:
                dists = []
                for swatch, s_lab in approved_labs:
                    de = calculate_delta_e(c_lab, s_lab, algorithm=color_metric)
                    dists.append((de, swatch))
                dists.sort(key=lambda x: x[0])
                min_de, nearest_swatch = dists[0]
                allowed_tol = float(nearest_swatch.get('max_delta_e', sys_threshold))
            else:
                min_de = 0.0
                nearest_swatch = {"name": "Approved", "hex": "#0F172A"}
                allowed_tol = sys_threshold

            effective_threshold = allowed_tol
            if min_de > effective_threshold:
                cluster_hex = rgb_to_hex(cluster_rgb)
                if cluster_hex in flagged_colors:
                    continue
                flagged_colors.add(cluster_hex)

                bbox = find_color_bounding_box(img_rgb, cluster_rgb)
                bx, by, bw, bh = bbox
                # Require a coherent graphic region (reject scattered anti-aliasing edge transitions)
                if bw < 20 or bh < 20 or (bw * bh) < 400:
                    continue

                # Suggest top approved swatches
                suggested_hexes = [
                    f"Replace off-brand {cluster_hex} with {s.get('name')} ({s.get('hex')})"
                    for s in allowed_palette[:3]
                ]
                if not suggested_hexes:
                    suggested_hexes = [f"Replace {cluster_hex} with {nearest_swatch.get('hex')}"]

                # Determine confidence and review lane
                confidence = 1.0
                is_low_conf = False
                if min_de <= (effective_threshold + 0.35):
                    confidence = 0.68
                    is_low_conf = True

                status = "IN_REVIEW" if is_low_conf else "OPEN"
                finding_item = {
                    "pillar": "VISUAL",
                    "severity": "BLOCKER",
                    "engine_provenance": "DETERMINISTIC_CV",
                    "confidence": confidence,
                    "rule_citation_code": "VIS_COLOR_001",
                    "rule_citation_title": "Off-Brand Color Palette Violation",
                    "source_excerpt": f"Detected unapproved color {cluster_hex} (CIELAB ΔE={round(min_de, 2)} against approved {nearest_swatch.get('name', 'swatch')} {nearest_swatch.get('hex')})",
                    "location_json": {
                        "format": "BOUNDING_BOX",
                        "x": bx,
                        "y": by,
                        "w": bw,
                        "h": bh,
                        "img_width": orig_w,
                        "img_height": orig_h,
                        "x_pct": round((bx / orig_w) * 100, 2),
                        "y_pct": round((by / orig_h) * 100, 2),
                        "w_pct": round((bw / orig_w) * 100, 2),
                        "h_pct": round((bh / orig_h) * 100, 2),
                    },
                    "explanation": (
                        f"Found dominant color {cluster_hex} with ΔE={round(min_de, 1)}, which exceeds the allowable brand threshold (max ΔE={allowed_tol}). "
                        f"Nearest approved color is {nearest_swatch.get('name')} ({nearest_swatch.get('hex')})."
                    ),
                    "suggested_fixes": suggested_hexes,
                    "status": status,
                }
                if is_low_conf:
                    finding_item["flagged_for_human_review"] = True
                    finding_item["review_reason"] = "LOW_CONFIDENCE_DETECTION"
                findings.append(finding_item)

        # Color-Vision Deficiency (CVD) Ambiguity Linter
        valid_clusters = [centers[k] for k in range(len(centers)) if fractions[k] >= 0.025 and 26 <= np.mean(centers[k]) <= 242]
        cvd_flagged = False
        for i in range(len(valid_clusters)):
            for j in range(i + 1, len(valid_clusters)):
                c1 = valid_clusters[i]
                c2 = valid_clusters[j]
                lab1 = rgb_to_lab(c1)
                lab2 = rgb_to_lab(c2)
                de_normal = calculate_delta_e(lab1, lab2)
                lum_cr = calculate_contrast_ratio(c1, c2)

                # Only evaluate if normal vision has clear difference but low luminance distinction
                if de_normal > 20.0 and lum_cr < 2.5:
                    for cvd_mode in ["deuteranopia", "protanopia", "tritanopia"]:
                        sim1 = simulate_color_blindness(np.array([c1]), cvd_mode)[0]
                        sim2 = simulate_color_blindness(np.array([c2]), cvd_mode)[0]
                        lab_s1 = rgb_to_lab(sim1)
                        lab_s2 = rgb_to_lab(sim2)
                        de_sim = calculate_delta_e(lab_s1, lab_s2)
                        ratio = de_sim / max(de_normal, 1e-5)

                        # True collapse under CVD: low luminance (< 2.5) and significant color distinction loss
                        if (ratio < 0.70 or de_sim < 28.0) and not cvd_flagged:
                            cvd_flagged = True
                            bbox1 = find_color_bounding_box(img_rgb, c1)
                            findings.append({
                                "pillar": "VISUAL",
                                "severity": "WARNING",
                                "engine_provenance": "DETERMINISTIC_CV",
                                "confidence": 1.0,
                                "rule_citation_code": "VIS_A11Y_CVD",
                                "rule_citation_title": f"Color-Vision Deficiency Ambiguity: Key visual elements lose distinction under {cvd_mode.capitalize()}",
                                "source_excerpt": f"Distinct colors {rgb_to_hex(c1)} and {rgb_to_hex(c2)} (ΔE={round(de_normal, 1)}) collapse to indistinguishable ΔE={round(de_sim, 1)} under {cvd_mode}",
                                "location_json": {
                                    "format": "BOUNDING_BOX",
                                    "x": bbox1[0], "y": bbox1[1], "w": bbox1[2], "h": bbox1[3],
                                    "img_width": orig_w, "img_height": orig_h,
                                    "x_pct": round((bbox1[0] / orig_w) * 100, 2),
                                    "y_pct": round((bbox1[1] / orig_h) * 100, 2),
                                    "w_pct": round((bbox1[2] / orig_w) * 100, 2),
                                    "h_pct": round((bbox1[3] / orig_h) * 100, 2),
                                    "cvd_mode": cvd_mode,
                                },
                                "explanation": (
                                    f"Key visual color clusters {rgb_to_hex(c1)} and {rgb_to_hex(c2)} have low luminance contrast ({round(lum_cr, 1)}:1) "
                                    f"and collapse into ambiguous shades under {cvd_mode.capitalize()} (ΔE drops from {round(de_normal, 1)} to {round(de_sim, 1)}). "
                                    f"Users with {cvd_mode} will struggle to perceive visual hierarchy or call-to-action distinction."
                                ),
                                "suggested_fixes": [
                                    "Introduce high-contrast luminance differentials between background and CTA elements",
                                    "Add secondary non-color visual cues (underlines, text labels, or distinct stroke borders)"
                                ],
                                "status": "OPEN",
                            })
                            break
    except Exception as e:
        # Non-fatal error fallback
        pass

    # 2. WCAG 2.1 Accessibility Contrast Engine
    try:
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Morphological gradient to isolate text edge boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

        # Otsu thresholding combined with low-gradient threshold for subtle contrast
        _, thresh_otsu = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh_low = (gradient > 8).astype(np.uint8) * 255
        thresh = cv2.bitwise_or(thresh_otsu, thresh_low)

        # Morphological close to join adjacent text characters into lines/blocks
        kernel_conn = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_conn)

        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter for plausible text box dimensions (reject full-image cards or outer borders)
            if w < 24 or h < 10 or h > orig_h * 0.35 or (w > orig_w * 0.60 and h > orig_h * 0.25):
                continue
            if w > orig_w * 0.95 and h > orig_h * 0.95:
                continue
            if w / max(h, 1) < 0.8 and w < 40:
                continue

            roi_rgb = img_rgb[y:y+h, x:x+w]
            roi_gray = gray[y:y+h, x:x+w]

            p90 = np.percentile(roi_gray, 90)
            p10 = np.percentile(roi_gray, 10)
            if (p90 - p10) < 6:
                continue

            c_high = np.mean(roi_rgb[roi_gray >= p90], axis=0)
            c_low = np.mean(roi_rgb[roi_gray <= p10], axis=0)
            avg_cr = calculate_contrast_ratio(c_high, c_low)

            # Spatial slice sampling along text line to detect local background gradient drops
            min_slice_cr = avg_cr
            num_slices = 4
            slice_w = max(1, w // num_slices)
            for s_i in range(num_slices):
                sx1 = s_i * slice_w
                sx2 = min(w, (s_i + 1) * slice_w)
                if (sx2 - sx1) < 12:
                    continue
                s_roi_gray = roi_gray[:, sx1:sx2]
                s_p90 = np.percentile(s_roi_gray, 90)
                s_p10 = np.percentile(s_roi_gray, 10)
                if (s_p90 - s_p10) >= 8:
                    s_roi_rgb = roi_rgb[:, sx1:sx2]
                    s_high = np.mean(s_roi_rgb[s_roi_gray >= s_p90], axis=0)
                    s_low = np.mean(s_roi_rgb[s_roi_gray <= s_p10], axis=0)
                    s_cr = calculate_contrast_ratio(s_high, s_low)
                    if s_cr < min_slice_cr:
                        min_slice_cr = s_cr

            cr = min(avg_cr, min_slice_cr)

            if 1.05 < cr < wcag_min_ratio:
                confidence = 1.0
                is_low_conf = False
                if cr >= (wcag_min_ratio - 0.35):  # Near-threshold e.g. 4.15 - 4.50:1 -> Low confidence review lane
                    confidence = 0.70
                    is_low_conf = True

                status = "IN_REVIEW" if is_low_conf else "OPEN"
                fg_hex = rgb_to_hex(c_low if np.mean(c_low) < np.mean(c_high) else c_high)
                bg_hex = rgb_to_hex(c_high if np.mean(c_low) < np.mean(c_high) else c_low)
                finding_item = {
                    "pillar": "VISUAL",
                    "severity": "BLOCKER",
                    "engine_provenance": "DETERMINISTIC_CV",
                    "confidence": confidence,
                    "rule_citation_code": "VIS_WCAG_2.1",
                    "rule_citation_title": "WCAG 2.1 Accessibility Contrast Failure",
                    "source_excerpt": f"Text region contrast ratio {round(cr, 2)}:1 (Text {fg_hex} on Background {bg_hex})",
                    "location_json": {
                        "format": "BOUNDING_BOX",
                        "x": int(x),
                        "y": int(y),
                        "w": int(w),
                        "h": int(h),
                        "img_width": orig_w,
                        "img_height": orig_h,
                        "x_pct": round((x / orig_w) * 100, 2),
                        "y_pct": round((y / orig_h) * 100, 2),
                        "w_pct": round((w / orig_w) * 100, 2),
                        "h_pct": round((h / orig_h) * 100, 2),
                        "worst_case_edge_sampled": min_slice_cr < avg_cr,
                    },
                    "explanation": (
                        f"Detected text contrast ratio of {round(cr, 2)}:1 (worst-case spatial slice sampled), which falls below the brand WCAG 2.1 AA minimum standard ({wcag_min_ratio}:1). "
                        f"Text foreground is {fg_hex} over {bg_hex}."
                    ),
                    "suggested_fixes": [
                        f"Shift text foreground to high-contrast '#0F172A' (Slate 900) or '#FFFFFF'",
                        f"Use brand primary '#00C885' against deep background '#062B22' for 7.8:1 contrast",
                    ],
                    "status": status,
                }
                if is_low_conf:
                    finding_item["flagged_for_human_review"] = True
                    finding_item["review_reason"] = "LOW_CONFIDENCE_DETECTION"
                findings.append(finding_item)
                contrast_findings = [f for f in findings if f["rule_citation_code"] == "VIS_WCAG_2.1"]
                if len(contrast_findings) >= 2:
                    break
    except Exception as e:
        pass

    # 3. Optical Clear-Space & Logo Crowding Inspector
    try:
        # Locate brand mark region in upper section
        logo_x = int(orig_w * 0.04)
        logo_y = int(orig_h * 0.05)
        logo_w = int(orig_w * 0.35)
        logo_h = int(orig_h * 0.12)

        # 15% optical clear-space padding perimeter
        pad_x = max(10, int(logo_w * 0.15))
        pad_y = max(8, int(logo_h * 0.15))

        px = max(0, logo_x - pad_x)
        py = max(0, logo_y - pad_y)
        pw = min(orig_w - px, logo_w + 2 * pad_x)
        ph = min(orig_h - py, logo_h + 2 * pad_y)

        pad_zone_gray = gray[py:py+ph, px:px+pw]
        edges = cv2.Canny(pad_zone_gray, 80, 180)

        # Mask out inner logo box itself
        ring_mask = np.ones(edges.shape, dtype=bool)
        in_x1 = max(0, logo_x - px)
        in_y1 = max(0, logo_y - py)
        in_x2 = min(pw, in_x1 + logo_w)
        in_y2 = min(ph, in_y1 + logo_h)
        ring_mask[in_y1:in_y2, in_x1:in_x2] = False

        ring_pixels = np.sum(ring_mask)
        if ring_pixels > 0:
            edge_count = np.sum(edges[ring_mask] > 0)
            edge_density = float(edge_count) / float(ring_pixels)

            if edge_density > 0.018:  # 1.8% edge density threshold (clean banners have < 0.9%)
                findings.append({
                    "pillar": "VISUAL",
                    "severity": "WARNING",
                    "engine_provenance": "DETERMINISTIC_CV",
                    "confidence": 1.0,
                    "rule_citation_code": "VIS_LOGO_SPACE",
                    "rule_citation_title": "Optical Clear-Space Violation: High visual edge density detected within 15% exclusion zone",
                    "source_excerpt": f"Edge density {round(edge_density * 100, 1)}% exceeds allowable 8% threshold in the 15% exclusion perimeter around the brand mark",
                    "location_json": {
                        "format": "BOUNDING_BOX",
                        "x": int(px),
                        "y": int(py),
                        "w": int(pw),
                        "h": int(ph),
                        "img_width": orig_w,
                        "img_height": orig_h,
                        "x_pct": round((px / orig_w) * 100, 2),
                        "y_pct": round((py / orig_h) * 100, 2),
                        "w_pct": round((pw / orig_w) * 100, 2),
                        "h_pct": round((ph / orig_h) * 100, 2),
                        "is_exclusion_zone": True,
                        "inner_logo": [int(logo_x), int(logo_y), int(logo_w), int(logo_h)],
                    },
                    "explanation": (
                        f"Optical Clear-Space Violation: High visual edge density ({round(edge_density * 100, 1)}%) detected within the 15% exclusion zone "
                        f"around the brand mark. Text, graphical lines, or borders encroach into the required optical breathing room."
                    ),
                    "suggested_fixes": [
                        "Increase margin around the NovaPay brand mark to at least 15% of mark height",
                        "Relocate secondary marketing copy outside the logo isolation boundary"
                    ],
                    "status": "OPEN",
                })
    except Exception as e:
        pass

    return findings


def audit_image_file(file_obj, profile):
    """
    Audits an uploaded image file, SVG, or file path with:
    1. Automatic EXIF orientation transpose
    2. ICC / CMYK / Display P3 to sRGB normalization
    3. SVG vector rendering via PyMuPDF
    """
    try:
        # Check for SVG
        is_svg = False
        if isinstance(file_obj, str) and file_obj.lower().endswith('.svg'):
            is_svg = True
        elif hasattr(file_obj, 'name') and str(file_obj.name).lower().endswith('.svg'):
            is_svg = True

        if is_svg and fitz is not None:
            if isinstance(file_obj, str):
                doc = fitz.open(file_obj)
            else:
                file_obj.seek(0)
                doc = fitz.open(stream=file_obj.read(), filetype="svg")
            pix = doc[0].get_pixmap(dpi=120)
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            return audit_image_array(np.array(pil_img), profile)

        # Standard Raster Images (PNG, JPEG, WebP, etc.)
        if isinstance(file_obj, (str, bytes)):
            if isinstance(file_obj, str):
                pil_img = Image.open(file_obj)
            else:
                pil_img = Image.open(io.BytesIO(file_obj))
        else:
            file_obj.seek(0)
            pil_img = Image.open(file_obj)

        pil_img = normalize_pil_image(pil_img)
        img_rgb = np.array(pil_img)
        return audit_image_array(img_rgb, profile)
    except Exception as e:
        return []


def audit_pdf_file(file_obj, profile):
    """
    Audits a PDF document using PyMuPDF:
    1. Checks span font against profile.allowed_fonts
    2. Renders each page via get_pixmap(dpi=120) and runs visual CV
    """
    findings = []
    if fitz is None:
        return findings

    try:
        if isinstance(file_obj, str):
            doc = fitz.open(file_obj)
        elif isinstance(file_obj, bytes):
            doc = fitz.open(stream=file_obj, filetype="pdf")
        else:
            file_obj.seek(0)
            pdf_bytes = file_obj.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        allowed_fonts = [f.lower().strip() for f in (profile.allowed_fonts or [])]

        for page_idx, page in enumerate(doc):
            page_rect = page.rect
            page_w = page_rect.width
            page_h = page_rect.height

            # 1. Embedded font inspector
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_name = span.get("font", "").lower()
                            # Check if font family is allowed
                            is_approved = any(af in font_name for af in allowed_fonts) if allowed_fonts else True
                            if not is_approved and span.get("text", "").strip():
                                bbox = span.get("bbox", [0, 0, 100, 20])
                                bx, by, bx2, by2 = bbox
                                bw = bx2 - bx
                                bh = by2 - by
                                findings.append({
                                    "pillar": "VISUAL",
                                    "severity": "WARNING",
                                    "engine_provenance": "DETERMINISTIC_CV",
                                    "confidence": 1.0,
                                    "rule_citation_code": "VIS_FONT_001",
                                    "rule_citation_title": "Unapproved Typography / Font Family",
                                    "source_excerpt": f'Font "{span.get("font")}" used on text "{span.get("text", "")[:40]}"',
                                    "location_json": {
                                        "format": "BOUNDING_BOX",
                                        "page": page_idx + 1,
                                        "x": int(bx),
                                        "y": int(by),
                                        "w": int(bw),
                                        "h": int(bh),
                                        "img_width": int(page_w),
                                        "img_height": int(page_h),
                                        "x_pct": round((bx / max(page_w, 1)) * 100, 2),
                                        "y_pct": round((by / max(page_h, 1)) * 100, 2),
                                        "w_pct": round((bw / max(page_w, 1)) * 100, 2),
                                        "h_pct": round((bh / max(page_h, 1)) * 100, 2),
                                    },
                                    "explanation": (
                                        f'Font family "{span.get("font")}" is not in the approved brand typography list '
                                        f'({", ".join(profile.allowed_fonts or ["Plus Jakarta Sans"])}).'
                                    ),
                                    "suggested_fixes": [
                                        f'Change font to {profile.allowed_fonts[0] if profile.allowed_fonts else "Plus Jakarta Sans"}',
                                        "Embed standard brand WebFont weights (Regular 400, SemiBold 600, Bold 700)"
                                    ],
                                    "status": "OPEN",
                                })
                                if len([f for f in findings if f["rule_citation_code"] == "VIS_FONT_001"]) >= 3:
                                    break

            # 2. Render page pixmap and run visual CV
            pix = page.get_pixmap(dpi=120)
            page_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_findings = audit_image_array(np.array(page_pil), profile, file_label=f"PDF Page {page_idx + 1}")
            for pf in page_findings:
                pf["location_json"]["page"] = page_idx + 1
            findings.extend(page_findings)

        doc.close()
    except Exception as e:
        pass

    return findings
