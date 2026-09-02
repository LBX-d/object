"""
上传检测路由

POST /api/upload  接收图像文件（最大 10MB），执行完整检测流水线并返回结果。
"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.detection_service import get_detection_service
from app.utils.logger import get_logger

logger = get_logger("router.upload")

router = APIRouter(prefix="/api", tags=["上传检测"])


@router.post("/upload", summary="上传产品图像并执行缺陷检测")
async def upload_image(
    file: UploadFile = File(..., description="图像文件（jpg/jpeg/png/bmp，最大 10MB）"),
):
    """
    上传一张产品外观图像，系统自动完成：
    预处理 -> YOLOv8 检测 -> 统计分析 -> 绘制标注图 -> 生成报告 -> 入库，
    返回完整检测结果（含结果图 URL、缺陷统计、检测框列表）。
    """
    service = get_detection_service()
    try:
        result = service.process_detection(file)
    except ValueError as e:
        # 用户输入问题（格式错、超大小等） -> 400
        logger.warning("上传检测被拒绝: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 系统内部错误 -> 500（全局异常处理器会兜底，这里再明确一次）
        logger.exception("上传检测处理异常")
        raise HTTPException(status_code=500, detail=f"检测处理失败: {e}")
    return {"code": 0, "msg": "检测完成", "data": result}
