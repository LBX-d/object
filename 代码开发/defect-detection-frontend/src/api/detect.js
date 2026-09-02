/**
 * 上传检测接口封装
 */
import request from './index'

/**
 * 上传图片并执行缺陷检测
 * @param {File} file 图像文件
 * @param {Function} onProgress 上传进度回调 (0-100)
 * @returns {Promise} 检测结果（DetectionResponse 结构）
 */
export function uploadImage(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}
