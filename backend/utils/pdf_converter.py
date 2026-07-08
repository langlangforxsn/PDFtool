"""PDF 格式转换功能"""
import os
import subprocess
from PIL import Image


"""PDF 格式转换功能"""
import os
import subprocess
from PIL import Image


def pdf_to_images(pdf_path, fmt="png", dpi=200):
    """
    PDF 转图片（使用 PyMuPDF，无需系统依赖）
    :param pdf_path: PDF 文件路径
    :param fmt: 输出格式 (png, jpg)
    :param dpi: 分辨率
    :return: 图片文件路径列表
    """
    import fitz

    output_dir = os.path.dirname(pdf_path)
    doc = fitz.open(pdf_path)
    output_files = []

    for i in range(doc.page_count):
        page = doc.load_page(i)
        # 按 DPI 渲染页面为图片
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        ext = "jpg" if fmt.lower() in ("jpg", "jpeg") else "png"
        output_path = os.path.join(output_dir, f"page_{i + 1}.{ext}")
        pix.save(output_path)
        output_files.append(output_path)

    doc.close()
    return output_files


def images_to_pdf(image_paths):
    """
    多张图片合并为 PDF
    :param image_paths: 图片文件路径列表
    :return: PDF 文件路径
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    output_dir = os.path.dirname(image_paths[0])
    output_path = os.path.join(output_dir, "images_to_pdf.pdf")

    c = canvas.Canvas(output_path)

    for img_path in image_paths:
        img = Image.open(img_path)
        img_width, img_height = img.size

        # 以图片尺寸为页面大小（转换为 points，1px ≈ 0.75pt）
        page_width = img_width * 0.75
        page_height = img_height * 0.75

        c.setPageSize((page_width, page_height))
        c.drawImage(img_path, 0, 0, page_width, page_height)
        c.showPage()

    c.save()
    return output_path


def office_to_pdf(file_path):
    """
    Office 文档转 PDF（需要 LibreOffice）
    :param file_path: Office 文件路径
    :return: PDF 文件路径
    """
    output_dir = os.path.dirname(file_path)

    # 尝试不同的 LibreOffice 路径
    lo_commands = ["libreoffice", "soffice",
                   r"C:\Program Files\LibreOffice\program\soffice.exe",
                   r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
    for cmd in lo_commands:
        try:
            result = subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf", "--outdir", output_dir, file_path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}.pdf")
                if os.path.exists(output_path):
                    return output_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except OSError:
            continue

    raise RuntimeError("LibreOffice 未安装。本地 Windows 开发环境不支持此功能，部署到 Docker 后将自动可用。")


def pdf_to_word(pdf_path):
    """
    PDF 转 Word（需要 pdf2docx）
    :param pdf_path: PDF 文件路径
    :return: Word 文件路径
    """
    from pdf2docx import Converter

    output_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.docx")

    cv = Converter(pdf_path)
    cv.convert(output_path)
    cv.close()

    return output_path
