import os
import uuid
import shutil
import tempfile
from werkzeug.utils import secure_filename

# 临时文件目录
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_tool_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_extension(filename):
    """获取文件扩展名（小写）"""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def save_upload(file_storage):
    """保存上传文件到临时目录，返回 (文件路径, 原始文件名)"""
    filename = secure_filename(file_storage.filename)
    if not filename:
        filename = f"upload_{uuid.uuid4().hex[:8]}.pdf"

    # 用 UUID 子目录避免文件名冲突
    task_dir = os.path.join(UPLOAD_DIR, uuid.uuid4().hex[:12])
    os.makedirs(task_dir, exist_ok=True)

    filepath = os.path.join(task_dir, filename)
    file_storage.save(filepath)
    return filepath, filename, task_dir


def cleanup_task_dir(task_dir):
    """清理任务临时目录"""
    if task_dir and os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)


def make_response_file(filepath, download_name=None):
    """构建文件下载响应"""
    from flask import send_file
    return send_file(
        filepath,
        as_attachment=True,
        download_name=download_name or os.path.basename(filepath)
    )
