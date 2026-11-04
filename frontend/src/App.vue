<script setup>
// App.vue：根组件 —— 左侧图标导航 + 主内容区
import LeftNav from './components/LeftNav.vue'
</script>

<template>
  <div class="app-shell">
    <LeftNav />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  background: var(--bg);
  overflow: hidden;
}
.app-main {
  flex: 1;
  min-width: 0;
  position: relative;
  overflow: auto;
}
</style>