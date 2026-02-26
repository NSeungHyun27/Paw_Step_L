# Feature Engineering 한 줄씩 비교: Data_AI_Final vs 서버

## 1. 특징 추출 순서 (27개 리스트)

| # | Data_AI_Final.py | 서버 (feature_extract.py) | 일치 |
|---|------------------|---------------------------|------|
| 키포인트 순서 | `target_labels` 10개 순서대로 `[x+aug_x, y+aug_y]` 또는 `[0,0]` | 동일 `target_labels` 순서로 `extend([x, y])` | ✅ |
| 0–19 | `keypoints = [kp / 1000.0 for kp in raw_keypoints]` | `keypoints = [kp / 1000.0 for kp in raw_keypoints]` | ✅ |
| 20 | `calculate_angle(trochanter, femorotibial, malleolus)` | `calculate_angle(..., (0,0))` 동일 인자 순서 | ✅ |
| 21 | `calculate_angle(iliac, trochanter, femorotibial)` | 동일 | ✅ |
| 22 | `calculate_angle(femorotibial, malleolus, fifth_metatarsus)` | 동일 | ✅ |
| 23 | `alignment = calculate_alignment(...); alignment = min(alignment, 5.0)` | `calculate_alignment(...)` 내부에서 `return min(..., 5.0)` | ✅ (결과 동일) |
| 24 | `leg_ratio = min(calf / (thigh + 1e-6), 2.0)` | 동일 | ✅ |
| 25 | `side = 0.5` → `pet_medical_record_info`에서 `value==1`이면 `left`→0.0 else 1.0 | JSON에 있으면 `_side_and_size_from_data`로 동일 로직 적용 | ✅ (수정 반영) |
| 26 | `size_map.get(data.get("size","소형견"), 0.0)` | `_side_and_size_from_data`에서 `{"소형견":0.0,"중형견":0.5,"대형견":1.0}` 동일 적용 | ✅ (수정 반영) |

**결론: 27개 데이터가 리스트에 담기는 순서는 두 코드에서 동일합니다.**

---

## 2. 정규화 계수

| 항목 | Data_AI_Final.py | 서버 | 일치 |
|------|------------------|------|------|
| 좌표 나눗셈 | `kp / 1000.0` | `kp / 1000.0` | ✅ |
| 각도 스케일 | `math.degrees(angle) / 180.0` | `math.degrees(angle) / 180.0` | ✅ |
| alignment 상한 | `5.0` | `5.0` | ✅ |
| leg_ratio 분모 | `thigh + 1e-6` | `thigh + 1e-6` | ✅ |
| leg_ratio 상한 | `2.0` | `2.0` | ✅ |

**결론: 좌표/각도/상한 등 사용하는 숫자(1000.0, 180.0, 5.0, 2.0)가 두 코드에서 동일합니다.**

---

## 3. 범주형 데이터 변환

| 항목 | Data_AI_Final.py | 서버 | 일치 |
|------|------------------|------|------|
| foot_position → side | `side = 0.0 if r.get('foot_position') == 'left' else 1.0` (value==1일 때) | `_side_and_size_from_data`: `0.0 if r.get("foot_position") == "left" else 1.0` | ✅ |
| size → dog_size | `size_map = {"소형견": 0.0, "중형견": 0.5, "대형견": 1.0}` | 동일 딕셔너리 사용 | ✅ |
| 기본값 | `data.get("size", "소형견")` → 없으면 0.0 | `data.get("size", "소형견")`, `.get(..., 0.0)` | ✅ |

**결론: size·foot_position을 숫자로 바꿀 때 사용하는 딕셔너리와 조건이 동일합니다. (JSON에 `annotation_info` 있을 때 서버에서도 `size`, `pet_medical_record_info`를 파싱해 적용함.)**

---

## 4. 모델 가중치 로드 / eval 모드

| 항목 | 서버 (model.py) | 비고 |
|------|-----------------|------|
| 로드 후 평가 모드 | `model.eval()` (69행) 호출 후 `return model` | ✅ |
| 호출 위치 | `load_dog_patella_model()` 내부, `model.to(device)` 직후 | ✅ |

**결론: model.eval()이 반드시 켜져 있어, BatchNorm/Dropout이 고정되고 추론 결과가 매번 동일합니다.**
