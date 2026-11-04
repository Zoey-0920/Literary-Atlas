<script setup>
// 我的阅读足迹页：只统计「已读」书籍
// - 足迹数据统一来自 API 层 getFootprint()：
//   真实模式 → GET /api/reading/footprint（后端只返回真实且坐标有效的地点）
//   Mock 模式 → 由本地已读书派生（与真实接口同构）
// - 在读 / 想读不计入足迹；虚构或无坐标地点不点亮地图
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { books, loading as shelfLoading, error as shelfError, initBookshelf, reloadBookshelf } from '../store/bookshelfStore'
import { setMode, focusTarget } from '../store/mapStore'
import { getFootprint, getWorks, READING_STATUS } from '../api'

const router = useRouter()
const allWorks = ref([])    // 作品库（用于已读书 → 作品详情跳转）
const footprint = ref([])   // 足迹城市列表（与真实接口同构：{ placeId, name, country, latitude, longitude, books }）
const fpLoading = ref(false)
const fpError = ref('')

async function loadFootprint() {
  fpLoading.value = true
  fpError.value = ''
  try {
    const data = await getFootprint()
    footprint.value = data.items
  } catch (e) {
    // 真实模式后端不可达：展示错误并可重试，不静默回退 Mock
    fpError.value = (e && e.message) || '足迹数据加载失败'
  } finally {
    fpLoading.value = false
  }
}

onMounted(() => {
  initBookshelf() // 幂等：确保书架数据已加载
  loadFootprint()
  getWorks().then(w => { allWorks.value = w }).catch(() => {})
})

// 已读作品列表（阅读足迹只看已读）
const readBooks = computed(() => books.value.filter(b => b.status === READING_STATUS.FINISHED))

// 城市足迹：过滤掉国家级地点（后端足迹接口可能返回国家本身，如"俄罗斯"），城市与国家概念分离
const cityFootprint = computed(() => footprint.value.filter(i => i.placeType !== 'country'))

// 涉及国家：国家级地点名称 + 各足迹条目的 country 字段，统一去重
const countriesSet = computed(() => {
  const s = new Set()
  for (const i of footprint.value) {
    if (i.placeType === 'country') { if (i.name) s.add(i.name) }
    else if (i.country) s.add(i.country)
  }
  return s
})

// 统计卡：已读作品数 / 涉及城市数 / 涉及国家数（全部动态计算，无写死数字）
const stats = computed(() => ({
  books: readBooks.value.length,
  cities: cityFootprint.value.length,
  countries: countriesSet.value.size
}))

// 已读书 → 作品库匹配：优先按书名精确匹配，其次按后端作品 id（避免 Mock/真实 id 冲突）
function workOf(b) {
  const byTitle = allWorks.value.find(w => w.title === b.title)
  if (byTitle) return byTitle
  const id = b.bookId != null ? b.bookId : b.id
  return id != null ? allWorks.value.find(w => String(w.id) === String(id)) || null : null
}

// 进入世界地图（个性化阅读地图模式）查看足迹：地图组件已有国家高亮与书籍标记
function viewOnMap() {
  setMode('personal')
  router.push('/')
}

// 定位到足迹城市：仅限有地图坐标且已收录的地点（placeId 为后端地点 id）
function focusCity(it) {
  if (it.placeId == null || it.latitude == null) return
  focusTarget('city', it.placeId)
  router.push('/')
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">我的阅读足迹</h1>
    </div>

    <!-- 加载 / 错误状态 -->
    <p v-if="fpLoading" class="fp-state">正在加载足迹数据…</p>
    <div v-else-if="fpError" class="fp-state err">
      <span>足迹数据加载失败：{{ fpError }}</span>
      <button class="btn btn-ghost-dark btn-sm" @click="loadFootprint">重试</button>
    </div>
    <div v-else-if="shelfError && readBooks.length === 0" class="fp-state err">
      <span>书架数据加载失败：{{ shelfError }}</span>
      <button class="btn btn-ghost-dark btn-sm" @click="reloadBookshelf">重试</button>
    </div>

    <!-- 空状态：没有已读作品时给出引导 -->
    <div v-else-if="stats.books === 0" class="empty-box">
      <div class="empty-mark">✦</div>
      <p class="empty-text">书架里还没有「已读」的书。</p>
      <p class="empty-sub">把书的状态改为「已读」后，这里会自动生成你的阅读足迹。</p>
      <router-link to="/bookshelf" class="btn btn-gold">前往我的书架</router-link>
    </div>

    <template v-else>
      <!-- 统计：动态计算，与书架实时同步 -->
      <div class="stat-row">
        <div class="stat-card">
          <span class="stat-num">{{ stats.books }}</span>
          <span class="stat-label">已读作品</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ stats.cities }}</span>
          <span class="stat-label">涉及城市</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ stats.countries }}</span>
          <span class="stat-label">涉及国家</span>
        </div>
        <button class="btn btn-gold map-entry" @click="viewOnMap">在世界地图中查看足迹</button>
      </div>

      <!-- 城市足迹：只展示有真实坐标的地点（后端已过滤；Mock 同构）；国家级地点不混入城市列表 -->
      <section v-if="cityFootprint.length > 0" class="section">
        <h2 class="section-title">到过的城市</h2>
        <div class="city-grid">
          <div v-for="(it, idx) in cityFootprint" :key="(it.placeId ?? it.name) + '-' + idx" class="city-card">
            <div class="city-head">
              <span class="city-name">{{ it.name }}</span>
              <span v-if="it.country" class="city-country">{{ it.country }}</span>
            </div>
            <button
              v-if="it.placeId != null && it.latitude != null"
              class="btn btn-ghost-dark btn-sm"
              @click="focusCity(it)"
            >在世界地图中查看</button>
            <p v-else class="city-miss">暂无地图坐标</p>
            <div class="city-books">
              <template v-for="bk in it.books" :key="bk.id ?? bk.title">
                <router-link v-if="workOf(bk)" :to="`/works/${workOf(bk).id}`" class="book-chip link">
                  {{ bk.title }}
                </router-link>
                <span v-else class="book-chip">{{ bk.title }}</span>
              </template>
            </div>
          </div>
        </div>
      </section>

      <!-- 已读作品列表：点击可进入作品详情（仅限作品库中收录的） -->
      <section class="section">
        <h2 class="section-title">已读作品</h2>
        <ul class="read-list">
          <li v-for="b in readBooks" :key="b.id" class="read-row">
            <router-link v-if="workOf(b)" :to="`/works/${workOf(b).id}`" class="read-title link">
              {{ b.title }}
            </router-link>
            <span v-else class="read-title">{{ b.title }}</span>
            <span class="read-author">{{ b.author || '作者未知' }}</span>
            <span v-if="b.city" class="read-place">{{ b.city }} · {{ b.country }}</span>
            <span v-else class="read-place miss">暂无城市关联</span>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* 空状态 */
.fp-state { margin-top: 30px; padding: 24px; text-align: center; color: var(--muted); font-size: 14px; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.fp-state.err { color: #e2a49c; }
.empty-box {
  margin-top: 30px; padding: 48px 20px; text-align: center;
  border: 1px dashed rgba(212, 180, 119, .35); border-radius: 12px;
  background: var(--bg-card);
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.empty-mark { font-size: 30px; color: var(--accent-soft); }
.empty-text { font-size: 16px; color: var(--ink); }
.empty-sub { font-size: 13px; color: var(--muted); margin-bottom: 8px; }

/* 统计行 */
.stat-row { margin-top: 26px; display: flex; align-items: stretch; gap: 14px; flex-wrap: wrap; }
.stat-card {
  min-width: 130px; padding: 16px 20px; text-align: center;
  border: 1px solid var(--line); border-radius: 12px; background: var(--bg-card);
  display: flex; flex-direction: column; gap: 4px;
}
.stat-num { font-family: Georgia, serif; font-size: 28px; color: var(--accent-soft); }
.stat-label { font-size: 12px; color: var(--muted); letter-spacing: .06em; }
.map-entry { align-self: center; margin-left: auto; }

/* 分区 */
.section { margin-top: 30px; }
.section-title { font-size: 14px; color: var(--muted); letter-spacing: .08em; margin-bottom: 12px; }

/* 城市卡片 */
.city-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.city-card {
  padding: 16px; border: 1px solid rgba(212, 180, 119, .3); border-radius: 12px;
  background: var(--bg-sidebar);
  display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
}
.city-head { display: flex; align-items: baseline; gap: 8px; }
.city-name { font-family: Georgia, serif; font-size: 17px; color: var(--ink); }
.city-country { font-size: 12px; color: var(--muted); }
.city-genre { font-size: 12px; color: var(--accent-soft); }
.city-summary { font-size: 13px; color: var(--muted); }
.city-miss { font-size: 12px; color: var(--muted); }
.city-books { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
.book-chip {
  font-size: 12px; color: var(--ink); padding: 2px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: rgba(212, 180, 119, .08);
}
.book-chip.link:hover { border-color: var(--accent); color: var(--accent); }

/* 已读作品列表 */
.read-list { list-style: none; display: flex; flex-direction: column; }
.read-row {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  padding: 12px 4px; border-bottom: 1px solid var(--line);
}
.read-row:last-child { border-bottom: none; }
.read-title { font-size: 15px; color: var(--ink); min-width: 110px; }
.read-author { font-size: 13px; color: var(--muted); flex: 1; }
.read-place {
  font-size: 12px; color: var(--accent-soft);
  border: 1px solid rgba(212, 180, 119, .3); border-radius: 999px; padding: 2px 10px;
}
.read-place.miss { color: var(--muted); border-style: dashed; }
.link { text-decoration: none; cursor: pointer; }
.link:hover { color: var(--accent); }
.btn-sm { height: 32px; padding: 0 12px; font-size: 12px; }
</style>