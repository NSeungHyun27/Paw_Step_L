/**
 * 백엔드 API 베이스 URL.
 * 개발: npm run dev 시 백엔드는 보통 http://localhost:8000
 */
export const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL) ||
  "http://localhost:8000";

/** 진단 결과 기반 추천 산책로 1건 */
export interface RecommendedCourse {
  name: string;
  distance: number;
  address: string;
  description: string;
  reason_tags?: string[];
  lat?: number;
  lon?: number;
}

/** /predict 응답 타입 (Data_AI_Final 3클래스: 정상, 1기, 3기) */
export interface PredictResult {
  status: "정상" | "1기" | "3기";
  confidence: number;
  chart_data: { name: string; value: number; color: string }[];
  metrics: Record<string, number>;
  joint_angles: { joint: string; angle: number; normal: string; status: string }[];
  recommendation: {
    duration: string;
    frequency: string;
    intensity: string;
    warnings: string[];
    recommendations: string[];
  };
  walk_filter_type: "easy" | "normal" | "rehab";
  recommended_courses?: RecommendedCourse[];
  /** 진단 결과 기반 추천 이유 한 줄 (결과 리스트 상단 표시용) */
  recommendation_reason?: string;
}

/** 반려견 프로필 (백엔드 저장) */
export interface PetProfile {
  name: string;
  breed: string;
  age: string;
  photo_base64: string | null;
}

/** 진단 기록 한 건 (result 있으면 상세 결과 재조회 시 사용) */
export interface DiagnosisRecord {
  id: number;
  date: string;
  time: string;
  grade: string;
  score: number;
  result?: PredictResult;
}

export async function getProfile(): Promise<PetProfile> {
  const res = await fetch(`${API_BASE}/api/profile`);
  if (!res.ok) throw new Error("프로필 조회 실패");
  return res.json();
}

export async function updateProfile(updates: Partial<{ name: string; breed: string; age: string; photo_base64: string | null }>): Promise<PetProfile> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("프로필 저장 실패");
  return res.json();
}

export async function getDiagnosisHistory(): Promise<DiagnosisRecord[]> {
  const res = await fetch(`${API_BASE}/api/diagnosis-history`);
  if (!res.ok) return [];
  return res.json();
}

export async function addDiagnosisRecord(
  record: { date: string; time: string; grade: string; score: number },
  result?: PredictResult
): Promise<void> {
  await fetch(`${API_BASE}/api/diagnosis-history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...record, result: result ?? undefined }),
  });
}

/** 저장된 결과가 없는 기록용 최소 PredictResult 생성 */
export function buildMinimalResult(grade: string, score: number): PredictResult {
  const status = (grade === "정상" || grade === "1기" || grade === "3기" ? grade : "1기") as PredictResult["status"];
  const chartColors = { 정상: "var(--patella-success)", "1기": "var(--patella-warning)", "3기": "var(--patella-danger)" };
  const v = Math.round(score);
  const rest = 100 - v;
  const o1 = Math.floor(rest / 2);
  const o2 = rest - o1;
  const chart_data = [
    { name: "정상", value: status === "정상" ? v : o1, color: chartColors["정상"] },
    { name: "1기", value: status === "1기" ? v : (status === "정상" ? o1 : o2), color: chartColors["1기"] },
    { name: "3기", value: status === "3기" ? v : o2, color: chartColors["3기"] },
  ];
  const recommendation = {
    정상: { duration: "20-30분", frequency: "하루 2-3회", intensity: "보통", warnings: ["과도한 점프·계단 주의"], recommendations: ["평지 산책", "일정한 속도 유지"] },
    "1기": { duration: "15-20분", frequency: "하루 2-3회", intensity: "저강도", warnings: ["계단 오르내리기 최소화", "미끄러운 바닥 주의"], recommendations: ["평지 산책 권장", "천천히 걷기"] },
    "3기": { duration: "5-10분", frequency: "수의사 지시에 따름", intensity: "최소", warnings: ["무리한 운동 금지", "계단·경사 금지"], recommendations: ["반드시 수의사 상담", "재활 계획 준수"] },
  };
  return {
    status,
    confidence: score,
    chart_data,
    metrics: {},
    joint_angles: [],
    recommendation: recommendation[status],
    walk_filter_type: status === "정상" ? "normal" : status === "1기" ? "easy" : "rehab",
  };
}

/** 산책로 한 건 (공원·걷기길 CSV). 위치 허용 시 distance_from_user_km, 카테고리별 tags 포함 */
export interface WalkRouteItem {
  id: string;
  name: string;
  region: string;
  difficulty: string;
  distance: string | null;
  duration: string | null;
  description: string;
  address: string;
  lat: number;
  lon: number;
  source: "park" | "walk";
  distance_from_user_km?: number;
  /** 코스 특징 태그 (예: ["평지", "단거리"]) */
  tags?: string[];
}

/** 카테고리: 평지위주 | 단거리 | 장거리 | 경사 (영문 flat | short | long | slope) */
export type WalkRouteCategory = "flat" | "short" | "long" | "slope" | "평지위주" | "단거리" | "장거리" | "경사";

/** 진단 기반 추천 시 API가 반환하는 형태 */
export interface WalkRoutesRecommendResponse {
  recommendation_reason: string;
  routes: WalkRouteItem[];
}

export async function getWalkRoutes(
  filterType: "easy" | "normal" | "rehab" = "normal",
  limit = 100,
  latitude?: number,
  longitude?: number,
  category?: WalkRouteCategory | null,
  diagnosisGrade?: "정상" | "1기" | "3기" | null
): Promise<WalkRouteItem[] | WalkRoutesRecommendResponse> {
  const params = new URLSearchParams({ filter_type: filterType, limit: String(limit) });
  if (latitude != null && longitude != null) {
    params.set("latitude", String(latitude));
    params.set("longitude", String(longitude));
  }
  if (category != null && category !== "") {
    params.set("category", String(category));
  }
  if (diagnosisGrade != null && diagnosisGrade !== "") {
    params.set("diagnosis_grade", diagnosisGrade);
  }
  const res = await fetch(`${API_BASE}/api/walk-routes?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export async function predictApi(
  file: File,
  options?: { latitude?: number; longitude?: number }
): Promise<PredictResult> {
  const formData = new FormData();
  formData.append("file", file, file.name || "upload");
  if (options?.latitude != null && options?.longitude != null) {
    formData.append("latitude", String(options.latitude));
    formData.append("longitude", String(options.longitude));
  }
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = text;
    try {
      const j = JSON.parse(text) as { detail?: string };
      if (typeof j.detail === "string") msg = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(res.status === 503 ? "서버가 준비되지 않았습니다. 잠시 후 다시 시도해주세요." : msg || `요청 실패 (${res.status})`);
  }
  return res.json();
}
