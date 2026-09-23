import cv2
from pathlib import Path
from typing import Dict, Any, Optional

class FaceTracker:
    """Intelligently detects and tracks the active speaker for 9:16 vertical reframing."""

    @classmethod
    def get_smart_vertical_crop(
        cls,
        video_path: str,
        start_time: float = 0.0,
        duration: float = 30.0,
        sample_interval: float = 0.75
    ) -> Dict[str, Any]:
        """
        Samples video frames, tracks the speaker's face, and computes the optimal
        horizontal crop window for 9:16 vertical output without cutting off faces.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return cls._fallback_center_crop(1920, 1080)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0:
            cap.release()
            return cls._fallback_center_crop(1920, 1080)

        # If already vertical (e.g. 1080x1920), no crop needed
        if height > width:
            cap.release()
            return {
                "face_detected": False,
                "is_vertical": True,
                "crop_w": width,
                "crop_h": height,
                "crop_x": 0,
                "crop_y": 0,
                "filter_str": "scale=1080:1920"
            }

        detected_centers_x = []

        try:
            if hasattr(cv2, 'CascadeClassifier'):
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face_cascade = cv2.CascadeClassifier(cascade_path)

                start_frame = int(start_time * fps)
                end_frame = min(total_frames, int((start_time + duration) * fps))
                step_frames = max(1, int(sample_interval * fps))

                curr_frame = start_frame
                while curr_frame < end_frame:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.15,
                        minNeighbors=4,
                        minSize=(int(height * 0.12), int(height * 0.12))
                    )

                    if len(faces) > 0:
                        largest_face = max(faces, key=lambda f: f[2] * f[3])
                        fx, _, fw, _ = largest_face
                        detected_centers_x.append(fx + (fw / 2.0))

                    curr_frame += step_frames
        except Exception:
            pass
        finally:
            cap.release()

        target_crop_w = int(height * (9.0 / 16.0))
        target_crop_h = height

        if not detected_centers_x:
            # Fallback to balanced center-crop
            return cls._fallback_center_crop(width, height)

        # Weighted median / smoothed average for robust horizontal tracking
        avg_center_x = sum(detected_centers_x) / len(detected_centers_x)

        # Calculate crop_x such that avg_center_x is in the middle of crop_w
        crop_x = int(avg_center_x - (target_crop_w / 2.0))
        # Clamp within frame boundaries
        crop_x = max(0, min(width - target_crop_w, crop_x))

        return {
            "face_detected": True,
            "is_vertical": False,
            "crop_w": target_crop_w,
            "crop_h": target_crop_h,
            "crop_x": crop_x,
            "crop_y": 0,
            "detected_samples": len(detected_centers_x),
            "filter_str": f"crop={target_crop_w}:{target_crop_h}:{crop_x}:0,scale=1080:1920"
        }

    @staticmethod
    def _fallback_center_crop(width: int, height: int) -> Dict[str, Any]:
        """Provides a safe center crop when no face is found."""
        crop_w = int(height * (9.0 / 16.0))
        crop_h = height
        crop_x = max(0, (width - crop_w) // 2)
        return {
            "face_detected": False,
            "is_vertical": False,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "crop_x": crop_x,
            "crop_y": 0,
            "filter_str": f"crop={crop_w}:{crop_h}:{crop_x}:0,scale=1080:1920"
        }
