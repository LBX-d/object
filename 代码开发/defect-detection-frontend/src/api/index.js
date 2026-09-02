/**
 * axios 实例封装
 * - baseURL = /api（由 Vite 代理转发到后端）
 * - 请求拦截器：打印日志；GET 请求自动加时间戳参数防浏览器缓存
 * - 响应拦截器：统一处理 {code, msg, data} 结构，非 0 弹错误提示
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 120000, // 推理可能较慢，超时设长一点
})

// ---- 请求拦截器 ----
service.interceptors.request.use(
  (config) => {
    if ((config.method || 'get').toLowerCase() === 'get') {
      config.params = { ...(config.params || {}), _t: Date.now() }
    }
    console.log(`[API请求] ${(config.method || 'GET').toUpperCase()} ${config.url}`, config.params || config.data || '')
    return config
  },
  (error) => Promise.reject(error)
)

// ---- 响应拦截器 ----
service.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.code !== 'undefined' && body.code !== 0) {
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    // 统一解包：直接返回业务数据 data
    return body ? body.data : response.data
  },
  (error) => {
    // 网络级错误（后端未启动/未就绪，error.response 为空）：
    // 不弹错误提示，由页面自行处理（显示连接中状态并自动重试）
    if (!error.response) {
      return Promise.reject(error)
    }
    const msg = error.response?.data?.msg || error.message || '网络错误'
    ElMessage.error(`请求失败: ${msg}`)
    return Promise.reject(error)
  }
)

export default service
