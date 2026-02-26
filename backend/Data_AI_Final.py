import os
import json
import torch
import math
import numpy as np
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import confusion_matrix

# [특징 추출] 뼈의 정렬 상태 계산
def calculate_alignment(p1, p2, p3, p4):
    try:
        slope1 = (p2[1]-p1[1]) / (p2[0]-p1[0] + 1e-6)
        slope2 = (p4[1]-p3[1]) / (p4[0]-p3[0] + 1e-6)
        return abs(slope1 - slope2) 
    except: return 0.0

def calculate_angle(p1, p2, p3):
    try:
        a = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        b = math.sqrt((p2[0]-p3[0])**2 + (p2[1]-p3[1])**2)
        c = math.sqrt((p3[0]-p1[0])**2 + (p3[1]-p1[1])**2)
        val = (a**2 + b**2 - c**2) / (2 * a * b + 1e-6)
        angle = math.acos(max(-1.0, min(1.0, val)))
        return math.degrees(angle) / 180.0
    except: return 0.0

def calculate_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def print_class_accuracy(all_targets, all_preds):
    labels = ["정상", "1기", "3기"]
    cm = confusion_matrix(all_targets, all_preds, labels=[0, 1, 2])
    print("\n" + "="*35)
    print("📊 RTX 3060 [정상/1기/3기] 진단 결과")
    for i, label in enumerate(labels):
        total = cm[i].sum()
        if total > 0:
            acc = 100 * cm[i][i] / total
            print(f"[{label}] 정확도: {acc:.2f}% ({cm[i][i]}/{total})")
    print("="*35 + "\n")

class DogJointDataset(Dataset):
    def __init__(self, root_dir, transform=False):
        self.root_dir = root_dir 
        self.data_list = []
        self.labels = []
        self.target_map = {"정상" : 0, "1기" : 1, "3기" : 2}
        self.transform = transform 
        self._load_all_json_paths()

    def _load_all_json_paths(self):
        if not os.path.exists(self.root_dir):
            print(f"⚠️ 경로를 찾을 수 없습니다: {self.root_dir}")
            return
        for severity_folder in os.listdir(self.root_dir):
            if severity_folder not in self.target_map: continue
            label = self.target_map[severity_folder]
            severity_path = os.path.join(self.root_dir, severity_folder)
            for root, dirs, files in os.walk(severity_path):
                for file_name in files:
                    if file_name.endswith('.json'):
                        self.data_list.append(os.path.join(root, file_name))
                        self.labels.append(label)
        print(f"✅ 데이터 수집 완료: {len(self.data_list)}개 (증강 적용: {self.transform})")

    def __len__(self): return len(self.data_list)
        
    def __getitem__(self, idx):
        json_path = self.data_list[idx]
        label = self.labels[idx]
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        target_labels = [
            "Iliac crest", "Femoral greater trochanter", "Femorotibial joint", 
            "Lateral malleolus of the distal tibia", "Distal lateral aspect of the fifth metatarsus",
            "T13 Spinous precess", "Dorsal scapular spine", "Acromion/Greater tubercle",
            "Lateral humeral epicondyle", "Ulnar styloid process"
        ]
        annos = data.get('annotation_info', [])
        joint_dict = {a['label']: (float(a['x']), float(a['y'])) for a in annos}
        
        # [데이터 증강 로직]
        aug_x, aug_y = 0.0, 0.0
        if self.transform:
            # 전체 좌표 미세 이동 (Shift)
            aug_x = np.random.normal(0, 5.0) 
            aug_y = np.random.normal(0, 5.0)

        raw_keypoints = []
        for t in target_labels:
            if t in joint_dict:
                x, y = joint_dict[t]
                if self.transform:
                    # 각 점마다 미세한 떨림 추가 (Jitter)
                    x += np.random.normal(0, 2.0)
                    y += np.random.normal(0, 2.0)
                raw_keypoints.extend([x + aug_x, y + aug_y])
            else:
                raw_keypoints.extend([0.0, 0.0])
        
        keypoints = [kp / 1000.0 for kp in raw_keypoints]
        
        # 각도 계산 (증강된 좌표가 반영된 joint_dict_aug 기반이면 더 좋으나 구조상 기존값 유지)
        angles = [
            calculate_angle(joint_dict.get("Femoral greater trochanter", (0,0)), joint_dict.get("Femorotibial joint", (0,0)), joint_dict.get("Lateral malleolus of the distal tibia", (0,0))),
            calculate_angle(joint_dict.get("Iliac crest", (0,0)), joint_dict.get("Femoral greater trochanter", (0,0)), joint_dict.get("Femorotibial joint", (0,0))),
            calculate_angle(joint_dict.get("Femorotibial joint", (0,0)), joint_dict.get("Lateral malleolus of the distal tibia", (0,0)), joint_dict.get("Distal lateral aspect of the fifth metatarsus", (0,0)))
        ]
        
        alignment = calculate_alignment(
            joint_dict.get("Femoral greater trochanter", (0,0)), 
            joint_dict.get("Femorotibial joint", (0,0)),
            joint_dict.get("Femorotibial joint", (0,0)), 
            joint_dict.get("Lateral malleolus of the distal tibia", (0,0))
        )
        alignment = min(alignment, 5.0) 
        
        thigh = calculate_distance(joint_dict.get("Femoral greater trochanter", (0,0)), joint_dict.get("Femorotibial joint", (0,0)))
        calf = calculate_distance(joint_dict.get("Femorotibial joint", (0,0)), joint_dict.get("Lateral malleolus of the distal tibia", (0,0)))
        leg_ratio = min(calf / (thigh + 1e-6), 2.0)
        
        side = 0.5
        for r in data.get('pet_medical_record_info', []):
            if r.get('value') == 1: side = 0.0 if r.get('foot_position') == 'left' else 1.0
            
        size_map = {"소형견": 0.0, "중형견": 0.5, "대형견": 1.0}
        dog_size = size_map.get(data.get("size", "소형견"), 0.0)
        
        features = torch.tensor(keypoints + angles + [alignment, leg_ratio, side, dog_size], dtype=torch.float32)
        return features, torch.tensor(label, dtype=torch.long)

class DogPatellaModel(nn.Module):
    def __init__(self):
        super(DogPatellaModel, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(27, 512), 
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.4), # 증강 적용 시 드롭아웃 살짝 상향
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 3) 
        )
    def forward(self, x): return self.fc(x)

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 현재 기기: {device} (RTX 3060)")

    train_path = r".\Training\02.라벨링데이터\TL"
    val_path = r".\Validation\02.라벨링데이터\VL"
    
    # [수정] 훈련용은 증강 ON, 검증용은 증강 OFF
    train_dataset = DogJointDataset(train_path, transform=True)
    val_dataset = DogJointDataset(val_path, transform=False)
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True, pin_memory=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=512, shuffle=False, pin_memory=True, num_workers=2)
    
    # [수정] 가중치 밸런스: 정상과 3기의 비중을 적절히 조율
    weights = torch.tensor([1.2, 1.0, 4.0]).to(device)
    
    model = DogPatellaModel().to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.AdamW(model.parameters(), lr=0.0001, weight_decay=0.05)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=3, factor=0.5)

    best_acc = 0.0
    print("🚀 데이터 증강 학습 시작...")
    for epoch in range(30):
        model.train()
        r_loss = 0.0
        for i, (feat, tar) in enumerate(train_loader):
            feat, tar = feat.to(device), tar.to(device)
            optimizer.zero_grad()
            loss = criterion(model(feat), tar)
            loss.backward()
            optimizer.step()
            r_loss += loss.item()

        model.eval()
        all_preds, all_targets = [], []
        with torch.no_grad():
            for feat, tar in val_loader:
                feat, tar = feat.to(device), tar.to(device)
                _, pred = torch.max(model(feat), 1)
                all_preds.extend(pred.cpu().numpy())
                all_targets.extend(tar.cpu().numpy())
        
        accuracy = 100 * np.sum(np.array(all_preds) == np.array(all_targets)) / len(all_targets)
        print(f"⭐ Epoch [{epoch+1}/30] 전체 정확도: {accuracy:.2f}% | Loss: {r_loss/len(train_loader):.4f}")
        
        # [추가] 최고 성능 모델 저장 로직
        if accuracy > best_acc:
            best_acc = accuracy
            torch.save(model.state_dict(), "dog_patella_best.pth")
            print(f"   🏆 최고 정확도 갱신! ({accuracy:.2f}%) 모델 저장됨.")
        
        scheduler.step(r_loss)
        
        if (epoch + 1) % 5 == 0 or epoch == 29:
            print_class_accuracy(all_targets, all_preds)

    print(f"✅ 학습 완료! (최고 정확도: {best_acc:.2f}%)")
