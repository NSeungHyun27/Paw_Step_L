"""
프로필·진단 기록 JSON 파일 저장 (재시작 후에도 유지).
"""
from __future__ import annotations

import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
PROFILE_PATH = DATA_DIR / "pet_profile.json"
HISTORY_PATH = DATA_DIR / "diagnosis_history.json"

DEFAULT_PROFILE = {
    "name": "복실이",
    "breed": "말티즈",
    "age": "3세",
    "photo_base64": None,
}

MAX_HISTORY = 100


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_profile() -> dict:
    _ensure_data_dir()
    if not PROFILE_PATH.is_file():
        return dict(DEFAULT_PROFILE)
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_PROFILE, **data}
    except Exception:
        return dict(DEFAULT_PROFILE)


_MISSING = object()


def save_profile(
    name: str | None = _MISSING,
    breed: str | None = _MISSING,
    age: str | None = _MISSING,
    photo_base64: str | None = _MISSING,
) -> dict:
    _ensure_data_dir()
    profile = load_profile()
    if name is not _MISSING:
        profile["name"] = name or DEFAULT_PROFILE["name"]
    if breed is not _MISSING:
        profile["breed"] = breed or DEFAULT_PROFILE["breed"]
    if age is not _MISSING:
        profile["age"] = age or DEFAULT_PROFILE["age"]
    if photo_base64 is not _MISSING:
        profile["photo_base64"] = photo_base64
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return profile


def load_diagnosis_history() -> list[dict]:
    _ensure_data_dir()
    if not HISTORY_PATH.is_file():
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def append_diagnosis(
    date: str,
    time: str,
    grade: str,
    score: float,
    result_snapshot: dict | None = None,
) -> list[dict]:
    _ensure_data_dir()
    history = load_diagnosis_history()
    new_id = max((h.get("id", 0) for h in history), default=0) + 1
    record: dict = {"id": new_id, "date": date, "time": time, "grade": grade, "score": round(score, 1)}
    if result_snapshot is not None:
        record["result"] = result_snapshot
    history.insert(0, record)
    history = history[:MAX_HISTORY]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return history
