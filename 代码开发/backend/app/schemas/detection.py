"""
请求/响应数据模型（Pydantic）

所有接口统一返回 {code, msg, data} 结构：
- code: 0 表示成功，非 0 表示失败
- msg: 提示信息
- data: 业务数据
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装"""

    code: int = Field(0, description="状态码，0=成功")
    msg: str = Field("success", description="提示信息")
    data: Optional[T] = Field(None, description="业务数据")


class BoxItem(BaseModel):
    """单个检测框（坐标为归一化值 0~1，方便前端按比例叠加显示）"""

    class_id: int = Field(..., description="缺陷类别ID")
    class_name: str = Field(..., description="缺陷类别中文名")
    confidence: float = Field(..., description="置信度")
    severity: str = Field("中", description="严重程度：高/中/低")
    box: List[float] = Field(..., description="归一化坐标 [x1, y1, x2, y2]")


class DetectionResponse(BaseModel):
    """上传检测接口的返回数据"""

    record_id: int = Field(..., description="数据库记录ID")
    report_no: str = Field(..., description="报告编号")
    file_name: str = Field(..., description="文件名")
    status: str = Field(..., description="检测结论：合格/不合格")
    total_defects: int = Field(..., description="缺陷总数")
    confidence_avg: float = Field(..., description="平均置信度")
    processing_time: float = Field(..., description="处理耗时(秒)")
    original_image_url: str = Field(..., description="原图访问URL")
    result_image_url: str = Field(..., description="结果标注图访问URL")
    image_size: Dict[str, int] = Field(..., description="原图尺寸 {width, height}")
    defect_types: Dict[str, int] = Field(..., description="缺陷类型及数量")
    statistics: Dict[str, Any] = Field(..., description="统计汇总(summary/by_type/by_severity/details)")
    boxes: List[BoxItem] = Field(default_factory=list, description="检测框列表")
    detect_mode: str = Field("model", description="检测方式：model=真实模型 / demo=演示模式")
    conclusion: str = Field("", description="检测结论描述")


class RecordItem(BaseModel):
    """历史记录列表项"""

    id: int
    file_name: str
    total_defects: int
    status: str
    defect_types: Dict[str, int]
    confidence_avg: float
    processing_time: float
    created_at: str
    result_image_url: str = ""
    original_image_url: str = ""


class RecordListResponse(BaseModel):
    """记录分页查询结果"""

    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页条数")
    items: List[RecordItem] = Field(default_factory=list, description="记录列表")


class RecordDetailResponse(BaseModel):
    """单条记录详情（含完整报告）"""

    record: RecordItem
    report: Optional[Dict[str, Any]] = Field(None, description="完整检测报告")


class StatisticsResponse(BaseModel):
    """统计总览数据"""

    total_count: int = Field(..., description="总检测数")
    pass_count: int = Field(..., description="合格数")
    fail_count: int = Field(..., description="不合格数")
    pass_rate: float = Field(..., description="合格率 0~1")
    today_count: int = Field(..., description="今日检测数")
    defect_distribution: Dict[str, int] = Field(..., description="各缺陷类型数量分布")
    severity_distribution: Dict[str, int] = Field(..., description="严重程度分布 高/中/低")
    daily_trend: List[Dict[str, Any]] = Field(..., description="近7天日检测趋势")
