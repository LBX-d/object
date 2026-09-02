"""
算法模块测试

覆盖：图像预处理（含异常）、坐标还原、标注图绘制、
缺陷统计（analyze_detections）、报告生成（generate_report）。
不依赖模型与数据库。
"""
import json
from pathlib import Path

import pytest
from PIL import Image

from app.algorithms.defect_mapping import analyze_detections, generate_report
from app.algorithms.preprocess import (
    draw_annotations,
    postprocess_boxes,
    preprocess_image,
)


@pytest.fixture
def sample_image_path(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (320, 240), (120, 120, 120)).save(path)
    return str(path)


class TestPreprocess:
    def test_preprocess_image(self, sample_image_path):
        result = preprocess_image(sample_image_path)
        assert result["original_shape"][:2] == (240, 320)
        # 缩放比例 > 0（小图会放大、大图会缩小到 640 画布）
        assert result["scale_ratio"] > 0
        assert Path(result["processed_path"]).exists()
        # 预处理图是 640x640
        from PIL import Image as PILImage

        with PILImage.open(result["processed_path"]) as img:
            assert img.size == (640, 640)

    def test_preprocess_missing_file(self):
        with pytest.raises(FileNotFoundError):
            preprocess_image("/nonexistent/path/img.jpg")

    def test_postprocess_boxes_restore(self):
        # 640 画布、无缩放无填充：归一化坐标 x 640 即原图坐标
        boxes = [[0.25, 0.25, 0.75, 0.75]]
        result = postprocess_boxes(boxes, (200, 200, 3), scale_ratio=1.0, pad=(0, 0))
        assert result == [[160, 160, 199, 199]]  # 右下角被裁剪到 199（w-1）

    def test_postprocess_boxes_with_scale(self):
        # 画布 640，缩放 0.5，左/上各填充 20：逆向还原
        boxes = [[0.5, 0.5, 1.0, 1.0]]
        result = postprocess_boxes(boxes, (400, 400, 3), scale_ratio=0.5, pad=(20, 20))
        # x1 = (0.5*640 - 20)/0.5 = 600 -> 裁剪到 399
        assert result == [[600, 600, 399, 399]]

    def test_draw_annotations(self, sample_image_path, tmp_path):
        save_path = str(tmp_path / "result.jpg")
        out = draw_annotations(
            sample_image_path,
            boxes=[[30, 30, 120, 100], [150, 80, 260, 200]],
            class_ids=[0, 5],
            class_names=["裂纹", "划痕"],
            confidences=[0.91, 0.87],
            save_path=save_path,
        )
        assert out == save_path
        assert Path(save_path).exists()
        # 结果图能正常打开
        Image.open(save_path).verify()


class TestDefectMapping:
    def test_analyze_detections(self):
        detections = {
            "boxes": [[0.1, 0.1, 0.5, 0.5], [0.2, 0.2, 0.6, 0.6], [0.3, 0.3, 0.4, 0.4]],
            "class_ids": [0, 0, 5],
            "confidences": [0.9, 0.8, 0.7],
            "class_names": ["裂纹", "裂纹", "划痕"],
            "inference_time": 0.02,
        }
        analysis = analyze_detections(detections)
        assert analysis["summary"] == {"total_defects": 3, "defect_type_count": 2}
        by_type = {item["class_name"]: item for item in analysis["by_type"]}
        assert by_type["裂纹"]["count"] == 2
        assert by_type["裂纹"]["ratio"] == round(2 / 3, 4)
        assert by_type["划痕"]["count"] == 1
        assert analysis["by_severity"] == {"高": 2, "中": 0, "低": 1}
        assert len(analysis["details"]) == 3
        assert analysis["details"][0]["severity"] == "高"

    def test_analyze_empty(self):
        analysis = analyze_detections(
            {"boxes": [], "class_ids": [], "confidences": [], "class_names": []}
        )
        assert analysis["summary"]["total_defects"] == 0
        assert analysis["by_type"] == []

    def test_generate_report(self):
        analysis = analyze_detections(
            {
                "boxes": [[0.1, 0.1, 0.5, 0.5]],
                "class_ids": [0],
                "confidences": [0.92],
                "class_names": ["裂纹"],
            }
        )
        report_json = generate_report(
            record_id=1,
            file_name="test.jpg",
            image_info={"width": 300, "height": 200},
            analysis=analysis,
            status="不合格",
            confidence_avg=0.92,
            processing_time=1.23,
            detect_mode="model",
        )
        report = json.loads(report_json)
        assert report["report_no"].startswith("RPT-")
        assert report["report_title"] == "智能车间产品外观缺陷检测报告"
        assert report["record_id"] == 1
        assert report["image_info"] == {"file_name": "test.jpg", "width": 300, "height": 200}
        assert len(report["defect_details"]) == 1
        assert report["statistics"]["total_defects"] == 1
        assert report["conclusion"]["status"] == "不合格"
        assert report["inspector"] == {"name": "自动检测系统", "model": "YOLOv8", "detect_mode": "model"}
