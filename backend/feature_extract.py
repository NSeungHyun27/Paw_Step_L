"""
Data_AI_Final.py와 동일한 특징 추출 함수.
강아지 관절 키포인트 -> 각도/정렬/비율 등 27차원 벡터 생성.
"""
import math
from typing import Any

import numpy as np


def calculate_alignment(p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], p4: tuple[float, float]) -> float:
    """뼈의 정렬 상태 (두 선분 기울기 차). Data_AI_Final과 동일."""
    try:
        slope1 = (p2[1] - p1[1]) / (p2[0] - p1[0] + 1e-6)
        slope2 = (p4[1] - p3[1]) / (p4[0] - p3[0] + 1e-6)
        return min(abs(slope1 - slope2), 5.0)
    except Exception:
        return 0.0


def calculate_angle(p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> float:
    """세 점으로 이루어진 각도. 반환값: 도(degree) / 180 (0~1 구간). Data_AI_Final과 동일."""
    try:
        a = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
        b = math.sqrt((p2[0] - p3[0]) ** 2 + (p2[1] - p3[1]) ** 2)
        c = math.sqrt((p3[0] - p1[0]) ** 2 + (p3[1] - p1[1]) ** 2)
        val = (a ** 2 + b ** 2 - c ** 2) / (2 * a * b + 1e-6)
        angle = math.acos(max(-1.0, min(1.0, val)))
        return math.degrees(angle) / 180.0
    except Exception:
        return 0.0


def calculate_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def build_27_features(
    joint_dict: dict[str, tuple[float, float]],
    side: float = 0.5,
    dog_size: float = 0.5,
) -> np.ndarray:
    """
    Data_AI_Final DogJointDataset.__getitem__과 동일한 27차원 특징 벡터 생성.
    joint_dict: 라벨 -> (x, y). 좌표는 0~1000 등 원본 스케일이면 /1000 적용.
    """
    target_labels = [
        "Iliac crest", "Femoral greater trochanter", "Femorotibial joint",
        "Lateral malleolus of the distal tibia", "Distal lateral aspect of the fifth metatarsus",
        "T13 Spinous precess", "Dorsal scapular spine", "Acromion/Greater tubercle",
        "Lateral humeral epicondyle", "Ulnar styloid process",
    ]
    raw_keypoints = []
    for label in target_labels:
        x, y = joint_dict.get(label, (0.0, 0.0))
        raw_keypoints.extend([x, y])
    keypoints = [kp / 1000.0 for kp in raw_keypoints]

    # 3각도 (Data_AI_Final과 동일한 순서)
    angles = [
        calculate_angle(
            joint_dict.get("Femoral greater trochanter", (0, 0)),
            joint_dict.get("Femorotibial joint", (0, 0)),
            joint_dict.get("Lateral malleolus of the distal tibia", (0, 0)),
        ),
        calculate_angle(
            joint_dict.get("Iliac crest", (0, 0)),
            joint_dict.get("Femoral greater trochanter", (0, 0)),
            joint_dict.get("Femorotibial joint", (0, 0)),
        ),
        calculate_angle(
            joint_dict.get("Femorotibial joint", (0, 0)),
            joint_dict.get("Lateral malleolus of the distal tibia", (0, 0)),
            joint_dict.get("Distal lateral aspect of the fifth metatarsus", (0, 0)),
        ),
    ]
    alignment = calculate_alignment(
        joint_dict.get("Femoral greater trochanter", (0, 0)),
        joint_dict.get("Femorotibial joint", (0, 0)),
        joint_dict.get("Femorotibial joint", (0, 0)),
        joint_dict.get("Lateral malleolus of the distal tibia", (0, 0)),
    )
    thigh = calculate_distance(
        joint_dict.get("Femoral greater trochanter", (0, 0)),
        joint_dict.get("Femorotibial joint", (0, 0)),
    )
    calf = calculate_distance(
        joint_dict.get("Femorotibial joint", (0, 0)),
        joint_dict.get("Lateral malleolus of the distal tibia", (0, 0)),
    )
    leg_ratio = min(calf / (thigh + 1e-6), 2.0)

    return np.array(keypoints + angles + [alignment, leg_ratio, side, dog_size], dtype=np.float32)
