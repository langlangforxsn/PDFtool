"""PDF 拆分功能"""
import os
from pypdf import PdfReader, PdfWriter


def split_pdf(pdf_path, page_ranges):
    """
    拆分 PDF 文件
    :param pdf_path: PDF 文件路径
    :param page_ranges: 页码范围列表，如 ["1-3", "5", "7-10"]
    :return: 拆分后的 PDF 文件路径列表
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    output_dir = os.path.dirname(pdf_path)
    output_files = []

    for idx, page_range in enumerate(page_ranges):
        writer = PdfWriter()
        pages = parse_page_range(page_range, total_pages)

        for page_num in pages:
            writer.add_page(reader.pages[page_num - 1])  # 转为 0-based 索引

        output_path = os.path.join(output_dir, f"split_part_{idx + 1}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)
        output_files.append(output_path)

    return output_files


def split_pdf_every_page(pdf_path):
    """
    将 PDF 拆分为每一页单独一个文件
    :param pdf_path: PDF 文件路径
    :return: 拆分后的 PDF 文件路径列表
    """
    reader = PdfReader(pdf_path)
    output_dir = os.path.dirname(pdf_path)
    output_files = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        output_path = os.path.join(output_dir, f"page_{i + 1}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)
        output_files.append(output_path)

    return output_files


def parse_page_range(range_str, total_pages):
    """
    解析页码范围字符串
    :param range_str: 如 "1-3", "5", "7-10"
    :param total_pages: 总页数
    :return: 页码列表
    """
    pages = []
    parts = range_str.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start))
            end = min(total_pages, int(end))
            pages.extend(range(start, end + 1))
        else:
            num = int(part)
            if 1 <= num <= total_pages:
                pages.append(num)

    return sorted(set(pages))
