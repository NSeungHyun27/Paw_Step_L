"""
공공데이터 CSV 두 개: 서버 시작 시 pandas로 로드·전처리.
- 주소, 코스명(공원명), 길이(km), 경사도 추출
- Haversine 거리 기반 + 진단별 상위 3개 추천
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARK_CSV = PROJECT_ROOT / "KC_498_DMSTC_MCST_PBL_CT_PARK_2025.csv"
WALK_CSV = PROJECT_ROOT / "KC_CFR_WLK_STRET_INFO_2021.csv"

# 전역: 서버 시작 시 로드된 코스 리스트 (dict 리스트)
_courses: list[dict] = []


def _parse_length_km(s: str | None) -> float | None:
    """길이 문자열 → km 수치. '2.1', '13.8' 등."""
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    s = str(s).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _slope_from_difficulty(difficulty: str | None) -> Literal["없음", "있음"]:
    """난이도 → 경사도. 쉬움=없음, 보통/어려움=있음."""
    if not difficulty:
        return "없음"
    d = str(difficulty).strip()
    return "없음" if d == "쉬움" else "있음"


def _extract_reason_tags(text: str, park_type: str = "") -> list[str]:
    """COURS_DC/ADIT_DC 또는 mcate_nm에서 '평지','경사','오르막' 키워드 분석 → 추천 사유 태그."""
    tags: list[str] = []
    combined = (text or "") + " " + (park_type or "")
    if "평지" in combined:
        tags.append("평지 위주")
    if "경사" in combined:
        tags.append("경사로 포함")
    if "오르막" in combined:
        tags.append("오르막 있음")
    if "어린이" in combined or "어린이공원" in combined:
        tags.append("어린이공원")
    if not tags and (park_type or "").strip():
        tags.append("공원")
    if not tags:
        tags.append("산책로")
    return tags


# 카테고리 필터: 프론트엔드 category 값에 따른 조건
def _desc_for_category(c: dict) -> str:
    """코스의 설명 전체(키워드 검색용)."""
    return (c.get("description_full") or c.get("description") or "").strip()


def _is_flat_course(c: dict) -> bool:
    """평지위주: COURS_LEVEL_NM이 '쉬움'이거나, 설명에 '평지','수변','공원','무장애' 포함."""
    if (c.get("difficulty") or "").strip() == "쉬움":
        return True
    desc = _desc_for_category(c)
    for kw in ("평지", "수변", "공원", "무장애"):
        if kw in desc:
            return True
    return False


def _is_short_course(c: dict) -> bool:
    """단거리: COURS_DETAIL_LT_CN(길이)이 3km 미만."""
    length = c.get("length_km")
    if length is None:
        return False
    try:
        return float(length) < 3.0
    except (TypeError, ValueError):
        return False


def _is_long_course(c: dict) -> bool:
    """장거리: COURS_DETAIL_LT_CN이 5km 이상."""
    length = c.get("length_km")
    if length is None:
        return False
    try:
        return float(length) >= 5.0
    except (TypeError, ValueError):
        return False


def _is_slope_course(c: dict) -> bool:
    """경사: COURS_LEVEL_NM이 '어려움'이거나, 설명에 '산','고개','오르막','계단' 포함."""
    if (c.get("difficulty") or "").strip() == "어려움":
        return True
    desc = _desc_for_category(c)
    for kw in ("산", "고개", "오르막", "계단"):
        if kw in desc:
            return True
    return False


def _build_course_tags(c: dict) -> list[str]:
    """각 코스의 특징을 나타내는 tags 배열 동적 생성 (예: ["평지", "단거리"])."""
    tags: list[str] = []
    if _is_flat_course(c):
        tags.append("평지")
    if _is_short_course(c):
        tags.append("단거리")
    if _is_long_course(c):
        tags.append("장거리")
    if _is_slope_course(c):
        tags.append("경사")
    if not tags:
        tags.append("산책로")
    return tags


def init_courses() -> None:
    """서버 시작 시 pandas로 두 CSV 읽어 전처리 후 _courses에 적재."""
    global _courses
    _courses = []

    # 공원: 주소, 공원명, 길이(없음), 경사도(평지/없음), 위경도
    if PARK_CSV.is_file():
        try:
            df = pd.read_csv(PARK_CSV, encoding="utf-8-sig")
            if not df.empty:
                for _, row in df.iterrows():
                    name = _str(row.get("poi_nm"))
                    if not name:
                        continue
                    sido = _str(row.get("sido_nm"))
                    sgg = _str(row.get("sgg_nm"))
                    bemd = _str(row.get("bemd_nm"))
                    ri = _str(row.get("ri_nm"))
                    beonji = _str(row.get("beonji"))
                    rd = _str(row.get("rd_nm"))
                    bld_num = _str(row.get("bld_num"))
                    address = " ".join(
                        filter(None, [sido, sgg, bemd, ri, beonji, rd, bld_num])
                    ).strip() or f"{sido} {sgg}"
                    lat = _float(row.get("y"))
                    lon = _float(row.get("x"))
                    if lat == 0 and lon == 0:
                        continue
                    mcate = _str(row.get("mcate_nm"))  # 지역근린공원, 어린이공원 등
                    desc = f"{address} {name} (공원)"
                    _courses.append({
                        "address": address,
                        "name": name,
                        "length_km": None,
                        "slope": "없음",
                        "lat": lat,
                        "lon": lon,
                        "description": desc,
                        "description_full": desc + " " + (mcate or ""),
                        "source": "park",
                        "difficulty": "쉬움",
                        "park_type": mcate or "",
                        "reason_tags": _extract_reason_tags(desc, mcate),
                    })
        except Exception:
            pass

    # 둘레길/걷기길: 주소, 코스명, 길이, 경사도(난이도→쉬움=없음)
    if WALK_CSV.is_file():
        try:
            df = pd.read_csv(WALK_CSV, encoding="utf-8-sig")
            if not df.empty:
                for _, row in df.iterrows():
                    name = _str(row.get("WLK_COURS_NM")) or _str(row.get("WLK_COURS_FLAG_NM"))
                    if not name:
                        continue
                    address = _str(row.get("LNM_ADDR")) or ""
                    lat = _float(row.get("COURS_SPOT_LA"))
                    lon = _float(row.get("COURS_SPOT_LO"))
                    if lat == 0 and lon == 0:
                        continue
                    length_raw = _str(row.get("COURS_DETAIL_LT_CN")) or _str(row.get("COURS_LT_CN"))
                    length_km = _parse_length_km(length_raw)
                    difficulty = _str(row.get("COURS_LEVEL_NM")) or "보통"
                    slope = _slope_from_difficulty(difficulty)
                    cours_dc = _str(row.get("COURS_DC")) or ""
                    adit_dc = _str(row.get("ADIT_DC")) or ""
                    desc_full = (cours_dc + " " + adit_dc).strip() or f"{address} {name}"
                    _courses.append({
                        "address": address,
                        "name": name,
                        "length_km": length_km,
                        "slope": slope,
                        "lat": lat,
                        "lon": lon,
                        "description": (cours_dc or adit_dc or f"{address} {name}")[:200],
                        "description_full": desc_full,
                        "source": "walk",
                        "difficulty": difficulty,
                        "park_type": "",
                        "reason_tags": _extract_reason_tags(cours_dc + " " + adit_dc),
                    })
        except Exception:
            pass


def _str(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return str(v).strip()


def _float(v) -> float:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    try:
        return float(str(v).strip().replace(",", ""))
    except ValueError:
        return 0.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위경도 간 직선 거리(km). Haversine 공식."""
    R = 6371.0  # Earth radius km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# 진단 결과별 산책로 추천 기준 (거리·장소 유형·안내 문구)
DIAGNOSIS_CRITERIA: dict[str, dict] = {
    "3기": {
        "max_radius_km": 1.0,
        "preferred_keywords": ["소공원", "어린이공원", "어린이"],
        "message": "관절 무리를 최소화하기 위해 가까운 평지 공원 위주의 코스를 추천합니다.",
        "allow_slope": False,
        "max_difficulty": "쉬움",
    },
    "1기": {
        "max_radius_km": 2.0,
        "preferred_keywords": ["근린공원", "수변공원", "수변"],
        "message": "적절한 근력 유지가 필요한 단계입니다. 경사가 완만한 산책 코스를 추천합니다.",
        "allow_slope": True,
        "max_difficulty": "보통",
    },
    "정상": {
        "max_radius_km": 3.0,
        "preferred_keywords": ["대형공원", "산림공원", "체육공원", "공원"],
        "message": "건강한 상태입니다! 활동량을 충분히 채울 수 있는 넓은 공원을 추천합니다.",
        "allow_slope": True,
        "max_difficulty": None,
    },
}

EXPAND_RADIUS_STEP_KM = 0.5
MIN_RESULTS_TO_EXPAND = 1


def _course_matches_keywords(c: dict, keywords: list[str]) -> bool:
    """코스의 park_type 또는 description_full에 키워드가 하나라도 포함되면 True."""
    text = ((c.get("park_type") or "") + " " + (c.get("description_full") or "")).strip()
    return any(kw in text for kw in keywords)


def _course_preference_score(c: dict, keywords: list[str]) -> int:
    """키워드 매칭 수가 많을수록 높은 점수 (정렬용)."""
    text = ((c.get("park_type") or "") + " " + (c.get("description_full") or "")).strip()
    return sum(1 for kw in keywords if kw in text)


def get_recommendation_reason(grade: Literal["정상", "1기", "3기"]) -> str:
    """진단 결과(기수)에 따른 추천 이유 한 줄 문구."""
    return DIAGNOSIS_CRITERIA.get(grade, {}).get("message", "진단 결과에 맞춘 산책로를 추천합니다.")


def recommend_walkway(
    diagnosis_result: Literal["정상", "1기", "3기"],
    user_lat: float,
    user_lon: float,
    limit: int = 3,
) -> tuple[list[dict], str]:
    """
    진단 결과에 따라 거리·장소 유형 기준으로 CSV 데이터를 필터한 뒤 상위 limit개 반환.
    결과가 너무 적으면 반경을 500m씩 넓혀 재검색(장소 유형 우선순위 유지).
    반환: (추천 코스 리스트, 추천 이유 한 줄 문구)
    """
    if not _courses:
        init_courses()
    criteria = DIAGNOSIS_CRITERIA.get(diagnosis_result, DIAGNOSIS_CRITERIA["정상"])
    max_radius = criteria["max_radius_km"]
    keywords = criteria.get("preferred_keywords") or []
    allow_slope = criteria.get("allow_slope", True)
    max_difficulty = criteria.get("max_difficulty")

    with_dist: list[dict] = []
    for c in _courses:
        d = haversine_km(user_lat, user_lon, c["lat"], c["lon"])
        with_dist.append({**c, "distance_km": d})

    def difficulty_ok(c: dict) -> bool:
        if max_difficulty is None:
            return True
        diff = (c.get("difficulty") or "").strip()
        order = ("쉬움", "보통", "어려움")
        try:
            return order.index(diff) <= order.index(max_difficulty)
        except (ValueError, KeyError):
            return diff == max_difficulty

    def slope_ok(c: dict) -> bool:
        if allow_slope:
            return True
        return (c.get("slope") or "") == "없음"

    selected: list[dict] = []
    radius = max_radius
    max_radius_tries = 10
    for _ in range(max_radius_tries):
        in_radius = [x for x in with_dist if x["distance_km"] <= radius and difficulty_ok(x) and slope_ok(x)]
        in_radius.sort(
            key=lambda x: (
                -_course_preference_score(x, keywords),
                x["distance_km"],
            )
        )
        selected = in_radius[:limit]
        if len(selected) >= limit or len(in_radius) >= limit:
            break
        radius += EXPAND_RADIUS_STEP_KM

    if not selected:
        with_dist.sort(key=lambda x: x["distance_km"])
        selected = with_dist[:limit]

    reason = get_recommendation_reason(diagnosis_result)
    return (selected, reason)


def get_recommended_courses(
    user_lat: float,
    user_lon: float,
    grade: Literal["정상", "1기", "3기"],
    limit: int = 3,
) -> list[dict]:
    """
    진단 결과별 상위 limit개 추천. recommend_walkway 사용.
    반환: [{ "name", "distance", "address", "description", "reason_tags", "lat", "lon" }, ...]
    """
    selected, _ = recommend_walkway(grade, user_lat, user_lon, limit)
    return [
        {
            "name": s["name"],
            "distance": round(s["distance_km"], 2),
            "address": s.get("address") or "",
            "description": s.get("description") or s["name"],
            "reason_tags": s.get("reason_tags") or ["산책로"],
            "lat": s["lat"],
            "lon": s["lon"],
        }
        for s in selected
    ]


# 프론트엔드 category 값 → 필터 함수 매핑 (영문/한글 모두 허용)
_CATEGORY_FILTERS: dict[str, callable] = {
    "flat": _is_flat_course,
    "평지위주": _is_flat_course,
    "short": _is_short_course,
    "단거리": _is_short_course,
    "long": _is_long_course,
    "장거리": _is_long_course,
    "slope": _is_slope_course,
    "경사": _is_slope_course,
}


def _apply_category_filter(courses: list[dict], category: str | None) -> list[dict]:
    """category 값에 따라 코스 목록 필터링. None/빈 문자열이면 필터 없음."""
    if not (category and str(category).strip()):
        return courses
    raw = str(category).strip()
    key_lower = raw.lower()
    pred = _CATEGORY_FILTERS.get(key_lower) or _CATEGORY_FILTERS.get(raw)
    if pred is None:
        return courses
    return [c for c in courses if pred(c)]


def _to_route_item(c: dict, distance_km: float | None = None) -> dict:
    """코스 dict → API 응답용 항목 (tags 포함)."""
    item = {
        "id": f"{c.get('source', '')}_{id(c)}",
        "name": c["name"],
        "region": c.get("address", "").split()[0] if c.get("address") else "",
        "difficulty": c.get("difficulty", "보통"),
        "distance": f"{c['length_km']}km" if c.get("length_km") is not None else None,
        "duration": None,
        "description": c.get("description", ""),
        "address": c.get("address", ""),
        "lat": c["lat"],
        "lon": c["lon"],
        "source": c.get("source", "walk"),
        "tags": _build_course_tags(c),
    }
    if distance_km is not None:
        item["distance_from_user_km"] = round(distance_km, 2)
    return item


def get_walk_routes(
    filter_type: str = "normal",
    limit: int = 100,
    user_lat: float | None = None,
    user_lon: float | None = None,
    category: str | None = None,
) -> list[dict]:
    """
    공원+걷기길 필터 후 반환.
    - category: 평지위주|단거리|장거리|경사 (또는 flat|short|long|slope) → 해당 조건으로 추가 필터.
    - 각 항목에 해당 코스 특징을 나타내는 tags 배열 포함.
    """
    if not _courses:
        init_courses()
    diff_ok = {"easy": ["쉬움"], "rehab": ["쉬움"], "normal": ["쉬움", "보통"]}.get(filter_type, ["쉬움", "보통"])
    filtered = [c for c in _courses if c.get("difficulty") in diff_ok]
    filtered = _apply_category_filter(filtered, category)

    if user_lat is not None and user_lon is not None:
        with_dist = [(c, haversine_km(user_lat, user_lon, c["lat"], c["lon"])) for c in filtered]
        with_dist.sort(key=lambda x: x[1])
        return [_to_route_item(c, d_km) for c, d_km in with_dist[:limit]]

    return [_to_route_item(c) for c in filtered[:limit]]
