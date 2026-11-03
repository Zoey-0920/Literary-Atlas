<script setup>
// 顶部导航栏组件
// links 数组：每一项表示一个菜单，path 是跳转地址，label 是显示文字
const links = [
  { path: '/', label: '首页' },
  { path: '/map', label: '世界地图' },
  { path: '/works', label: '作品探索' },
  { path: '/bookshelf', label: '我的书架' },
  { path: '/footprint', label: '我的足迹' },
  { path: '/ai', label: 'AI 探索' }
]
</script>

<template>
  <header class="navbar">
    <div class="container navbar-inner">
      <!-- 品牌名：点击回到首页 -->
      <router-link to="/" class="brand">
        <span class="brand-mark">◈</span>
        <span class="brand-text">Literary Atlas</span>
      </router-link>

      <!-- 导航菜单 -->
      <nav class="nav-links">
        <router-link
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          class="nav-link"
        >
          {{ link.label }}
        </router-link>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  background: var(--deep);
  color: var(--paper);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.15);
}
.navbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: "Georgia", "Noto Serif SC", serif;
  font-size: 20px;
  letter-spacing: 0.03em;
}
.brand-mark {
  color: var(--gold);
  font-size: 22px;
}
.nav-links {
  display: flex;
  gap: 6px;
}
.nav-link {
  padding: 8px 14px;
  border-radius: 2px;
  font-size: 14px;
  color: rgba(246, 241, 231, 0.85);
  transition: all 0.2s;
}
.nav-link:hover {
  color: var(--gold-soft);
  background: rgba(255, 255, 255, 0.06);
}
/* 当前所在页面的菜单高亮 */
.nav-link.router-link-active {
  color: var(--gold-soft);
}

/* 移动端：菜单换行显示 */
@media (max-width: 760px) {
  .navbar-inner {
    height: auto;
    flex-direction: column;
    padding: 12px 24px;
    gap: 10px;
  }
  .nav-links {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>