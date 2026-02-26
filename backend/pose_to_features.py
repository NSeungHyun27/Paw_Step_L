"""
ZIP 내 이미지 → 강아지 포즈 모델(YOLO dog-pose) 또는 사람 포즈(COCO)로 관절 추출 → 27차원 특징 계산.
강아지 전용 가중치(dog-pose.yaml 학습) 사용 시 24점, 미사용 시 COCO 17점 매핑.
"""
from __future__ import annotations

import os
import logging

import numpy as np

from .feature_extract import build_27_features

logger = logging.getLogger(__name__)

# Data_AI_Final.py와 동일한 10개 키포인트 라벨 순서
TARGET_LABELS = [
    "Iliac crest",
    "Femoral greater trochanter",
    "Femorotibial joint",
    "Lateral malleolus of the distal tibia",
    "Distal lateral aspect of the fifth metatarsus",
    "T13 Spinous precess",
    "Dorsal scapular spine",
    "Acromion/Greater tubercle",
    "Lateral humeral epicondyle",
    "Ulnar styloid process",
]

# COCO 17 keypoints (사람): 0 nose, 1 L_eye, 2 R_eye, 3 L_ear, 4 R_ear,
# 5 L_shoulder, 6 R_shoulder, 7 L_elbow, 8 R_elbow, 9 L_wrist, 10 R_wrist,
# 11 L_hip, 12 R_hip, 13 L_knee, 14 R_knee, 15 L_ankle, 16 R_ankle
# 강아지 측면 가정: 우측 관절 우선 (사람 모델은 강아지에 부적합)
COCO_17_TO_OUR_10 = [
    12,   # Iliac crest <- R_hip
    12,   # Femoral greater trochanter <- R_hip
    14,   # Femorotibial joint <- R_knee
    16,   # Lateral malleolus <- R_ankle
    16,   # Fifth metatarsus <- R_ankle
    12,   # T13 Spinous <- R_hip
    6,    # Dorsal scapular spine <- R_shoulder
    6,    # Acromion <- R_shoulder
    8,    # Lateral humeral epicondyle <- R_elbow
    10,   # Ulnar styloid <- R_wrist
]

# dog-pose.yaml 24 keypoints (Ultralytics Dog-Pose): 측면 우측 기준
# 0 front_left_paw, 1 front_left_knee, 2 front_left_elbow, 3 rear_left_paw, 4 rear_left_knee, 5 rear_left_elbow,
# 6 front_right_paw, 7 front_right_knee, 8 front_right_elbow, 9 rear_right_paw, 10 rear_right_knee, 11 rear_right_elbow,
# 12 tail_start, 13 tail_end, 14 left_ear_base, 15 right_ear_base, 16 nose, 17 chin, 18 left_ear_tip, 19 right_ear_tip,
# 20 left_eye, 21 right_eye, 22 withers, 23 throat
DOG_24_TO_OUR_10 = [
    22,   # Iliac crest <- withers (등 상단)
    11,   # Femoral greater trochanter <- rear_right_elbow (hip)
    10,   # Femorotibial joint <- rear_right_knee
    9,    # Lateral malleolus <- rear_right_paw
    9,    # Fifth metatarsus <- rear_right_paw (아래 보정)
    12,   # T13 Spinous <- tail_start
    22,   # Dorsal scapular spine <- withers
    8,    # Acromion <- front_right_elbow
    8,    # Lateral humeral epicondyle <- front_right_elbow
    6,    # Ulnar styloid <- front_right_paw
]
MIN_KEYPOINT_CONF = 0.25

# 환경 변수: 강아지 포즈 모델 경로 (dog-pose.yaml로 학습한 .pt 권장)
# 예: POSE_MODEL_PATH=./weights/yolov8n-pose-dog.pt 또는 Hugging Face URL
POSE_MODEL_ENV = "POSE_MODEL_PATH"
DOG_POSE_MODEL_ENV = "DOG_POSE_MODEL_PATH"


def _get_pose_model():
    """
    강아지 전용 포즈 모델 우선 로드.
    - DOG_POSE_MODEL_PATH 또는 POSE_MODEL_PATH에 .pt 경로/URL 지정 시 해당 모델 사용.
    - 없으면 현재 디렉터리/backend에서 yolov8n-pose-dog.pt 탐색.
    - 없으면 yolov8n-pose.pt(사람 COCO 17점) 로드 후 경고 (강아지 관절 인식 한계).
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError(
            "ZIP 이미지 분석을 위해 ultralytics가 필요합니다. pip install ultralytics"
        )
    path = os.environ.get(DOG_POSE_MODEL_ENV) or os.environ.get(POSE_MODEL_ENV)
    if path and path.strip():
        path = path.strip()
        logger.info("Loading pose model from env: %s", path)
        return YOLO(path)
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent
    for base in (backend_dir, project_root, Path.cwd()):
        for name in ("yolov8n-pose-dog.pt", "yolo11n-pose-dog.pt"):
            candidate = base / name
            if candidate.is_file():
                logger.info("Loading dog pose model: %s", candidate)
                return YOLO(str(candidate))
    logger.warning(
        "강아지 전용 포즈 가중치를 찾지 못했습니다. yolov8n-pose.pt(사람용)를 사용합니다. "
        "강아지 관절 인식이 제한적일 수 있습니다. dog-pose.yaml로 학습한 .pt를 POSE_MODEL_PATH로 지정하세요."
    )
    return YOLO("yolov8n-pose.pt")


def _keypoints_to_joint_dict(
    kpts: np.ndarray,
    img_width: int,
    img_height: int,
    mapping: list[int],
) -> dict[str, tuple[float, float]]:
    """
    YOLO pose keypoints (N, 3) x,y,conf → Data_AI_Final 10개 라벨 좌표.
    mapping: 우리 10개 라벨 순서대로 사용할 키포인트 인덱스 (COCO 17 또는 dog-pose 24).
    좌표는 0~1000 스케일로 반환 (Data_AI_Final/feature_extract에서 /1000 적용).
    """
    joint_dict = {}
    scale_x = 1000.0 / max(img_width, 1)
    scale_y = 1000.0 / max(img_height, 1)
    n_kpts = kpts.shape[0]
    for i, label in enumerate(TARGET_LABELS):
        idx = mapping[i] if i < len(mapping) else 0
        if idx < n_kpts:
            x, y = float(kpts[idx, 0]), float(kpts[idx, 1])
            conf = float(kpts[idx, 2]) if kpts.shape[1] > 2 else 1.0
            if conf >= MIN_KEYPOINT_CONF:
                joint_dict[label] = (x * scale_x, y * scale_y)
            else:
                joint_dict[label] = (0.0, 0.0)
        else:
            joint_dict[label] = (0.0, 0.0)
    # Fifth metatarsus: ankle 아래로 약간 (y 증가)
    if "Lateral malleolus of the distal tibia" in joint_dict:
        ax, ay = joint_dict["Lateral malleolus of the distal tibia"]
        if (ax, ay) != (0.0, 0.0):
            joint_dict["Distal lateral aspect of the fifth metatarsus"] = (ax, min(ay + 50, 1000.0))
    return joint_dict


def image_to_27_features(img_bgr: np.ndarray, pose_model=None) -> tuple[np.ndarray, float]:
    """
    단일 이미지(BGR) → 포즈 추정 → 10점 좌표 → 27차원 특징.
    모델 출력이 24점이면 dog-pose 매핑, 17점이면 COCO(사람) 매핑 사용.
    반환: (features shape (27,), keypoint_confidence 0~1).
    """
    if pose_model is None:
        pose_model = _get_pose_model()
    h, w = img_bgr.shape[:2]
    if h == 0 or w == 0:
        raise ValueError("Empty image")
    results = pose_model(img_bgr, verbose=False)
    if not results or len(results) == 0:
        raise ValueError("No pose detection")
    r = results[0]
    if r.keypoints is None or r.keypoints.data is None:
        raise ValueError("No keypoints")
    kpts_all = r.keypoints.data.cpu().numpy()
    if kpts_all.size == 0 or kpts_all.shape[0] == 0:
        raise ValueError("No keypoints data")
    kpts = kpts_all[0]
    num_kpts = kpts.shape[0]
    if num_kpts >= 24:
        mapping = DOG_24_TO_OUR_10
        kpts = kpts[:24]
    else:
        mapping = COCO_17_TO_OUR_10
        if num_kpts < 17:
            kpts = np.pad(kpts, ((0, 17 - num_kpts), (0, 0)), constant_values=0.0)
        kpts = kpts[:17]
    joint_dict = _keypoints_to_joint_dict(kpts, w, h, mapping)
    use_k = min(len(kpts), 17)
    conf = float(np.mean(kpts[:use_k, 2]) if kpts.shape[1] > 2 else 0.5)
    side = 0.5
    dog_size = 0.5
    features = build_27_features(joint_dict, side=side, dog_size=dog_size)
    return features.astype(np.float32), min(max(conf, 0.0), 1.0)
