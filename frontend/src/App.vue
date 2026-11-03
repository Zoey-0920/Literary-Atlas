<script setup>
// App.vue：整个应用的根组件，负责整体布局骨架
import NavBar from './components/NavBar.vue'
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航栏：每个页面都会显示 -->
    <NavBar />

    <!-- 页面主体：router-view 会根据当前路由显示对应页面 -->
    <main class="app-main">
      <router-view />
    </main>

    <!-- 底部信息 -->
    <footer class="app-footer">
      <p>Literary Atlas · 以阅读丈量世界文学</p>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--paper);
}
.app-main {
  flex: 1;
}
.app-footer {
  text-align: center;
  padding: 24px;
  color: var(--muted);
  font-size: 13px;
  border-top: 1px solid var(--line);
  letter-spacing: 0.05em;
}
</style>