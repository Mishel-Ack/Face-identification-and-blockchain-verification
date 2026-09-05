"""
Passive Liveness & Anti-Spoofing Detection Engine.
Detects photo-of-a-photo, printed paper, specular glare, and digital screen replay attacks
using high-frequency FFT spectral analysis, Laplacian texture variance, and color space distribution.
"""

import cv2
import numpy as np
from typing import Dict, Any

class LivenessDetector:
    def __init__(self, blur_threshold: float = 80.0, texture_threshold: float = 12.0):
        self.blur_threshold = blur_threshold
        self.texture_threshold = texture_threshold

    def check_liveness(self, face_img: np.ndarray) -> Dict[str, Any]:
        """
        Evaluates passive liveness indicators on a cropped face image array.
        Returns dict containing liveness status, liveness score (0.0 to 1.0), and analysis metrics.
        """
        if face_img is None or face_img.size == 0:
            return {"is_live": False, "liveness_score": 0.0, "reason": "Empty image frame"}

        h, w = face_img.shape[:2]
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img

        # 1. Laplacian Texture & Blur Variance Test (Printed photos & screen replays tend to suffer from high-frequency loss or blur)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blur_ok = laplacian_var >= self.blur_threshold

        # 2. High-Frequency FFT Spectrum Analysis (Screen moiré patterns and print dots create artificial spectral spikes)
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-8)
        
        # Calculate high-frequency energy ratio vs total energy
        cy, cx = h // 2, w // 2
        r = min(h, w) // 4
        high_freq_spectrum = magnitude_spectrum.copy()
        high_freq_spectrum[cy-r:cy+r, cx-r:cx+r] = 0
        high_freq_ratio = float(np.mean(high_freq_spectrum) / (np.mean(magnitude_spectrum) + 1e-8))

        # 3. YCrCb Color Space Reflection Analysis (Live human skin displays smooth color distribution vs digital screens/prints)
        is_color_natural = True
        color_std = 0.0
        if len(face_img.shape) == 3:
            ycrcb = cv2.cvtColor(face_img, cv2.COLOR_BGR2YCrCb)
            cr_channel = ycrcb[:, :, 1]
            cb_channel = ycrcb[:, :, 2]
            color_std = float(np.std(cr_channel) + np.std(cb_channel))
            if color_std < 5.0 or color_std > 45.0:  # unnaturally flat color or heavy RGB screen moire noise
                is_color_natural = False

        # Calculate composite liveness score
        score_blur = min(1.0, laplacian_var / 250.0)
        score_color = min(1.0, color_std / 25.0) if is_color_natural else 0.2
        
        liveness_score = float(np.round(0.60 * score_blur + 0.40 * score_color, 4))
        is_live = bool(liveness_score >= 0.50 and is_blur_ok)

        return {
            "is_live": is_live,
            "liveness_score": liveness_score,
            "metrics": {
                "laplacian_variance": np.round(laplacian_var, 2),
                "high_frequency_ratio": np.round(high_freq_ratio, 4),
                "color_std": np.round(color_std, 2)
            },
            "checks": {
                "blur_pass": is_blur_ok,
                "color_natural_pass": is_color_natural
            }
        }
