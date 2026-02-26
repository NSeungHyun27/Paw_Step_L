"""
Data_AI_Final.py와 동일한 27개 특징 구성으로 전처리.
이미지/영상: 휴리스틱 키포인트 -> build_27_features.
JSON: annotation_info 또는 [f1..f27] / { features: [...] } 직접 사용.
"""
import io
import os
import tempfile
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .feature_extract import build_27_features

NUM_FEATURES = 27

# Data_AI_Final과 동일한 10개 키포인트 라벨 순서
TARGET_LABELS = [
    "Iliac crest", "Femoral greater trochanter", "Femorotibial joint",
    "Lateral malleolus of the distal tibia", "Distal lateral aspect of the fifth metatarsus",
    "T13 Spinous precess", "Dorsal scapular spine", "Acromion/Greater tubercle",
    "Lateral humeral epicondyle", "Ulnar styloid process",
]


def _points_to_joint_dict(points: list[tuple[float, float]]) -> dict[str, tuple[float, float]]:
    """이미지에서 추정한 10개 포인트를 라벨별 좌표로. 좌표는 0~1000 스케일로 넘김 (/1000 되므로 0~1)."""
    # points는 0~1 정규화. Data_AI_Final은 raw/1000 사용하므로 0~1 * 1000 = 0~1000
    scale = 1000.0
    d = {}
    for i, label in enumerate(TARGET_LABELS):
        if i < len(points):
            x, y = points[i]
            d[label] = (float(x) * scale, float(y) * scale)
        else:
            d[label] = (0.0, 0.0)
    return d


def _extract_frame_features(frame: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """
    단일 프레임에서 Data_AI_Final 형식 27차원 + 피그마용 메트릭.
    키포인트가 없으면 컨투어 기반 10점 근사.
    """
    h, w = frame.shape[:2]
    if h == 0 or w == 0:
        feats = np.zeros(NUM_FEATURES, dtype=np.float32)
        return feats, _default_metrics()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    roi = gray[h // 2 :, :]
    blurred = cv2.GaussianBlur(roi, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    points: list[tuple[float, float]] = []
    for c in contours[:6]:
        M = cv2.moments(c)
        if M["m00"] > 10:
            cx = (M["m10"] / M["m00"] + 0) / w
            cy = (M["m01"] / M["m00"] + h // 2) / h
            points.append((min(max(cx, 0), 1), min(max(cy, 0), 1)))
    while len(points) < 10:
        i, j = len(points) // 3, len(points) % 3
        points.append((0.2 + 0.3 * (i % 3) + 0.1 * (j - 1), 0.5 + 0.15 * (i - 1)))
    points = points[:10]

    joint_dict = _points_to_joint_dict(points)
    features = build_27_features(joint_dict, side=0.5, dog_size=0.5)

    # 피그마용 메트릭: 3각도는 0~1 구간이므로 *180 복원
    a1 = float(features[20]) * 180.0  # trochanter-femorotibial-malleolus
    a2 = float(features[21]) * 180.0  # iliac-trochanter-femorotibial
    a3 = float(features[22]) * 180.0  # femorotibial-malleolus-fifth
    metrics = {
        "knee_angle": round(a1, 1),
        "hip_angle": round(a2, 1),
        "ankle_angle": round(a3, 1),
        "alignment_error": round(float(features[23]), 2),
        "normal_hip": "120-135°",
        "normal_knee": "135-150°",
        "normal_ankle": "125-140°",
    }
    return features, metrics


def _default_metrics() -> dict[str, Any]:
    return {
        "knee_angle": 140.0,
        "hip_angle": 125.0,
        "ankle_angle": 130.0,
        "alignment_error": 1.5,
        "normal_hip": "120-135°",
        "normal_knee": "135-150°",
        "normal_ankle": "125-140°",
    }


def _side_and_size_from_data(data: dict[str, Any]) -> tuple[float, float]:
    """Data_AI_Final과 동일: pet_medical_record_info → side, size → dog_size."""
    side = 0.5
    for r in data.get("pet_medical_record_info", []):
        if r.get("value") == 1:
            side = 0.0 if r.get("foot_position") == "left" else 1.0
            break
    size_map = {"소형견": 0.0, "중형견": 0.5, "대형견": 1.0}
    dog_size = size_map.get(data.get("size", "소형견"), 0.0)
    return side, dog_size


def parse_json_to_features(data: Any) -> np.ndarray:
    """JSON에서 27차원 벡터 추출. annotation_info가 있으면 build_27_features 사용 (Data_AI_Final 형식)."""
    if isinstance(data, list) and len(data) == NUM_FEATURES:
        return np.array(data, dtype=np.float32)
    if isinstance(data, dict):
        if "features" in data:
            return np.array(data["features"], dtype=np.float32)
        annos = data.get("annotation_info", [])
        if annos:
            joint_dict = {a["label"]: (float(a["x"]), float(a["y"])) for a in annos}
            side, dog_size = _side_and_size_from_data(data)
            return build_27_features(joint_dict, side=side, dog_size=dog_size)
    raise ValueError("JSON must be [f1..f27], { features: [...] }, or { annotation_info: [...] }")


def preprocess_logic(file_bytes: bytes, content_type: str) -> tuple[np.ndarray, dict[str, Any]]:
    """
    이미지/영상: 프레임별 27차원 추출 (Data_AI_Final 형식).
    반환: (features shape (27,), metrics dict)
    """
    nparr = np.frombuffer(file_bytes, np.uint8)
    metrics_agg: dict[str, list] = {}

    if content_type.startswith("video/"):
        suffix = ".mp4" if "mp4" in content_type else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(file_bytes)
            f.flush()
            temp_path = f.name
        cap = cv2.VideoCapture(temp_path)
        try:
            if not cap.isOpened():
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    return _extract_frame_features(img)
                return np.zeros(NUM_FEATURES, dtype=np.float32), _default_metrics()
            feat_list = []
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
            step = max(1, total_frames // 10)
            idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if idx % step == 0:
                    f, m = _extract_frame_features(frame)
                    feat_list.append(f)
                    for k, v in m.items():
                        if isinstance(v, (int, float)):
                            metrics_agg.setdefault(k, []).append(v)
                idx += 1
        finally:
            cap.release()
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        if not feat_list:
            return np.zeros(NUM_FEATURES, dtype=np.float32), _default_metrics()
        features = np.mean(feat_list, axis=0).astype(np.float32)
        metrics = {k: round(float(np.mean(v)), 2) for k, v in metrics_agg.items() if v}
        if "normal_hip" not in metrics:
            metrics.update(_default_metrics())
        return features, metrics

    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        try:
            pil = Image.open(io.BytesIO(file_bytes))
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        except Exception:
            return np.zeros(NUM_FEATURES, dtype=np.float32), _default_metrics()
    return _extract_frame_features(img)
