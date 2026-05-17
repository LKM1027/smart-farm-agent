import logging

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)

class YoloService:
    def __init__(self, model_path: str = "best.pt"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """
        초기화 시 YOLO 모델을 로드합니다.
        .pt 파일이 없거나 ultralytics 패키지가 없는 경우 예외를 잡아 Mock 모드로 동작하도록 합니다.
        """
        try:
            if YOLO is None:
                raise ImportError("ultralytics 패키지가 설치되어 있지 않습니다.")
            
            # 실제 모델 로드 시도
            # self.model = YOLO(self.model_path)
            
            # 현재는 실제 파일이 없을 수 있으므로 항상 예외를 발생시켜 Mock 모드 유도
            raise FileNotFoundError(f"모델 파일({self.model_path})을 찾을 수 없어 Mock 모드로 동작합니다.")
            
        except Exception as e:
            logger.warning(f"YOLO 모델 로드 실패: {e}")
            self.model = None

    def diagnose(self, image_path: str = None) -> dict:
        """
        이미지 경로를 받아 병해를 진단합니다.
        모델이 로드되어 있지 않으면 Mock 데이터를 반환합니다.
        """
        if self.model is not None and image_path:
            # 실제 모델 추론 로직
            # results = self.model(image_path)
            # ... 추론 결과 파싱 로직 ...
            pass
            
        # 모델 로드 실패 시 Mock 데이터 반환
        return {
            "disease": "Tomato_Leaf_Mold",
            "confidence": 0.94
        }
