import { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router";
import { ArrowLeft, MapPin, Navigation, Clock, Ruler, TrendingUp, Loader2 } from "lucide-react";
import { Link } from "react-router";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { motion } from "motion/react";
import { getWalkRoutes, getProfile, getDiagnosisHistory, type WalkRouteItem, type WalkRouteCategory, type WalkRoutesRecommendResponse } from "../api";

const SEOUL_CENTER: [number, number] = [37.5665, 126.978];
/** 반경 2km가 보이도록 하는 줌 레벨 */
const ZOOM_2KM_RADIUS = 14;

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

const NAVER_MAP_CLIENT_ID =
  (typeof import.meta !== "undefined" && (import.meta as unknown as { env?: { VITE_NAVER_MAP_CLIENT_ID?: string } }).env?.VITE_NAVER_MAP_CLIENT_ID) || "";

/** 네이버 지도 스크립트 로드 (ncpKeyId 사용, 인증 실패 시 ncpClientId로 재시도) */
function loadNaverMapScript(): Promise<void> {
  if (typeof window !== "undefined" && window.naver?.maps) return Promise.resolve();
  if (!NAVER_MAP_CLIENT_ID) return Promise.reject(new Error("NO_CLIENT_ID"));

  const loadWithParam = (param: "ncpKeyId" | "ncpClientId"): Promise<void> =>
    new Promise((resolve, reject) => {
      const callbackName = "naverMapInit_" + param;
      const script = document.createElement("script");
      script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?${param}=${encodeURIComponent(NAVER_MAP_CLIENT_ID)}&callback=${callbackName}`;
      script.async = true;
      (window as unknown as Record<string, () => void>)[callbackName] = () => resolve();
      window.navermap_authFailure = () => reject(new Error("AUTH_FAIL"));
      script.onerror = () => reject(new Error("SCRIPT_LOAD_FAIL"));
      document.head.appendChild(script);
    });

  return loadWithParam("ncpKeyId").catch((err) => {
    if (err?.message === "AUTH_FAIL") return loadWithParam("ncpClientId");
    return Promise.reject(err);
  });
}

function NaverMap({
  center,
  zoom,
  centerOnUserWith2km,
  boundsLocations,
  userLocation,
  walkRoutes,
}: {
  center: [number, number];
  zoom: number;
  centerOnUserWith2km: [number, number] | null;
  boundsLocations: [number, number][];
  userLocation: { lat: number; lon: number } | null;
  walkRoutes: WalkRouteItem[];
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<naver.maps.Map | null>(null);
  const markersRef = useRef<naver.maps.Marker[]>([]);
  const infoWindowRef = useRef<naver.maps.InfoWindow | null>(null);
  const listenersRef = useRef<naver.maps.MapEventListener[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!mapRef.current || !NAVER_MAP_CLIENT_ID) return;
    setLoadError(null);
    let cancelled = false;
    loadNaverMapScript()
      .then(() => {
        if (cancelled || !mapRef.current || !window.naver?.maps) return;
        const naver = window.naver;
        const map = new naver.maps.Map(mapRef.current, {
          center: new naver.maps.LatLng(center[0], center[1]),
          zoom,
          scaleControl: false,
          logoControl: true,
          mapDataControl: false,
          zoomControl: true,
        });
        mapInstanceRef.current = map;

        if (centerOnUserWith2km) {
          map.setCenter(new naver.maps.LatLng(centerOnUserWith2km[0], centerOnUserWith2km[1]));
          map.setZoom(ZOOM_2KM_RADIUS);
        } else if (boundsLocations.length > 1) {
          const bounds = new naver.maps.LatLngBounds(
            new naver.maps.LatLng(
              Math.min(...boundsLocations.map((p) => p[0])),
              Math.min(...boundsLocations.map((p) => p[1]))
            ),
            new naver.maps.LatLng(
              Math.max(...boundsLocations.map((p) => p[0])),
              Math.max(...boundsLocations.map((p) => p[1]))
            )
          );
          map.fitBounds(bounds, 24);
        }
      })
      .catch((err) => {
        const msg = err?.message;
        if (msg === "NO_CLIENT_ID") setLoadError("NO_CLIENT_ID");
        else if (msg === "AUTH_FAIL") setLoadError("AUTH_FAIL");
        else setLoadError("LOAD_FAIL");
        console.error("[Naver Map]", err);
      });
    return () => {
      cancelled = true;
      listenersRef.current.forEach((l) => l?.remove?.());
      listenersRef.current = [];
      if (infoWindowRef.current) {
        infoWindowRef.current.close();
      }
      mapInstanceRef.current = null;
      markersRef.current = [];
    };
  }, [NAVER_MAP_CLIENT_ID]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.naver?.maps) return;
    const naver = window.naver;
    if (centerOnUserWith2km) {
      map.setCenter(new naver.maps.LatLng(centerOnUserWith2km[0], centerOnUserWith2km[1]));
      map.setZoom(ZOOM_2KM_RADIUS);
    } else if (boundsLocations.length === 1) {
      map.setCenter(new naver.maps.LatLng(boundsLocations[0][0], boundsLocations[0][1]));
      map.setZoom(ZOOM_2KM_RADIUS);
    } else if (boundsLocations.length > 1) {
      const bounds = new naver.maps.LatLngBounds(
        new naver.maps.LatLng(
          Math.min(...boundsLocations.map((p) => p[0])),
          Math.min(...boundsLocations.map((p) => p[1]))
        ),
        new naver.maps.LatLng(
          Math.max(...boundsLocations.map((p) => p[0])),
          Math.max(...boundsLocations.map((p) => p[1]))
        )
      );
      map.fitBounds(bounds, 24);
    }
  }, [centerOnUserWith2km, boundsLocations]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.naver?.maps) return;
    const naver = window.naver;
    listenersRef.current.forEach((l) => l?.remove?.());
    listenersRef.current = [];
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    if (userLocation) {
      const userMarker = new naver.maps.Marker({
        position: new naver.maps.LatLng(userLocation.lat, userLocation.lon),
        map,
      });
      markersRef.current.push(userMarker);
    }

    if (!infoWindowRef.current) {
      infoWindowRef.current = new naver.maps.InfoWindow({ borderWidth: 0 });
    }
    const infoWindow = infoWindowRef.current;

    const routesWithCoords = walkRoutes.filter(
      (r) => r.lat != null && r.lon != null && Number.isFinite(r.lat) && Number.isFinite(r.lon)
    );
    routesWithCoords.forEach((route) => {
      const marker = new naver.maps.Marker({
        position: new naver.maps.LatLng(route.lat, route.lon),
        map,
      });
      markersRef.current.push(marker);

      const label = route.source === "park" ? "공원" : "걷기길";
      const cardHtml = `
        <div style="
          padding: 8px 12px;
          min-width: 100px;
          max-width: 200px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
          font-size: 13px;
          font-family: inherit;
          border: 1px solid #eee;
        ">
          <div style="font-weight: 600; color: #333;">${escapeHtml(route.name)}</div>
          <div style="font-size: 11px; color: #666; margin-top: 2px;">${escapeHtml(label)}</div>
        </div>
      `;
      const listener = naver.maps.Event.addListener(marker, "click", () => {
        infoWindow.close();
        infoWindow.setContent(cardHtml);
        infoWindow.open(map, marker);
      });
      listenersRef.current.push(listener);
    });
  }, [userLocation, walkRoutes]);

  if (!NAVER_MAP_CLIENT_ID) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center gap-2 bg-gray-100 text-gray-600 text-sm p-4 text-center">
        <p className="font-medium">네이버 지도 키가 없습니다</p>
        <p>.env 파일에 VITE_NAVER_MAP_CLIENT_ID=발급받은_Client_ID 를 넣고 개발 서버를 다시 실행하세요.</p>
      </div>
    );
  }

  if (loadError === "AUTH_FAIL") {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center gap-2 bg-amber-50 text-amber-900 text-sm p-4 text-center">
        <p className="font-medium">네이버 지도 인증 실패</p>
        <p className="text-left">
          1) 콘솔에서 Application 수정 → <strong>Dynamic Map</strong>이 체크되어 있는지 확인하세요.<br />
          2) <strong>Web 서비스 URL</strong>에 사용 주소를 등록하세요. (예: http://localhost:5173 또는 실제 도메인)<br />
          3) .env에는 <strong>Client ID</strong>(클라이언트 아이디)만 넣고, Client Secret은 넣지 마세요.
        </p>
        <p className="text-xs text-amber-700">콘솔: 네이버 클라우드 플랫폼 → Application Services → Maps → Application</p>
      </div>
    );
  }

  if (loadError === "LOAD_FAIL") {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center gap-2 bg-gray-100 text-gray-600 text-sm p-4 text-center">
        <p className="font-medium">지도 스크립트를 불러오지 못했습니다</p>
        <p>네트워크 상태를 확인하거나, 잠시 후 다시 시도해주세요.</p>
      </div>
    );
  }

  return <div ref={mapRef} className="h-full w-full min-h-[256px]" />;
}

const FILTER_MAP: Record<string, "easy" | "normal" | "rehab"> = {
  "전체": "normal",
  "평지": "easy",
  "단거리": "normal",
  "경사로": "normal",
  "장거리": "normal",
};

/** 탭 id → API category 쿼리 파라미터 (없으면 미전송) */
const TAB_TO_CATEGORY: Record<string, WalkRouteCategory | null> = {
  "전체": null,
  "평지": "flat",
  "단거리": "short",
  "경사로": "slope",
  "장거리": "long",
};

/** 태그별 뱃지 스타일 (컬러풀) */
const TAG_STYLES: Record<string, { bg: string; text: string }> = {
  평지: { bg: "bg-blue-100", text: "text-blue-800" },
  단거리: { bg: "bg-emerald-100", text: "text-emerald-800" },
  장거리: { bg: "bg-violet-100", text: "text-violet-800" },
  경사: { bg: "bg-amber-100", text: "text-amber-800" },
  산책로: { bg: "bg-gray-100", text: "text-gray-700" },
};

const PAGE_SIZE = 3;

export function WalkRoute() {
  const location = useLocation();
  const diagnosisFilterType = useRef<"normal" | "easy" | "rehab" | null>(location.state?.filterType ?? null);
  const diagnosisGradeFromState = (location.state as { grade?: string } | null)?.grade ?? null;
  const [latestDiagnosisGrade, setLatestDiagnosisGrade] = useState<string | null>(null);
  const diagnosisGrade = diagnosisGradeFromState ?? latestDiagnosisGrade;
  const useDiagnosisGrade = useRef(!!diagnosisGradeFromState);
  const [activeFilter, setActiveFilter] = useState("전체");
  const [walkRoutes, setWalkRoutes] = useState<WalkRouteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [locationBanner, setLocationBanner] = useState<string | null>(null);
  const [bannerFadeOut, setBannerFadeOut] = useState(false);
  const [petName, setPetName] = useState<string>("반려견");
  const [recommendationReason, setRecommendationReason] = useState<string | null>(null);
  const bannerTimeouts = useRef<ReturnType<typeof setTimeout>[]>([]);

  const setActiveFilterAndClearDiagnosis = (tabId: string) => {
    diagnosisFilterType.current = null;
    useDiagnosisGrade.current = false;
    setActiveFilter(tabId);
  };

  useEffect(() => {
    getProfile()
      .then((p) => setPetName(p.name || "반려견"))
      .catch(() => setPetName("반려견"));
  }, []);

  // 홈바(하단 네비)에서 진입 시에도 최근 진단 기록 기반으로 추천
  useEffect(() => {
    if (diagnosisGradeFromState) return;
    getDiagnosisHistory()
      .then((history) => {
        if (history.length > 0 && ["정상", "1기", "3기"].includes(history[0].grade)) {
          setLatestDiagnosisGrade(history[0].grade);
          useDiagnosisGrade.current = true;
        }
      })
      .catch(() => {});
  }, [diagnosisGradeFromState]);

  const filters = [
    { id: "전체", label: "전체", recommended: false },
    { id: "평지", label: "평지 위주", recommended: true },
    { id: "단거리", label: "단거리", recommended: true },
    { id: "장거리", label: "장거리", recommended: false },
    { id: "경사로", label: "경사로 포함", recommended: false },
  ];

  useEffect(() => {
    setLoading(true);
    setVisibleCount(PAGE_SIZE);
    const filterType = diagnosisFilterType.current ?? (FILTER_MAP[activeFilter] ?? "normal");
    const category = TAB_TO_CATEGORY[activeFilter] ?? undefined;
    const grade = useDiagnosisGrade.current && diagnosisGrade && ["정상", "1기", "3기"].includes(diagnosisGrade) ? diagnosisGrade as "정상" | "1기" | "3기" : undefined;
    getWalkRoutes(filterType, 80, userLocation?.lat, userLocation?.lon, category ?? undefined, grade ?? undefined)
      .then((data) => {
        if (Array.isArray(data)) {
          setWalkRoutes(data);
          setRecommendationReason(null);
        } else {
          const res = data as WalkRoutesRecommendResponse;
          setWalkRoutes(res.routes ?? []);
          setRecommendationReason(res.recommendation_reason ?? null);
        }
      })
      .catch(() => {
        setWalkRoutes([]);
        setRecommendationReason(null);
      })
      .finally(() => setLoading(false));
  }, [activeFilter, userLocation, diagnosisGrade, latestDiagnosisGrade]);

  const showBannerWithFadeOut = (message: string) => {
    bannerTimeouts.current.forEach(clearTimeout);
    bannerTimeouts.current = [];
    setBannerFadeOut(false);
    setLocationBanner(message);
    const t1 = setTimeout(() => {
      setBannerFadeOut(true);
      const t2 = setTimeout(() => {
        setLocationBanner(null);
        setBannerFadeOut(false);
      }, 300);
      bannerTimeouts.current.push(t2);
    }, 2000);
    bannerTimeouts.current.push(t1);
  };

  const handleMyLocation = () => {
    setLocationError(null);
    setLocationBanner(null);
    setBannerFadeOut(false);
    if (!navigator.geolocation) {
      setLocationError("이 브라우저에서는 위치를 사용할 수 없습니다.");
      showBannerWithFadeOut("이 브라우저에서는 위치를 사용할 수 없습니다.");
      return;
    }
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setLocationLoading(false);
        showBannerWithFadeOut("📍 위치가 설정되었습니다. 가까운 순으로 정렬됩니다.");
      },
      () => {
        setLocationError("위치 허용이 필요합니다. 버튼을 다시 눌러 '허용'을 선택해주세요.");
        setLocationLoading(false);
        showBannerWithFadeOut("위치 허용이 필요합니다. 버튼을 다시 눌러 '허용'을 선택해주세요.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const visibleRoutes = walkRoutes.slice(0, visibleCount);
  const hasMore = visibleCount < walkRoutes.length;
  const loadMore = () => setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, walkRoutes.length));

  const routeCoords = walkRoutes
    .filter((r) => r.lat != null && r.lon != null && Number.isFinite(r.lat) && Number.isFinite(r.lon))
    .map((r) => [r.lat, r.lon] as [number, number]);
  const first3Coords = routeCoords.slice(0, 3);
  const boundsLocations: [number, number][] = [
    ...(userLocation ? [[userLocation.lat, userLocation.lon] as [number, number]] : []),
    ...first3Coords,
  ];
  const useFitBounds = boundsLocations.length > 1;
  const mapCenter: [number, number] =
    userLocation
      ? [userLocation.lat, userLocation.lon]
      : routeCoords.length > 0
        ? routeCoords[0]
        : SEOUL_CENTER;
  const initialZoom = userLocation ? ZOOM_2KM_RADIUS : 13;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[var(--patella-primary-light)] to-white pb-8">
      <div className="max-w-md mx-auto">
        {/* 헤더 */}
        <div className="flex items-center gap-4 p-6 pb-4">
          <Link to="/">
            <Button variant="ghost" size="icon" className="rounded-full">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl">맞춤 산책로 추천</h1>
            <p className="text-sm text-gray-600">{petName}에게 안전한 산책로</p>
          </div>
        </div>

        {/* 지도: 현재 위치 + 주변 산책로 마커 */}
        <div className="px-6 mb-4">
          <Card className="overflow-hidden border-0 shadow-lg">
            <div className="relative h-64 w-full rounded-t-lg overflow-hidden">
              <NaverMap
                center={mapCenter}
                zoom={initialZoom}
                centerOnUserWith2km={useFitBounds ? null : userLocation ? [userLocation.lat, userLocation.lon] : null}
                boundsLocations={boundsLocations}
                userLocation={userLocation}
                walkRoutes={walkRoutes}
              />
              <div className="absolute bottom-3 right-3 z-[1000]">
                <Button
                  size="sm"
                  className="bg-white text-gray-800 shadow-lg hover:bg-gray-50"
                  onClick={handleMyLocation}
                  disabled={locationLoading}
                >
                  {locationLoading ? (
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  ) : (
                    <Navigation className="w-4 h-4 mr-1" />
                  )}
                  내 위치
                </Button>
              </div>
              {locationBanner && (
                <div
                  className={`absolute bottom-3 left-3 right-24 z-[1000] px-3 py-2 rounded-lg bg-black/70 text-white text-xs transition-opacity duration-300 ease-out ${
                    bannerFadeOut ? "opacity-0" : "opacity-100"
                  }`}
                >
                  {locationBanner}
                </div>
              )}
            </div>
          </Card>
        </div>

        {(recommendationReason || diagnosisGrade) && (
          <div className="px-6 mb-3">
            <p className="text-sm text-[var(--patella-primary-dark)] font-medium">
              {recommendationReason ?? `최근 진단(${diagnosisGrade})에 맞춘 산책로예요.`}
            </p>
          </div>
        )}

        {/* 필터 버튼 */}
        <div className="px-6 mb-4">
          <div className="flex gap-2 overflow-x-auto pb-2">
            {filters.map((filter) => (
              <Button
                key={filter.id}
                variant={activeFilter === filter.id ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveFilterAndClearDiagnosis(filter.id)}
                className="flex-shrink-0"
                style={
                  activeFilter === filter.id
                    ? {
                        backgroundColor: 'var(--patella-primary)',
                        color: 'var(--primary-foreground)'
                      }
                    : {}
                }
              >
                {filter.label}
                {filter.recommended && (
                  <Badge className="ml-2 bg-green-500 text-white text-xs px-1">추천</Badge>
                )}
              </Button>
            ))}
          </div>
        </div>

        {/* 산책로 리스트 */}
        <div className="px-6 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-5 h-5 text-[var(--patella-primary-dark)]" />
            <h3 className="text-lg">
              산책로 ({visibleRoutes.length}곳 표시 {walkRoutes.length > 0 ? `/ 총 ${walkRoutes.length}곳` : ""})
              {loading && <Loader2 className="inline w-4 h-4 ml-2 animate-spin" />}
            </h3>
          </div>

          {loading && walkRoutes.length === 0 ? (
            <Card className="p-8 text-center text-gray-500">
              <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin" />
              산책로 목록을 불러오는 중…
            </Card>
          ) : (
            <>
            {visibleRoutes.map((route, index) => (
              <motion.div
                key={route.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.05, 0.3) }}
              >
                <Card className="overflow-hidden shadow-md hover:shadow-lg transition-shadow border border-gray-200">
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {(route.tags ?? []).map((tag) => {
                        const style = TAG_STYLES[tag] ?? TAG_STYLES["산책로"];
                        return (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className={`text-xs font-medium ${style.bg} ${style.text} border-0`}
                          >
                            {tag}
                          </Badge>
                        );
                      })}
                    </div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <CardTitle className="text-base mb-1 truncate">{route.name}</CardTitle>
                        <p className="text-sm text-gray-500 truncate">{route.region}</p>
                      </div>
                      <Badge className="bg-[var(--patella-success)] text-green-900 flex-shrink-0">
                        {route.difficulty}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {route.distance != null && (
                      <div className="flex items-center gap-2 rounded-lg bg-[var(--patella-primary-light)]/50 px-3 py-2">
                        <Ruler className="w-5 h-5 text-[var(--patella-primary-dark)]" />
                        <span className="text-lg font-bold text-[var(--patella-primary-dark)]">{route.distance}</span>
                        <span className="text-sm text-gray-600">코스 거리</span>
                      </div>
                    )}
                    <p className="text-sm text-gray-600 line-clamp-2">{route.description}</p>

                    <div className="flex items-center gap-4 text-sm text-gray-500 flex-wrap">
                      {route.distance_from_user_km != null && (
                        <div className="flex items-center gap-1 text-[var(--patella-primary-dark)] font-medium">
                          <MapPin className="w-4 h-4" />
                          <span>현재 위치에서 약 {route.distance_from_user_km}km</span>
                        </div>
                      )}
                      {route.duration && (
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4 text-gray-400" />
                          <span>{route.duration}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <TrendingUp className="w-4 h-4 text-gray-400" />
                        <span>{route.difficulty}</span>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline" className="text-xs border-[var(--patella-primary)] text-[var(--patella-primary-dark)]">
                        {route.source === "park" ? "공원" : "걷기길"}
                      </Badge>
                      {route.region && (
                        <Badge variant="outline" className="text-xs text-gray-600">
                          {route.region}
                        </Badge>
                      )}
                    </div>

                    <Button
                      className="w-full mt-2"
                      variant="outline"
                      style={{
                        borderColor: "var(--patella-primary)",
                        color: "var(--patella-primary-dark)",
                      }}
                      onClick={() => {
                        const query = [route.address, route.name].filter(Boolean).join(" ").trim() || route.name || "산책로";
                        window.open(`https://map.naver.com/v5/search/${encodeURIComponent(query)}`, "_blank");
                      }}
                    >
                      <Navigation className="w-4 h-4 mr-2" />
                      길안내 시작
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}

            {/* 더 추천받기 */}
            {!loading && hasMore && (
              <div className="pt-2 pb-4">
                <Button
                  variant="outline"
                  className="w-full"
                  style={{
                    borderColor: "var(--patella-primary)",
                    color: "var(--patella-primary-dark)",
                  }}
                  onClick={loadMore}
                >
                  더 추천받기 (+{Math.min(PAGE_SIZE, walkRoutes.length - visibleCount)}곳)
                </Button>
              </div>
            )}
            </>
          )}
        </div>

        {/* 안내 문구 */}
        <div className="px-6 mt-6">
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <p className="text-sm text-blue-900">
                💡 <strong>Tip:</strong> 슬개골 1기 진단 결과를 기준으로 평지 위주의 산책로를 추천해드렸어요. 
                산책 중 반려견이 불편해하면 즉시 휴식을 취해주세요.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
