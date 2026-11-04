<script setup>
// 作家详情页：展示现有数据中能提供的信息，代表作品可进入作品详情
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAuthorById, getWorks, getCities } from '../api'
import { focusTarget } from '../store/mapStore'

const route = useRoute()
const router = useRouter()

const author = ref(null)    // 当前作家
const allWorks = ref([])    // 作品库（用于关联代表作品详情页）
const city = ref(null)      // 出生地匹配到的文学城市（用于地图定位）
const notFound = ref(false)

onMounted(async () => {
  const [a, works, cities] = await Promise.all([
    getAuthorById(String(route.params.id)),
    getWorks(),
    getCities()
  ])
  if (!a) { notFound.value = true; return }
  author.value = a
  allWorks.value = works
  // 出生地文本中包含某个文学城市名，才认为是“可靠地点”，提供地图入口
  city.value = (a.birthPlace ? cities.find(c => a.birthPlace.includes(c.city)) : null) || null
})

// 代表作品：能匹配到现有作品库的才可点击进详情，其余仅文本展示（不编造详情）
const workLinks = computed(() => {
  if (!author.value) return []
  return (author.value.works || []).map(title => ({
    title,
    work: allWorks.value.find(w => w.title === title) || null
  }))
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
    <!-- 未找到作家 -->
    <div v-if="notFound" class="page-head">
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
        <p v-if="author.birthPlace" class="birth-line">出生地：{{ author.birthPlace }}</p>
      </div>

      <!-- 出生地与地图定位入口（文本存在即显示；能匹配到城市才提供定位） -->
      <div v-if="author.birthPlace" class="city-box">
        <div class="city-head">
          <span class="city-name">坐标：{{ author.birthPlace }}</span>
          <span v-if="city" class="city-genre">已收录城市：{{ city.city }}（{{ city.country }}）</span>
          <span v-else class="city-genre">暂未收录为城市</span>
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
              <span class="work-genre">{{ wl.work.genre }}</span>
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