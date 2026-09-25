from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_URL: str = "http://localhost:5173"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Planogram Compliance"

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION_NAME: str = "us-east-1"
    AWS_S3_BUCKET: str = "planogram-audits"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    PROJECT_ROOT: Path = BASE_DIR.parent

    # ML Models (pointing to project root)
    YOLO_MODEL_PATH: str = str(PROJECT_ROOT / "runs" / "grocery_baseline" / "weights" / "best.pt")
    RESNET_MODEL_PATH: str = str(PROJECT_ROOT / "outputs" / "metric_learning" / "resnet50_triplet_best.pth")
    REFERENCE_EMBEDDINGS_PATH: str = str(PROJECT_ROOT / "outputs" / "embeddings" / "reference_embeddings.npy")
    REFERENCE_LABELS_PATH: str = str(PROJECT_ROOT / "outputs" / "embeddings" / "reference_labels.json")
    YOLO_CLUSTER_EPS_RATIO: float = 0.4

    # Human-in-the-Loop & Retraining (Phase 12)
    RECOGNITION_REVIEW_THRESHOLD: float = 0.40
    MIN_NEW_TRAINING_SAMPLES: int = 20
    
    # Retraining Hyperparameters
    TRAINING_EPOCHS: int = 5
    TRAINING_LEARNING_RATE: float = 0.0001
    TRAINING_TRIPLET_MARGIN: float = 1.0
    TRAINING_EVALUATION_LOSS_THRESHOLD: float = 0.5

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()