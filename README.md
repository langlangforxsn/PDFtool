# PDF 工具开发文档

## 项目概述

**项目名称：** 叮当猫的口袋 - PDF 编辑转换工具
**项目路径：** `D:\Code\dingdangCatPocket\changePDF`
**创建日期：** 2026-07-08
**项目目标：** 开发一个在线 PDF 工具，作为"叮当猫的口袋"门户的第三个工具

---

## 技术架构

### 部署方案：Vercel + Render 混合架构

| 层级 | 平台 | 说明 |
|------|------|------|
| **前端** | Vercel | 静态页面托管（HTML/Tailwind/Alpine.js），CDN 加速 |
| **后端 API** | Render (Docker) | Flask PDF 处理服务，安装 LibreOffice/Poppler/Ghostscript |

### 前后端通信流程

```
用户浏览器 → Vercel (前端页面)
    ↓ 上传文件 + 选择操作
用户浏览器 → Render (Flask API)  ← 直接上传，不经过 Vercel
    ↓ 处理完成，返回结果
用户浏览器 ← 下载处理后的文件
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask | 轻量灵活 |
| PDF 核心库 | pypdf, reportlab, pikepdf | 纯 Python，无系统依赖 |
| 图片处理 | Pillow | 图片 ↔ PDF |
| Office 转换 | LibreOffice Headless | Word/Excel/PPT → PDF（Docker 安装）|
| PDF 渲染 | pdf2image + Poppler | PDF → 图片（Docker 安装）|
| 压缩 | pikepdf / Ghostscript | 压缩优化（Docker 安装）|
| 跨域 | Flask-CORS | 前后端分离通信 |
| 前端样式 | Tailwind CSS (CDN) | 和门户保持一致风格 |
| 前端交互 | Alpine.js + Fetch API | 文件上传 + API 调用 |

---

## 功能模块

### 第一期（核心功能 - 纯 Python 库）

| 功能 | 说明 | 核心库 |
|------|------|--------|
| PDF 合并 | 多个 PDF 合并为一个 | pypdf |
| PDF 拆分 | 按页码范围拆分/提取指定页面 | pypdf |
| PDF 添加水印 | 文字水印 + 图片水印 | reportlab + pypdf |
| PDF 删除页面 | 删除指定页面 | pypdf |
| PDF 页面旋转 | 旋转指定页面 | pypdf |
| PDF 加密/解密 | 设置/移除密码保护 | pypdf |

### 第二期（需系统依赖）

| 功能 | 说明 | 核心库/工具 |
|------|------|------------|
| PDF → 图片 | 将 PDF 转为 PNG/JPG | pdf2image + Poppler |
| 图片 → PDF | 多张图片合并为 PDF | Pillow + reportlab |
| Word/Excel/PPT → PDF | Office 文档转 PDF | LibreOffice Headless |
| PDF 压缩 | 减小文件体积 | pikepdf / Ghostscript |
| PDF → Word | PDF 转为可编辑 Word | pdf2docx |

### 第三期（高级功能）

| 功能 | 说明 | 核心库 |
|------|------|--------|
| PDF 页面重排 | 拖拽调整页面顺序 | pypdf + 前端拖拽 |
| PDF 添加页码 | 批量添加页码/页眉页脚 | reportlab + pypdf |
| PDF 文字提取 | 提取 PDF 中的文字 | pdfplumber |
| PDF 编辑 | 删除/修改 PDF 中的文字 | PyMuPDF | 🚧 开发中 |
| PDF 表单填写 | 填写/提取表单数据 | pypdf |

---

## 项目结构

```
changePDF/
├── backend/                     # Render 部署的 Flask 后端
│   ├── app.py                   # Flask 主应用 + API 路由
│   ├── requirements.txt         # Python 依赖
│   ├── Dockerfile               # Docker 构建（含系统依赖）
│   ├── render.yaml              # Render 部署配置
│   └── utils/
│       ├── pdf_merger.py        # 合并逻辑
│       ├── pdf_splitter.py      # 拆分逻辑
│       ├── pdf_watermark.py     # 水印逻辑
│       ├── pdf_converter.py     # 格式转换逻辑
│       ├── pdf_compressor.py    # 压缩逻辑
│       └── file_handler.py      # 文件上传/下载/清理
│
└── frontend/                    # Vercel 部署的前端
    ├── index.html               # 首页（功能选择大卡片）
    ├── merge.html               # PDF 合并
    ├── split.html               # PDF 拆分
    ├── watermark.html           # 水印
    ├── convert.html             # 格式转换
    ├── compress.html            # 压缩
    ├── css/
    │   └── style.css            # 公共样式
    ├── js/
    │   └── app.js               # 公共交互逻辑
    └── vercel.json              # Vercel 部署配置
```

---

## 部署方案

### Render（后端）

1. 使用 Dockerfile 构建，安装 LibreOffice、Poppler、Ghostscript
2. 配置 `render.yaml` 部署为 Web Service
3. 免费方案可用，但有 30-60 秒冷启动

### Vercel（前端）

1. 纯静态站点，免费无限制
2. 配置 `vercel.json` 指向前端目录

### 门户集成

部署完成后，更新 `portal/index.html` 添加第三个工具卡片

---

## 开发顺序

1. ✅ 写开发文档（本文档）
2. 搭建后端基础 — Flask 应用骨架 + CORS + 文件上传/下载 API
3. 搭建前端基础 — 首页 + 公共模板 + 导航栏
4. 第一期功能 — 合并、拆分、水印
5. 第二期功能 — 格式转换、压缩
6. 高级功能 — 删除页面、旋转、加密等
7. 部署 — 后端推送到 Render，前端推送到 Vercel
8. 集成到门户 — 更新 portal/index.html

---

## 难度评估

| 功能 | 难度 | 说明 |
|------|------|------|
| PDF 合并/拆分/旋转/删除 | ⭐ 简单 | pypdf 几行代码 |
| 添加水印 | ⭐⭐ 简单 | reportlab 生成 + pypdf 叠加 |
| 加密/解密 | ⭐ 简单 | pypdf 内置支持 |
| 图片 ↔ PDF | ⭐⭐ 中等 | Pillow + reportlab |
| PDF → 图片 | ⭐⭐ 中等 | Docker 安装 Poppler |
| Office → PDF | ⭐⭐⭐ 中等偏难 | Docker 安装 LibreOffice |
| PDF 压缩 | ⭐⭐ 中等 | pikepdf 或 Ghostscript |
| 前端页面 | ⭐⭐ 中等 | 每个功能一个独立页面 |

## 费用

| 平台 | 免费方案 | 付费方案 |
|------|---------|---------|
| Vercel (前端) | ✅ 完全免费 | — |
| Render (后端) | ✅ 免费（有冷启动） | $7/月（无冷启动） |

---

## 参考资料

- [pypdf 文档](https://pypdf.readthedocs.io/)
- [reportlab 文档](https://docs.reportlab.com/)
- [pikepdf 文档](https://pikepdf.readthedocs.io/)
- [Flask 文档](https://flask.palletsprojects.com/)
- [LibreOffice 命令行](https://wiki.documentfoundation.org/Documentation/DevGuide/Advanced_Topics)
