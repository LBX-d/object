"""
检测器单元测试

- 演示模式（无模型文件）：detect 返回格式完整性
- 真实模型（存在 best.pt 时）：模型加载成功 + 推理返回格式
"""
from pathlib import Path

import pytest

from app.algorithms.detector import YOLODetector
from app.config import settings


@pytest.fixture
def sample_image(tmp_path):
    """生成一张测试图像文件"""
    from PIL import Image

    path = tmp_path / "sample.png"
    Image.new("RGB", (320, 240), (100, 100, 100)).save(path)
    return str(path)


class TestDemoMode:
    def test_demo_mode_detect_format(self, sample_image):
        """无模型文件时进入演示模式，detect 返回完整结构"""
        detector = YOLODetector(model_path=str(Path("nonexistent") / "no_model.pt"))
        assert detector.demo_mode is True

        result = detector.detect(sample_image)
        # 返回字段完整
        for key in ("boxes", "class_ids", "confidences", "class_names", "inference_time"):
            assert key in result
        # 各列表长度一致
        n = len(result["boxes"])
        assert n == len(result["class_ids"]) == len(result["confidences"]) == len(result["class_names"])
        # 演示模式同一张图结果稳定（确定性）
        result2 = detector.detect(sample_image)
        assert result["boxes"] == result2["boxes"]

    def test_demo_mode_predict_batch(self, sample_image, tmp_path):
        from PIL import Image

        p2 = tmp_path / "b.png"
        Image.new("RGB", (200, 200), (200, 200, 200)).save(p2)
        detector = YOLODetector(model_path=str(Path("nonexistent") / "no_model.pt"))
        results = detector.predict_batch([sample_image, str(p2)])
        assert len(results) == 2
        for r in results:
            assert "boxes" in r and "class_ids" in r


@pytest.mark.skipif(
    not Path(settings.MODEL_PATH).exists(),
    reason="未找到训练好的模型文件 models/best.pt，跳过真实模型测试",
)
class TestRealModel:
    def test_model_load(self):
        detector = YOLODetector()
        assert detector.demo_mode is False
        assert detector.model is not None

    def test_real_detect_format(self, sample_image):
        detector = YOLODetector()
        result = detector.detect(sample_image)
        for key in ("boxes", "class_ids", "confidences", "class_names", "inference_time"):
            assert key in result
        n = len(result["boxes"])
        assert n == len(result["class_ids"]) == len(result["confidences"])
        # 坐标在 0~1 之间（归一化）
        for box in result["boxes"]:
            assert all(0 <= v <= 1 for v in box)
