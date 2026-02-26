"""
피그마 맞춤형 API 요청/응답 스키마.
"""
from typing import Literal

from pydantic import BaseModel, Field


# --- Response (Figma 화면 대응) ---

class ChartDataItem(BaseModel):
    name: str
    value: int = Field(..., ge=0, le=100, description="기수별 확률 %")
    color: str = ""


class JointMetric(BaseModel):
    joint: str
    angle: float
    normal: str
    status: Literal["정상", "주의", "이상"]


class WalkPrescription(BaseModel):
    duration: str
    frequency: str
    intensity: str
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class RecommendedCourse(BaseModel):
    """진단 결과 기반 추천 산책로 1건."""
    name: str
    distance: float = Field(..., description="사용자 위치부터 직선 거리(km)")
    address: str
    description: str
    reason_tags: list[str] = Field(default_factory=list, description="평지 위주, 경사로 포함 등 추천 사유")
    lat: float = 0.0
    lon: float = 0.0


class PredictResponse(BaseModel):
    status: Literal["정상", "1기", "3기"]
    confidence: float = Field(..., ge=0, le=100, description="진단 확신도 %")
    chart_data: list[ChartDataItem]
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="실제 계산된 관절 각도·정렬 수치 (knee_angle, alignment_error 등)",
    )
    joint_angles: list[JointMetric] = Field(
        default_factory=list,
        description="피그마 '주요 관절 각도 수치' 카드용",
    )
    recommendation: WalkPrescription = Field(
        ...,
        description="기수별 맞춤 산책 가이드",
    )
    walk_filter_type: Literal["easy", "normal", "rehab"] = Field(
        ...,
        description="공공데이터 산책로 API 필터용",
    )
    recommended_courses: list[RecommendedCourse] = Field(
        default_factory=list,
        description="현재 위치 기준 진단별 상위 3개 산책로 (위경도 제공 시)",
    )
    recommendation_reason: str | None = Field(
        default=None,
        description="진단 결과 기반 추천 이유 한 줄 (결과 리스트 상단 표시용)",
    )
    frames_analyzed: int | None = Field(
        default=None,
        description="ZIP 업로드 시 분석에 사용된 이미지(프레임) 수",
    )
    representative_frame: dict | None = Field(
        default=None,
        description="ZIP 업로드 시 가장 명확하게 분석된 대표 프레임 정보 (frame_index, confidence 등)",
    )
