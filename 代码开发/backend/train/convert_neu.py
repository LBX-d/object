"""
NEU-DET 数据集格式转换脚本

把 NEU-DET（VOC 格式 XML 标注）转换为 YOLOv8 训练格式：
  - 按 8:2 随机划分训练集/验证集（seed 固定，可复现）
  - 每张图生成同名 .txt 标注：class_id cx cy w h（归一化坐标）
  - 生成 data.yaml 训练配置

用法（backend 目录下）：
    .venv/Scripts/python.exe train/convert_neu.py
"""
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------- 配置 ----------------
NEU_ROOT = Path(r"C:/Users/asus/Desktop/data/NEU/NEU-DET")
IMAGES_DIR = NEU_ROOT / "IMAGES"
ANNOTATIONS_DIR = NEU_ROOT / "ANNOTATIONS"
OUTPUT_DIR = Path(__file__).resolve().parent / "datasets" / "NEU"

# 类别顺序必须与 backend/app/algorithms/defect_mapping.py 中的 DEFECT_CLASSES 完全一致！
CLASS_NAMES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLASS_ID = {name: i for i, name in enumerate(CLASS_NAMES)}

TRAIN_RATIO = 0.8
SEED = 42


def parse_voc_xml(xml_path: Path):
    """解析 VOC 格式 XML，返回 [(class_name, xmin, ymin, xmax, ymax), ...]"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    size = root.find("size")
    width = int(size.find("width").text)
    height = int(size.find("height").text)
    objects = []
    for obj in root.findall("object"):
        name = obj.find("name").text.strip()
        bndbox = obj.find("bndbox")
        xmin = int(float(bndbox.find("xmin").text))
        ymin = int(float(bndbox.find("ymin").text))
        xmax = int(float(bndbox.find("xmax").text))
        ymax = int(float(bndbox.find("ymax").text))
        objects.append((name, xmin, ymin, xmax, ymax))
    return width, height, objects


def to_yolo_label(objects, width, height):
    """VOC 坐标 -> YOLO 归一化坐标字符串（每行一个目标）"""
    lines = []
    for name, xmin, ymin, xmax, ymax in objects:
        if name not in CLASS_ID:
            print(f"  [警告] 未知类别 {name}，跳过")
            continue
        cx = (xmin + xmax) / 2.0 / width
        cy = (ymin + ymax) / 2.0 / height
        w = (xmax - xmin) / width
        h = (ymax - ymin) / height
        lines.append(f"{CLASS_ID[name]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("NEU-DET 数据集转换 (VOC XML -> YOLOv8 格式)")
    print("=" * 60)

    image_files = sorted(IMAGES_DIR.glob("*.jpg"))
    print(f"共发现 {len(image_files)} 张图像")

    # 固定随机种子打乱，保证每次划分一致
    random.seed(SEED)
    random.shuffle(image_files)
    n_train = int(len(image_files) * TRAIN_RATIO)
    train_files, val_files = image_files[:n_train], image_files[n_train:]
    print(f"训练集: {len(train_files)} 张 / 验证集: {len(val_files)} 张")

    # 清空旧输出目录，避免重复数据
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    def convert(file_list, split):
        for img_path in file_list:
            xml_path = ANNOTATIONS_DIR / (img_path.stem + ".xml")
            if not xml_path.exists():
                print(f"  [警告] 缺少标注文件: {xml_path.name}")
                continue
            width, height, objects = parse_voc_xml(xml_path)
            label_text = to_yolo_label(objects, width, height)

            img_out = OUTPUT_DIR / "images" / split / img_path.name
            label_out = OUTPUT_DIR / "labels" / split / (img_path.stem + ".txt")
            img_out.parent.mkdir(parents=True, exist_ok=True)
            label_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_path, img_out)
            label_out.write_text(label_text, encoding="utf-8")

    convert(train_files, "train")
    convert(val_files, "val")
    print("图像与标注转换完成")

    # 生成 data.yaml
    data_yaml = OUTPUT_DIR / "data.yaml"
    data_yaml.write_text(
        "\n".join([
            f"# NEU-DET 钢表面缺陷数据集（自动生成）",
            f"path: {OUTPUT_DIR.as_posix()}",
            "train: images/train",
            "val: images/val",
            "",
            "names:",
        ] + [f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES)]),
        encoding="utf-8",
    )
    print(f"data.yaml 已生成: {data_yaml}")
    print("转换完成！接下来运行 train/train.py 开始训练。")


if __name__ == "__main__":
    main()
