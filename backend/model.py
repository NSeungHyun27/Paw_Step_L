"""
Data_AI_Final.py와 동일한 강아지 슬개골 탈구 진단 모델.
27 features -> 3 classes (정상, 1기, 3기). dog_patella_best.pth 로드.
"""
from pathlib import Path

import torch
import torch.nn as nn

NUM_FEATURES = 27
NUM_CLASSES = 3
CLASS_NAMES = ("정상", "1기", "3기")


class DogPatellaModel(nn.Module):
    """
    Data_AI_Final.py와 동일한 구조.
    Linear(27, 512) -> BN -> ReLU -> Dropout(0.4) -> Linear(512, 256) -> ReLU -> Linear(256, 3)
    """
    def __init__(self):
        super(DogPatellaModel, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(27, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 3),
        )
        self.in_features = NUM_FEATURES
        self.num_classes = NUM_CLASSES

    def forward(self, x):
        if x.dim() == 1:
            x = x.unsqueeze(0)
        return self.fc(x)


def get_model_path() -> Path:
    """dog_patella_best.pth 경로 (backend 폴더)."""
    return Path(__file__).resolve().parent / "dog_patella_best.pth"


def load_dog_patella_model(device: str | None = None) -> DogPatellaModel:
    """Data_AI_Final에서 저장한 state_dict 로드."""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)
    path = get_model_path()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    try:
        state = torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(path, map_location=device)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]

    model = DogPatellaModel()
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        print(f"[Patella] Model load: missing keys: {missing}")
    if unexpected:
        print(f"[Patella] Model load: unexpected keys: {unexpected}")
    if not missing and not unexpected:
        print("[Patella] Model loaded OK (Data_AI_Final 구조, 3 classes)")
    model.to(device)
    model.eval()
    return model
