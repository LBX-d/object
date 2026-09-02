"""
数据库连接模块

- 创建 SQLite 数据库引擎（数据存到 backend/data/defect_detection.db）
- SessionLocal：会话工厂，每个请求/操作用它开一个"数据库会话"
- get_db：FastAPI 依赖注入函数（供路由层直接使用）
- init_db：建表初始化函数（应用启动时调用）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("database")

# SQLite 数据库文件路径（Windows 路径统一转成正斜杠给 SQLAlchemy 用）
_db_path = settings.DATABASE_PATH.replace("\\", "/")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # FastAPI 多线程处理请求，SQLite 默认不允许跨线程共用连接，这里放开
    connect_args={"check_same_thread": False},
    echo=False,
)

# 会话工厂：每次调用 SessionLocal() 得到一个新的数据库会话
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# 所有 ORM 模型的基类（模型类继承它）
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：为每个请求提供独立的数据库会话，用完自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库：创建所有表（表不存在时才建，已有数据不受影响）"""
    from app.models import detection_record  # noqa: F401  导入以注册模型到 Base

    Base.metadata.create_all(bind=engine)
    logger.info("数据库初始化完成: %s", SQLALCHEMY_DATABASE_URL)
