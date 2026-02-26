# GitHub + 링크 배포 가이드 (발표용)

코드를 GitHub에 올리고, 실제로 돌아가는 링크로 보여주는 방법입니다.

---

## 1단계: GitHub에 올리기

### 1-1. GitHub 저장소 만들기

1. [GitHub](https://github.com) 로그인
2. 우측 상단 **+** → **New repository**
3. Repository name: 예) `paw-step` (원하는 이름)
4. **Public** 선택 → **Create repository**

### 1-2. 프로젝트 폴더에서 Git 초기화 후 푸시

**프로젝트 폴더**에서 CMD 또는 PowerShell 열고:

```cmd
cd 프로젝트폴더경로
```

```cmd
git init
git add .
git status
```

→ `.env`가 목록에 **있으면 안 됩니다.** 있으면 `.gitignore`에 `.env`가 있는지 확인하고, `git add .` 다시 하면 `.env`는 제외됩니다.

```cmd
git commit -m "Initial commit: Patella Care AI App"
git branch -M main
git remote add origin https://github.com/내아이디/저장소이름.git
git push -u origin main
```

- `내아이디/저장소이름`은 본인 GitHub 사용자명과 방금 만든 저장소 이름으로 바꾸세요.
- 처음 푸시 시 GitHub 로그인(또는 토큰) 요청하면 입력하면 됩니다.

---

## 2단계: 백엔드 배포 (Render)

백엔드가 있어야 진단 API가 동작합니다.

### 2-1. Render 가입 및 새 Web Service

1. [Render](https://render.com) 가입 (GitHub 로그인 가능)
2. **Dashboard** → **New +** → **Web Service**
3. **Connect a repository**에서 방금 푸시한 GitHub 저장소 선택
4. 아래처럼 설정:

| 항목 | 값 |
|------|-----|
| **Name** | `paw-step-api` (원하는 이름) |
| **Region** | Singapore 또는 가까운 곳 |
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

5. **Advanced** → **Add Environment Variable**  
   - 필요하면 나중에 추가 (지금은 없어도 됨)

6. **Create Web Service** 클릭  
   - 첫 빌드에 5~10분 걸릴 수 있습니다 (torch 등 패키지가 커서).  
   - 완료되면 **https://paw-step-api.onrender.com** 같은 URL이 생깁니다.

7. **이 URL 복사** → 나중에 프론트엔드에서 API 주소로 씁니다.  
   - 예: `https://paw-step-api.onrender.com` (끝에 `/` 없이)

⚠️ **모델 파일**: `dog_patella_best.pth`를 `backend` 폴더에 넣어두고 **Git에 커밋**해서 올려야 Render에서도 로드됩니다. (파일이 크면 Git LFS 사용 가능.)

---

## 3단계: 프론트엔드 배포 (Vercel)

### 3-1. Vercel 가입 및 프로젝트 import

1. [Vercel](https://vercel.com) 가입 (GitHub 로그인 가능)
2. **Add New...** → **Project**
3. **Import** 할 GitHub 저장소 선택 (같은 repo, 루트가 프론트)
4. 설정:

| 항목 | 값 |
|------|-----|
| **Framework Preset** | Vite (자동 감지될 수 있음) |
| **Root Directory** | `.` (루트 그대로) |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 3-2. 환경 변수 설정 (중요)

**Environment Variables**에서 아래 두 개 추가:

| Name | Value |
|------|--------|
| `VITE_API_URL` | 2단계에서 복사한 백엔드 URL (예: `https://paw-step-api.onrender.com`) |
| `VITE_NAVER_MAP_CLIENT_ID` | 네이버 지도 Client ID (없으면 지도만 안 나오고 앱은 동작) |

- **VITE_API_URL**에 `http` 없이 `https://...` 형태로, 끝에 슬래시 없이 넣으세요.

5. **Deploy** 클릭  
   - 끝나면 **https://paw-step-xxx.vercel.app** 같은 주소가 나옵니다. **이게 발표할 링크입니다.**

---

## 4단계: 네이버 지도 (선택)

맞춤 산책로 지도를 쓰려면:

1. [네이버 클라우드 콘솔](https://console.ncloud.com/maps/application) → Maps → Application
2. 사용 중인 애플리케이션 **수정**
3. **Web 서비스 URL**에 Vercel 주소 추가  
   - 예: `https://paw-step-xxx.vercel.app`
4. 저장 후, Vercel의 `VITE_NAVER_MAP_CLIENT_ID`에 그 앱의 Client ID가 들어갔는지 확인

---

## 5단계: 링크로 공유

- **앱 링크**: Vercel 배포 URL (예: `https://paw-step-xxx.vercel.app`)
- **코드 링크**: GitHub 저장소 URL (예: `https://github.com/내아이디/paw-step`)

발표할 때는 “이 링크 들어가시면 됩니다” 하고 Vercel URL만 보내면 됩니다.

---

## 자주 나오는 문제

- **백엔드가 느리거나 503**  
  - Render 무료 티어는 한동안 요청 없으면 슬립됩니다. 첫 요청 시 깨우는 데 30초~1분 걸릴 수 있어요.  
  - 진단 버튼 누른 뒤 한 번 기다려 보세요.

- **CORS 오류**  
  - 백엔드(`main.py`)에서 이미 `allow_origins=["*"]`로 두면 됩니다.  
  - 배포 URL이 바뀌었으면 Render에서 다시 배포(Deploy) 한 번 해보세요.

- **모델 파일 없음**  
  - `backend/dog_patella_best.pth`가 GitHub에 올라가 있어야 합니다.  
  - 용량이 커서 푸시가 안 되면 [Git LFS](https://git-lfs.com) 사용하거나, Render에서 빌드 시 외부 URL로 다운로드하는 스크립트를 쓸 수 있습니다.
