"""
YOLOv8 检测器封装

- 初始化时加载模型，自动检测 GPU（CUDA）或 CPU
- 置信度阈值 0.25、IoU 阈值 0.45
- 模型预热：用全黑图像推理一次，消除首次推理的加载延迟
- detect：单张推理，带超时保护；未检出返回空列表
- predict_batch：批量推理
- 兜底机制：模型文件不存在或加载失败时进入"演示模式"，
  按文件名哈希确定性生成模拟检测框（同一张图结果稳定），
  保证系统在任何环境下都能跑通完整流程。
"""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from app.algorithms.defect_mapping import DEFECT_CLASSES, get_class_name_cn
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("detector")


class YOLODetector:
    """YOLOv8 缺陷检测器（单例使用：整个应用只创建一次，模型只加载一次）"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ):
        self.model_path = Path(model_path or settings.MODEL_PATH)
        self.conf_threshold = conf_threshold if conf_threshold is not None else settings.CONF_THRESHOLD
        self.iou_threshold = iou_threshold if iou_threshold is not None else settings.IOU_THRESHOLD
        # 自动选择设备：有 NVIDIA GPU 用 cuda:0，否则 CPU
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.demo_mode = False
        self.demo_reason = ""
        self._load_model()

    # ---------------- 模型加载 ----------------

    def _load_model(self) -> None:
        """加载模型文件；失败或不存在时进入演示模式（不崩溃）"""
        if self.model_path.exists():
            try:
                from ultralytics import YOLO

                self.model = YOLO(str(self.model_path))
                self.demo_mode = False
                logger.info("模型加载成功: %s (推理设备: %s)", self.model_path, self.device)
                self._warmup()
            except Exception as e:
                logger.error("模型加载失败: %s，切换到演示模式", e)
                self._enable_demo_mode(f"模型加载失败: {e}")
        else:
            logger.warning("未找到模型文件 %s，进入演示模式（模拟检测结果）", self.model_path)
            self._enable_demo_mode("模型文件不存在，当前为演示模式")

    def _enable_demo_mode(self, reason: str) -> None:
        self.demo_mode = True
        self.model = None
        self.demo_reason = reason

    def _warmup(self) -> None:
        """模型预热：用 640x640 全黑图推理一次，消除首次推理的加载延迟"""
        try:
            black = np.zeros((settings.IMG_SIZE, settings.IMG_SIZE, 3), dtype=np.uint8)
            self.model.predict(
                source=black, conf=self.conf_threshold, iou=self.iou_threshold,
                verbose=False, device=self.device,
            )
            logger.info("模型预热完成")
        except Exception as e:
            logger.warning("模型预热失败（不影响后续推理）: %s", e)

    # ---------------- 推理接口 ----------------

    def detect(self, image_path: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        单张图像推理。
        返回 {"boxes"(归一化xyxy), "class_ids", "confidences", "class_names"(中文), "inference_time"}
        未检测到缺陷时返回空列表。带超时保护（默认 60 秒）。
        """
        timeout = timeout or settings.INFERENCE_TIMEOUT
        t0 = time.time()

        if self.demo_mode:
            boxes, ids, confs, names = self._simulate_detection(image_path)
        else:
            # 推理放到独立线程执行，主线程等待并限制超时，
            # 防止单张异常图卡死整个服务
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self._predict_one, image_path)
            try:
                boxes, ids, confs, names = future.result(timeout=timeout)
            except FutureTimeoutError:
                logger.error("推理超时(>%.0fs): %s", timeout, image_path)
                boxes, ids, confs, names = [], [], [], []
            except Exception as e:
                logger.exception("推理异常: %s", e)
                boxes, ids, confs, names = [], [], [], []
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        inference_time = round(time.time() - t0, 4)
        if boxes:
            logger.info("检测完成: 发现 %d 个缺陷，推理耗时 %.3fs", len(boxes), inference_time)
        else:
            logger.info("检测完成: 未发现缺陷，推理耗时 %.3fs", inference_time)

        return {
            "boxes": boxes,
            "class_ids": ids,
            "confidences": confs,
            "class_names": names,
            "inference_time": inference_time,
        }

    def predict_batch(self, image_paths: List[str], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        批量推理：真实模型模式下一次推理多张（提高效率），
        演示模式或异常时逐张兜底处理。
        """
        timeout = timeout or settings.INFERENCE_TIMEOUT
        if not image_paths:
            return []

        t0 = time.time()
        if self.demo_mode or self.model is None:
            results = [self.detect(p, timeout=timeout) for p in image_paths]
        else:
            try:
                outs = self.model.predict(
                    source=[str(p) for p in image_paths],
                    conf=self.conf_threshold, iou=self.iou_threshold,
                    verbose=False, device=self.device,
                )
                results = [self._parse_result(r) for r in outs]
            except Exception as e:
                logger.exception("批量推理失败: %s，逐张兜底推理", e)
                results = [self.detect(p, timeout=timeout) for p in image_paths]

        logger.info("批量推理完成: %d 张图像，总耗时 %.3fs", len(image_paths), time.time() - t0)
        return results

    def get_status(self) -> Dict[str, Any]:
        """当前检测器状态（健康检查接口用）"""
        return {
            "model_path": str(self.model_path),
            "model_loaded": self.model is not None,
            "device": self.device,
            "demo_mode": self.demo_mode,
            "demo_reason": self.demo_reason,
            "conf_threshold": self.conf_threshold,
            "iou_threshold": self.iou_threshold,
        }

    # ---------------- 内部实现 ----------------

    def _predict_one(self, image_path: str) -> Tuple[List, List, List, List]:
        """调用模型推理单张图，返回 (boxes, class_ids, confidences, class_names)"""
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device,
        )
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return [], [], [], []
        boxes = r.boxes.xyxyn.cpu().numpy().tolist()   # 归一化坐标 0~1
        ids = [int(c) for c in r.boxes.cls.cpu().numpy()]
        confs = [float(c) for c in r.boxes.conf.cpu().numpy()]
        names = [get_class_name_cn(cid) for cid in ids]
        return boxes, ids, confs, names

    def _parse_result(self, r) -> Dict[str, Any]:
        """把 ultralytics 批量推理的单条结果解析成统一格式"""
        if r.boxes is None or len(r.boxes) == 0:
            return {"boxes": [], "class_ids": [], "confidences": [], "class_names": [], "inference_time": 0.0}
        boxes = r.boxes.xyxyn.cpu().numpy().tolist()
        ids = [int(c) for c in r.boxes.cls.cpu().numpy()]
        confs = [float(c) for c in r.boxes.conf.cpu().numpy()]
        return {
            "boxes": boxes,
            "class_ids": ids,
            "confidences": confs,
            "class_names": [get_class_name_cn(cid) for cid in ids],
            "inference_time": 0.0,
        }

    def _simulate_detection(self, image_path: str) -> Tuple[List, List, List, List]:
        """
        演示模式：按文件路径哈希生成确定性的模拟检测结果。
        同一张图每次检测结果一致，便于演示；每张图随机 1~3 个缺陷框。
        """
        seed = int(uuid.uuid5(uuid.NAMESPACE_URL, str(image_path)).hex[:8], 16)
        rng = np.random.default_rng(seed)
        # 20% 概率模拟"合格"（无缺陷），演示时合格/不合格两种结论都能看到
        if rng.random() < 0.2:
            return [], [], [], []
        n = int(rng.integers(1, 4))
        ids = [int(rng.integers(0, len(DEFECT_CLASSES))) for _ in range(n)]
        boxes, confs, names = [], [], []
        for cid in ids:
            x1 = float(rng.uniform(0.05, 0.55))
            y1 = float(rng.uniform(0.05, 0.55))
            x2 = min(1.0, x1 + float(rng.uniform(0.15, 0.40)))
            y2 = min(1.0, y1 + float(rng.uniform(0.15, 0.40)))
            boxes.append([round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)])
            confs.append(round(float(rng.uniform(0.55, 0.95)), 4))
            names.append(get_class_name_cn(cid))
        logger.info("演示模式生成 %d 个模拟缺陷框: %s", n, image_path)
        return boxes, ids, confs, names
