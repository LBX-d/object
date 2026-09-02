"""
记录查询业务逻辑层

提供分页查询、详情查询、统计汇总三个能力，依赖注入 DAO 层。
把文件路径转换成前端可直接访问的 URL（/uploads/xxx、/results/xxx）。
"""
from pathlib import Path
from typing import Any, Dict, Optional

from app.dao.record_dao import DetectionRecordDAO
from app.utils.logger import get_logger

logger = get_logger("record_service")


class RecordService:
    """历史记录与统计的业务封装"""

    def __init__(self, dao: Optional[DetectionRecordDAO] = None):
        self.dao = dao or DetectionRecordDAO()

    def get_records(
        self,
        page: int = 1,
        size: int = 10,
        defect_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询历史记录"""
        data = self.dao.get_list(page, size, defect_type, start_date, end_date)
        items = [self._with_urls(item) for item in data["items"]]
        logger.info("记录查询完成: 第 %s 页 / 共 %s 条", page, data["total"])
        return {"total": data["total"], "page": page, "size": size, "items": items}

    def get_record_detail(self, record_id: int) -> Optional[Dict[str, Any]]:
        """获取单条记录详情（含完整检测报告）；不存在返回 None"""
        rec = self.dao.get_by_id(record_id)
        if rec is None:
            return None
        report = rec.get("report_data")
        return {"record": self._with_urls(rec), "report": report}

    def get_report(self, record_id: int) -> Optional[Dict[str, Any]]:
        """获取单次检测的完整报告 JSON；不存在返回 None"""
        rec = self.dao.get_by_id(record_id)
        if rec is None:
            return None
        return rec.get("report_data")

    def get_statistics(self) -> Dict[str, Any]:
        """统计总览"""
        return self.dao.get_statistics()

    @staticmethod
    def _with_urls(rec: Dict[str, Any]) -> Dict[str, Any]:
        """把存储路径补成前端可访问的 URL 字段"""
        item = dict(rec)
        item["result_image_url"] = (
            f"/results/{Path(rec['result_image_path']).name}" if rec.get("result_image_path") else ""
        )
        item["original_image_url"] = (
            f"/uploads/{Path(rec['file_path']).name}" if rec.get("file_path") else ""
        )
        return item


# 模块级单例（路由层统一使用）
record_service = RecordService()
