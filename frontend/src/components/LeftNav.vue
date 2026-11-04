<script setup>
// 左侧图标导航：品牌徽记 + 地图 / 探索 / 书架 / 足迹 / AI 助手 / 个人中心
const items = [
  { to: '/', label: '地图', icon: 'map' },
  { to: '/works', label: '探索', icon: 'compass' },
  { to: '/bookshelf', label: '书架', icon: 'books' },
  { to: '/footprint', label: '足迹', icon: 'footprints' },
  { to: '/ai', label: 'AI 助手', icon: 'ai' },
  { to: '/profile', label: '个人中心', icon: 'user' }
]
</script>

<template>
  <nav class="left-nav">
    <router-link to="/" class="brand-icon" title="Literary Atlas">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3c2.5 2.6 4 5.6 4 9s-1.5 6.4-4 9c-2.5-2.6-4-5.6-4-9s1.5-6.4 4-9z" />
        <path d="M12 12l4-2.5" />
      </svg>
    </router-link>

    <router-link
      v-for="it in items"
      :key="it.to"
      :to="it.to"
      class="nav-item"
      :title="it.label"
    >
      <span class="ico">
        <!-- 地图：房子（与参考图一致） -->
        <svg v-if="it.icon === 'map'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 11l9-8 9 8" />
          <path d="M5 10.5V20h14v-9.5" />
          <path d="M10 20v-5h4v5" />
        </svg>
        <!-- 探索：指南针 -->
        <svg v-else-if="it.icon === 'compass'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M15.5 8.5l-2 5-5 2 2-5z" />
        </svg>
        <!-- 书架：书堆 -->
        <svg v-else-if="it.icon === 'books'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        <!-- 足迹 -->
        <svg v-else-if="it.icon === 'footprints'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <ellipse cx="8" cy="6" rx="2.6" ry="4" />
          <ellipse cx="17" cy="6" rx="2.6" ry="4" />
          <ellipse cx="8" cy="16" rx="3" ry="4" />
          <ellipse cx="17" cy="16" rx="3" ry="4" />
        </svg>
        <!-- AI 助手：对话气泡 + 星标（与参考图一致） -->
        <svg v-else-if="it.icon === 'ai'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.2 0-2.4-.2-3.4-.7L4 21l1.6-4.1A8.5 8.5 0 1 1 21 11.5z" />
          <path d="M12 9.2l.95 2.05 2.05.95-2.05.95L12 15.2l-.95-2.05-2.05-.95 2.05-.95z" />
        </svg>
        <!-- 个人中心 -->
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
        </svg>
      </span>
      <span class="lab">{{ it.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.left-nav {
  width: 84px; height: 100%; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center;
  padding: 16px 0; gap: 4px;
  background: rgba(6, 11, 20, .88); border-right: 1px solid rgba(210, 175, 110, .28);
}
.brand-icon { color: var(--accent); width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.brand-icon svg { width: 28px; height: 28px; }

.nav-item {
  width: 68px; padding: 9px 0; border-radius: 4px; position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  color: var(--muted); transition: all .15s;
}
.nav-item .ico { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; }
.nav-item .ico svg { width: 21px; height: 21px; }
.nav-item .lab { font-size: 10px; letter-spacing: .02em; line-height: 1; }
.nav-item:hover { color: var(--accent-soft); background: rgba(212, 180, 119, .07); }
.nav-item.router-link-active { color: var(--accent); background: rgba(212, 180, 119, .1); }
.nav-item.router-link-active::before {
  content: ""; position: absolute; left: -12px; top: 50%; transform: translateY(-50%);
  width: 3px; height: 26px; background: var(--accent); border-radius: 2px;
}
</style>