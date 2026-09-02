"""
文件处理工具：文件名校验、唯一命名、保存上传文件等
"""
import uuid
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("file_utils")

# 允许上传的图像格式（扩展名小写）
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def validate_image_filename(filename: str) -> bool:
    """校验文件名是否为允许的图像格式"""
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTS


def get_file_ext(filename: str) -> str:
    """获取小写扩展名，如 .jpg"""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_name: str) -> str:
    """
    生成唯一文件名（UUID 重命名），防止不同用户上传同名文件互相覆盖。
    保留原始扩展名，方便按格式读取。
    """
    ext = get_file_ext(original_name) or ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def save_upload_file(content: bytes, original_name: str) -> Path:
    """
    保存上传文件到 uploads 目录，返回保存后的完整路径。
    content: 文件二进制内容；original_name: 原始文件名（用于取扩展名）
    """
    unique_name = generate_unique_filename(original_name)
    save_path = Path(settings.UPLOAD_DIR) / unique_name
    save_path.write_bytes(content)
    logger.info("上传文件已保存: %s (原始名: %s, %d 字节)", save_path, original_name, len(content))
    return save_path
