"""PDF 合并功能"""
from pypdf import PdfWriter, PdfReader


def merge_pdfs(pdf_paths):
    """
    合并多个 PDF 文件
    :param pdf_paths: PDF 文件路径列表
    :return: 合并后的 PDF 文件路径
    """
    writer = PdfWriter()

    for path in pdf_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)

    # 输出到第一个文件所在目录
    import os
    output_path = os.path.join(os.path.dirname(pdf_paths[0]), "merged.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
