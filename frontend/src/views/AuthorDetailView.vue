<script setup>
// 作家详情页：展示现有数据中能提供的信息，代表作品可进入作品详情
// - 真实模式：getAuthorById 直连 GET /api/authors/{id}（生卒/国籍/简介/关联作品），
//   出生地按地点 id 直查单条地点详情（有真实坐标才提供定位）
// - Mock 模式：读 mockAuthors，按出生地文本匹配 26 城库（与旧行为一致）
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAuthorById, getWorks, getCities, getPlaceById, USE_MOCK } from '../api'
import { focusTarget } from '../store/mapStore'

const route = useRoute()
const router = useRouter()

const author = ref(null)    // 当前作家
const allWorks = ref([])    // 作品库（用于关联代表作品详情页）
const city = ref(null)      // 出生地匹配到的文学城市（用于地图定位）
const notFound = ref(false)
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  notFound.value = false
  try {
    // 真实模式：作者详情自带 books[]（含作品 id/标题），无需加载作品库；
    // 仅 Mock 模式下 works 为书名数组，才需要作品库解析详情链接（避免全量请求）
    const [a, works] = await Promise.all([
      getAuthorById(String(route.params.id)),
      USE_MOCK ? getWorks() : Promise.resolve([])
    ])
    if (!a) { notFound.value = true; author.value = null; return }
    author.value = a
    allWorks.value = works
    // 出生地定位城市：
    // - Mock：按 26 城库 id/文本匹配（与旧行为一致）
    // - 真实：按出生地地点 id 直查单条地点详情（1 次请求），有真实坐标才提供定位，
    //   绝不给虚构/无坐标地点编造定位
    if (USE_MOCK) {
      const cs = await getCities()
      city.value = (a.birthPlaceId != null
        ? cs.find(c => String(c.id) === String(a.birthPlaceId))
        : null)
        || (a.birthPlace ? cs.find(c => a.birthPlace.includes(c.city)) : null)
        || null
    } else if (a.birthPlaceId != null) {
      const p = await getPlaceById(a.birthPlaceId).catch(() => null)
      city.value = (p && !p.is_fictional && Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))
        ? { id: p.id, city: p.name, country: p.country, genre: null, summary: p.description ?? null }
        : null
    } else {
      city.value = null
    }
  } catch (e) {
    // 真实模式后端不可达：展示错误并可重试，不静默回退 Mock
    loadError.value = (e && e.message) || '作家详情加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)

// 代表作品：能匹配到现有作品库的才可点击进详情，其余仅文本展示（不编造详情）
// 兼容两种形态：Mock 为作品名字符串数组；真实模式为 { id, title, genre } 对象数组
const workLinks = computed(() => {
  if (!author.value) return []
  return (author.value.works || []).map(w => {
    const isObj = w && typeof w === 'object'
    const title = isObj ? w.title : w
    const work = isObj && w.id != null
      ? (allWorks.value.find(x => String(x.id) === String(w.id)) || { id: w.id, title, genre: w.genre || null })
      : (allWorks.value.find(x => x.title === title) || null)
    return { title, work }
  })
})

// 在世界地图中查看：写入定位请求后返回首页，由地图响应
function viewOnMap() {
  if (!city.value) return
  focusTarget('city', city.value.id)
  router.push('/')
}
</script>

<template>
  <div class="container">
    <!-- 加载 / 错误状态 -->
    <div v-if="loading" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">正在加载作家详情…</h1>
    </div>
    <div v-else-if="loadError" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">作家详情加载失败</h1>
      <p class="notfound">{{ loadError }}</p>
      <p class="notfound"><button class="btn btn-ghost-dark btn-sm" @click="load">重试</button></p>
      <p class="notfound">
        <router-link to="/works" class="return-link">← 返回作品探索</router-link>
      </p>
    </div>

    <!-- 未找到作家 -->
    <div v-else-if="notFound" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">未找到这位作家</h1>
      <p class="notfound">
        <router-link to="/works" class="return-link">← 返回作品探索</router-link>
      </p>
    </div>

    <!-- 作家详情 -->
    <template v-else-if="author">
      <div class="page-head">
        <p class="eyebrow">Literary Atlas · 作家详情</p>
        <p class="back-link">
          <router-link to="/works" class="return-link">← 返回作品探索</router-link>
        </p>
        <h1 class="page-title">{{ author.name }}</h1>
        <p v-if="author.nationality" class="birth-line">国籍：{{ author.nationality }}</p>
        <p v-if="author.birthYear" class="birth-line">生卒年份：{{ author.birthYear }}{{ author.deathYear ? ' — ' + author.deathYear : '' }}</p>
        <p v-if="author.birthPlace" class="birth-line">出生地：{{ author.birthPlace }}</p>
        <p v-if="author.bio" class="birth-line bio-text">{{ author.bio }}</p>
      </div>

      <!-- 出生地与地图定位入口（能匹配到有真实坐标的城市才提供定位） -->
      <div v-if="author.birthPlace || city" class="city-box">
        <div class="city-head">
          <span class="city-name">坐标：{{ city ? city.city : author.birthPlace }}<template v-if="city && city.country">（{{ city.country }}）</template></span>
          <span v-if="city" class="city-genre">已收录城市：{{ city.city }}（{{ city.country }}）</span>
          <span v-else class="city-genre">暂无有效坐标，暂不提供地图定位</span>
        </div>
        <button v-if="city" class="btn btn-gold btn-sm" @click="viewOnMap">在世界地图中查看</button>
      </div>

      <!-- 代表作品：有作品数据的可点击进入详情页 -->
      <div v-if="workLinks.length > 0" class="works-box">
        <h2 class="box-title">代表作品</h2>
        <ul class="work-list">
          <li v-for="wl in workLinks" :key="wl.title" class="work-row">
            <router-link v-if="wl.work" :to="`/works/${wl.work.id}`" class="work-link">
              {{ wl.title }}
              <span v-if="wl.work.genre" class="work-genre">{{ wl.work.genre }}</span>
            </router-link>
            <span v-else class="work-text">
              {{ wl.title }}
              <span class="work-note">（作品详情待收录）</span>
            </span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-link { margin-top: 8px; }
.return-link { color: var(--accent-soft); text-decoration: none; font-size: 14px; }
.return-link:hover { color: var(--accent); }
.birth-line { margin-top: 10px; font-size: 15px; color: var(--ink-soft, #C8C2B5); }
.bio-text { max-width: 720px; line-height: 1.7; font-size: 14px; color: var(--muted); }

.city-box {
  margin-top: 26px; padding: 16px; border: 1px solid rgba(212, 180, 119, .35);
  border-radius: 12px; background: var(--bg-sidebar);
  display: flex; flex-direction: column; gap: 10px; align-items: flex-start;
}
.city-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.city-name { font-family: Georgia, serif; font-size: 16px; color: var(--ink); }
.city-genre { font-size: 12px; color: var(--muted); }
.btn-sm { height: 34px; padding: 0 14px; font-size: 13px; }

.works-box {
  margin-top: 18px; padding: 16px; border: 1px solid var(--line);
  border-radius: 12px; background: var(--bg-card);
}
.box-title { font-size: 14px; color: var(--muted); letter-spacing: .06em; margin-bottom: 10px; }
.work-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.work-row { font-size: 15px; }
.work-link {
  color: var(--ink); text-decoration: none;
  display: inline-flex; align-items: center; gap: 8px;
}
.work-link:hover { color: var(--accent); }
.work-genre {
  font-size: 12px; color: var(--accent-soft);
  border: 1px solid rgba(212, 180, 119, .35); border-radius: 999px; padding: 1px 8px;
}
.work-text { color: var(--ink); }
.work-note { font-size: 12px; color: var(--muted); }

.notfound { margin-top: 14px; }
</style>