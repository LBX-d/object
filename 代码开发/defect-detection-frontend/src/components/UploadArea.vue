<template>
  <el-card shadow="hover" class="upload-card">
    <template #header>
      <div class="card-title">📤 上传产品图像</div>
    </template>

    <!-- 拖拽/点击上传区域（auto-upload=false，由父组件控制触发检测） -->
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      :disabled="loading"
      accept=".jpg,.jpeg,.png,.bmp"
      :on-change="handleChange"
    >
      <div class="upload-content">
        <div class="upload-icon">📷</div>
        <div class="upload-text">将图片拖到此处，或 <em>点击选择文件</em></div>
        <div class="upload-tip">支持 jpg / jpeg / png / bmp，大小不超过 10MB</div>
      </div>
    </el-upload>

    <!-- 已选文件名 -->
    <div v-if="fileName" class="file-info">
      <el-tag type="info" effect="plain">已选择: {{ fileName }}</el-tag>
    </div>

    <!-- 检测中的加载动画 -->
    <div v-if="loading" class="loading-box">
      <span class="spinner"></span>
      <span>AI 检测中，请稍候（首次上传需加载模型，可能较慢）...</span>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /** 是否正在检测（显示加载动画） */
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['upload'])

const fileName = ref('')

const ALLOWED_EXTS = ['jpg', 'jpeg', 'png', 'bmp']
const MAX_SIZE = 10 * 1024 * 1024 // 10MB

/** 选择文件后校验格式与大小，通过则通知父组件上传 */
function handleChange(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED_EXTS.includes(ext)) {
    ElMessage.error('仅支持 jpg / jpeg / png / bmp 格式的图片')
    return
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error(`文件大小超过 10MB 限制（当前 ${(file.size / 1024 / 1024).toFixed(1)}MB）`)
    return
  }
  fileName.value = file.name
  emit('upload', file.raw)
}
</script>

<style scoped>
.upload-content {
  padding: 26px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon { font-size: 46px; line-height: 1; }

.upload-text { color: #606266; font-size: 14px; }
.upload-text em { color: #409eff; font-style: normal; }

.upload-tip { color: #909399; font-size: 12px; }

.file-info { margin-top: 12px; text-align: center; }

.loading-box {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #409eff;
  font-size: 14px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 3px solid #d0e5ff;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
