import { useEffect, useRef, useState } from "react";
import { ArrowLeft, AlertCircle, Clock, MapPin, ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { motion } from "motion/react";
import type { PredictResult } from "../api";
import { addDiagnosisRecord } from "../api";

function formatDateTime() {
  const d = new Date();
  return {
    date: d.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" }).replace(/\. /g, ".").replace(/\.$/, ""),
    time: d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false }),
  };
}

const MOCK_RESULT: PredictResult = {
  status: "1기",
  confidence: 78,
  chart_data: [
    { name: "정상", value: 15, color: "var(--patella-success)" },
    { name: "1기", value: 78, color: "var(--patella-warning)" },
    { name: "3기", value: 7, color: "var(--patella-danger)" },
  ],
  metrics: {},
  joint_angles: [
    { joint: "고관절", angle: 125, normal: "120-135°", status: "정상" },
    { joint: "슬관절", angle: 142, normal: "135-150°", status: "주의" },
    { joint: "발목관절", angle: 130, normal: "125-140°", status: "정상" },
  ],
  recommendation: {
    duration: "15-20분",
    frequency: "하루 2-3회",
    intensity: "저강도",
    warnings: ["계단 오르내리기 최소화", "미끄러운 바닥 주의", "급격한 방향 전환 자제", "점프나 과격한 운동 피하기"],
    recommendations: ["평지 산책 권장", "천천히 일정한 속도로 걷기", "하네스 착용 권장"],
  },
  walk_filter_type: "easy",
};

export function Result() {
  const location = useLocation();
  const navigate = useNavigate();
  const apiResult = location.state?.result as PredictResult | undefined;
  const stateDate = location.state?.date as string | undefined;
  const stateTime = location.state?.time as string | undefined;
  const fromHistory = location.state?.fromHistory === true;
  const { date: defaultDate, time: defaultTime } = formatDateTime();
  const date = stateDate ?? defaultDate;
  const time = stateTime ?? defaultTime;
  const savedToHistory = useRef(false);
  const [courseIndex, setCourseIndex] = useState(0);

  useEffect(() => {
    if (!apiResult) navigate("/upload", { replace: true });
  }, [apiResult, navigate]);

  useEffect(() => {
    setCourseIndex(0);
  }, [apiResult?.recommended_courses]);

  useEffect(() => {
    if (fromHistory || !apiResult || savedToHistory.current) return;
    savedToHistory.current = true;
    addDiagnosisRecord(
      { date, time, grade: apiResult.status, score: apiResult.confidence },
      apiResult
    ).catch(() => {});
  }, [fromHistory, apiResult, date, time]);

  if (!apiResult) return null;

  const diagnosisResult = {
    grade: apiResult.status,
    probability: apiResult.confidence / 100,
    date,
    time,
  };
  const walkPrescription = apiResult.recommendation;

  const getGradeBadgeStyle = (grade: string) => {
    switch (grade) {
      case "정상":
        return "bg-[var(--patella-success)] text-green-900 text-lg px-6 py-2";
      case "1기":
        return "bg-[var(--patella-warning)] text-orange-900 text-lg px-6 py-2";
      case "2기":
        return "bg-[var(--patella-warning)] text-orange-900 text-lg px-6 py-2";
      case "3기":
        return "bg-[var(--patella-danger)] text-red-900 text-lg px-6 py-2";
      default:
        return "bg-gray-200 text-gray-900 text-lg px-6 py-2";
    }
  };

  /** 진단 결과별 추천 이유 문구 (칩용) */
  const getRecommendReasonChips = (): string[] => {
    switch (apiResult.status) {
      case "정상":
        return ["가까운 거리"];
      case "1기":
        return ["평지·쉬운 코스", "2km 이내"];
      case "3기":
        return ["짧은 거리(1km 이내)", "공원 위주", "경사 없음"];
      default:
        return ["맞춤 추천"];
    }
  };

  const openMapWithAddress = (address: string, name: string, lat?: number, lon?: number) => {
    if (lat != null && lon != null && lat !== 0 && lon !== 0) {
      const naverUrl = `https://map.naver.com/v5/?c=${lon},${lat},15,0,0,0,dh`;
      window.open(naverUrl, "_blank");
      return;
    }
    const query = (address || name || "").trim() || "산책로";
    window.open(`https://map.naver.com/v5/search/${encodeURIComponent(query)}`, "_blank");
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[var(--patella-primary-light)] to-white pb-8">
      <div className="max-w-md mx-auto p-6">
        {/* 헤더 */}
        <div className="flex items-center gap-4 mb-6">
          <Link to="/">
            <Button variant="ghost" size="icon" className="rounded-full">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl">진단 결과 리포트</h1>
            <p className="text-sm text-gray-600">{diagnosisResult.date} {diagnosisResult.time}</p>
          </div>
        </div>

        {/* 진단 결과 배지 */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="mb-6"
        >
          <Card className="border-0 shadow-lg overflow-hidden" style={{ backgroundColor: 'var(--patella-card-bg)' }}>
            <CardContent className="p-8 text-center">
              <p className="text-sm text-gray-600 mb-3">슬개골 탈구 진단 결과</p>
              <Badge className={getGradeBadgeStyle(diagnosisResult.grade)}>
                {diagnosisResult.grade}
              </Badge>
              <p className="text-sm text-gray-500 mt-4">
                AI 신뢰도: {(diagnosisResult.probability * 100).toFixed(0)}%
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* 맞춤형 산책 처방 */}
        <Card className="mb-6 shadow-md border-2 border-[var(--patella-primary)]">
          <CardHeader className="bg-[var(--patella-primary-light)]">
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="w-5 h-5" />
              맞춤형 산책 처방
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-blue-50 text-center">
                  <p className="text-xs text-gray-600 mb-1">시간</p>
                  <p className="font-semibold text-sm">{walkPrescription.duration}</p>
                </div>
                <div className="p-3 rounded-lg bg-blue-50 text-center">
                  <p className="text-xs text-gray-600 mb-1">빈도</p>
                  <p className="font-semibold text-sm">{walkPrescription.frequency}</p>
                </div>
                <div className="p-3 rounded-lg bg-blue-50 text-center">
                  <p className="text-xs text-gray-600 mb-1">강도</p>
                  <p className="font-semibold text-sm">{walkPrescription.intensity}</p>
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4 text-orange-600" />
                  <p className="text-sm font-medium">주의사항</p>
                </div>
                <ul className="space-y-1">
                  {walkPrescription.warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                      <span className="text-orange-600 mt-1">•</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="w-4 h-4 text-green-600" />
                  <p className="text-sm font-medium">권장사항</p>
                </div>
                <ul className="space-y-1">
                  {walkPrescription.recommendations.map((rec, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                      <span className="text-green-600 mt-1">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 진단 결과 기반 추천 이유 한 줄 (기수별 항상 표시) */}
        {apiResult.recommendation_reason && (
          <p className="text-sm text-[var(--patella-primary-dark)] font-medium mb-3 px-1">
            {apiResult.recommendation_reason}
          </p>
        )}

        {/* 🐾 내 주변 맞춤 산책로 Top 3 (위치 기반) - 좌우 화살표로 이동 */}
        {apiResult.recommended_courses && apiResult.recommended_courses.length > 0 && (() => {
          const courses = apiResult.recommended_courses!;
          const current = courses[courseIndex] ?? courses[0];
          const goPrev = () => setCourseIndex((i) => (i <= 0 ? courses.length - 1 : i - 1));
          const goNext = () => setCourseIndex((i) => (i >= courses.length - 1 ? 0 : i + 1));
          return (
            <>
              <Card className="mb-6 shadow-md overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <span role="img" aria-label="paw">🐾</span>
                    내 주변 맞춤 산책로 Top 3
                  </CardTitle>
                  <p className="text-xs text-gray-500 mt-1">현재 위치 기준 가까운 순 · 좌우 화살표로 이동</p>
                </CardHeader>
              <CardContent className="px-2 pb-4 pt-0">
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="flex-shrink-0 rounded-full h-10 w-10"
                    style={{ borderColor: "var(--patella-primary)", color: "var(--patella-primary-dark)" }}
                    onClick={goPrev}
                    aria-label="이전 코스"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </Button>
                  <div className="flex-1 min-w-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                    <p className="font-semibold text-[var(--patella-primary-dark)] truncate" title={current.name}>
                      {current.name}
                    </p>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">{current.description}</p>
                    <p className="text-xs text-gray-500 mt-2 flex items-start gap-1">
                      <MapPin className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                      <span className="line-clamp-2">{current.address || "주소 없음"}</span>
                    </p>
                    <p className="text-xs font-medium text-gray-600 mt-2">
                      거리 약 {current.distance.toFixed(1)} km
                    </p>
                    {(current.reason_tags && current.reason_tags.length > 0) && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {current.reason_tags.map((tag, i) => (
                          <Badge
                            key={i}
                            variant="outline"
                            className="text-xs border-[var(--patella-primary)] text-[var(--patella-primary-dark)]"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full mt-3 gap-1.5"
                      style={{ borderColor: "var(--patella-primary)", color: "var(--patella-primary-dark)" }}
                      onClick={() => openMapWithAddress(current.address, current.name, current.lat, current.lon)}
                    >
                      <ExternalLink className="w-4 h-4" />
                      지도에서 보기 (네이버 지도)
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="flex-shrink-0 rounded-full h-10 w-10"
                    style={{ borderColor: "var(--patella-primary)", color: "var(--patella-primary-dark)" }}
                    onClick={goNext}
                    aria-label="다음 코스"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </Button>
                </div>
                <div className="flex justify-center gap-1.5 mt-3">
                  {courses.map((_, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setCourseIndex(i)}
                      className={`h-2 rounded-full transition-all ${
                        i === courseIndex
                          ? "w-5 bg-[var(--patella-primary)]"
                          : "w-2 bg-gray-300 hover:bg-gray-400"
                      }`}
                      aria-label={`${i + 1}번 코스`}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
            </>
          );
        })()}

        {/* 액션 버튼 */}
        <div className="flex flex-col gap-[20px]">
          <Link
            to="/walk-route"
            state={{
              filterType: apiResult.status === "정상" ? "normal" : apiResult.status === "1기" ? "easy" : "rehab",
              grade: apiResult.status,
            }}
          >
            <Button
              className="w-full h-12 shadow-lg"
              style={{
                backgroundColor: 'var(--patella-primary)',
                color: 'var(--primary-foreground)'
              }}
            >
              맞춤 산책로 추천받기
            </Button>
          </Link>
          <Link to="/">
            <Button variant="outline" className="w-full">
              홈으로 돌아가기
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
