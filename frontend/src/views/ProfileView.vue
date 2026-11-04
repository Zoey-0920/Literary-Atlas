<script setup>
// 个人中心页：查看 / 编辑本地演示资料 + 动态阅读统计 + 快捷入口
// - 书架统计直接派生自 bookshelfStore 的共享 books，不另维护数据
// - 城市 / 国家数量与阅读足迹页同一套派生逻辑（已读书去重）
// - 用户资料来自 profileStore（localStorage 持久化，演示资料，非真实登录用户）
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { books, shelfStats, statsError, initBookshelf } from '../store/bookshelfStore'
import { profile, initProfile, updateProfile, AVATARS } from '../store/profileStore'
import { getCities } from '../api'

// 预设头像的简笔画图形（金色线条 + 深蓝底，主题：阅读与世界）
// 统一 64x64 视图，linecap 圆角，保持同一套线宽与视觉风格
const G = 'fill="none" stroke="#D4B477" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
const AVATAR_SVG = {
  // 罗盘：圆 + 刻度 + 指针
  compass: `<svg viewBox="0 0 64 64" ${G}><circle cx="32" cy="32" r="21"/><path d="M32 6v6M32 52v6M6 32h6M52 32h6"/><path d="M40 24l-4.6 11.4L24 40l4.6-11.4z"/></svg>`,
  // 翻开的书：左右两页 + 中缝
  book: `<svg viewBox="0 0 64 64" ${G}><path d="M8 15c6-4 16-4 22 0v34c-6-4-16-4-22 0z"/><path d="M56 15c-6-4-16-4-22 0v34c6-4 16-4 22 0z"/><path d="M32 15v34"/></svg>`,
  // 地球：球体 + 经线 + 纬线
  globe: `<svg viewBox="0 0 64 64" ${G}><circle cx="32" cy="32" r="21"/><ellipse cx="32" cy="32" rx="9.5" ry="21"/><path d="M13.5 24c5-3.4 27-3.4 37 0M13.5 40c5 3.4 27 3.4 37 0"/></svg>`,
  // 折纸地图：世界地图折页
  map: `<svg viewBox="0 0 64 64" ${G}><path d="M9 15l15 6 16-6 15 6v28l-15 6-16-6-15 6z"/><path d="M24 21v28M40 15v28"/><path d="M15 31c3-2 6-2 9 0M50 37c-3-2-6-2-9 0" stroke-width="2"/></svg>`,
  // 钢笔尖：写作
  quill: `<svg viewBox="0 0 64 64" ${G}><path d="M32 8l14 24c1 10-5 18-14 24-9-6-15-14-14-24z"/><circle cx="32" cy="36" r="3"/><path d="M32 39v17"/></svg>`,
  // 望远镜：观星探索
  telescope: `<svg viewBox="0 0 64 64" ${G}><path d="M12 36l32-17 6 11-32 17z"/><path d="M44 19l6 11M12 36l-2 5"/><path d="M32 45l-5 11M32 45l7 11"/><path d="M52 8v6M49 11h6"/></svg>`
}

const router = useRouter()
const editing = ref(false)          // 是否处于编辑态
const errText = ref('')             // 昵称校验错误提示
const draft = ref({ nickname: '', bio: '', avatar: '' })
const totalCities = ref(0)          // 全站文学城市总量（展示用）

onMounted(() => {
  initBookshelf()
  initProfile()
  getCities().then(cs => { totalCities.value = cs.length }).catch(() => {})
})

// 进入编辑态：把当前资料拷贝进草稿
function startEdit() {
  draft.value = { nickname: profile.value.nickname, bio: profile.value.bio, avatar: profile.value.avatar }
  errText.value = ''
  editing.value = true
}

// 保存：昵称非空校验通过后写入 profileStore（内部会持久化）
function saveEdit() {
  if (!draft.value.nickname.trim()) {
    errText.value = '昵称不能为空'
    return
  }
  updateProfile(draft.value)
  editing.value = false
}

// 取消编辑：丢弃草稿，回到展示态
function cancelEdit() {
  editing.value = false
  errText.value = ''
}

// ── 阅读统计：状态计数走后端 GET /api/reading/statistics（store 统一管理，失败保留最近一次有效值）；
//    城市 / 国家数量与阅读足迹页同一套派生逻辑（后端统计无此字段，由已读书去重计算）──
const stats = computed(() => {
  const read = books.value.filter(b => b.status === 'finished')
  // 与阅读足迹页一致的派生方式：城市按 书名+国家 去重，国家去重
  const cities = new Set(read.filter(b => b.city).map(b => b.city + '|' + (b.country || ''))).size
  const countries = new Set(read.filter(b => b.country).map(b => b.country)).size
  return {
    total: shelfStats.value.total,
    finished: shelfStats.value.finished,   // finished / reading / want_to_read（与后端状态值一致）
    reading: shelfStats.value.reading,
    want_to_read: shelfStats.value.want_to_read,
    cities,
    countries
  }
})

// 统计卡定义：to 为空表示不跳转
const STAT_CARDS = [
  { key: 'total', label: '总藏书', to: '/bookshelf' },
  { key: 'finished', label: '已读', to: '/bookshelf' },
  { key: 'reading', label: '在读', to: '/bookshelf' },
  { key: 'want_to_read', label: '想读', to: '/bookshelf' },
  { key: 'cities', label: '涉及城市', to: '/footprint' },
  { key: 'countries', label: '涉及国家', to: '/footprint' }
]

// 快捷入口
const QUICK_LINKS = [
  { label: '我的书架', to: '/bookshelf', desc: '管理已读 / 在读 / 想读' },
  { label: '我的阅读足迹', to: '/footprint', desc: '看走过的文学地图' },
  { label: '世界地图', to: '/', desc: '探索全球文学城市' },
  { label: 'AI 阅读助手', to: '/ai', desc: '聊作品、作家与推荐' }
]
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">个人中心</h1>
    </div>

    <!-- 用户资料卡 -->
    <div class="profile-card">
      <div class="avatar" v-html="AVATAR_SVG[profile.avatar] || AVATAR_SVG.compass"></div>

      <!-- 展示态 -->
      <div v-if="!editing" class="profile-info">
        <div class="nick-row">
          <span class="nick">{{ profile.nickname }}</span>
          <button class="btn btn-ghost-dark btn-sm" @click="startEdit">编辑资料</button>
        </div>
        <p class="bio">{{ profile.bio || '这个人还没有写简介。' }}</p>
        <p class="joined">加入 Literary Atlas：{{ profile.joinedAt }}</p>
        <p class="demo-tag">演示资料：本地模拟用户，非真实登录账号</p>
      </div>

      <!-- 编辑态：昵称 + 简介 + 预设头像 -->
      <div v-else class="profile-info">
        <label class="field">
          <span class="field-label">昵称</span>
          <input v-model="draft.nickname" class="field-input" maxlength="20" placeholder="输入昵称" />
        </label>
        <p v-if="errText" class="err">{{ errText }}</p>
        <label class="field">
          <span class="field-label">个人简介</span>
          <textarea v-model="draft.bio" class="field-input" rows="2" maxlength="80" placeholder="写一句介绍自己（选填）"></textarea>
        </label>
        <div class="field">
          <span class="field-label">选择头像</span>
          <div class="avatar-list">
            <button
              v-for="a in AVATARS" :key="a"
              :class="['avatar-opt', { active: draft.avatar === a }]"
              @click="draft.avatar = a"
              v-html="AVATAR_SVG[a]"
            ></button>
          </div>
        </div>
        <div class="edit-actions">
          <button class="btn btn-gold btn-sm" @click="saveEdit">保存</button>
          <button class="btn btn-ghost-dark btn-sm" @click="cancelEdit">取消</button>
        </div>
      </div>
    </div>

    <!-- 阅读统计：状态计数来自后端 /api/reading/statistics；城市/国家由已读书派生 -->
    <section class="section">
      <h2 class="section-title">阅读概况</h2>
      <p v-if="statsError" class="stats-warn">统计暂时不可用（显示最近一次结果）：{{ statsError }}</p>
      <div class="stat-grid">
        <component
          v-for="c in STAT_CARDS" :key="c.key"
          :is="c.to ? 'router-link' : 'div'"
          :to="c.to"
          class="stat-card"
        >
          <span class="stat-num">{{ stats[c.key] }}</span>
          <span class="stat-label">{{ c.label }}</span>
        </component>
      </div>
      <p class="stat-note">全站共收录 {{ totalCities }} 座文学城市，等你探索。</p>
    </section>

    <!-- 快捷入口 -->
    <section class="section">
      <h2 class="section-title">快捷入口</h2>
      <div class="link-grid">
        <router-link v-for="l in QUICK_LINKS" :key="l.to" :to="l.to" class="link-card">
          <span class="link-title">{{ l.label }}</span>
          <span class="link-desc">{{ l.desc }}</span>
          <span class="link-arrow">→</span>
        </router-link>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* 资料卡 */
.profile-card {
  margin-top: 24px; padding: 22px;
  display: flex; gap: 20px; align-items: flex-start;
  border: 1px solid rgba(212, 180, 119, .3); border-radius: 12px;
  background: var(--bg-card);
}
.avatar {
  width: 72px; height: 72px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle, #1B2C5E, #0D1836);  /* 深蓝底 */
  border: 1px solid rgba(212, 180, 119, .45);
}
.avatar :deep(svg), .avatar-opt :deep(svg) { width: 58%; height: 58%; }
.profile-info { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.nick-row { display: flex; align-items: center; gap: 14px; }
.nick { font-family: Georgia, serif; font-size: 20px; color: var(--ink); }
.bio { font-size: 14px; color: var(--muted); }
.joined { font-size: 12px; color: var(--muted); }
.demo-tag {
  align-self: flex-start; font-size: 11px; color: var(--accent-soft);
  border: 1px dashed rgba(212, 180, 119, .4); border-radius: 999px; padding: 2px 10px;
}

/* 编辑表单 */
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 12px; color: var(--muted); letter-spacing: .06em; }
.field-input {
  padding: 8px 12px; font-size: 14px; color: var(--ink);
  background: var(--bg-sidebar); border: 1px solid var(--line);
  border-radius: 10px; outline: none; resize: none;
}
.field-input:focus { border-color: rgba(212, 180, 119, .55); }
.err { font-size: 12px; color: #d98a7a; }
.avatar-list { display: flex; gap: 10px; flex-wrap: wrap; }
.avatar-opt {
  width: 44px; height: 44px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; border: 1px solid var(--line);
  background: radial-gradient(circle, #1B2C5E, #0D1836);  /* 深蓝底 */
}
.avatar-opt.active { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(212, 180, 119, .25); }
.edit-actions { display: flex; gap: 10px; margin-top: 4px; }
.btn-sm { height: 32px; padding: 0 14px; font-size: 12px; }

/* 分区与统计 */
.section { margin-top: 30px; }
.section-title { font-size: 14px; color: var(--muted); letter-spacing: .08em; margin-bottom: 12px; }
.stats-warn { margin: -6px 0 10px; font-size: 12px; color: #C9AB72; opacity: .85; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
.stat-card {
  padding: 16px; text-align: center; text-decoration: none;
  display: flex; flex-direction: column; gap: 4px;
  border: 1px solid var(--line); border-radius: 12px; background: var(--bg-card);
}
.stat-card:hover { border-color: rgba(212, 180, 119, .5); }
.stat-num { font-family: Georgia, serif; font-size: 26px; color: var(--accent-soft); }
.stat-label { font-size: 12px; color: var(--muted); letter-spacing: .05em; }
.stat-note { margin-top: 10px; font-size: 12px; color: var(--muted); }

/* 快捷入口 */
.link-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.link-card {
  position: relative; padding: 16px; text-decoration: none;
  display: flex; flex-direction: column; gap: 6px;
  border: 1px solid var(--line); border-radius: 12px; background: var(--bg-sidebar);
}
.link-card:hover { border-color: var(--accent); }
.link-title { font-size: 15px; color: var(--ink); }
.link-desc { font-size: 12px; color: var(--muted); }
.link-arrow {
  position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
  color: var(--accent-soft); font-size: 16px;
}
</style>