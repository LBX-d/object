"""
历史记录路由

GET /api/records            分页查询（page/size/defect_type/start_date/end_date）
GET /api/records/{id}       单条记录详情（含完整报告）
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.record_service import record_service
from app.utils.logger import get_logger

logger = get_logger("router.records")

router = APIRouter(prefix="/api", tags=["历史记录"])


@router.get("/records", summary="分页查询检测记录")
async def get_records(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页条数，最大 100"),
    defect_type: Optional[str] = Query(None, description="按缺陷类型筛选，如：裂纹"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD（含当天）"),
):
    try:
        data = record_service.get_records(page, size, defect_type, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("分页查询接口异常")
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/records/{record_id}", summary="获取单条检测记录详情")
async def get_record_detail(record_id: int):
    detail = record_service.get_record_detail(record_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"检测记录不存在: {record_id}")
    return {"code": 0, "msg": "success", "data": detail}
