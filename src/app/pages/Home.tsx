import { useEffect, useState } from "react";
import { Video, Calendar, Activity, Pencil, ChevronRight } from "lucide-react";
import { Link } from "react-router";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  getProfile,
  updateProfile,
  getDiagnosisHistory,
  buildMinimalResult,
  type PetProfile,
  type DiagnosisRecord,
} from "../api";

/** 기수(정상/1기/3기)에 따른 상태 점수 (0~100). 카드 표시용 */
const GRADE_CONDITION_SCORE: Record<string, number> = {
  정상: 100,
  "1기": 65,
  "3기": 30,
};

/** 기수 → 산책로 API filter_type (맞춤 산책로 추천용) */
const GRADE_TO_WALK_FILTER: Record<string, "normal" | "easy" | "rehab"> = {
  정상: "normal",
  "1기": "easy",
  "3기": "rehab",
};

const DEFAULT_IMAGE =
  "https://images.unsplash.com/photo-1710062958147-f7d458844a3f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=400";

export function Home() {
  const [profile, setProfile] = useState<PetProfile | null>(null);
  const [recentRecords, setRecentRecords] = useState<DiagnosisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editBreed, setEditBreed] = useState("");
  const [editAge, setEditAge] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    try {
      const [p, h] = await Promise.all([getProfile(), getDiagnosisHistory()]);
      setProfile(p);
      setRecentRecords(h);
      setEditName(p.name);
      setEditBreed(p.breed);
      setEditAge(p.age);
    } catch {
      setProfile({
        name: "복실이",
        breed: "말티즈",
        age: "3세",
        photo_base64: null,
      });
      setEditName("복실이");
      setEditBreed("말티즈");
      setEditAge("3세");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const syncEditForm = () => {
    if (profile) {
      setEditName(profile.name);
      setEditBreed(profile.breed);
      setEditAge(profile.age);
      setPhotoFile(null);
      setPhotoPreview(profile.photo_base64 ? `data:image/jpeg;base64,${profile.photo_base64}` : null);
    }
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    setPhotoFile(file);
    const reader = new FileReader();
    reader.onload = () => setPhotoPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      let photo_base64: string | null = null;
      if (photoFile) {
        const base64 = await new Promise<string>((res, rej) => {
          const r = new FileReader();
          r.onload = () => {
            const data = (r.result as string).split(",")[1];
            res(data ?? "");
          };
          r.onerror = rej;
          r.readAsDataURL(photoFile);
        });
        photo_base64 = base64 || null;
      }
      const updated = await updateProfile({
        name: editName.trim() || profile.name,
        breed: editBreed.trim() || profile.breed,
        age: editAge.trim() || profile.age,
        ...(photo_base64 !== null ? { photo_base64 } : {}),
      });
      setProfile(updated);
      setEditOpen(false);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const profileImage =
    profile?.photo_base64
      ? `data:image/jpeg;base64,${profile.photo_base64}`
      : DEFAULT_IMAGE;

  const getGradeBadgeStyle = (grade: string) => {
    switch (grade) {
      case "정상":
        return "bg-[var(--patella-success)] text-green-900";
      case "1기":
        return "bg-[var(--patella-warning)] text-orange-900";
      case "3기":
        return "bg-[var(--patella-danger)] text-red-900";
      default:
        return "bg-gray-200 text-gray-900";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[var(--patella-primary-light)] to-white flex items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </div>
    );
  }

  const p = profile ?? { name: "복실이", breed: "말티즈", age: "3세", photo_base64: null };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[var(--patella-primary-light)] to-white">
      <div className="max-w-md mx-auto p-6 pb-8">
        <div className="mb-6">
          <h1 className="text-2xl text-[var(--patella-primary-dark)] mb-2">
            슬개골 케어 AI
          </h1>
          <p className="text-sm text-gray-600">반려견의 관절 건강을 지켜드려요</p>
        </div>

        {/* 반려견 프로필 카드 + 편집 */}
        <Card className="mb-6 overflow-hidden shadow-lg border-0" style={{ backgroundColor: "var(--patella-card-bg)" }}>
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-24 h-24 rounded-full overflow-hidden flex-shrink-0 border-4 border-[var(--patella-primary)]">
                <img
                  src={profileImage}
                  alt={p.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl mb-2">{p.name}</h2>
                  <Dialog open={editOpen} onOpenChange={(o) => { setEditOpen(o); if (o) syncEditForm(); }}>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
                        <Pencil className="w-4 h-4" />
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-md">
                      <DialogHeader>
                        <DialogTitle>프로필 수정</DialogTitle>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                          <Label htmlFor="name">이름</Label>
                          <Input
                            id="name"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            placeholder="반려견 이름"
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="breed">품종</Label>
                          <Input
                            id="breed"
                            value={editBreed}
                            onChange={(e) => setEditBreed(e.target.value)}
                            placeholder="품종"
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="age">나이</Label>
                          <Input
                            id="age"
                            value={editAge}
                            onChange={(e) => setEditAge(e.target.value)}
                            placeholder="예: 3세"
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label>프로필 사진</Label>
                          <Input
                            type="file"
                            accept="image/*"
                            onChange={handlePhotoChange}
                          />
                          {photoPreview && (
                            <div className="mt-2 w-20 h-20 rounded-full overflow-hidden border-2 border-gray-200">
                              <img src={photoPreview} alt="미리보기" className="w-full h-full object-cover" />
                            </div>
                          )}
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)}>
                          취소
                        </Button>
                        <Button onClick={handleSaveProfile} disabled={saving}>
                          {saving ? "저장 중..." : "저장"}
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <p>{p.breed} • {p.age}</p>
                  <div className="flex items-center gap-2 mt-3">
                    <Activity className="w-4 h-4 text-[var(--patella-primary-dark)]" />
                    <span className="text-sm">종합 건강 상태</span>
                  </div>
                  <Badge className={`${getGradeBadgeStyle("정상")} mt-2`}>
                    양호
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Link to="/upload">
          <Button
            className="w-full h-20 mb-6 shadow-lg text-lg"
            style={{ backgroundColor: "var(--patella-primary)", color: "var(--primary-foreground)" }}
          >
            <Video className="w-6 h-6 mr-3" />
            슬개골 건강 진단하기
          </Button>
        </Link>

        <div className="mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-[var(--patella-primary-dark)]" />
            <h3 className="text-lg">최근 진단 기록</h3>
          </div>
          <div className="flex flex-col gap-[15px]">
            {recentRecords.length === 0 ? (
              <p className="text-sm text-gray-500 py-4">아직 진단 기록이 없어요. 진단을 진행해 보세요.</p>
            ) : (
              recentRecords.slice(0, 3).map((record) => {
                const result = record.result ?? buildMinimalResult(record.grade, record.score);
                return (
                  <Link
                    key={record.id}
                    to="/result"
                    state={{ result, date: record.date, time: record.time, fromHistory: true }}
                  >
                    <Card className="overflow-hidden border border-gray-200 hover:shadow-md transition-shadow cursor-pointer">
                      <CardContent className="p-4 flex items-center justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-600 mb-1">{record.date} {record.time}</p>
                          <div className="flex items-center gap-2">
                            <Badge className={getGradeBadgeStyle(record.grade)}>{record.grade}</Badge>
                            <span className="text-sm text-gray-500">
                              상태 점수: {GRADE_CONDITION_SCORE[record.grade] ?? record.score}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: "var(--patella-primary-light)" }}>
                            <span className="text-lg font-semibold text-[var(--patella-primary-dark)]">
                              {GRADE_CONDITION_SCORE[record.grade] ?? record.score}
                            </span>
                          </div>
                          <ChevronRight className="w-5 h-5 text-gray-400" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })
            )}
          </div>
        </div>

        {recentRecords.length > 0 && (
          <p className="text-sm text-gray-600 mb-3">
            최근 진단({recentRecords[0].grade})에 맞춘 산책로를 추천해 드려요.
          </p>
        )}
        <Link
          to="/walk-route"
          state={
            recentRecords.length > 0
              ? { filterType: GRADE_TO_WALK_FILTER[recentRecords[0].grade] ?? "normal", grade: recentRecords[0].grade }
              : undefined
          }
        >
          <Button variant="outline" className="w-full border-[var(--patella-primary)] text-[var(--patella-primary-dark)] hover:bg-[var(--patella-primary-light)]">
            맞춤 산책로 추천 보기
          </Button>
        </Link>
      </div>
    </div>
  );
}
