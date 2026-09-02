import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器配置：
// - 端口 5173
// - 代理：/api、/uploads、/results 请求转发到后端 8000 端口，
//   前端代码里写相对路径即可，无跨域问题
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
      '/results': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
