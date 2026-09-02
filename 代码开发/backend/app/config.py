"""
全局配置模块

使用 Pydantic Settings 管理配置，支持两种配置方式：
1. 代码里的默认值（开箱即用，无需任何配置）
2. backend/.env 文件覆盖（可选，把 .env.example 复制为 .env 修改即可）

配置项包括：数据库路径、模型路径、上传目录、结果目录、日志级别、检测参数等。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（本文件在 backend/app/ 下，向上两级）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用全局配置（环境变量同名大写可覆盖，如 DATABASE_PATH）"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",      # 可选的配置文件
        env_file_encoding="utf-8",
        extra="ignore",                  # 忽略未知环境变量
    )

    # ---------- 路径配置 ----------
    # 数据库路径（SQLite 文件）
    DATABASE_PATH: str = (BASE_DIR / "data" / "defect_detection.db").as_posix()
    # YOLOv8 训练好的模型文件路径
    MODEL_PATH: str = (BASE_DIR / "models" / "best.pt").as_posix()
    # 上传原图保存目录
    UPLOAD_DIR: str = (BASE_DIR / "uploads").as_posix()
    # 检测结果标注图保存目录
    RESULT_DIR: str = (BASE_DIR / "results").as_posix()
    # 预处理中间图像临时目录
    TEMP_DIR: str = (BASE_DIR / "temp").as_posix()
    # 日志目录
    LOG_DIR: str = (BASE_DIR / "logs").as_posix()

    # ---------- 日志配置 ----------
    LOG_LEVEL: str = "INFO"              # DEBUG / INFO / WARNING / ERROR

    # ---------- 检测参数 ----------
    CONF_THRESHOLD: float = 0.25         # 置信度阈值（低于该值的框被丢弃）
    IOU_THRESHOLD: float = 0.45          # IoU 阈值（重叠框去重用）
    IMG_SIZE: int = 640                  # 模型输入图像尺寸
    MAX_UPLOAD_SIZE_MB: int = 10         # 上传文件大小上限（MB）
    INFERENCE_TIMEOUT: float = 60.0      # 单张推理超时（秒）

    def ensure_dirs(self) -> None:
        """确保所有运行所需目录存在（启动时自动创建）"""
        for d in (
            self.UPLOAD_DIR,
            self.RESULT_DIR,
            self.TEMP_DIR,
            self.LOG_DIR,
            Path(self.DATABASE_PATH).parent,
            Path(self.MODEL_PATH).parent,
        ):
            Path(d).mkdir(parents=True, exist_ok=True)


# 全局唯一配置实例（其他模块统一 from app.config import settings 使用）
settings = Settings()
settings.ensure_dirs()
