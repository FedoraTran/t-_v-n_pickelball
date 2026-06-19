"""Sinh feedback tiếng Việt cho người dùng.

Ưu tiên:
1. Angle-based: so sánh góc khớp user vs reference (cụ thể hơn, dễ sửa hơn).
2. Position-based: joint có score thấp nhất kèm hướng cần dịch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pose_utils import KP_NAMES_VI

_NEEDS_FIX_TH  = 70.0
_MIN_OFFSET_N  = 0.08   # 8% torso (đơn vị normalized)
_ANGLE_TH_WARN = 15.0   # delta ° để báo cần sửa
_ANGLE_TH_BAD  = 25.0   # delta ° nghiêm trọng


def _direction_phrase(dx_n: float, dy_n: float) -> str:
    parts: list[str] = []
    if abs(dy_n) >= _MIN_OFFSET_N:
        parts.append("nâng cao hơn" if dy_n > 0 else "hạ thấp hơn")
    if abs(dx_n) >= _MIN_OFFSET_N:
        parts.append("dịch sang trái" if dx_n > 0 else "dịch sang phải")
    return ", ".join(parts) if parts else "điều chỉnh nhẹ"


def _angle_feedback(
    user_angles: dict[str, float],
    ref_angles:  dict[str, float],
    max_msgs: int,
) -> list[str]:
    """Tạo feedback dựa trên delta góc giữa user và ref."""
    candidates: list[tuple[float, str]] = []
    for label in user_angles:
        ua = user_angles[label]
        ra = ref_angles.get(label, float("nan"))
        if np.isnan(ua) or np.isnan(ra):
            continue
        delta = ua - ra          # dương = user mở góc hơn ref (cần gập lại)
        if abs(delta) < _ANGLE_TH_WARN:
            continue
        action = "gập lại hơn" if delta > 0 else "duỗi ra hơn"
        severity = "!" if abs(delta) >= _ANGLE_TH_BAD else ""
        msg = f"{label}{severity}: {action} ({ua:.0f}° → {ra:.0f}°)"
        candidates.append((abs(delta), msg))

    candidates.sort(reverse=True)
    return [m for _, m in candidates[:max_msgs]]


def generate_feedback(
    per_joint: np.ndarray,
    joint_offset: np.ndarray,
    torso_px: float = 0.0,       # không dùng, giữ để tương thích
    top_k: int = 3,
    user_angles: dict[str, float] | None = None,
    ref_angles:  dict[str, float] | None = None,
) -> list[str]:
    """Trả về danh sách feedback tiếng Việt (tối đa top_k câu)."""
    del torso_px
    msgs: list[str] = []

    # 1. Angle-based (ưu tiên cao nhất – tối đa 2 câu)
    if user_angles and ref_angles:
        msgs.extend(_angle_feedback(user_angles, ref_angles, max_msgs=2))

    # 2. Position-based để lấp các slot còn lại
    remaining = top_k - len(msgs)
    if remaining > 0 and per_joint is not None and len(per_joint) > 0:
        valid_idx = [i for i in range(len(per_joint)) if not np.isnan(per_joint[i])]
        bad = sorted(
            [(i, float(per_joint[i])) for i in valid_idx if per_joint[i] < _NEEDS_FIX_TH],
            key=lambda t: t[1],
        )
        for i, score in bad[:remaining]:
            name = KP_NAMES_VI[i] if i < len(KP_NAMES_VI) else f"joint {i}"
            direction = _direction_phrase(float(joint_offset[i, 0]), float(joint_offset[i, 1]))
            msgs.append(f"{name.capitalize()}: {direction} ({score:.0f}%)")

    return msgs if msgs else ["Tư thế tốt, giữ nguyên nhịp."]


def estimate_torso_px(kpts: np.ndarray, conf: np.ndarray, conf_th: float = 0.25) -> float:
    from pose_utils import KP_LEFT_HIP, KP_LEFT_SHOULDER, KP_RIGHT_HIP, KP_RIGHT_SHOULDER

    def ok(i):
        return conf[i] >= conf_th

    if ok(KP_LEFT_SHOULDER) and ok(KP_RIGHT_SHOULDER) and ok(KP_LEFT_HIP) and ok(KP_RIGHT_HIP):
        sho = 0.5 * (kpts[KP_LEFT_SHOULDER] + kpts[KP_RIGHT_SHOULDER])
        hip = 0.5 * (kpts[KP_LEFT_HIP] + kpts[KP_RIGHT_HIP])
        return float(np.linalg.norm(sho - hip))
    if ok(KP_LEFT_SHOULDER) and ok(KP_RIGHT_SHOULDER):
        return float(np.linalg.norm(kpts[KP_LEFT_SHOULDER] - kpts[KP_RIGHT_SHOULDER]))
    return 0.0
