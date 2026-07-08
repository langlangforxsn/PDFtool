"""PDF 压缩功能"""
import os
import subprocess


def compress_pdf(pdf_path, quality="medium"):
    """
    压缩 PDF 文件
    :param pdf_path: PDF 文件路径
    :param quality: 压缩质量 (low, medium, high)
    :return: 压缩后的 PDF 文件路径
    """
    # 先尝试 pikepdf 压缩
    try:
        return _compress_with_pikepdf(pdf_path, quality)
    except Exception:
        pass

    # 回退到 Ghostscript
    try:
        return _compress_with_ghostscript(pdf_path, quality)
    except Exception:
        pass

    # 最后用 pypdf 基础压缩
    return _compress_with_pypdf(pdf_path)


def _compress_with_pikepdf(pdf_path, quality):
    """使用 pikepdf 压缩"""
    import pikepdf

    quality_map = {
        "low": "/Screen",      # 最小体积
        "medium": "/eBook",    # 平衡
        "high": "/Printer",    # 高质量
    }
    compression = quality_map.get(quality, "/eBook")

    output_path = os.path.join(os.path.dirname(pdf_path), "compressed.pdf")

    with pikepdf.open(pdf_path) as pdf:
        pdf.save(output_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)

    return output_path


def _compress_with_ghostscript(pdf_path, quality):
    """使用 Ghostscript 压缩"""
    quality_map = {
        "low": "/screen",
        "medium": "/ebook",
        "high": "/printer",
    }
    gs_quality = quality_map.get(quality, "/ebook")

    output_path = os.path.join(os.path.dirname(pdf_path), "compressed.pdf")

    gs_commands = ["gs", "gswin64c", "gswin32c"]
    for cmd in gs_commands:
        try:
            result = subprocess.run([
                cmd, "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={gs_quality}",
                "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={output_path}",
                pdf_path
            ], capture_output=True, timeout=60)
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    raise RuntimeError("Ghostscript 不可用")


def _compress_with_pypdf(pdf_path):
    """使用 pypdf 基础压缩（移除重复对象）"""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # 移除重复对象
    writer.compress_identical_objects()

    output_path = os.path.join(os.path.dirname(pdf_path), "compressed.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
