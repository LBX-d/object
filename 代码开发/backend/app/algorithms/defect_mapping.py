"""
缺陷类型映射、检测结果统计与报告生成

DEFECT_CLASSES 定义 6 类钢表面缺陷（与训练数据集的类别顺序严格一致）：
裂纹、夹杂、斑块、麻点、氧化皮、划痕
每类包含：中文名、英文名、RGB/BGR 颜色（画框用）、严重程度。
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger("defect_mapping")

# 缺陷类别定义（key = YOLO 类别 ID，必须与训练 data.yaml 的 names 顺序一致）
DEFECT_CLASSES: Dict[int, Dict[str, Any]] = {
    0: {"name_cn": "裂纹",   "name_en": "crazing",         "rgb": (220, 20, 60),   "bgr": (60, 20, 220),    "severity": "高"},
    1: {"name_cn": "夹杂",   "name_en": "inclusion",       "rgb": (255, 140, 0),   "bgr": (0, 140, 255),    "severity": "中"},
    2: {"name_cn": "斑块",   "name_en": "patches",         "rgb": (50, 205, 50),   "bgr": (50, 205, 50),    "severity": "中"},
    3: {"name_cn": "麻点",   "name_en": "pitted_surface",  "rgb": (30, 144, 255),  "bgr": (255, 144, 30),   "severity": "低"},
    4: {"name_cn": "氧化皮", "name_en": "rolled-in_scale", "rgb": (148, 0, 211),   "bgr": (211, 0, 148),    "severity": "中"},
    5: {"name_cn": "划痕",   "name_en": "scratches",       "rgb": (0, 206, 209),   "bgr": (209, 206, 0),    "severity": "低"},
}

# 中文名 -> 严重程度 的快速查询表
NAME_CN_TO_SEVERITY: Dict[str, str] = {v["name_cn"]: v["severity"] for v in DEFECT_CLASSES.values()}


def get_class_name_cn(class_id: int) -> str:
    """类别ID -> 中文名（未知ID给兜底名）"""
    info = DEFECT_CLASSES.get(int(class_id))
    return info["name_cn"] if info else f"类别{class_id}"


def get_severity_by_name(class_name: str) -> str:
    """缺陷中文名 -> 严重程度（未知类型按"中"处理）"""
    return NAME_CN_TO_SEVERITY.get(class_name, "中")


def analyze_detections(detections: Dict[str, Any]) -> Dict[str, Any]:
    """
    统计检测结果，返回结构化分析数据。

    入参 detections 为 detector.detect 的返回字典：
      {boxes, class_ids, confidences, class_names, inference_time}
    返回：
      summary       总览（缺陷总数、涉及缺陷种类数）
      by_type       按类型统计 [{class_name, count, ratio}]
      by_severity   按严重程度统计 {高: n, 中: n, 低: n}
      details       明细列表 [{class_id, class_name, confidence, severity, box}]
    """
    class_ids = detections.get("class_ids", []) or []
    confidences = detections.get("confidences", []) or []
    boxes = detections.get("boxes", []) or []
    class_names = detections.get("class_names", []) or []

    by_type: Dict[str, int] = {}
    details: List[Dict[str, Any]] = []

    for i, cid in enumerate(class_ids):
        name = class_names[i] if i < len(class_names) else get_class_name_cn(int(cid))
        conf = float(confidences[i]) if i < len(confidences) else 0.0
        box = boxes[i] if i < len(boxes) else []
        severity = get_severity_by_name(name)

        by_type[name] = by_type.get(name, 0) + 1
        details.append({
            "class_id": int(cid),
            "class_name": name,
            "confidence": round(conf, 4),
            "severity": severity,
            "box": [round(float(v), 4) for v in box],
        })

    total = sum(by_type.values())
    by_type_list = sorted(
        [
            {"class_name": name, "count": count,
             "ratio": round(count / total, 4) if total else 0.0}
            for name, count in by_type.items()
        ],
        key=lambda x: -x["count"],
    )

    by_severity = {"高": 0, "中": 0, "低": 0}
    for d in details:
        by_severity[d["severity"]] = by_severity.get(d["severity"], 0) + 1

    analysis = {
        "summary": {
            "total_defects": total,
            "defect_type_count": len(by_type),
        },
        "by_type": by_type_list,
        "by_severity": by_severity,
        "details": details,
    }
    logger.info("统计分析完成: 共 %d 个缺陷，%d 种类型", total, len(by_type))
    return analysis


def generate_report(
    record_id: int,
    file_name: str,
    image_info: Dict[str, Any],
    analysis: Dict[str, Any],
    status: str,
    confidence_avg: float,
    processing_time: float,
    detect_mode: str,
) -> str:
    """
    生成 JSON 格式的结构化检测报告（返回 JSON 字符串）。

    报告包含：报告编号、检测时间、产品图像信息、缺陷明细表、
    统计汇总、检测结论、检测员信息。
    """
    now = datetime.now()
    report_no = f"RPT-{now:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4].upper()}"

    report = {
        "report_no": report_no,
        "report_title": "智能车间产品外观缺陷检测报告",
        "detect_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "record_id": record_id,
        "image_info": {
            "file_name": file_name,
            "width": image_info.get("width"),
            "height": image_info.get("height"),
        },
        "defect_details": analysis.get("details", []),
        "statistics": {
            "total_defects": analysis.get("summary", {}).get("total_defects", 0),
            "by_type": analysis.get("by_type", []),
            "by_severity": analysis.get("by_severity", {}),
        },
        "conclusion": {
            "status": status,
            "total_defects": analysis.get("summary", {}).get("total_defects", 0),
            "confidence_avg": round(confidence_avg or 0.0, 4),
            "processing_time": round(processing_time or 0.0, 4),
        },
        "inspector": {
            "name": "自动检测系统",
            "model": "YOLOv8",
            "detect_mode": detect_mode,
        },
    }
    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    logger.info("检测报告已生成: %s (记录ID=%s)", report_no, record_id)
    return report_json
