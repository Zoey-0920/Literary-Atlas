<script setup>
// 作品浏览页：展示作品列表，支持按名称搜索、按国家/流派筛选，点击进入详情
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getWorks } from '../api'

const router = useRouter()

// 作品列表经 API 层获取（USE_MOCK=false 时请求真实后端 /api/books，作者/流派/地点由作品详情补全）
const allWorks = ref([])
const loading = ref(false)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    allWorks.value = await getWorks()
  } catch (e) {
    // 真实模式后端不可达：展示错误并提供重试，不静默回退 Mock
    error.value = (e && e.message) || '作品列表加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const keyword = ref('')
const countryFilter = ref('all')
const genreFilter = ref('all')

// 国家和流派筛选选项直接从现有数据推导，不写死（缺失字段不进入筛选项）
const countries = computed(() => [...new Set(allWorks.value.map(w => w.country).filter(Boolean))])
const genres = computed(() => [...new Set(allWorks.value.map(w => w.genre).filter(Boolean))])

// 作品搜索：书名 / 作者 / 国家 / 流派 / 地点 任一处包含关键词即命中
// （直接输入"法国"这类国家名也能找到该国作品）
function matchKeyword(w, kw) {
  if (kw === '') return true
  return [w.title, w.author, w.country, w.genre, w.place]
    .some(f => f != null && String(f).includes(kw))
}

const filteredWorks = computed(() => {
  const kw = keyword.value.trim()
  return allWorks.value.filter(w =>
    matchKeyword(w, kw) &&
    (countryFilter.value === 'all' || w.country === countryFilter.value) &&
    (genreFilter.value === 'all' || w.genre === genreFilter.value)
  )
})

function goDetail(w) {
  router.push(`/works/${w.id}`)
}

function reset() {
  keyword.value = ''
  countryFilter.value = 'all'
  genreFilter.value = 'all'
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">作品探索</h1>
    </div>

    <!-- 搜索与筛选工具栏 -->
    <div class="toolbar">
      <input
        v-model="keyword"
        class="search"
        type="text"
        placeholder="搜索作品、作者、国家或流派…"
      />
      <select v-model="countryFilter" class="filter">
        <option value="all">全部国家</option>
        <option v-for="c in countries" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="genreFilter" class="filter">
        <option value="all">全部流派</option>
        <option v-for="g in genres" :key="g" :value="g">{{ g }}</option>
      </select>
      <button class="btn btn-ghost-dark btn-sm" @click="reset">重置</button>
    </div>

    <!-- 加载 / 错误状态 -->
    <p v-if="loading" class="empty">正在加载作品列表…</p>
    <div v-else-if="error" class="empty">
      <span class="err-text">作品列表加载失败：{{ error }}</span>
      <button class="btn btn-ghost-dark btn-sm" @click="load">重试</button>
    </div>

    <!-- 作品列表 -->
    <ul v-else class="grid">
      <li v-for="w in filteredWorks" :key="w.id" class="work-card" @click="goDetail(w)">
        <span v-if="w.genre" class="genre-chip">{{ w.genre }}</span>
        <h2 class="work-title">{{ w.title }}</h2>
        <p class="work-author">{{ w.author || '作者未知' }}</p>
        <p class="work-meta">{{ w.country || '未知国家' }} · {{ w.year || '年份不详' }}</p>
      </li>
    </ul>

    <p v-if="!loading && !error && filteredWorks.length === 0" class="empty">
      <span>没有找到符合条件的作品。</span>
      <span v-if="keyword.trim() || countryFilter !== 'all' || genreFilter !== 'all'" class="empty-cond">
        当前条件：
        <template v-if="keyword.trim()">搜索关键词「{{ keyword.trim() }}」</template>
        <template v-if="countryFilter !== 'all'"> · 国家 =「{{ countryFilter }}」</template>
        <template v-if="genreFilter !== 'all'"> · 流派 =「{{ genreFilter }}」</template>
      </span>
      <button class="btn btn-ghost-dark btn-sm" @click="reset">清除搜索和筛选</button>
    </p>

    <p class="back">
      <router-link to="/" class="btn btn-ghost-dark">返回世界地图</router-link>
    </p>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; align-items: center;
}
.search {
  flex: 1; min-width: 200px; height: 36px; padding: 0 12px; font-size: 14px;
  color: var(--ink); background: rgba(3, 8, 16, .82); border: 1px solid rgba(210, 175, 110, .45);
  border-radius: 8px; outline: none;
}
.search:focus { border-color: rgba(246, 225, 170, .95); }
.filter {
  height: 36px; padding: 0 10px; font-size: 13px; color: #E3C78E;
  background: rgba(3, 8, 16, .82); border: 1px solid rgba(210, 175, 110, .45); border-radius: 10px;
  outline: none; cursor: pointer;
}
.filter:focus { border-color: rgba(246, 225, 170, .95); }
.btn-sm { height: 36px; padding: 0 14px; font-size: 13px; }

.grid {
  list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px; margin-top: 22px;
}
.work-card {
  display: flex; flex-direction: column; gap: 8px; padding: 18px;
  border: 1px solid rgba(210, 175, 110, .3); border-radius: 12px; background: rgba(6, 12, 22, .78);
  cursor: pointer; transition: border-color .15s, transform .15s;
}
.work-card:hover { border-color: rgba(246, 225, 170, .8); transform: translateY(-2px); }
.genre-chip {
  align-self: flex-start; padding: 3px 10px; font-size: 12px; border-radius: 999px;
  border: 1px solid rgba(212, 180, 119, .35); color: var(--accent-soft);
}
.work-title { font-family: Georgia, serif; font-size: 20px; color: var(--ink); }
.work-author { font-size: 14px; color: var(--ink-soft, #C8C2B5); }
.work-meta { font-size: 12px; color: var(--muted); }

.empty {
  padding: 40px 0; text-align: center; color: var(--muted); font-size: 14px;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.empty-cond { color: var(--accent-soft); }
.err-text { color: #e2a49c; }
.back { margin-top: 30px; padding-bottom: 40px; }
</style>