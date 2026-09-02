<template>
  <div class="app-container">
    <!-- 顶部系统标题栏 + 导航 -->
    <header class="app-header">
      <div class="header-inner">
        <div class="logo">🏭 智能车间产品外观缺陷检测与报告系统</div>
        <nav class="nav">
          <router-link to="/" class="nav-link" exact-active-class="active">检测台</router-link>
          <router-link to="/history" class="nav-link" active-class="active">历史记录</router-link>
        </nav>
      </div>
    </header>

    <!-- 页面主体 -->
    <main class="app-main">
      <router-view />
    </main>

    <footer class="app-footer">基于 YOLOv8 深度学习 · FastAPI · Vue 3 的工业缺陷检测平台</footer>
  </div>
</template>

<script setup>
// 根组件：只负责整体布局（顶栏 + 内容区）
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background: #f0f2f5;
}

.app-container { min-height: 100vh; display: flex; flex-direction: column; }

.app-header {
  background: linear-gradient(135deg, #1f3a5f 0%, #2b5a94 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo { font-size: 19px; font-weight: 600; letter-spacing: 1px; }

.nav { display: flex; gap: 8px; }

.nav-link {
  color: #d5e3f5;
  text-decoration: none;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 15px;
  transition: all 0.2s;
}

.nav-link:hover { background: rgba(255, 255, 255, 0.12); color: #fff; }

.nav-link.active { background: #fff; color: #1f3a5f; font-weight: 600; }

.app-main {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 24px 32px;
}

.app-footer {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 14px 0 18px;
}

.card-title { font-weight: 600; font-size: 15px; }
</style>
