"""
检测业务逻辑层

process_detection 是核心流水线：
  校验文件 -> 保存上传 -> 预处理 -> 模型检测 -> 坐标还原
  -> 统计分析 -> 绘制标注图 -> 生成报告 -> 入库 -> 返回完整结果

YOLODetector 以单例（懒加载）方式创建：整个应用只加载一次模型，
第一次上传时初始化（含模型预热），后续请求直接复用。
"""
import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import UploadFile

from app.algorithms.defect_mapping import analyze_detections, generate_report
from app.algorithms.detector import YOLODetector
from app.algorithms.preprocess import draw_annotations, postprocess_boxes, preprocess_image
from app.config import settings
from app.dao.record_dao import DetectionRecordDAO
from app.utils.file_utils import save_upload_file, validate_image_filename
from app.utils.logger import get_logger

logger = get_logger("detection_service")


class DetectionService:
    """检测业务：接收上传文件，跑完整检测流水线并入库"""

    def __init__(self):
        self.detector: YOLODetector | None = None
        self.dao = DetectionRecordDAO()

    def _get_detector(self) -> YOLODetector:
        """懒加载单例检测器（首次使用时才加载模型）"""
        if self.detector is None:
            logger.info("首次初始化 YOLOv8 检测器（加载模型 + 预热）...")
            self.detector = YOLODetector()
        return self.detector

    def process_detection(self, file: UploadFile) -> Dict[str, Any]:
        """
        处理一次完整的检测请求，返回结构化结果（含结果图 URL 和全部统计数据）。
        用户输入错误抛 ValueError（路由层转 400），系统错误抛 RuntimeError（转 500）。
        """
        t_start = time.time()

        # 1. 校验文件格式（jpg/jpeg/png/bmp）
        if not validate_image_filename(file.filename or ""):
            raise ValueError(f"不支持的文件格式，仅支持 jpg/jpeg/png/bmp: {file.filename}")

        # 2. 读取内容并校验大小（最大 10MB）
        content = file.file.read()
        if not content:
            raise ValueError("上传文件内容为空")
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制（当前 {len(content) / 1024 / 1024:.1f}MB）")

        # 3. 保存上传文件（UUID 重命名防止冲突）
        save_path = save_upload_file(content, file.filename or "image.jpg")

        try:
            # 4. 预处理（缩放 + CLAHE 增强 + 归一化）
            pre = preprocess_image(str(save_path))

            # 5. 模型检测
            detector = self._get_detector()
            detections = detector.detect(pre["processed_path"])

            # 6. 检测框坐标还原到原图尺寸（整数像素坐标）
            boxes_orig = postprocess_boxes(
                detections["boxes"], pre["original_shape"], pre["scale_ratio"], pre["pad"]
            )

            # 7. 统计分析（分类统计、严重程度分布、明细）
            analysis = analyze_detections(detections)

            # 8. 在原图上绘制标注框，保存结果图
            result_path = Path(settings.RESULT_DIR) / f"{Path(save_path).stem}_result.jpg"
            draw_annotations(
                str(save_path),
                boxes_orig,
                detections["class_ids"],
                detections["class_names"],
                detections["confidences"],
                str(result_path),
            )

            # 9. 汇总检测结论
            total = analysis["summary"]["total_defects"]
            confs = detections["confidences"] or []
            confidence_avg = round(sum(confs) / len(confs), 4) if confs else 0.0
            processing_time = round(time.time() - t_start, 4)
            status = "不合格" if total > 0 else "合格"
            defect_types = {item["class_name"]: item["count"] for item in analysis["by_type"]}
            detect_mode = "demo" if detector.demo_mode else "model"

            # 10. 写入数据库（先建记录拿到 ID，再补完整报告）
            record_id = self.dao.create(
                file_name=file.filename,
                file_path=str(save_path),
                result_image_path=str(result_path),
                defect_types=defect_types,
                total_defects=total,
                status=status,
                confidence_avg=confidence_avg,
                processing_time=processing_time,
            )
            image_info = {"width": pre["original_shape"][1], "height": pre["original_shape"][0]}
            report_json = generate_report(
                record_id, file.filename, image_info, analysis,
                status, confidence_avg, processing_time, detect_mode,
            )
            self.dao.update(record_id, report_data=json.loads(report_json))

            # 11. 组装返回结果
            boxes_payload = [
                {
                    "class_id": d["class_id"],
                    "class_name": d["class_name"],
                    "confidence": d["confidence"],
                    "severity": d["severity"],
                    "box": d["box"],
                }
                for d in analysis["details"]
            ]
            result = {
                "record_id": record_id,
                "report_no": json.loads(report_json)["report_no"],
                "file_name": file.filename,
                "status": status,
                "conclusion": "检测合格" if status == "合格" else f"检测不合格：发现 {total} 处缺陷",
                "total_defects": total,
                "confidence_avg": confidence_avg,
                "processing_time": processing_time,
                "original_image_url": f"/uploads/{Path(save_path).name}",
                "result_image_url": f"/results/{result_path.name}",
                "image_size": image_info,
                "defect_types": defect_types,
                "statistics": analysis,
                "boxes": boxes_payload,
                "detect_mode": detect_mode,
            }
            logger.info(
                "检测流水线完成: %s -> 结论=%s 缺陷=%d 耗时=%.3fs (record_id=%s)",
                file.filename, status, total, processing_time, record_id,
            )
            return result
        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            logger.exception("检测流水线异常: %s", e)
            raise RuntimeError(f"检测处理失败: {e}") from e


# 模块级单例实例（懒加载：detector 在首次 process_detection 时才初始化）
_instance: DetectionService | None = None


def get_detection_service() -> DetectionService:
    """获取 DetectionService 单例"""
    global _instance
    if _instance is None:
        _instance = DetectionService()
    return _instance
