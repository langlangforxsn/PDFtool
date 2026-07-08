/**
 * 叮当猫的口袋 - PDF 工具 公共 JS
 */

// 后端 API 地址（自动判断：本地 / Render / 环境变量）
const API_BASE = (() => {
  // 本地开发环境（Flask 同时托管前后端）
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1') return '';
  // 生产环境：前端和后端同一服务器
  return '';
})();

/**
 * 上传文件并处理
 */
async function uploadAndProcess(endpoint, formData, downloadName, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${endpoint}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const blob = xhr.response;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = downloadName || "output.pdf";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        resolve(true);
      } else {
        reject(new Error("处理失败，状态码: " + xhr.status));
      }
    };
    xhr.onerror = () => reject(new Error("网络错误，请检查后端服务是否启动"));
    xhr.responseType = "blob";
    xhr.send(formData);
  });
}

/**
 * 格式化文件大小
 */
function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

/**
 * 生成上传组件数据（使用 Object.assign 避免破坏 Alpine 响应式）
 * 用法: return uploadData({ multiFile: true, accept: '.pdf' }, { ...定制属性... });
 */
function uploadData(options, custom) {
  return Object.assign({
    files: [],
    processing: false,
    progress: 0,
    error: "",
    success: false,
    multiFile: options.multiFile || false,
    accept: options.accept || ".pdf",
    maxSize: options.maxSize || 50 * 1024 * 1024,
    dragOver: false,

    handleDrop(e) {
      this.dragOver = false;
      this.addFiles(Array.from(e.dataTransfer.files));
    },

    handleFileSelect(e) {
      const selected = Array.from(e.target.files);
      this.addFiles(selected);
      e.target.value = "";
    },

    addFiles(newFiles) {
      this.error = "";
      this.success = false;
      for (const file of newFiles) {
        if (file.size > this.maxSize) {
          this.error = `文件 ${file.name} 超过 50MB 限制`;
          continue;
        }
        if (this.multiFile) {
          this.files.push(file);
        } else {
          this.files = [file];
        }
      }
    },

    removeFile(index) {
      this.files.splice(index, 1);
    },

    clearFiles() {
      this.files = [];
      this.error = "";
      this.success = false;
      this.progress = 0;
    },

    get totalSize() {
      return this.files.reduce((sum, f) => sum + f.size, 0);
    },

    get hasFiles() {
      return this.files.length > 0;
    },

    async processRequest(endpoint, formData, downloadName) {
      this.processing = true;
      this.progress = 0;
      this.error = "";
      this.success = false;
      try {
        await uploadAndProcess(endpoint, formData, downloadName, (p) => { this.progress = p; });
        this.success = true;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.processing = false;
      }
    }
  }, custom);
}
