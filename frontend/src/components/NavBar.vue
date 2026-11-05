<script setup>
// 顶部融合层：品牌名 + 地图模式切换 + 分类搜索 + 用户头像（悬浮于地图之上）
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { mapStore, setMode, focusTarget } from '../store/mapStore'
import { searchLiterature, normalizeSearchKeyword } from '../api'

const router = useRouter()
const query = ref('')
const menuOpen = ref(false)

// 统一模糊搜索：作品 / 作家 / 城市 / 国家 / 文学类型
// 250ms 防抖 + 请求序号防竞态（旧请求晚到不会覆盖新结果）
const results = ref([])
const searching = ref(false)
const noResults = ref(false)
const fuzzyFallback = ref(false)
const cleanedQuery = computed(() => normalizeSearchKeyword(query.value))

let searchTimer = null
let searchSeq = 0

watch(query, (q) => {
  const cleaned = normalizeSearchKeyword(q)
  clearTimeout(searchTimer)
  if (!cleaned) {
    searchSeq++
    searching.value = false
    results.value = []
    noResults.value = false
    fuzzyFallback.value = false
    return
  }
  searching.value = true
  searchTimer = setTimeout(async () => {
    const seq = ++searchSeq
    try {
      const r = await searchLiterature(cleaned)
      if (seq !== searchSeq) return // 已有更新的搜索，丢弃过期结果
      results.value = r
      fuzzyFallback.value = !!(r.length && r[0].fuzzyFallback)
      noResults.value = r.length === 0
    } finally {
      if (seq === searchSeq) searching.value = false
    }
  }, 250)
})

function choose(r) {
  query.value = ''
  if (r.bookId) focusTarget('book', r.bookId)
  else if (r.cityId) focusTarget('city', r.cityId)
  else if (r.authorId) router.push(`/authors/${r.authorId}`)
  else if (r.genreName) router.push({ path: '/works', query: { genre: r.genreName } })
  else if (r.countryName) router.push({ path: '/works', query: { country: r.countryName } })
}
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <!-- 品牌徽记：地球仪 + 翻开的书本（与参考图一致） -->
      <svg class="brand-star" viewBox="0 0 32 26" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="13" cy="13" r="9.5" />
        <path d="M3.5 13h19M13 3.5c2.2 2.3 3.3 5 3.3 9.5s-1.1 7.2-3.3 9.5c-2.2-2.3-3.3-5-3.3-9.5S10.8 5.8 13 3.5z" />
        <path d="M26 8.2c1.9 1.6 3 3.7 3 4.8s-1.1 3.2-3 4.8c-1.9-1.6-3-3.7-3-4.8s1.1-3.2 3-4.8z" />
        <path d="M26 8.2v9.6" />
      </svg>
      <div class="brand-text">
        <span class="brand-title">Literary Atlas</span>
        <span class="brand-sub">Explore Literature Through Geography</span>
      </div>
    </div>

    <div class="mode-switch">
      <button :class="{ active: mapStore.mode === 'overview' }" @click="setMode('overview')" title="世界地图">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.6 4 5.6 4 9s-1.5 6.4-4 9" /></svg>
        <span class="txt">世界地图</span>
      </button>
      <button :class="{ active: mapStore.mode === 'personal' }" @click="setMode('personal')" title="个性化阅读地图">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" /></svg>
        <span class="txt">个性化阅读地图</span>
      </button>
    </div>

    <div class="search">
      <svg class="search-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>
      <input v-model="query" type="text" placeholder="搜索作品、作家、类型、国家或城市…" />
      <span class="search-divider" aria-hidden="true"></span>
      <svg class="search-star" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6z" /></svg>
      <transition name="drop">
        <ul v-if="results.length" class="search-results">
          <li v-if="fuzzyFallback" class="sr-hint" @mousedown.prevent>未找到完全匹配，以下为近似结果</li>
          <li v-for="r in results" :key="r.cat + r.id" @mousedown.prevent="choose(r)">
            <span class="sr-type">{{ r.cat }}</span>
            <span class="sr-title">{{ r.title }}</span>
            <span class="sr-sub">{{ r.sub }}</span>
          </li>
        </ul>
        <ul v-else-if="cleanedQuery && !searching && noResults" class="search-results">
          <li class="sr-hint" @mousedown.prevent>未找到与「{{ cleanedQuery }}」相关的内容，换个关键词试试</li>
        </ul>
      </transition>
    </div>

    <div class="user" @click="menuOpen = !menuOpen">
      <span class="avatar">
        <svg viewBox="0 0 24 24" aria-label="用户头像">
          <circle cx="12" cy="12" r="12" fill="#31405e" />
          <circle cx="12" cy="9" r="3.6" fill="#e9dcc2" />
          <path d="M4.8 20.5c1-3.4 3.9-5.2 7.2-5.2s6.2 1.8 7.2 5.2" fill="#e9dcc2" />
          <!-- 墨镜（与参考图头像一致） -->
          <circle cx="9.7" cy="9.7" r="2" fill="#12182a" />
          <circle cx="14.3" cy="9.7" r="2" fill="#12182a" />
          <path d="M11.7 9.7h.6" stroke="#12182a" stroke-width="1.1" />
        </svg>
      </span>
      <transition name="drop">
        <ul v-if="menuOpen" class="user-menu">
          <li><router-link to="/bookshelf" @click="menuOpen = false">我的书架</router-link></li>
          <li><router-link to="/profile" @click="menuOpen = false">个人中心</router-link></li>
          <li><router-link to="/works" @click="menuOpen = false">阅读探索</router-link></li>
        </ul>
      </transition>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: absolute; top: 0; left: 0; right: 0; z-index: 50;
  display: flex; align-items: center; gap: 18px;
  height: 62px; padding: 0 20px;
  background: linear-gradient(180deg, rgba(10, 17, 30, .97), rgba(10, 17, 30, .86));
  border-bottom: 1px solid rgba(212, 180, 119, .16);
  backdrop-filter: blur(6px);
}
.brand { display: flex; align-items: center; gap: 9px; white-space: nowrap; }
.brand-star { width: 26px; height: 22px; color: var(--accent); filter: drop-shadow(0 0 6px rgba(212, 180, 119, .7)); flex-shrink: 0; }
.brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.brand-title { font-family: Georgia, "Songti SC", serif; font-size: 17px; color: var(--ink); letter-spacing: .03em; }
.brand-sub { font-size: 10px; letter-spacing: .06em; color: var(--muted); margin-top: 3px; }

.mode-switch { display: flex; background: rgba(3, 6, 12, .6); border: 1px solid rgba(210, 175, 110, .4); border-radius: 999px; padding: 3px; }
.mode-switch button { display: flex; align-items: center; gap: 6px; background: none; border: none; padding: 6px 15px; font-size: 13px; color: #C9AB72; cursor: pointer; border-radius: 999px; transition: all .15s; }
.mode-switch button svg { width: 14px; height: 14px; }
.mode-switch button.active { background: rgba(3, 6, 12, .92); color: #F0DCAB; box-shadow: inset 0 0 0 1px rgba(246, 225, 170, .95), 0 0 14px rgba(243, 226, 179, .22); }

.search { position: relative; flex: 1; max-width: 400px; margin-left: auto; }
.search input { width: 100%; height: 36px; padding: 0 44px 0 36px; font-size: 13px; color: var(--ink); background: rgba(3, 8, 16, .82); border: 1px solid rgba(210, 175, 110, .45); border-radius: 999px; outline: none; }
.search input::placeholder { color: var(--muted); }
.search input:focus { border-color: rgba(246, 225, 170, .95); }
.search-ico { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 15px; height: 15px; color: var(--muted); pointer-events: none; }
.search-star { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); width: 13px; height: 13px; fill: var(--accent); opacity: .55; pointer-events: none; }
.search-divider { position: absolute; right: 32px; top: 50%; transform: translateY(-50%); width: 1px; height: 14px; background: rgba(212, 180, 119, .35); pointer-events: none; }
.search-results { position: absolute; top: 44px; left: 0; right: 0; background: var(--bg-card); border: 1px solid var(--line); border-radius: 10px; list-style: none; max-height: 360px; overflow: auto; z-index: 60; box-shadow: 0 18px 50px rgba(0, 0, 0, .55); }
.search-results li { display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; }
.search-results li:hover { background: rgba(212, 180, 119, .1); }
.sr-hint { font-size: 12px; color: var(--muted); cursor: default; }
.sr-hint:hover { background: none; }
.sr-type { font-size: 11px; color: var(--accent); border: 1px solid var(--line); padding: 1px 6px; border-radius: 6px; flex-shrink: 0; }
.sr-title { font-size: 14px; color: var(--ink); }
.sr-sub { font-size: 12px; color: var(--muted); margin-left: auto; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.user { position: relative; cursor: pointer; }
.avatar { width: 34px; height: 34px; border-radius: 50%; border: 1.5px solid rgba(212, 180, 119, .8); display: flex; align-items: center; justify-content: center; overflow: hidden; background: #1a2737; }
.avatar svg { width: 100%; height: 100%; display: block; }
.user-menu { position: absolute; top: 44px; right: 0; min-width: 150px; background: var(--bg-card); border: 1px solid var(--line); border-radius: 10px; list-style: none; z-index: 60; box-shadow: 0 18px 50px rgba(0, 0, 0, .55); padding: 6px 0; }
.user-menu a { display: block; padding: 9px 16px; font-size: 13px; color: var(--ink); }
.user-menu a:hover { background: rgba(212, 180, 119, .1); color: var(--accent-soft); }

.drop-enter-active, .drop-leave-active { transition: opacity .12s, transform .12s; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 760px) {
  .topbar { gap: 10px; padding: 0 14px; }
  .brand-text { display: none; }
  .search { max-width: 200px; }
  /* 窄屏：模式切换只留图标，避免文字竖排溢出 */
  .mode-switch .txt { display: none; }
  .mode-switch button { padding: 6px 12px; }
}
</style>