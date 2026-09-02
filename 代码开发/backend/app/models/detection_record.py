"""
检测记录数据模型（ORM）

对应数据库表 detection_records，每上传检测一张图片插入一条记录。
defect_types 使用 JSON 类型存储"缺陷类型 -> 数量"映射，如 {"裂纹": 2, "划痕": 1}。
"""
from datetime import datetime
import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.types import TypeDecorator

from app.database import Base


class UnicodeJSON(TypeDecorator):
    """自定义 JSON 列类型（SQLite 按文本存储）

    与 SQLAlchemy 内置 JSON 类型的区别：序列化时 ensure_ascii=False，
    中文以原文存储。若中文被转义成 unicode 编码形式，
    按中文关键词（如"裂纹"）的 LIKE 筛选会失效。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """写入数据库前：dict -> JSON 文本（中文不转义）"""
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        """读出数据库后：JSON 文本 -> dict"""
        if not value:
            return None
        return json.loads(value)


class DetectionRecord(Base):
    """一次缺陷检测的完整记录"""

    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(512), nullable=False, comment="上传文件存储路径")
    result_image_path = Column(String(512), nullable=True, comment="标注结果图路径")
    # JSON 格式：{"裂纹": 2, "划痕": 1}，缺陷类型中文名 -> 数量
    defect_types = Column(UnicodeJSON, nullable=False, default=dict, comment="缺陷类型及数量(JSON)")
    total_defects = Column(Integer, nullable=False, default=0, comment="缺陷总数")
    status = Column(String(20), nullable=False, default="合格", comment="检测结论：合格/不合格")
    confidence_avg = Column(Float, nullable=False, default=0.0, comment="平均置信度")
    processing_time = Column(Float, nullable=False, default=0.0, comment="处理耗时(秒)")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="检测时间")
    # 完整检测报告 JSON（包含缺陷明细、统计、结论等，供报告接口返回）
    report_data = Column(UnicodeJSON, nullable=True, comment="完整检测报告(JSON)")

    def to_dict(self) -> dict:
        """把 ORM 对象转成字典（接口返回用），日期统一格式化"""
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "result_image_path": self.result_image_path,
            "defect_types": self.defect_types or {},
            "total_defects": self.total_defects or 0,
            "status": self.status,
            "confidence_avg": round(self.confidence_avg or 0.0, 4),
            "processing_time": round(self.processing_time or 0.0, 4),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "report_data": self.report_data,
        }
