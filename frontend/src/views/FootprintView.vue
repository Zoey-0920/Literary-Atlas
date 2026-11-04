<script setup>
// 我的阅读足迹页：只统计「已读」书籍，全部数据从 bookshelfStore 动态派生
// - 在读 / 想读不计入足迹
// - 城市与 26 城数据匹配成功的才提供"在世界地图中查看"入口，不编造关联
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { books, initBookshelf } from '../store/bookshelfStore'
import { setMode, focusTarget } from '../store/mapStore'
import { getCities, getWorks } from '../api'

const router = useRouter()
const allCities = ref([])   // 26 城文学城市库（用于城市匹配）
const allWorks = ref([])    // 作品库（用于已读书 → 作品详情跳转）

onMounted(async () => {
  initBookshelf() // 幂等：确保书架数据已加载
  const [cities, works] = await Promise.all([getCities(), getWorks()])
  allCities.value = cities
  allWorks.value = works
})

// 已读作品列表（阅读足迹只看已读）
const readBooks = computed(() => books.value.filter(b => b.status === 'read'))

// 按"书籍自带的城市"分组：城市为空的书不参与分组，但仍计入已读数量
// hit = 该城市能否匹配到 26 城数据（能匹配才有城市详情与地图定位入口）
const cityGroups = computed(() => {
  const map = new Map()
  for (const b of readBooks.value) {
    if (!b.city) continue
    const key = b.city + '|' + (b.country || '')
    if (!map.has(key)) {
      const hit = allCities.value.find(c =>
        c.city === b.city && (!b.country || c.country === b.country)
      ) || null
      map.set(key, { city: b.city, country: b.country || '', hit, books: [] })
    }
    map.get(key).books.push(b)
  }
  return [...map.values()]
})

// 统计卡：已读作品数 / 涉及城市数 / 涉及国家数（全部动态计算，无写死数字）
const stats = computed(() => ({
  books: readBooks.value.length,
  cities: cityGroups.value.length,
  countries: new Set(readBooks.value.filter(b => b.country).map(b => b.country)).size
}))

// 已读书 → 作品库匹配：能匹配到的才可点击进入作品详情，其余纯文本展示
function workOf(title) {
  return allWorks.value.find(w => w.title === title) || null
}

// 进入世界地图（个性化阅读地图模式）查看足迹：地图组件已有国家高亮与书籍标记
function viewOnMap() {
  setMode('personal')
  router.push('/')
}

// 定位到已收录的文学城市：写入定位请求后回首页，由地图响应
function focusCity(g) {
  if (!g.hit) return
  focusTarget('city', g.hit.id)
  router.push('/')
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">我的阅读足迹</h1>
    </div>

    <!-- 空状态：没有已读作品时给出引导 -->
    <div v-if="stats.books === 0" class="empty-box">
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

      <!-- 城市足迹：与 26 城数据匹配的城市才有详情与定位入口 -->
      <section v-if="cityGroups.length > 0" class="section">
        <h2 class="section-title">到过的城市</h2>
        <div class="city-grid">
          <div v-for="g in cityGroups" :key="g.city + g.country" class="city-card">
            <div class="city-head">
              <span class="city-name">{{ g.city }}</span>
              <span class="city-country">{{ g.country }}</span>
            </div>
            <template v-if="g.hit">
              <p class="city-genre">{{ g.hit.genre }}</p>
              <p class="city-summary">{{ g.hit.summary }}</p>
              <button class="btn btn-ghost-dark btn-sm" @click="focusCity(g)">在世界地图中查看</button>
            </template>
            <p v-else class="city-miss">暂未收录为城市</p>
            <div class="city-books">
              <template v-for="b in g.books" :key="b.id">
                <router-link v-if="workOf(b.title)" :to="`/works/${workOf(b.title).id}`" class="book-chip link">
                  {{ b.title }}
                </router-link>
                <span v-else class="book-chip">{{ b.title }}</span>
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
            <router-link v-if="workOf(b.title)" :to="`/works/${workOf(b.title).id}`" class="read-title link">
              {{ b.title }}
            </router-link>
            <span v-else class="read-title">{{ b.title }}</span>
            <span class="read-author">{{ b.author }}</span>
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