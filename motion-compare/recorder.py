"""Lưu kết quả phiên so sánh.

- Side-by-side video: [user_annotated | reference_annotated].
- Report JSON: list các entry {frame, accuracy, per_joint, feedback}.
- Tự tạo session folder: motion-compare/sessions/<timestamp>/.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from supabase_client import supabase


SESSIONS_DIR = Path(__file__).resolve().parent / "sessions"


class SessionRecorder:
    def __init__(
        self,
        session_dir: Optional[Path] = None,
        fps: float = 30.0,
        size: tuple[int, int] = (1280, 480),
    ) -> None:
        """size = (width, height) của video side-by-side đã ghép."""
        if session_dir is None:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            session_dir = SESSIONS_DIR / stamp
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.video_path = self.session_dir / "side_by_side.mp4"
        self.report_path = self.session_dir / "report.json"

        self.fps = float(fps)
        self.size = size  # (w, h)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(str(self.video_path), fourcc, self.fps, self.size)

        self.entries: list[dict] = []
        self.started_at = time.time()
        self.closed = False

    @staticmethod
    def make_side_by_side(left: np.ndarray, right: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        """Ghép 2 frame thành 1 frame side-by-side với size cố định."""
        w, h = target_size
        half_w = w // 2
        l = cv2.resize(left, (half_w, h))
        r = cv2.resize(right, (w - half_w, h))
        return np.hstack([l, r])

    def write_frame(self, left: np.ndarray, right: np.ndarray) -> None:
        if self.closed:
            return
        frame = self.make_side_by_side(left, right, self.size)
        self.writer.write(frame)

    def add_entry(
        self,
        frame_idx: int,
        ref_frame_idx: int,
        accuracy: float,
        per_joint: np.ndarray,
        feedback: list[str],
        valid: bool,
    ) -> None:
        if self.closed:
            return
        per_joint_list = [None if np.isnan(v) else float(v) for v in per_joint.tolist()]
        self.entries.append({
            "frame": int(frame_idx),
            "ref_frame": int(ref_frame_idx),
            "accuracy": float(accuracy),
            "valid": bool(valid),
            "per_joint": per_joint_list,   # length 17, COCO order
            "feedback": list(feedback),
            "t": round(time.time() - self.started_at, 3),
        })

    def close(self) -> Path:
        if self.closed:
            return self.session_dir
        self.closed = True
        try:
            self.writer.release()
        except Exception:
            pass

        report = {
            "started_at": self.started_at,
            "duration_sec": round(time.time() - self.started_at, 3),
            "fps": self.fps,
            "video": self.video_path.name,
            "num_frames": len(self.entries),
            "avg_accuracy": (
                float(np.mean([e["accuracy"] for e in self.entries if e["valid"]]))
                if any(e["valid"] for e in self.entries) else 0.0
            ),
            "frames": self.entries,
        }
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return self.session_dir

    def save_to_supabase(self, user_id: str, preset_name: str, mode: str = "camera") -> str:
        """Lưu metadata session lên Supabase, rồi upload video + report.

        Args:
            user_id: Supabase auth.users.id của người đang tập
            preset_name: tên preset (ví dụ Forehand-Drive)
            mode: 'camera' hoặc 'video'

        Returns:
            UUID của row vừa insert
        """
        valid_frames = [f for f in self.entries if f.get("valid")]
        if not valid_frames:
            avg_accuracy = 0.0
        else:
            avg_accuracy = sum(f["accuracy"] for f in valid_frames) / len(valid_frames)

        # Top 5 feedback xuất hiện nhiều nhất
        all_feedback: list[str] = []
        for f in valid_frames:
            all_feedback.extend(f.get("feedback", []))
        top_feedback = [fb for fb, _ in Counter(all_feedback).most_common(5)]

        # Trung bình per-joint (17 khớp)
        per_joint_avg: list[float | None] = [None] * 17
        for joint_idx in range(17):
            values = [
                f["per_joint"][joint_idx]
                for f in valid_frames
                if f["per_joint"][joint_idx] is not None
            ]
            if values:
                per_joint_avg[joint_idx] = round(sum(values) / len(values), 1)

        row = {
            "user_id":          user_id,
            "preset_name":      preset_name,
            "mode":             mode,
            "overall_accuracy": round(avg_accuracy, 2),
            "num_frames":       len(self.entries),
            "duration_sec":     round(time.time() - self.started_at, 2),
            "feedback":         top_feedback,
            "per_joint":        per_joint_avg,
        }

        result = supabase.table("sessions").insert(row).execute()
        session_id = result.data[0]["id"]

        # ━━━ UPLOAD FILES ━━━
        video_url  = None
        report_url = None

        # 1. Upload video
        if self.video_path.exists():
            storage_path = f"{user_id}/{session_id}.mp4"
            with open(self.video_path, "rb") as f:
                supabase.storage.from_("session-videos").upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "video/mp4"},
                )
            signed = supabase.storage.from_("session-videos").create_signed_url(
                storage_path, expires_in=60 * 60 * 24 * 7
            )
            video_url = signed["signedURL"]

        # 2. Upload report.json
        if self.report_path.exists():
            storage_path = f"{user_id}/{session_id}.json"
            with open(self.report_path, "rb") as f:
                supabase.storage.from_("session-reports").upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "application/json"},
                )
            signed = supabase.storage.from_("session-reports").create_signed_url(
                storage_path, expires_in=60 * 60 * 24 * 7
            )
            report_url = signed["signedURL"]

        # 3. Update row sessions với 2 URL
        supabase.table("sessions").update({
            "video_url":  video_url,
            "report_url": report_url,
        }).eq("id", session_id).execute()

        return session_id
