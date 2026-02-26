# Patella Care AI - Backend (FastAPI)

피그마 디자인에 맞춘 슬개골 탈구 진단 API. `dog_patella_best.pth` (27 features 입력) 사용.

## 한 번에 실행 (권장)

프로젝트 루트에서 아래 중 하나만 실행하면, 가상환경 생성·설치·서버 실행을 한 번에 처리합니다.

- **Windows (CMD)**  
  ```cmd
  .\run-backend.bat
  ```
- **Windows (PowerShell)**  
  ```powershell
  .\run-backend.ps1
  ```

최초 1회만 의존성 설치가 이루어지고, 이후에는 바로 서버만 켜집니다.  
모델 파일 `dog_patella_best.pth`는 **backend** 폴더 안에 두세요.

## 수동 설치 및 실행

```bash
# 프로젝트 루트에서
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- **Health**: `GET /health`
- **진단**: `POST /predict` — `multipart/form-data`, 필드명 `file`, 이미지 또는 영상

## API 응답 (피그마 대응)

- `status`: 최종 진단 (정상, 1기, 2기, 3기)
- `confidence`: 확신도 (%)
- `chart_data`: 기수별 확률 (막대그래프용)
- `metrics`: 무릎 각도, 정렬 오차 등
- `joint_angles`: 고관절/슬관절/발목 각도 및 정상 범위
- `recommendation`: 기수별 산책 가이드 (시간, 빈도, 강도, 주의사항, 권장사항)
- `walk_filter_type`: 공공데이터 산책로 필터 (`easy` / `normal` / `rehab`)

## 3기 판정

- 3기 확률이 **60% 이상**일 때만 `status: "3기"`로 반환.
- 확률이 애매한 경우 더 안전한 기수(정상/1기)를 우선.

## ZIP 업로드(프레임 이미지)와 강아지 포즈 모델

`POST /predict`에 **ZIP 파일**(동영상을 프레임별로 나눈 .jpg/.png 묶음)을 보내면,  
이미지마다 **포즈 추정 → 10개 관절 좌표 → 27차원 특징**을 계산한 뒤 다중 프레임 확률을 합산해 진단합니다.

- **기본 포즈 모델**: `yolov8n-pose.pt`(사람 COCO 17점)는 **강아지 관절을 잘 잡지 못합니다.**
- **강아지 전용 모델**을 쓰려면 아래 "하는 방법"을 따라하세요.

---

### 강아지 포즈 모델 사용 방법 (단계별)

#### 1단계: ultralytics 설치

이미 `pip install -r requirements.txt`로 백엔드를 설치했다면 ultralytics는 포함되어 있습니다.  
별도로만 쓰려면:

```bash
pip install ultralytics
```

#### 2단계: 강아지 포즈 모델 학습 (dog-pose 데이터셋)

**먼저 백엔드 가상환경을 활성화**한 뒤, 아래 명령 중 하나를 실행합니다.  
`dog-pose.yaml`을 쓰면 Ultralytics가 강아지 포즈 데이터셋을 **자동 다운로드**합니다.

```bash
# 1) 가상환경 활성화 (프로젝트 루트에서)
cd backend
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux
cd ..

# 2) 학습 실행 (아래 둘 중 하나)
yolo pose train data=dog-pose.yaml model=yolo11n-pose.pt epochs=100 imgsz=640

# yolo 명령이 없다면 python -m 으로 실행
python -m ultralytics pose train data=dog-pose.yaml model=yolo11n-pose.pt epochs=100 imgsz=640
```

> ⚠️ **Windows에서 `yolo`를 찾을 수 없다고 나오면**  
> `python -m ultralytics pose train data=dog-pose.yaml model=yolo11n-pose.pt epochs=100 imgsz=640` 를 사용하세요.  
> 반드시 **backend 가상환경이 활성화된 상태**에서 실행해야 합니다 (`cd backend` → `.venv\Scripts\activate`).

- **데이터**: 약 6,700장 학습 / 1,700장 검증, 24개 키포인트 (강아지 전용).
- **시간**: GPU 있으면 1~2시간 내외, CPU만 있으면 더 걸릴 수 있음.
- **결과**: 학습이 끝나면 `runs/pose/train/weights/best.pt` 에 최적 가중치가 저장됩니다.

#### 3단계: 학습된 가중치를 프로젝트에 복사

`best.pt`를 이 프로젝트에서 쓰기 쉽게 복사합니다.

**방법 A – backend 폴더에 두기 (자동 인식)**

```bash
# 학습이 끝난 폴더에서 (runs/pose/train/weights/ 에 best.pt 가 있음)
copy runs\pose\train\weights\best.pt "C:\Users\...\Downloads\Patella Care AI App\backend\yolov8n-pose-dog.pt"
```

또는 PowerShell:

```powershell
Copy-Item runs\pose\train\weights\best.pt "C:\Users\...\Downloads\Patella Care AI App\backend\yolov8n-pose-dog.pt"
```

`"C:\Users\...\Downloads\Patella Care AI App"` 부분을 **실제 프로젝트 경로**로 바꾸세요.  
이렇게 하면 **환경 변수 없이** backend가 `yolov8n-pose-dog.pt`를 자동으로 찾습니다.

**방법 B – 다른 경로에 두고 환경 변수로 지정**

```bash
# Windows CMD
set POSE_MODEL_PATH=C:\경로\best.pt

# Windows PowerShell
$env:POSE_MODEL_PATH = "C:\경로\best.pt"

# macOS / Linux
export POSE_MODEL_PATH=/경로/best.pt
```

서버를 **이 터미널에서** 실행하면 해당 경로의 모델이 로드됩니다.

#### 4단계: 백엔드 서버 실행

프로젝트 루트에서:

```bash
.\run-backend.bat
```

또는 수동으로:

```bash
cd backend
.venv\Scripts\activate
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

서버 로그에 `Loading dog pose model: ...` 이 보이면 강아지 포즈 모델이 적용된 것입니다.  
`yolov8n-pose.pt(사람용)를 사용합니다` 라고 나오면 아직 사람용 모델이 쓰이고 있는 상태입니다.

#### 5단계: ZIP으로 진단 테스트

1. 강아지 걸음 영상을 프레임별로 잘라 .jpg 또는 .png로 저장한 뒤, 하나의 **ZIP 파일**로 압축합니다.
2. 앱의 **슬개골 건강 진단** 화면에서 해당 ZIP을 업로드하고 **AI 분석 시작**을 누릅니다.
3. 백엔드가 ZIP 안 이미지마다 강아지 포즈 → 27차원 특징 → 슬개골 모델로 진단한 뒤, 프레임을 합산해 최종 결과를 돌려줍니다.

---

### 요약 (옵션 정리)

| 방법 | 설명 |
|------|------|
| **1) 환경 변수** | `POSE_MODEL_PATH` 또는 `DOG_POSE_MODEL_PATH`에 학습된 `.pt` 경로 지정. |
| **2) dog-pose 학습** | `yolo pose train data=dog-pose.yaml model=yolo11n-pose.pt epochs=100 imgsz=640` 후 `best.pt` 사용. |
| **3) 자동 탐색** | `yolov8n-pose-dog.pt` 또는 `yolo11n-pose-dog.pt` 를 backend/프로젝트 루트에 두면 자동 로드. |

- 24점 출력 모델(dog-pose 학습) → 강아지 24점 매핑 사용  
- 17점 출력 모델(COCO 사람) → 기존 17점 매핑 사용(강아지 인식 제한적)
