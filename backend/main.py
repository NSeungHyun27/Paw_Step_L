"""
Patella Care AI - FastAPI 백엔드.
서버 시작 시 dog_patella_best.pth 로드, /predict 에서 피그마 맞춤 JSON 응답.
이미지·영상·JSON·ZIP(프레임 이미지 묶음) 업로드 지원.
"""
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import cv2
import numpy as np

from .inference import run_predict, run_predict_from_features, run_predict_from_features_multi_frame
from .store import append_diagnosis, load_diagnosis_history, load_profile, save_profile
from .model import load_dog_patella_model
from .preprocess import parse_json_to_features
from .pose_to_features import image_to_27_features
from .schemas import PredictResponse, RecommendedCourse
from .walk_routes import get_walk_routes, get_recommended_courses, get_recommendation_reason, init_courses

# 앱 수명주기: 시작 시 모델 로드
_model = None
_device = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _device
    import torch
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        _model = load_dog_patella_model(str(_device))
    except FileNotFoundError as e:
        print(f"[Patella] Model file not found, /predict will return 503: {e}")
        _model = None
    init_courses()
    try:
        yield
    finally:
        _model = None


app = FastAPI(
    title="Patella Care AI API",
    description="슬개골 탈구 진단 (dog_patella_best.pth, 27 features)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """프로젝트 루트(Patella Care AI App)의 백엔드 API. 브라우저에서는 /docs 로 이동하면 됩니다."""
    return {
        "message": "Patella Care AI API",
        "docs": "/docs",
        "health": "/health",
        "predict": "POST /predict (이미지·영상·JSON 업로드)",
    }


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


# --- 프로필·진단 기록 (JSON 파일 저장, 재시작 후 유지) ---

@app.get("/api/profile")
def api_get_profile():
    """반려견 이름·사진 등 프로필 조회."""
    return load_profile()


@app.put("/api/profile")
def api_update_profile(body: dict = Body(default_factory=dict)):
    """프로필 수정. body에 포함된 필드만 갱신 (photo_base64=null 이면 사진 제거)."""
    kwargs = {}
    if "name" in body:
        kwargs["name"] = body["name"]
    if "breed" in body:
        kwargs["breed"] = body["breed"]
    if "age" in body:
        kwargs["age"] = body["age"]
    if "photo_base64" in body:
        kwargs["photo_base64"] = body["photo_base64"]
    return save_profile(**kwargs)


@app.get("/api/diagnosis-history")
def api_get_diagnosis_history():
    """최근 진단 기록 목록 (날짜 내림차순)."""
    return load_diagnosis_history()


@app.post("/api/diagnosis-history")
def api_add_diagnosis(
    date: str = Body(..., embed=True),
    time: str = Body(..., embed=True),
    grade: str = Body(..., embed=True),
    score: float = Body(..., embed=True),
    result: dict | None = Body(None, embed=True),
):
    """진단 한 건 추가. result 있으면 상세 결과 재조회용으로 저장."""
    append_diagnosis(date=date, time=time, grade=grade, score=score, result_snapshot=result)
    return {"ok": True, "history": load_diagnosis_history()}


# --- 산책로 추천 (공원·걷기길 CSV) ---

@app.get("/api/walk-routes")
def api_walk_routes(
    filter_type: str = "normal",
    limit: int = 100,
    latitude: float | None = None,
    longitude: float | None = None,
    category: str | None = None,
    diagnosis_grade: str | None = None,
):
    """
    공공데이터 CSV(공원 + 둘레길/걷기길) 기반 산책로 목록.
    filter_type: easy | normal | rehab
    category: 평지위주|단거리|장거리|경사 (또는 flat|short|long|slope) — 해당 조건으로 필터.
    latitude, longitude: 선택. 있으면 해당 위치에서 가까운 순으로 정렬하고 distance_from_user_km 포함.
    diagnosis_grade: 선택. 정상|1기|3기 — 있으면 진단 결과별 거리·장소 유형 기준으로 추천하고 recommendation_reason 포함해 반환.
    """
    from .walk_routes import recommend_walkway

    if diagnosis_grade and diagnosis_grade.strip() in ("정상", "1기", "3기"):
        grade = diagnosis_grade.strip()
        lat, lon = _DEFAULT_LAT, _DEFAULT_LON
        if latitude is not None and longitude is not None:
            try:
                lat = float(latitude)
                lon = float(longitude)
            except (TypeError, ValueError):
                pass
        routes_raw, reason = recommend_walkway(
            grade, lat, lon, limit=min(limit, 200)
        )
        from .walk_routes import _to_route_item

        out = [_to_route_item(r, r["distance_km"]) for r in routes_raw]
        return {"recommendation_reason": reason, "routes": out}

    return get_walk_routes(
        filter_type=filter_type,
        limit=min(limit, 200),
        user_lat=latitude,
        user_lon=longitude,
        category=category,
    )


def _is_json_type(content_type: str, filename: str) -> bool:
    return (
        content_type.startswith("application/json")
        or (filename or "").lower().endswith(".json")
    )


# Content-Type이 비어 있어도 확장자 또는 파일 시그니처로 이미지/영상 허용
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
ZIP_EXTENSIONS = {".zip"}
IMAGE_EXT_TO_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _body_looks_like_image(body: bytes) -> bool:
    """파일 시그니처(매직 바이트)로 이미지 여부 판별. 파일명이 없을 때 사용."""
    if len(body) < 12:
        return False
    if body[:2] == b"\xff\xd8":
        return True  # JPEG
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return True  # PNG
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return True  # GIF
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return True  # WebP
    if body[:2] == b"BM":
        return True  # BMP
    return False


def _body_looks_like_video(body: bytes) -> bool:
    """파일 시그니처로 영상 여부 판별."""
    if len(body) < 12:
        return False
    if body[4:8] == b"ftyp":
        return True  # MP4/MOV (ftyp 뒤에 브랜드가 옴)
    if body[:4] == b"RIFF" and body[8:12] == b"WEBM":
        return True  # WebM
    return False


def _is_image_or_video_type(content_type: str, filename: str, body: bytes) -> bool:
    if content_type.startswith("image/") or content_type.startswith("video/"):
        return True
    ext = (filename or "").lower()
    for e in IMAGE_EXTENSIONS:
        if ext.endswith(e):
            return True
    for e in VIDEO_EXTENSIONS:
        if ext.endswith(e):
            return True
    # 파일명이 없거나 blob 등일 때: 본문 시그니처로 판별
    if _body_looks_like_image(body):
        return True
    if _body_looks_like_video(body):
        return True
    return False


def _is_zip_type(content_type: str, filename: str, body: bytes) -> bool:
    """ZIP 압축 파일 여부 (동영상 프레임 이미지 묶음용)."""
    if content_type in ("application/zip", "application/x-zip-compressed"):
        return True
    ext = (filename or "").lower()
    if any(ext.endswith(e) for e in ZIP_EXTENSIONS):
        return True
    if len(body) >= 4 and body[:4] == b"PK\x03\x04":
        return True
    return False


# ZIP 내 추출 대상: .jpg, .png만 (동영상 프레임 이미지)
ZIP_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _extract_images_from_zip(zip_bytes: bytes) -> list[tuple[bytes, str]]:
    """ZIP 압축 해제 후 내부 .jpg/.png 이미지 리스트. 반환: [(bytes, content_type), ...]"""
    out: list[tuple[bytes, str]] = []
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
            for name in sorted(zf.namelist()):
                if zf.getinfo(name).is_dir():
                    continue
                ext = "." + (name.rsplit(".", 1)[-1].lower()) if "." in name else ""
                if ext not in ZIP_IMAGE_EXTENSIONS:
                    continue
                content_type = IMAGE_EXT_TO_CONTENT_TYPE.get(ext, "image/jpeg")
                try:
                    data = zf.read(name)
                    if len(data) < 100:
                        continue
                    out.append((data, content_type))
                except Exception:
                    continue
    except zipfile.BadZipFile:
        return []
    return out


def _decode_image(img_bytes: bytes) -> np.ndarray:
    """이미지 bytes → BGR numpy (OpenCV)."""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is not None:
        return img
    from PIL import Image
    pil = Image.open(BytesIO(img_bytes))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _run_predict_zip(
    zip_bytes: bytes,
    model,
    device,
) -> PredictResponse:
    """
    ZIP 처리: 압축 해제 → .jpg/.png 리스트 → 각 이미지 YOLOv8-pose로 10점 추출
    → Data_AI_Final 동일 방식으로 27차원 특징 계산 → 다중 프레임 확률 평균/대표 프레임으로 최종 진단.
    """
    images = _extract_images_from_zip(zip_bytes)
    if not images:
        raise HTTPException(
            status_code=400,
            detail="ZIP 파일에 .jpg 또는 .png 이미지가 없습니다. 동영상을 프레임별로 나눈 이미지를 넣어주세요.",
        )
    from .pose_to_features import _get_pose_model
    pose_model = _get_pose_model()
    list_features: list[np.ndarray] = []
    for img_bytes, _ in images:
        try:
            img_bgr = _decode_image(img_bytes)
            if img_bgr is None or img_bgr.size == 0:
                continue
            features, _ = image_to_27_features(img_bgr, pose_model=pose_model)
            list_features.append(features)
        except Exception:
            continue
    if not list_features:
        raise HTTPException(
            status_code=400,
            detail="ZIP 내 이미지에서 포즈를 추출할 수 없었습니다. YOLOv8-pose가 인식할 수 있는 형태의 이미지인지 확인해주세요.",
        )
    return run_predict_from_features_multi_frame(list_features, model, device)


# 위치 미제공 시 시연용 기본값 (서울시청)
_DEFAULT_LAT, _DEFAULT_LON = 37.5667, 126.9784


def _attach_recommended_courses(response: PredictResponse, latitude: str | None, longitude: str | None) -> PredictResponse:
    """위경도가 있으면 진단 결과별 상위 3개 산책로를 붙여 반환. 없으면 서울시청 기준으로 추천."""
    lat, lon = _DEFAULT_LAT, _DEFAULT_LON
    if latitude and longitude and latitude.strip() and longitude.strip():
        try:
            lat = float(latitude.strip())
            lon = float(longitude.strip())
        except ValueError:
            pass
    raw = get_recommended_courses(lat, lon, response.status, limit=3)
    courses = [
        RecommendedCourse(
            name=r["name"],
            distance=r["distance"],
            address=r["address"],
            description=r["description"],
            reason_tags=r.get("reason_tags") or [],
            lat=r.get("lat", 0),
            lon=r.get("lon", 0),
        )
        for r in raw
    ]
    reason = get_recommendation_reason(response.status)
    return response.model_copy(update={"recommended_courses": courses, "recommendation_reason": reason})


@app.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    latitude: str | None = Form(None),
    longitude: str | None = Form(None),
):
    """
    이미지·영상·JSON·ZIP 파일 업로드.
    - 이미지/영상: 27개 특징 추출 후 모델 추론.
    - ZIP: 압축 내 이미지마다 모델 추론 후, 확률(confidence)이 가장 높은 결과를 최종 진단으로 반환.
    - JSON: 27개 숫자 배열 또는 {"features": [27개]} 형태로 바로 추론.
    - latitude, longitude(선택): 현재 위치 위경도. 있으면 응답에 recommended_courses(진단별 상위 3개) 포함.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    content_type = (file.content_type or "").strip() or "application/octet-stream"
    filename = file.filename or ""
    try:
        body = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
    if not body:
        raise HTTPException(status_code=400, detail="Empty file")

    print(f"[predict] filename={filename!r} content_type={content_type!r} size={len(body)}")

    response: PredictResponse
    if _is_json_type(content_type, filename):
        try:
            import json
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        try:
            features = parse_json_to_features(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            response = run_predict_from_features(features, _model, _device)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif _is_image_or_video_type(content_type, filename, body):
        try:
            response = run_predict(body, content_type, _model, _device)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif _is_zip_type(content_type, filename, body):
        try:
            response = _run_predict_zip(body, _model, _device)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file: filename={filename!r}, content_type={content_type!r}. "
                "Use image (jpg/png/...), video (mp4/...), ZIP (프레임 이미지 묶음), or .json with 27 features."
            ),
        )
    return _attach_recommended_courses(response, latitude, longitude)
