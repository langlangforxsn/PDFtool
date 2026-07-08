"""
叮当猫的口袋 - PDF 工具后端 API
"""
import os
import zipfile
import tempfile
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# 前端文件目录（开发和生产均可用）
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if not os.path.isdir(FRONTEND_DIR):
    # Docker 中 frontend 在 /app/frontend/
    FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

from utils.file_handler import save_upload, cleanup_task_dir, allowed_file, get_extension
from utils.pdf_merger import merge_pdfs
from utils.pdf_splitter import split_pdf, split_pdf_every_page
from utils.pdf_watermark import add_text_watermark, add_image_watermark
from utils.pdf_converter import pdf_to_images, images_to_pdf, office_to_pdf, pdf_to_word
from utils.pdf_compressor import compress_pdf

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})


@app.after_request
def add_cors_headers(response):
    """手动添加 CORS 头，确保跨域请求正常"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# 配置
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB


# ============================================================
#  工具函数
# ============================================================

@app.before_request
def handle_options():
    """全局处理 OPTIONS 预检请求"""
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response


def error_response(message, status=400):
    return jsonify({"error": message}), status


def get_file_list():
    """从请求中获取多个文件"""
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return None
    return [f for f in files if f.filename]


def get_single_file():
    """从请求中获取单个文件"""
    f = request.files.get("file")
    if not f or f.filename == "":
        return None
    return f


def make_zip(file_paths, zip_name="output.zip"):
    """将多个文件打包为 ZIP"""
    zip_path = os.path.join(os.path.dirname(file_paths[0]), zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            zf.write(fp, os.path.basename(fp))
    return zip_path


# ============================================================
#  健康检查
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "PDF 工具 API"})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """生成 PDF 页面预览缩略图（base64）"""
    file = request.files.get("file")
    if not file or file.filename == "":
        return error_response("请上传 PDF 文件")

    import fitz
    import base64
    import io

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        doc = fitz.open(path)
        total_pages = doc.page_count
        previews = []

        for i in range(total_pages):
            page = doc.load_page(i)
            # 生成高清缩略图 (宽度 1200px，在大列模式下也很清晰)
            pix = page.get_pixmap(dpi=200)
            factor = 1200 / pix.width
            pix = page.get_pixmap(dpi=int(200 * factor))
            img_data = pix.tobytes("jpeg")

            buf = io.BytesIO()
            buf.write(img_data)
            buf.seek(0)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            previews.append({
                "page": i + 1,
                "width": pix.width,
                "height": pix.height,
                "data_url": f"data:image/jpeg;base64,{b64}"
            })

        doc.close()
        return jsonify({"pages": total_pages, "previews": previews})
    except Exception as e:
        return error_response(f"生成预览失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


@app.route("/api/test-upload", methods=["POST", "OPTIONS"])
def test_upload():
    """测试上传是否正常工作"""
    if request.method == "OPTIONS":
        return "", 204

    files = request.files.getlist("files")
    file_count = len([f for f in files if f.filename])
    return jsonify({
        "received_files": file_count,
        "names": [f.filename for f in files if f.filename]
    })


# ============================================================
#  前端页面（开发模式：Flask 直接托管前端，避免 CORS 问题）
# ============================================================

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_frontend(filename):
    """托管前端静态文件（HTML、CSS、JS）"""
    filepath = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(FRONTEND_DIR, filename)
    return send_from_directory(FRONTEND_DIR, "index.html")


# ============================================================
#  PDF 合并
# ============================================================

@app.route("/api/merge", methods=["POST", "OPTIONS"])
def api_merge():
    if request.method == "OPTIONS":
        return "", 204

    files = get_file_list()
    if not files or len(files) < 2:
        return error_response("请上传至少 2 个 PDF 文件")

    task_dir = None
    try:
        paths = []
        for f in files:
            if get_extension(f.filename) != "pdf":
                return error_response(f"文件 {f.filename} 不是 PDF 格式")
            path, _, task_dir = save_upload(f)
            paths.append(path)

        output = merge_pdfs(paths)
        return send_file(output, as_attachment=True, download_name="merged.pdf")
    except Exception as e:
        return error_response(f"合并失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 拆分
# ============================================================

@app.route("/api/split", methods=["POST"])
def api_split():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    if get_extension(file.filename) != "pdf":
        return error_response("请上传 PDF 格式文件")

    mode = request.form.get("mode", "range")  # range 或 every_page
    page_ranges = request.form.get("page_ranges", "")

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)

        if mode == "every_page":
            outputs = split_pdf_every_page(path)
        else:
            if not page_ranges.strip():
                return error_response("请指定页码范围，如: 1-3,5,7-10")
            ranges = [r.strip() for r in page_ranges.split(",") if r.strip()]
            outputs = split_pdf(path, ranges)

        if len(outputs) == 1:
            return send_file(outputs[0], as_attachment=True, download_name="split.pdf")
        else:
            zip_path = make_zip(outputs, "split_files.zip")
            return send_file(zip_path, as_attachment=True, download_name="split_files.zip")
    except Exception as e:
        return error_response(f"拆分失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 添加文字水印
# ============================================================

@app.route("/api/watermark/text", methods=["POST"])
def api_watermark_text():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    text = request.form.get("text", "水印")
    opacity = float(request.form.get("opacity", 0.3))
    font_size = int(request.form.get("font_size", 40))
    color = request.form.get("color", "#999999")
    angle = int(request.form.get("angle", 45))

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        output = add_text_watermark(path, text, opacity=opacity, font_size=font_size,
                                     color=color, angle=angle)
        return send_file(output, as_attachment=True, download_name="watermarked.pdf")
    except Exception as e:
        return error_response(f"添加水印失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 添加图片水印
# ============================================================

@app.route("/api/watermark/image", methods=["POST"])
def api_watermark_image():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    watermark_img = request.files.get("watermark_image")
    if not watermark_img:
        return error_response("请上传水印图片")

    opacity = float(request.form.get("opacity", 0.3))
    scale = float(request.form.get("scale", 0.3))
    position = request.form.get("position", "center")

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        img_path, _, _ = save_upload(watermark_img)
        output = add_image_watermark(path, img_path, opacity=opacity, scale=scale,
                                      position=position)
        return send_file(output, as_attachment=True, download_name="watermarked.pdf")
    except Exception as e:
        return error_response(f"添加水印失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 转图片
# ============================================================

@app.route("/api/convert/pdf-to-image", methods=["POST"])
def api_pdf_to_image():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    fmt = request.form.get("format", "png")
    dpi = int(request.form.get("dpi", 200))

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        outputs = pdf_to_images(path, fmt=fmt, dpi=dpi)

        if len(outputs) == 1:
            return send_file(outputs[0], as_attachment=True,
                             download_name=f"page_1.{fmt}")
        else:
            zip_path = make_zip(outputs, f"pdf_images.{fmt}.zip")
            return send_file(zip_path, as_attachment=True,
                             download_name=f"pdf_images.{fmt}.zip")
    except Exception as e:
        return error_response(f"转换失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  图片转 PDF
# ============================================================

@app.route("/api/convert/image-to-pdf", methods=["POST"])
def api_image_to_pdf():
    files = get_file_list()
    if not files:
        return error_response("请上传图片文件")

    task_dir = None
    try:
        paths = []
        for f in files:
            ext = get_extension(f.filename)
            if ext not in ("png", "jpg", "jpeg", "bmp", "tiff", "tif"):
                return error_response(f"文件 {f.filename} 不是支持的图片格式")
            path, _, task_dir = save_upload(f)
            paths.append(path)

        output = images_to_pdf(paths)
        return send_file(output, as_attachment=True, download_name="images.pdf")
    except Exception as e:
        return error_response(f"转换失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  Office 转 PDF
# ============================================================

@app.route("/api/convert/office-to-pdf", methods=["POST"])
def api_office_to_pdf():
    file = get_single_file()
    if not file:
        return error_response("请上传 Office 文件")

    ext = get_extension(file.filename)
    if ext not in ("doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"):
        return error_response("不支持的文件格式，请上传 Word/Excel/PPT/TXT 文件")

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        output = office_to_pdf(path)
        download_name = os.path.splitext(file.filename)[0] + ".pdf"
        return send_file(output, as_attachment=True, download_name=download_name)
    except Exception as e:
        return error_response(f"转换失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 转 Word
# ============================================================

@app.route("/api/convert/pdf-to-word", methods=["POST"])
def api_pdf_to_word():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        output = pdf_to_word(path)
        download_name = os.path.splitext(file.filename)[0] + ".docx"
        return send_file(output, as_attachment=True, download_name=download_name)
    except Exception as e:
        return error_response(f"转换失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 压缩
# ============================================================

@app.route("/api/compress", methods=["POST"])
def api_compress():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    quality = request.form.get("quality", "medium")

    task_dir = None
    try:
        path, _, task_dir = save_upload(file)
        output = compress_pdf(path, quality=quality)
        return send_file(output, as_attachment=True, download_name="compressed.pdf")
    except Exception as e:
        return error_response(f"压缩失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 页面旋转
# ============================================================

@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    angle = int(request.form.get("angle", 90))
    pages_str = request.form.get("pages", "all")

    task_dir = None
    try:
        from pypdf import PdfReader, PdfWriter
        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)
        writer = PdfWriter()

        total = len(reader.pages)

        if pages_str == "all":
            page_indices = list(range(total))
        else:
            from utils.pdf_splitter import parse_page_range
            page_indices = [p - 1 for p in parse_page_range(pages_str, total)]

        for i, page in enumerate(reader.pages):
            if i in page_indices:
                page.rotate(angle)
            writer.add_page(page)

        output_path = os.path.join(task_dir, "rotated.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name="rotated.pdf")
    except Exception as e:
        return error_response(f"旋转失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 删除页面
# ============================================================

@app.route("/api/delete-pages", methods=["POST"])
def api_delete_pages():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    pages_str = request.form.get("pages", "")
    if not pages_str.strip():
        return error_response("请指定要删除的页码")

    task_dir = None
    try:
        from pypdf import PdfReader, PdfWriter
        from utils.pdf_splitter import parse_page_range
        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)
        writer = PdfWriter()

        total = len(reader.pages)
        delete_indices = set(p - 1 for p in parse_page_range(pages_str, total))

        for i, page in enumerate(reader.pages):
            if i not in delete_indices:
                writer.add_page(page)

        output_path = os.path.join(task_dir, "pages_deleted.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name="pages_deleted.pdf")
    except Exception as e:
        return error_response(f"删除页面失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 加密
# ============================================================

@app.route("/api/encrypt", methods=["POST"])
def api_encrypt():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    password = request.form.get("password", "")
    if not password:
        return error_response("请设置密码")

    task_dir = None
    try:
        from pypdf import PdfReader, PdfWriter
        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)

        output_path = os.path.join(task_dir, "encrypted.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name="encrypted.pdf")
    except Exception as e:
        return error_response(f"加密失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 解密
# ============================================================

@app.route("/api/decrypt", methods=["POST"])
def api_decrypt():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    password = request.form.get("password", "")

    task_dir = None
    try:
        from pypdf import PdfReader, PdfWriter
        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)

        if reader.is_encrypted:
            if not password:
                return error_response("PDF 已加密，请提供密码")
            reader.decrypt(password)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_path = os.path.join(task_dir, "decrypted.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name="decrypted.pdf")
    except Exception as e:
        return error_response(f"解密失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  PDF 添加页码
# ============================================================

@app.route("/api/add-page-numbers", methods=["POST"])
def api_add_page_numbers():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    position = request.form.get("position", "bottom-center")
    font_size = int(request.form.get("font_size", 12))

    task_dir = None
    try:
        import io
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as rl_canvas

        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)
        writer = PdfWriter()
        total = len(reader.pages)

        for i, page in enumerate(reader.pages):
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # 生成页码 PDF
            buf = io.BytesIO()
            c = rl_canvas.Canvas(buf, pagesize=(page_width, page_height))
            c.setFont("Helvetica", font_size)
            text = str(i + 1)

            positions = {
                "bottom-center": (page_width / 2, 30),
                "bottom-right": (page_width - 50, 30),
                "bottom-left": (50, 30),
                "top-center": (page_width / 2, page_height - 30),
                "top-right": (page_width - 50, page_height - 30),
                "top-left": (50, page_height - 30),
            }
            x, y = positions.get(position, (page_width / 2, 30))

            c.drawCentredString(x, y, text)
            c.save()
            buf.seek(0)

            num_reader = PdfReader(buf)
            page.merge_page(num_reader.pages[0])
            writer.add_page(page)

        output_path = os.path.join(task_dir, "numbered.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name="numbered.pdf")
    except Exception as e:
        return error_response(f"添加页码失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  获取 PDF 信息
# ============================================================

@app.route("/api/info", methods=["POST"])
def api_info():
    file = get_single_file()
    if not file:
        return error_response("请上传 PDF 文件")

    task_dir = None
    try:
        from pypdf import PdfReader
        path, _, task_dir = save_upload(file)
        reader = PdfReader(path)

        info = {
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "metadata": {}
        }

        if reader.metadata:
            info["metadata"] = {
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "creator": reader.metadata.get("/Creator", ""),
                "producer": reader.metadata.get("/Producer", ""),
            }

        return jsonify(info)
    except Exception as e:
        return error_response(f"获取信息失败: {str(e)}", 500)
    finally:
        cleanup_task_dir(task_dir)


# ============================================================
#  启动
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
