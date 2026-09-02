"""
YOLOv8 模型训练脚本

先运行 convert_neu.py 完成数据转换，再运行本脚本：
    .venv/Scripts/python.exe train/train.py           # 首次训练
    .venv/Scripts/python.exe train/train.py --epochs 80   # 断点续训（从 best.pt 继续）

若 backend/models/best.pt 已存在，自动从它继续训练（断点续训）；
否则使用官方预训练权重 yolov8n.pt 从头训练。
训练完成后自动把 best.pt 复制到 backend/models/best.pt（后端检测器直接使用）。
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_YAML = Path(__file__).resolve().parent / "datasets" / "NEU" / "data.yaml"
MODEL_OUTPUT = BACKEND_ROOT / "models" / "best.pt"

# ---------------- 训练参数（按需调整） ----------------
DEFAULT_EPOCHS = 80  # 每次运行的训练轮数（续训时累加到已有进度上）
IMG_SIZE = 640       # 输入图像尺寸（与后端预处理一致）
BATCH_SIZE = 16      # 批次大小（RTX 4050 6GB 显存可稳定运行）
DEVICE = 0           # 0 = 第一块 GPU；无 GPU 自动回退 CPU


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 缺陷检测模型训练")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS, help=f"训练轮数（默认 {DEFAULT_EPOCHS}）")
    args = parser.parse_args()

    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"未找到 {DATA_YAML}，请先运行 convert_neu.py 完成数据转换"
        )

    # 断点续训：已有 best.pt 则从它继续学，否则用官方预训练权重
    resume = MODEL_OUTPUT.exists()
    pretrained = MODEL_OUTPUT if resume else "yolov8n.pt"

    print("=" * 60)
    print("开始训练 YOLOv8 缺陷检测模型")
    print(f"  数据配置: {DATA_YAML}")
    print(f"  训练轮数: {args.epochs}  图像尺寸: {IMG_SIZE}  批次: {BATCH_SIZE}")
    print(f"  权重来源: {'best.pt 断点续训' if resume else 'yolov8n.pt 官方预训练'}")
    print("=" * 60)

    # 加载权重（断点续训或官方预训练，官方权重首次运行会自动下载 ~6MB）
    model = YOLO(str(pretrained))

    model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        # Windows 下必须 workers=0（主进程直接读数据）：
        # 默认的多进程 DataLoader 在 Windows 上反复重启子进程（每个都要重新
        # 加载 torch/ultralytics），会导致训练卡住几十分钟不出一轮结果
        workers=0,
        project=str(Path(__file__).resolve().parent / "runs"),
        name="neu_defect",
        exist_ok=True,
        seed=42,
    )

    # 把最优权重复制到后端模型目录
    best_path = Path(__file__).resolve().parent / "runs" / "neu_defect" / "weights" / "best.pt"
    MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_path, MODEL_OUTPUT)
    print("=" * 60)
    print(f"训练完成！模型已复制到: {MODEL_OUTPUT}")
    print("后端重启后即可使用真实模型检测（python run.py）")
    print("=" * 60)


if __name__ == "__main__":
    main()
