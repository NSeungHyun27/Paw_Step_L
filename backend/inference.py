"""
추론: 전처리 -> 모델 예측 -> 3기 민감도 보정 -> 피그마용 응답 생성.
"""
from __future__ import annotations

import numpy as np
import torch

from .model import CLASS_NAMES, DogPatellaModel, NUM_CLASSES
from .preprocess import preprocess_logic
from .schemas import ChartDataItem, JointMetric, PredictResponse, WalkPrescription

# 3기 판정: 3기 확률이 최소 이 값 이상일 때만 '3기'로 판정
THRESHOLD_3 = 0.60
# 애매한 경우: 최대 확률과 차이가 이보다 작으면 더 안전한 기수 우선
AMBIGUITY_MARGIN = 0.15

# 기수별 색상 (Data_AI_Final: 정상/1기/3기 3클래스)
CHART_COLORS = {
    "정상": "var(--patella-success)",
    "1기": "var(--patella-warning)",
    "3기": "var(--patella-danger)",
}

# 기수별 산책 가이드 (피그마 디자인 명시)
RECOMMENDATIONS = {
    "정상": WalkPrescription(
        duration="20-30분",
        frequency="하루 2-3회",
        intensity="보통",
        warnings=["과도한 점프·계단 주의"],
        recommendations=["평지 산책", "일정한 속도 유지", "충분한 휴식"],
    ),
    "1기": WalkPrescription(
        duration="15-20분",
        frequency="하루 2-3회",
        intensity="저강도",
        warnings=[
            "계단 오르내리기 최소화",
            "미끄러운 바닥 주의",
            "급격한 방향 전환 자제",
            "점프나 과격한 운동 피하기",
        ],
        recommendations=["평지 산책 권장", "천천히 일정한 속도로 걷기", "하네스 착용 권장"],
    ),
    "3기": WalkPrescription(
        duration="5-10분",
        frequency="수의사 지시에 따름",
        intensity="최소",
        warnings=[
            "무리한 운동 금지",
            "계단·경사 절대 금지",
            "수술·치료 후 재활 시에만 가벼운 운동",
        ],
        recommendations=["반드시 수의사 상담", "재활 계획 준수", "통증 모니터링"],
    ),
}

# 공공데이터 산책로 API 필터 (Data_AI_Final: 3클래스)
WALK_FILTER_MAP = {
    "정상": "normal",
    "1기": "easy",
    "3기": "rehab",
}


def _apply_threshold(probs: np.ndarray) -> tuple[int, float]:
    """
    3기(인덱스 2) 확률이 THRESHOLD_3 미만이면 3기로 내지 않고 안전한 기수 우선.
    애매한 경우 정상/1기 우선. 반환: (class_index 0~2, confidence 0~100)
    """
    idx = int(np.argmax(probs))
    conf = float(probs[idx])

    # 3기(인덱스 2)인데 확률 60% 미만이면 3기로 확정하지 않음
    if idx == 2 and conf < THRESHOLD_3:
        probs_no_3 = np.array(probs, copy=True)
        probs_no_3[2] = 0.0
        idx = int(np.argmax(probs_no_3))
        conf = float(probs[idx])

    sorted_idx = np.argsort(probs)[::-1]
    if len(sorted_idx) >= 2 and (probs[sorted_idx[0]] - probs[sorted_idx[1]]) < AMBIGUITY_MARGIN:
        idx = int(min(sorted_idx[0], sorted_idx[1]))
        conf = float(probs[idx])

    return idx, round(conf * 100.0, 1)


def _metrics_to_joint_angles(metrics: dict) -> list[JointMetric]:
    """전처리 메트릭을 피그마 '주요 관절 각도 수치' 카드 형식으로 변환."""
    normal_hip = metrics.get("normal_hip", "120-135°")
    normal_knee = metrics.get("normal_knee", "135-150°")
    normal_ankle = metrics.get("normal_ankle", "125-140°")
    return [
        JointMetric(
            joint="고관절",
            angle=round(metrics.get("hip_angle", 0), 1),
            normal=normal_hip,
            status="정상" if 120 <= metrics.get("hip_angle", 0) <= 135 else "주의",
        ),
        JointMetric(
            joint="슬관절",
            angle=round(metrics.get("knee_angle", 0), 1),
            normal=normal_knee,
            status="정상" if 135 <= metrics.get("knee_angle", 0) <= 150 else "주의",
        ),
        JointMetric(
            joint="발목관절",
            angle=round(metrics.get("ankle_angle", 0), 1),
            normal=normal_ankle,
            status="정상" if 125 <= metrics.get("ankle_angle", 0) <= 140 else "주의",
        ),
    ]


def _default_metrics_from_features(features: np.ndarray) -> dict:
    """JSON 업로드 시 Data_AI_Final 27형식: 인덱스 20,21,22=각도(0~1), 23=alignment."""
    f = features.ravel()
    if len(f) < 27:
        return {
            "knee_angle": 140, "hip_angle": 125, "ankle_angle": 130,
            "normal_hip": "120-135°", "normal_knee": "135-150°", "normal_ankle": "125-140°",
        }
    return {
        "knee_angle": round(float(f[20]) * 180, 1),
        "hip_angle": round(float(f[21]) * 180, 1),
        "ankle_angle": round(float(f[22]) * 180, 1),
        "alignment_error": round(float(f[23]), 2),
        "normal_hip": "120-135°",
        "normal_knee": "135-150°",
        "normal_ankle": "125-140°",
    }


def run_predict_from_features(
    features: np.ndarray,
    model: DogPatellaModel,
    device: torch.device,
) -> PredictResponse:
    """
    JSON 업로드: 27개 특징 배열만으로 모델 추론 후 PredictResponse 생성.
    """
    features = np.asarray(features, dtype=np.float32)
    if features.size != model.in_features:
        raise ValueError(f"Expected {model.in_features} features, got {features.size}")
    if features.ndim == 1:
        features = features.reshape(1, -1)
    metrics = _default_metrics_from_features(features[0]) if features.shape[0] else {}
    joint_angles = _metrics_to_joint_angles(metrics)

    x = torch.from_numpy(features).float().to(device)
    with torch.no_grad():
        logits = model(x)
    probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    probs = np.clip(probs, 0.0, 1.0)
    probs = probs / (probs.sum() + 1e-8)

    class_idx, confidence = _apply_threshold(probs)
    status = CLASS_NAMES[class_idx]
    chart_data = [
        ChartDataItem(name=CLASS_NAMES[i], value=int(round(probs[i] * 100)), color=CHART_COLORS[CLASS_NAMES[i]])
        for i in range(NUM_CLASSES)
    ]
    return PredictResponse(
        status=status,
        confidence=confidence,
        chart_data=chart_data,
        metrics={k: v for k, v in metrics.items() if isinstance(v, (int, float))},
        joint_angles=joint_angles,
        recommendation=RECOMMENDATIONS[status],
        walk_filter_type=WALK_FILTER_MAP[status],
    )


def run_predict_from_features_multi_frame(
    list_features: list[np.ndarray],
    model: DogPatellaModel,
    device: torch.device,
) -> PredictResponse:
    """
    ZIP 내 다중 프레임: 각 프레임별 27차원 특징 → 모델 확률 → 평균 확률로 최종 진단.
    가장 확률이 높게 나온 프레임을 대표 프레임으로 반환.
    """
    if not list_features:
        raise ValueError("list_features must not be empty")
    features_stack = np.stack([np.asarray(f, dtype=np.float32).ravel() for f in list_features])
    if features_stack.shape[1] != model.in_features:
        raise ValueError(f"Expected {model.in_features} features, got {features_stack.shape[1]}")

    x = torch.from_numpy(features_stack).float().to(device)
    with torch.no_grad():
        logits = model(x)
    probs_all = torch.softmax(logits, dim=1).cpu().numpy()
    probs_all = np.clip(probs_all, 0.0, 1.0)
    probs_all = probs_all / (probs_all.sum(axis=1, keepdims=True) + 1e-8)

    avg_probs = np.mean(probs_all, axis=0)
    avg_probs = avg_probs / (avg_probs.sum() + 1e-8)
    class_idx, confidence = _apply_threshold(avg_probs)
    status = CLASS_NAMES[class_idx]

    representative_idx = int(np.argmax(probs_all[:, class_idx]))
    rep_conf = float(probs_all[representative_idx, class_idx] * 100.0)
    metrics = _default_metrics_from_features(features_stack[representative_idx])
    joint_angles = _metrics_to_joint_angles(metrics)

    chart_data = [
        ChartDataItem(name=CLASS_NAMES[i], value=int(round(avg_probs[i] * 100)), color=CHART_COLORS[CLASS_NAMES[i]])
        for i in range(NUM_CLASSES)
    ]
    return PredictResponse(
        status=status,
        confidence=confidence,
        chart_data=chart_data,
        metrics={k: v for k, v in metrics.items() if isinstance(v, (int, float))},
        joint_angles=joint_angles,
        recommendation=RECOMMENDATIONS[status],
        walk_filter_type=WALK_FILTER_MAP[status],
        frames_analyzed=len(list_features),
        representative_frame={
            "frame_index": representative_idx,
            "confidence": round(rep_conf, 1),
            "status": status,
        },
    )


def run_predict(
    file_bytes: bytes,
    content_type: str,
    model: DogPatellaModel,
    device: torch.device,
) -> PredictResponse:
    """
    이미지/영상 -> 전처리 -> 모델 추론 -> 3기 보정 -> PredictResponse 생성.
    """
    features, metrics = preprocess_logic(file_bytes, content_type)
    x = torch.from_numpy(features).float().unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
    probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    probs = np.clip(probs, 0.0, 1.0)
    probs = probs / (probs.sum() + 1e-8)

    class_idx, confidence = _apply_threshold(probs)
    status = CLASS_NAMES[class_idx]

    chart_data = [
        ChartDataItem(name=CLASS_NAMES[i], value=int(round(probs[i] * 100)), color=CHART_COLORS[CLASS_NAMES[i]])
        for i in range(NUM_CLASSES)
    ]
    joint_angles = _metrics_to_joint_angles(metrics)
    recommendation = RECOMMENDATIONS[status]
    walk_filter_type = WALK_FILTER_MAP[status]

    return PredictResponse(
        status=status,
        confidence=confidence,
        chart_data=chart_data,
        metrics={k: v for k, v in metrics.items() if isinstance(v, (int, float))},
        joint_angles=joint_angles,
        recommendation=recommendation,
        walk_filter_type=walk_filter_type,
    )
