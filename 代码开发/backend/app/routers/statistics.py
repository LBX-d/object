"""
统计路由

GET /api/statistics/overview          统计总览（总检测数、合格率、缺陷分布、日趋势）
GET /api/statistics/report/{id}       单次检测的完整结构化报告
"""
from fastapi import APIRouter, HTTPException

from app.services.record_service import record_service
from app.utils.logger import get_logger

logger = get_logger("router.statistics")

router = APIRouter(prefix="/api", tags=["统计分析"])


@router.get("/statistics/overview", summary="获取检测统计总览")
async def statistics_overview():
    """
    返回：总检测数、合格/不合格数、合格率、今日检测数、
    缺陷类型分布、严重程度分布、近 7 天检测趋势。
    """
    try:
        data = record_service.get_statistics()
    except Exception as e:
        logger.exception("统计接口异常")
        raise HTTPException(status_code=500, detail=f"统计失败: {e}")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/statistics/report/{record_id}", summary="获取单次检测的详细报告")
async def statistics_report(record_id: int):
    report = record_service.get_report(record_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"检测记录不存在: {record_id}")
    return {"code": 0, "msg": "success", "data": report}
