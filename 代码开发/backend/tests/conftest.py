"""
pytest 全局配置

测试隔离策略：
1. 数据库：使用内存 SQLite（StaticPool），DAO 的会话工厂被替换，不碰真实数据库
2. 文件目录：uploads/results/temp 指向临时目录，测完自动清理
3. 模型：API 测试注入 FakeDetector（不加载 YOLOv8 模型，测试秒级完成）
"""
import io
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")

# 把 backend 目录加入模块搜索路径，保证 from app.xxx 可用
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.detection_record import DetectionRecord  # noqa: F401 注册模型


class FakeDetector:
    """测试用假检测器：不加载模型，返回固定检测结果（1 裂纹 + 1 划痕）"""

    demo_mode = False

    def get_status(self):
        return {"model_loaded": False, "device": "cpu", "demo_mode": False, "demo_reason": ""}

    def detect(self, image_path, timeout=None):
        return {
            "boxes": [[0.10, 0.10, 0.45, 0.45], [0.55, 0.55, 0.90, 0.90]],
            "class_ids": [0, 5],
            "confidences": [0.92, 0.88],
            "class_names": ["裂纹", "划痕"],
            "inference_time": 0.01,
        }


@pytest.fixture(scope="session")
def test_engine():
    """会话级内存 SQLite 引擎"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_env(test_engine, tmp_path, monkeypatch):
    """
    每个测试自动生效的隔离环境：
    - DAO 会话工厂 -> 内存数据库
    - 文件目录 -> 临时目录
    - 每个测试前清空数据表
    """
    TestSession = sessionmaker(bind=test_engine)

    # 1. DAO 使用内存数据库（DAO 的 session_factory 是类属性，替换即可全局生效）
    from app.dao import record_dao
    monkeypatch.setattr(record_dao.DetectionRecordDAO, "session_factory", TestSession)

    # 2. 文件目录指向临时目录
    from app import config
    monkeypatch.setattr(config.settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(config.settings, "RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(config.settings, "TEMP_DIR", str(tmp_path / "temp"))
    for d in ("uploads", "results", "temp"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # 3. 清空数据表，测试间互不影响
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    yield


@pytest.fixture
def api_client(isolated_env, monkeypatch):
    """
    FastAPI TestClient：注入假检测器，跳过真实的模型加载与推理
    """
    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.services import detection_service as ds_module

    # 跳过真实建库（避免测试创建真实数据库文件）
    monkeypatch.setattr(main_module, "init_db", lambda: None)

    # 用假检测器替换单例服务
    ds_module._instance = ds_module.DetectionService()
    ds_module._instance.detector = FakeDetector()

    with TestClient(main_module.app) as client:
        yield client


def make_image_bytes(size=(300, 200), color=(128, 128, 128)) -> bytes:
    """生成一张纯色 PNG 图像的二进制内容（测试上传用）"""
    from PIL import Image

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
