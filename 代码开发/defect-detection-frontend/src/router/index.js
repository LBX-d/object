/**
 * 路由配置
 * /          -> Dashboard 检测台（上传 + 检测结果 + 统计看板 + 最近记录）
 * /history   -> History 历史记录（筛选 + 完整报告）
 */
import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from '../views/Dashboard.vue'
import History from '../views/History.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard, meta: { title: '检测台' } },
    { path: '/history', name: 'history', component: History, meta: { title: '历史记录' } },
  ],
})

// 切换页面时同步浏览器标签标题
router.afterEach((to) => {
  document.title = `${to.meta.title} - 智能车间缺陷检测系统`
})

export default router
