"""Pose utilities dùng chung cho module motion-compare.

- COCO-17 keypoint indices và tên.
- Skeleton edges (giống `yolo-tracking.py`).
- Hàm vẽ skeleton với màu theo per-joint accuracy.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


# COCO-17 keypoint indices
KP_NOSE = 0
KP_LEFT_EYE = 1
KP_RIGHT_EYE = 2
KP_LEFT_EAR = 3
KP_RIGHT_EAR = 4
KP_LEFT_SHOULDER = 5
KP_RIGHT_SHOULDER = 6
KP_LEFT_ELBOW = 7
KP_RIGHT_ELBOW = 8
KP_LEFT_WRIST = 9
KP_RIGHT_WRIST = 10
KP_LEFT_HIP = 11
KP_RIGHT_HIP = 12
KP_LEFT_KNEE = 13
KP_RIGHT_KNEE = 14
KP_LEFT_ANKLE = 15
KP_RIGHT_ANKLE = 16


KP_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


# Tên tiếng Việt cho feedback
KP_NAMES_VI = [
    "mũi", "mắt trái", "mắt phải", "tai trái", "tai phải",
    "vai trái", "vai phải", "khuỷu tay trái", "khuỷu tay phải",
    "cổ tay trái", "cổ tay phải", "hông trái", "hông phải",
    "đầu gối trái", "đầu gối phải", "cổ chân trái", "cổ chân phải",
]


SKELETON_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]


# Nhóm joint dùng cho UI breakdown
JOINT_GROUPS = [
    ("Đầu",       [KP_NOSE, KP_LEFT_EYE, KP_RIGHT_EYE, KP_LEFT_EAR, KP_RIGHT_EAR]),
    ("Vai",       [KP_LEFT_SHOULDER, KP_RIGHT_SHOULDER]),
    ("Khuỷu tay", [KP_LEFT_ELBOW, KP_RIGHT_ELBOW]),
    ("Cổ tay",    [KP_LEFT_WRIST, KP_RIGHT_WRIST]),
    ("Hông",      [KP_LEFT_HIP, KP_RIGHT_HIP]),
    ("Đầu gối",   [KP_LEFT_KNEE, KP_RIGHT_KNEE]),
    ("Cổ chân",   [KP_LEFT_ANKLE, KP_RIGHT_ANKLE]),
]


CONF_TH = 0.25  # ngưỡng confidence mặc định


def _as_int_tuple(xy):
    return int(round(float(xy[0]))), int(round(float(xy[1])))


def score_to_color(score: float) -> tuple[int, int, int]:
    """Map accuracy score (0-100) -> màu BGR.

    >=80: xanh lá; 50-80: vàng; <50: đỏ.
    """
    if score >= 80.0:
        return (60, 220, 60)
    if score >= 50.0:
        return (40, 200, 220)
    return (60, 60, 230)


def _avg_color(
    ca: tuple[int, int, int], cb: tuple[int, int, int]
) -> tuple[int, int, int]:
    return (
        (ca[0] + cb[0]) // 2,
        (ca[1] + cb[1]) // 2,
        (ca[2] + cb[2]) // 2,
    )


def draw_skeleton(
    im: np.ndarray,
    kpts_xy: np.ndarray,
    kpts_conf: Optional[np.ndarray] = None,
    base_color: tuple[int, int, int] = (255, 255, 255),
    joint_scores: Optional[np.ndarray] = None,
    kpt_radius: int = 5,
    conf_th: float = CONF_TH,
) -> None:
    """Vẽ skeleton lên ảnh với màu per-joint và cạnh gradient."""
    if kpts_xy is None or len(kpts_xy) == 0:
        return

    def ok(i: int) -> bool:
        if kpts_conf is None:
            return True
        return float(kpts_conf[i]) >= conf_th

    def color_for(i: int) -> tuple[int, int, int]:
        if (
            joint_scores is not None
            and i < len(joint_scores)
            and not np.isnan(joint_scores[i])
        ):
            return score_to_color(float(joint_scores[i]))
        return base_color

    # Edges – màu trung bình 2 đầu, nét dày hơn
    for a, b in SKELETON_EDGES:
        if ok(a) and ok(b):
            pa = _as_int_tuple((kpts_xy[a, 0], kpts_xy[a, 1]))
            pb = _as_int_tuple((kpts_xy[b, 0], kpts_xy[b, 1]))
            ec = _avg_color(color_for(a), color_for(b))
            cv2.line(im, pa, pb, ec, 3, cv2.LINE_AA)

    # Keypoints – vòng đen ngoài + màu bên trong
    for i in range(kpts_xy.shape[0]):
        if ok(i):
            p = _as_int_tuple((kpts_xy[i, 0], kpts_xy[i, 1]))
            c = color_for(i)
            cv2.circle(im, p, kpt_radius + 2, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(im, p, kpt_radius, c, -1, cv2.LINE_AA)


class PoseSmoother:
    """EMA temporal smoother – giảm jitter keypoints giữa các frame."""

    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = alpha
        self._smooth: Optional[np.ndarray] = None

    def update(
        self,
        kpts: np.ndarray,
        conf: np.ndarray,
        conf_th: float = CONF_TH,
    ) -> np.ndarray:
        if self._smooth is None:
            self._smooth = kpts.astype(np.float32).copy()
            return self._smooth.copy()
        a = self.alpha
        for i in range(len(kpts)):
            if float(conf[i]) >= conf_th:
                self._smooth[i] = a * kpts[i] + (1.0 - a) * self._smooth[i]
        return self._smooth.copy()

    def reset(self) -> None:
        self._smooth = None


def angle_between(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Góc tại p2 tạo bởi vector p2→p1 và p2→p3 (độ, 0-180)."""
    v1 = p1.astype(np.float32) - p2
    v2 = p3.astype(np.float32) - p2
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return float("nan")
    cos_a = np.dot(v1, v2) / (n1 * n2)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0))))


# (label, kp_a, kp_center, kp_b) – góc đo tại kp_center
ANGLE_DEFS: list[tuple[str, int, int, int]] = [
    ("Khuỷu P", KP_RIGHT_SHOULDER, KP_RIGHT_ELBOW,    KP_RIGHT_WRIST),
    ("Khuỷu T", KP_LEFT_SHOULDER,  KP_LEFT_ELBOW,     KP_LEFT_WRIST),
    ("Vai P",   KP_RIGHT_ELBOW,    KP_RIGHT_SHOULDER,  KP_RIGHT_HIP),
    ("Vai T",   KP_LEFT_ELBOW,     KP_LEFT_SHOULDER,   KP_LEFT_HIP),
    ("Gối P",   KP_RIGHT_HIP,      KP_RIGHT_KNEE,      KP_RIGHT_ANKLE),
    ("Gối T",   KP_LEFT_HIP,       KP_LEFT_KNEE,       KP_LEFT_ANKLE),
]

# kp index của joint trung tâm cho mỗi góc (để vẽ text)
ANGLE_CENTER_KP: dict[str, int] = {label: c for label, _, c, _ in ANGLE_DEFS}


def compute_angles(
    kpts: np.ndarray, conf: np.ndarray, conf_th: float = CONF_TH
) -> dict[str, float]:
    """Tính 6 góc khớp quan trọng từ keypoints pixel. Trả về {label: độ | nan}."""
    result: dict[str, float] = {}
    for label, i1, i2, i3 in ANGLE_DEFS:
        if conf[i1] >= conf_th and conf[i2] >= conf_th and conf[i3] >= conf_th:
            result[label] = angle_between(kpts[i1], kpts[i2], kpts[i3])
        else:
            result[label] = float("nan")
    return result


def draw_angles_overlay(
    im: np.ndarray,
    kpts: np.ndarray,
    conf: np.ndarray,
    user_angles: dict[str, float],
    ref_angles: dict[str, float] | None = None,
    conf_th: float = CONF_TH,
) -> None:
    """Vẽ số góc (°) và delta so với ref lên ảnh cạnh joint trung tâm."""
    for label, angle in user_angles.items():
        if np.isnan(angle):
            continue
        kp_idx = ANGLE_CENTER_KP.get(label)
        if kp_idx is None or conf[kp_idx] < conf_th:
            continue

        x, y = _as_int_tuple((kpts[kp_idx, 0], kpts[kp_idx, 1]))

        ref_a = ref_angles.get(label, float("nan")) if ref_angles else float("nan")
        if not np.isnan(ref_a):
            delta = angle - ref_a
            txt = f"{angle:.0f}\xb0 ({delta:+.0f}\xb0)"
            color = (60, 60, 230) if abs(delta) > 20 else (40, 200, 220) if abs(delta) > 10 else (60, 220, 60)
        else:
            txt = f"{angle:.0f}\xb0"
            color = (200, 200, 60)

        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        ox, oy = x + 8, y - 4
        cv2.rectangle(im, (ox - 2, oy - th - 2), (ox + tw + 2, oy + 3), (0, 0, 0), -1)
        cv2.putText(im, txt, (ox, oy), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)


def pick_best_person(boxes_xyxy: np.ndarray, kpts_conf: Optional[np.ndarray]) -> int:
    """Chọn 1 người mỗi frame (tổng confidence keypoints cao nhất).

    Trả về index trong arrays; mặc định 0 nếu chỉ có 1 người.
    """
    if boxes_xyxy is None or len(boxes_xyxy) == 0:
        return -1
    if len(boxes_xyxy) == 1 or kpts_conf is None:
        return 0
    sums = kpts_conf.sum(axis=1)
    return int(np.argmax(sums))
