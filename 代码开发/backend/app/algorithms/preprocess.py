"""
图像预处理模块

- preprocess_image   读取图像 -> 等比缩放640x640(灰色填充) -> CLAHE增强 -> 归一化0~1 -> 存临时文件
- postprocess_boxes  把归一化检测框坐标还原到原始图像尺寸（整数像素坐标）
- draw_annotations   在原图上绘制检测框（中文标签 + 置信度），不同缺陷类型不同颜色

注意：全程使用 numpy 解码 + write_bytes 保存，避免 OpenCV 在
Windows 上处理含中文路径时失败的问题。
"""
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("preprocess")

SUPPORTED_FORMATS = ("jpg", "jpeg", "png", "bmp")

# 中文字体候选（Windows 系统字体，按优先级尝试）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
    "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
    "C:/Windows/Fonts/simsun.ttc",  # 宋体
]
_FONT_CACHE: Dict[int, Any] = {}


def read_image(image_path: str) -> np.ndarray:
    """读取图像（支持 jpg/jpeg/png/bmp），失败抛出带原因的异常"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    ext = path.suffix.lower().lstrip(".")
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的图像格式 .{ext}（支持: {SUPPORTED_FORMATS}）")
    # np.fromfile + imdecode 可正确处理含中文/特殊字符的路径
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"图像读取失败（文件可能已损坏）: {image_path}")
    return img


def letterbox_resize(
    img: np.ndarray, target_size: int = 640, fill_color: Tuple[int, int, int] = (114, 114, 114)
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    等比缩放：长边缩到 target_size，短边居中，不足部分用灰色(114,114,114)填充。
    返回 (缩放后图像, 缩放比例, (左侧填充量, 顶部填充量))
    """
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((target_size, target_size, 3), fill_color, dtype=np.uint8)
    pad_w = (target_size - new_w) // 2
    pad_h = (target_size - new_h) // 2
    canvas[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized
    return canvas, scale, (pad_w, pad_h)


def apply_clahe(img: np.ndarray) -> np.ndarray:
    """
    CLAHE 自适应直方图均衡化（对比度限制 2.0，网格 8x8）。
    在 LAB 颜色空间的亮度通道上做增强，避免直接对 RGB 增强导致颜色失真。
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_enhanced = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l_enhanced, a, b)), cv2.COLOR_LAB2BGR)


def preprocess_image(image_path: str) -> Dict[str, Any]:
    """
    完整预处理流程，返回：
      original_shape  原图形状 (H, W, C)
      processed_path  预处理后图像保存路径（temp 目录）
      scale_ratio     缩放比例（还原坐标用）
      pad             (左填充, 上填充)
    """
    t0 = time.time()
    try:
        img = read_image(image_path)
        original_shape = img.shape

        # 1. 等比缩放至 640x640，灰边填充
        processed, scale, pad = letterbox_resize(img, settings.IMG_SIZE)
        # 2. CLAHE 增强
        enhanced = apply_clahe(processed)
        # 3. 归一化到 0~1
        normalized = enhanced.astype(np.float32) / 255.0

        # 4. 保存预处理图到临时目录
        save_name = f"pre_{Path(image_path).stem}_{uuid.uuid4().hex[:6]}.jpg"
        save_path = Path(settings.TEMP_DIR) / save_name
        ok, buf = cv2.imencode(".jpg", (normalized * 255).astype(np.uint8))
        if not ok:
            raise RuntimeError("预处理图像编码保存失败")
        save_path.write_bytes(buf.tobytes())

        logger.info(
            "预处理完成: %s -> %s (原始尺寸 %s, 缩放比例 %.4f, 耗时 %.3fs)",
            image_path, save_path.name, original_shape[:2], scale, time.time() - t0,
        )
        return {
            "original_shape": original_shape,
            "processed_path": str(save_path),
            "scale_ratio": scale,
            "pad": pad,
        }
    except (FileNotFoundError, ValueError) as e:
        logger.error("预处理失败: %s", e)
        raise
    except Exception as e:
        logger.exception("预处理异常: %s", e)
        raise RuntimeError(f"图像预处理失败: {e}") from e


def postprocess_boxes(
    boxes: List[List[float]],
    original_shape: Tuple[int, int, int],
    scale_ratio: float,
    pad: Tuple[int, int] = (0, 0),
) -> List[List[int]]:
    """
    把归一化检测框（xyxy，0~1，相对 640 画布）还原到原始图像尺寸的整数像素坐标。
    坐标会被裁剪到原图范围内。
    """
    h, w = original_shape[:2]
    pad_w, pad_h = pad
    result: List[List[int]] = []
    for box in boxes:
        x1, y1, x2, y2 = box[:4]
        # 逆变换：先乘 640 回到画布坐标，再去填充、除缩放比例回到原图坐标
        nx1 = (x1 * settings.IMG_SIZE - pad_w) / scale_ratio
        ny1 = (y1 * settings.IMG_SIZE - pad_h) / scale_ratio
        nx2 = (x2 * settings.IMG_SIZE - pad_w) / scale_ratio
        ny2 = (y2 * settings.IMG_SIZE - pad_h) / scale_ratio
        x1i, y1i = max(0, int(round(nx1))), max(0, int(round(ny1)))
        x2i, y2i = min(w - 1, int(round(nx2))), min(h - 1, int(round(ny2)))
        result.append([x1i, y1i, x2i, y2i])
    return result


def _load_chinese_font(size: int):
    """加载中文字体（带缓存）。找不到任何中文字体时退回 PIL 默认字体。"""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    from PIL import ImageFont

    for font_path in _FONT_CANDIDATES:
        if Path(font_path).exists():
            font = ImageFont.truetype(font_path, size)
            _FONT_CACHE[size] = font
            return font
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


def draw_annotations(
    image_path: str,
    boxes: List[List[int]],
    class_ids: List[int],
    class_names: List[str],
    confidences: List[float],
    save_path: str,
) -> str:
    """
    在原图上绘制检测框并保存：
    - 不同缺陷类型用不同颜色（DEFECT_CLASSES 中的 rgb）
    - 框上方标注"类别中文名 + 置信度"（白字 + 彩色底）
    使用 PIL 绘制，因为 OpenCV 的 putText 不支持中文。
    返回保存路径。
    """
    from PIL import Image, ImageDraw

    from app.algorithms.defect_mapping import DEFECT_CLASSES

    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        font = _load_chinese_font(22)

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                continue
            cid = int(class_ids[i]) if i < len(class_ids) else 0
            info = DEFECT_CLASSES.get(cid, {})
            color = tuple(info.get("rgb", (255, 0, 0)))
            name = class_names[i] if i < len(class_names) else info.get("name_cn", f"类别{cid}")
            conf = float(confidences[i]) if i < len(confidences) else 0.0

            # 检测框（线宽随框大小自适应）
            draw.rectangle([x1, y1, x2, y2], outline=color, width=max(3, (x2 - x1) // 100))

            # 标签：类别中文名 + 置信度
            label = f"{name} {conf:.2f}"
            label_pos = (x1, max(0, y1 - 26))
            bbox = draw.textbbox(label_pos, label, font=font)
            draw.rectangle([bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2], fill=color)
            draw.text(label_pos, label, fill=(255, 255, 255), font=font)

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
        logger.info("标注结果图已保存: %s (%d 个检测框)", save_path, len(boxes))
        return str(save_path)
    except Exception as e:
        logger.exception("绘制标注图失败: %s", e)
        raise RuntimeError(f"绘制标注图失败: {e}") from e
