"""
Vision Analysis Router
POST /api/interview/vision — accepts a base64 JPEG, runs DeepFace emotion detection,
returns dominant_emotion + status. Gracefully degrades on any failure.
"""
import os
import base64
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

# MUST be set before any DeepFace/TF import to avoid tf_keras ModuleNotFoundError
os.environ["TF_USE_LEGACY_KERAS"] = "1"

router = APIRouter(prefix="/api/interview", tags=["vision"])


class VisionRequest(BaseModel):
    image_b64: str  # base64-encoded JPEG/PNG from canvas.toDataURL()


class VisionResponse(BaseModel):
    dominant_emotion: str
    emotion_scores: dict = {}
    status: str = "ok"  # "ok" | "no_face_detected" | "error" | "unavailable"


@router.post("/vision", response_model=VisionResponse)
async def analyze_vision(request: VisionRequest):
    """
    Analyze a single webcam frame for dominant emotion.
    Uses DeepFace with enforce_detection=False so a missing/partial face
    doesn't crash. Always returns valid JSON — never raises 500.
    """
    try:
        import cv2
        from deepface import DeepFace
    except ImportError:
        return VisionResponse(dominant_emotion="neutral", status="unavailable")

    try:
        # ── Decode base64 → OpenCV BGR numpy array ───────────────────────────
        b64_data = request.image_b64
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        img_bytes = base64.b64decode(b64_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img_bgr   = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img_bgr is None or img_bgr.size == 0:
            print("[VISION] Failed to decode image bytes — returning neutral")
            return VisionResponse(dominant_emotion="neutral", status="error")

        # ── DeepFace emotion analysis ────────────────────────────────────────
        try:
            results = DeepFace.analyze(
                img_path=img_bgr,
                actions=["emotion"],
                enforce_detection=False,   # partial/missing face → still analyze
                silent=True
            )
        except ValueError as ve:
            # DeepFace raises ValueError("Face could not be detected") when
            # enforce_detection=True, but can also surface with =False on blank frames
            print(f"[VISION] No face detected: {ve}")
            return VisionResponse(dominant_emotion="neutral", status="no_face_detected")

        # results is a list; take first face
        face = results[0] if isinstance(results, list) else results
        dominant = face.get("dominant_emotion", "neutral")
        scores   = face.get("emotion", {})

        print(f"[VISION] Dominant: {dominant} | scores: {scores}")
        return VisionResponse(dominant_emotion=dominant, emotion_scores=scores, status="ok")

    except Exception as e:
        print(f"[VISION] Unexpected error: {e}")
        return VisionResponse(dominant_emotion="neutral", status="error")

