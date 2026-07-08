"""PDF 水印功能（PIL 图片渲染 + PyMuPDF 叠加）"""
import os
import math
import tempfile
import fitz
from PIL import Image, ImageDraw, ImageFont


def _render_text_to_png(text, font_size, color, opacity, angle):
    """将文字渲染为带透明度的 PNG 图片，完美支持中文和任意角度"""
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)

    fonts_to_try = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simkai.ttf",
    ]

    font = None
    for fpath in fonts_to_try:
        if os.path.exists(fpath):
            try:
                font = ImageFont.truetype(fpath, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    # 计算文字大小
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20

    # 旋转后画布
    rad = math.radians(abs(angle))
    cw = int(abs(tw * math.cos(rad)) + abs(th * math.sin(rad))) + 40
    ch = int(abs(tw * math.sin(rad)) + abs(th * math.cos(rad))) + 40

    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    alpha = int(255 * opacity)
    draw.text(((cw - tw) / 2, (ch - th) / 2), text, font=font, fill=(r, g, b, alpha))

    if angle != 0:
        img = img.rotate(angle, expand=True, resample=Image.BICUBIC)

    return img


def add_text_watermark(pdf_path, text, opacity=0.3, font_size=40, color="#999999",
                       angle=0, spacing_x=200, spacing_y=150):
    """给 PDF 添加文字水印（平铺），图片渲染，完美支持中文 + 任意角度"""
    wm_img = _render_text_to_png(text, font_size, color, opacity, angle)
    wm_path = os.path.join(tempfile.gettempdir(), f"_wm_{os.getpid()}.png")
    wm_img.save(wm_path)

    doc = fitz.open(pdf_path)

    for page in doc:
        pw = page.rect.width
        ph = page.rect.height
        ww = wm_img.width * 0.75   # px -> pt
        wh = wm_img.height * 0.75

        for cy in range(0, int(ph) + spacing_y, spacing_y):
            for cx in range(-spacing_x, int(pw) + spacing_x, spacing_x):
                rect = fitz.Rect(cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
                page.insert_image(rect, filename=wm_path, keep_proportion=True, overlay=True)

    output_path = os.path.join(os.path.dirname(pdf_path), "watermarked.pdf")
    doc.save(output_path, incremental=False)
    doc.close()

    try:
        os.remove(wm_path)
    except:
        pass

    return output_path


def add_image_watermark(pdf_path, image_path, opacity=0.3, scale=0.3, position="center"):
    """给 PDF 添加图片水印（PIL 预处理透明度）"""
    from PIL import Image as PILImage

    # 用 PIL 打开图片，设置透明度
    img = PILImage.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # 修改 alpha 通道
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * opacity))
    img = PILImage.merge("RGBA", (r, g, b, a))

    wm_path = os.path.join(tempfile.gettempdir(), f"_wm_img_{os.getpid()}.png")
    img.save(wm_path)

    doc = fitz.open(pdf_path)

    for page in doc:
        pw = page.rect.width
        ph = page.rect.height
        dw = pw * scale
        dh = dw

        if position == "center":
            x = (pw - dw) / 2
            y = (ph - dh) / 2
            rect = fitz.Rect(x, y, x + dw, y + dh)
            page.insert_image(rect, filename=wm_path, keep_proportion=True, overlay=True)
        elif position == "tile":
            sx = dw * 1.5
            sy = dh * 1.5
            for yp in range(0, int(ph) + int(sy), int(sy)):
                for xp in range(0, int(pw) + int(sx), int(sx)):
                    rect = fitz.Rect(xp, yp, xp + dw, yp + dh)
                    page.insert_image(rect, filename=wm_path, keep_proportion=True, overlay=True)

    output_path = os.path.join(os.path.dirname(pdf_path), "watermarked.pdf")
    doc.save(output_path, incremental=False)
    doc.close()

    try:
        os.remove(wm_path)
    except:
        pass

    return output_path
