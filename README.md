
# Patella Care AI App

This is a code bundle for Patella Care AI App. The original project is available at https://www.figma.com/design/gdskmEX2FP78vlG1nnQC04/Patella-Care-AI-App.

## Running the code

Run `npm i` to install the dependencies.

Run `npm run dev` to start the development server.

## USB로 옮겨서 다른 PC에서 실행하기 (발표용)

1. **폴더 통째로 USB에 복사**  
   - `.env` 파일도 같이 복사해야 네이버 지도가 동작합니다. (그 PC에만 쓸 거면 .env 포함해서 복사해도 됩니다.)

2. **해당 PC에 설치되어 있어야 하는 것**  
   - **Node.js** (LTS 권장): https://nodejs.org  
   - **Python 3.10+**: https://www.python.org  
   - **백엔드 모델 파일**: `backend` 폴더 안에 `dog_patella_best.pth` 있는지 확인.

3. **CMD(명령 프롬프트) 두 개 열기**

   **첫 번째 CMD — 백엔드**
   ```cmd
   cd 프로젝트폴더경로
   .\run-backend.bat
   ```
   → `http://localhost:8000` 에서 API 대기할 때까지 기다리기.

   **두 번째 CMD — 프론트엔드**
   ```cmd
   cd 프로젝트폴더경로
   npm i
   npm run dev
   ```
   → 터미널에 나오는 주소(예: `http://localhost:5173`)로 브라우저에서 접속.

4. **끝**  
   - 브라우저에서 해당 주소 열면 앱 사용 가능. (백엔드 CMD는 끄지 말고 켜 둔 상태로 두세요.)

## 네이버 지도 (맞춤 산책로 화면)

맞춤 산책로 추천 지도를 쓰려면 네이버 지도 API Client ID가 필요합니다.

1. [네이버 클라우드 플랫폼 콘솔](https://console.ncloud.com/maps/application) → **Application Services → Maps → Application**에서 애플리케이션 등록
2. **Application 수정**에서 **Dynamic Map**이 체크되어 있는지 확인 (필수, 아니면 429 오류)
3. **Web 서비스 URL**에 사용할 주소 등록  
   - 로컬: `http://localhost` 또는 `http://localhost:5173`  
   - 배포 시: 실제 도메인 (예: `https://your-app.com`)
4. 발급된 **Client ID**(클라이언트 아이디)만 복사
5. 프로젝트 루트에 `.env` 파일 생성 후 아래 한 줄 추가 (값은 본인 Client ID로 변경):
   ```env
   VITE_NAVER_MAP_CLIENT_ID=여기에_Client_ID_붙여넣기
   ```
6. `.env` 수정 후에는 **개발 서버를 한 번 종료했다가 다시 실행** (`npm run dev`)

⚠️ Client **Secret**이 아니라 **Client ID**를 넣어야 합니다. 인증 실패 시 앱 지도 영역에 체크할 항목 안내가 표시됩니다.

**배포 (GitHub + 링크로 보여주기):** [DEPLOY.md](./DEPLOY.md) 참고 — 1단계 GitHub 푸시 → 2단계 백엔드(Render) → 3단계 프론트(Vercel) → 링크 공유.

## ⚠️ .env는 GitHub에 올리지 마세요

- `.env`에는 API 키·시크릿이 들어가므로 **Git에 커밋하지 마세요.** (이미 `.gitignore`에 포함되어 있습니다.)
- 필요한 환경 변수 목록은 **`.env.example`**을 참고하세요.
- **배포 시** (Vercel, Render 등): 각 서비스의 **환경 변수(Environment Variables)** 설정에 `.env.example`에 적힌 이름 그대로 넣으세요. (예: `VITE_API_URL`, `VITE_NAVER_MAP_CLIENT_ID`)
