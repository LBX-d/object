"""
FastAPI 应用入口

- CORS 跨域（允许所有来源，方便前端开发调试）
- 挂载 /uploads、/results 静态目录（前端直接访问上传图与结果图）
- 全局异常处理器（统一返回 {code, msg, data} 格式）
- 健康检查接口 /api/health
- 注册上传、记录、统计三个路由模块
"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import records, statistics, upload
from app.services.detection_service import get_detection_service
from app.utils.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    init_db()
    logger.info("=" * 60)
    logger.info("智能车间产品外观缺陷检测与报告系统 - 后端启动完成")
    logger.info("接口文档: http://localhost:8000/docs")
    logger.info("=" * 60)
    yield


app = FastAPI(
    title="智能车间产品外观缺陷检测与报告系统",
    description="基于 YOLOv8 的工业产品外观图像自动缺陷检测与报告生成 API",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------- CORS 跨域配置（允许所有来源，方便前端联调） ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- 全局异常处理器（统一返回 {code, msg, data}） ----------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": f"参数校验失败: {first}", "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": f"服务器内部错误: {exc}", "data": None},
    )


# ---------------- 基础接口 ----------------

@app.get("/", tags=["系统"], summary="服务信息")
async def root():
    return {
        "code": 0,
        "msg": "智能车间产品外观缺陷检测与报告系统",
        "data": {"api_docs": "/docs", "health": "/api/health"},
    }


@app.get("/api/health", tags=["系统"], summary="健康检查")
async def health_check():
    """
    健康检查：返回服务状态与检测器状态。
    注意：不主动加载模型（避免健康检查触发耗时的模型加载），
    只返回"是否已加载/演示模式"等信息。
    """
    detector = get_detection_service().detector
    detector_status = (
        detector.get_status()
        if detector is not None
        else {"model_loaded": False, "demo_mode": False, "device": "not-initialized"}
    )
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "service": "defect-detection-backend",
            "status": "ok",
            "version": "1.0.0",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "detector": detector_status,
        },
    }


# ---------------- 注册业务路由 ----------------
app.include_router(upload.router)
app.include_router(records.router)
app.include_router(statistics.router)

# ---------------- 挂载静态目录（上传原图 / 检测结果图） ----------------
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/results", StaticFiles(directory=settings.RESULT_DIR), name="results")
