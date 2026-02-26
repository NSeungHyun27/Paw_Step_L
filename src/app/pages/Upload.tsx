import { useState, useRef } from "react";
import { Upload as UploadIcon, ArrowLeft, CheckCircle2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { motion } from "motion/react";
import { predictApi } from "../api";

export function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const isAcceptedFile = (f: File) =>
    f.type.startsWith("video/") ||
    f.type.startsWith("image/") ||
    f.type === "application/json" ||
    f.type === "application/zip" ||
    f.name.toLowerCase().endsWith(".json") ||
    f.name.toLowerCase().endsWith(".zip");

  const handleFileChange = (selectedFile: File | null) => {
    if (selectedFile && isAcceptedFile(selectedFile)) {
      setFile(selectedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFileChange(droppedFile);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsProcessing(true);
    setProgress(0);
    setError(null);
    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 10 : prev));
    }, 400);
    try {
      let location: { latitude: number; longitude: number } | undefined;
      if (navigator.geolocation) {
        try {
          const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000, maximumAge: 60000 });
          });
          location = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
        } catch {
          /* 위치 미제공 시 추천 코스 없이 진행 */
        }
      }
      const result = await predictApi(file, location);
      setProgress(100);
      clearInterval(progressInterval);
      setTimeout(() => navigate("/result", { state: { result } }), 500);
    } catch (e) {
      clearInterval(progressInterval);
      setError(e instanceof Error ? e.message : "진단 요청에 실패했습니다.");
      setIsProcessing(false);
      setProgress(0);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[var(--patella-primary-light)] to-white">
      <div className="max-w-md mx-auto p-6">
        {/* 헤더 */}
        <div className="flex items-center gap-4 mb-6">
          <Link to="/">
            <Button variant="ghost" size="icon" className="rounded-full">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl">슬개골 건강 진단</h1>
            <p className="text-sm text-gray-600">영상·이미지·ZIP(프레임 이미지)·JSON(27개 특징) 업로드</p>
            <p className="text-xs text-gray-500 mt-1">📍 위치 허용 시 진단 결과에 가까운 추천 산책로(Top 3)가 표시됩니다</p>
          </div>
        </div>

        {!isProcessing ? (
          <>
            {/* 파일 업로드 영역 */}
            <Card
              className={`mb-6 border-2 border-dashed transition-all cursor-pointer ${
                isDragging
                  ? 'border-[var(--patella-primary)] bg-[var(--patella-primary-light)]'
                  : 'border-gray-300 hover:border-[var(--patella-primary)]'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <CardContent className="p-12">
                <div className="flex flex-col items-center justify-center text-center">
                  <div
                    className="w-20 h-20 rounded-full flex items-center justify-center mb-4"
                    style={{ backgroundColor: 'var(--patella-primary-light)' }}
                  >
                    <UploadIcon className="w-10 h-10 text-[var(--patella-primary-dark)]" />
                  </div>
                  
                  {file ? (
                    <>
                      <CheckCircle2 className="w-6 h-6 text-green-600 mb-2" />
                      <p className="font-medium text-gray-800 mb-1">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-lg font-medium text-gray-800 mb-2">
                        파일을 드래그하거나 클릭하여 선택
                      </p>
                      <p className="text-sm text-gray-500 mb-4">
                        지원 형식: MP4, MOV, JPG, PNG, ZIP(프레임 이미지), JSON (27개 특징)
                      </p>
                      <p className="text-xs text-gray-400">
                        반려견이 걷는 모습을 측면에서 촬영한 영상이 가장 정확합니다
                      </p>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            <input
              ref={fileInputRef}
              type="file"
              accept="video/*,image/*,.zip,application/zip,.json,application/json"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            />

            {/* 안내사항 */}
            <Card className="mb-6 bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <h4 className="font-medium text-blue-900 mb-2">📸 촬영 가이드</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• 반려견이 자연스럽게 걷는 모습을 촬영해주세요</li>
                  <li>• 측면에서 전신이 보이도록 촬영하면 정확도가 높아집니다</li>
                  <li>• 최소 3초 이상의 영상을 권장합니다</li>
                  <li>• 밝은 장소에서 촬영해주세요</li>
                </ul>
              </CardContent>
            </Card>

            {error && (
              <p className="text-sm text-red-600 mb-3">{error}</p>
            )}
            {/* 분석 버튼 */}
            <Button
              className="w-full h-14 shadow-lg text-lg"
              style={{
                backgroundColor: file ? 'var(--patella-primary)' : 'var(--muted)',
                color: file ? 'var(--primary-foreground)' : 'var(--muted-foreground)'
              }}
              disabled={!file}
              onClick={handleAnalyze}
            >
              AI 분석 시작하기
            </Button>
          </>
        ) : (
          /* 분석 중 화면 */
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-12"
          >
            <Card className="border-0 shadow-lg" style={{ backgroundColor: 'var(--patella-card-bg)' }}>
              <CardContent className="p-8">
                <div className="text-center">
                  {/* 걷는 강아지 애니메이션 */}
                  <motion.div
                    animate={{
                      x: [0, 100, 0],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                    className="mb-8 flex justify-center"
                  >
                    <div className="text-6xl">🐕</div>
                  </motion.div>

                  <h3 className="text-xl mb-2">AI가 관절 각도를 분석 중입니다...</h3>
                  <p className="text-sm text-gray-600 mb-6">
                    영상을 정밀하게 분석하고 있어요
                  </p>

                  <Progress value={progress} className="h-3 mb-4" />
                  <p className="text-sm font-medium text-[var(--patella-primary-dark)]">
                    {progress}%
                  </p>
                </div>
              </CardContent>
            </Card>

            <div className="mt-6 space-y-3">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="flex items-center gap-3 text-sm text-gray-600"
              >
                <div className="w-2 h-2 rounded-full bg-[var(--patella-primary)]" />
                <span>걸음걸이 패턴 감지 중...</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="flex items-center gap-3 text-sm text-gray-600"
              >
                <div className="w-2 h-2 rounded-full bg-[var(--patella-primary)]" />
                <span>관절 각도 계산 중...</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 }}
                className="flex items-center gap-3 text-sm text-gray-600"
              >
                <div className="w-2 h-2 rounded-full bg-[var(--patella-primary)]" />
                <span>진단 결과 생성 중...</span>
              </motion.div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
