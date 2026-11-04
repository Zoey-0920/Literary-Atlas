<script setup>
// 作品详情页：展示作品信息、作者入口、关联城市定位入口、添加/查看书架状态
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getWorkById, getAuthors, getCities } from '../api'
import { books, initBookshelf, addBook, updateBookStatus } from '../store/bookshelfStore'
import { focusTarget } from '../store/mapStore'

const route = useRoute()
const router = useRouter()

const work = ref(null)      // 当前作品
const author = ref(null)    // 匹配到的作家（用于跳转作者详情）
const city = ref(null)      // 匹配到的关联城市（用于地图定位）
const notFound = ref(false)

const STATUS_TEXT = { read: '已读', reading: '在读', want: '想读' }
// 添加到书架时可选状态（顺序与阅读流程一致）
const ADD_OPTIONS = [
  { value: 'want', label: '想读' },
  { value: 'reading', label: '在读' },
  { value: 'read', label: '已读' }
]

onMounted(async () => {
  const [w, authors, cities] = await Promise.all([
    getWorkById(String(route.params.id)),
    getAuthors(),
    getCities()
  ])
  if (!w) { notFound.value = true; return }
  work.value = w
  // 作家关联：优先用“代表作品列表包含本作品”匹配，姓名匹配兜底；
  // 都匹配不到才不提供跳转（不编造作者 id）
  author.value = authors.find(a => (a.works || []).includes(w.title))
    || authors.find(a => a.name === w.author)
    || null
  // 关联城市：优先用城市数据中的“代表作品”匹配，再用地点文本包含城市名匹配
  city.value = cities.find(c => c.authors.some(a => (a.works || []).includes(w.title)))
    || (w.place ? cities.find(c => w.place.includes(c.city)) : null)
    || null
  initBookshelf()
})

// 是否已在书架（按书名判断，防止重复添加）
const shelfBook = computed(() =>
  work.value ? books.value.find(b => b.title === work.value.title) || null : null
)

function addToShelf(status) {
  if (!work.value) return
  addBook({ title: work.value.title, author: work.value.author, status })
}

// 在地图中查看：先写入定位请求，再回到首页由地图响应
function viewOnMap() {
  if (!city.value) return
  focusTarget('city', city.value.id)
  router.push('/')
}

// 已在书架时：点击状态标签循环切换（与书架页行为一致）
const STATUS_ORDER = ['want', 'reading', 'read']
function cycleStatus() {
  const b = shelfBook.value
  if (!b) return
  const i = STATUS_ORDER.indexOf(b.status)
  updateBookStatus(b.id, STATUS_ORDER[(i + 1) % STATUS_ORDER.length])
}
</script>

<template>
  <div class="container">
    <!-- 未找到作品 -->
    <div v-if="notFound" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">未找到这部作品</h1>
      <p class="notfound">
        <router-link to="/works" class="return-link">← 返回作品探索</router-link>
      </p>
    </div>

    <!-- 作品详情 -->
    <template v-else-if="work">
      <div class="page-head">
        <p class="eyebrow">Literary Atlas · 作品详情</p>
        <p class="back-link">
          <router-link to="/works" class="return-link">← 返回作品探索</router-link>
        </p>
        <span v-if="work.genre" class="genre-chip">{{ work.genre }}</span>
        <h1 class="page-title">{{ work.title }}</h1>
        <p class="author-line">
          <template v-if="author">
            <router-link :to="`/authors/${author.id}`" class="author-link">{{ work.author }}</router-link>
          </template>
          <template v-else>{{ work.author }}</template>
        </p>
      </div>

      <!-- 基本信息：只显示数据中实际存在的字段 -->
      <div class="info-grid">
        <div v-if="work.country" class="info-item">
          <span class="info-lab">所属国家</span>
          <span class="info-val">{{ work.country }}</span>
        </div>
        <div v-if="work.year" class="info-item">
          <span class="info-lab">创作年代</span>
          <span class="info-val">{{ work.year }}</span>
        </div>
        <div v-if="work.genre" class="info-item">
          <span class="info-lab">文学流派</span>
          <span class="info-val">{{ work.genre }}</span>
        </div>
        <div v-if="work.place" class="info-item">
          <span class="info-lab">相关地点</span>
          <span class="info-val">{{ work.place }}</span>
        </div>
      </div>

      <!-- 关联城市与地图定位入口（能匹配到城市数据时才显示） -->
      <div v-if="city" class="city-box">
        <div class="city-head">
          <span class="city-name">坐标：{{ city.city }}（{{ city.country }}）</span>
          <span class="city-genre">{{ city.genre }}</span>
        </div>
        <p class="city-summary">{{ city.summary }}</p>
        <button class="btn btn-gold btn-sm" @click="viewOnMap">在世界地图中查看</button>
      </div>

      <!-- 书架状态：已在书架显示当前状态（可点击切换），否则提供添加入口 -->
      <div class="shelf-box">
        <template v-if="shelfBook">
          <p class="shelf-tip">已在书架中，当前状态：</p>
          <button
            class="status"
            :class="shelfBook.status"
            type="button"
            title="点击切换阅读状态"
            @click="cycleStatus"
          >
            {{ STATUS_TEXT[shelfBook.status] }}
            <span class="switch-hint">（点击切换）</span>
          </button>
          <p class="shelf-tip">
            <router-link to="/bookshelf" class="return-link">前往书架管理 →</router-link>
          </p>
        </template>
        <template v-else>
          <p class="shelf-tip">这部作品还不在你的书架里，选择状态加入：</p>
          <div class="add-actions">
            <button
              v-for="o in ADD_OPTIONS"
              :key="o.value"
              class="btn add-btn"
              :class="{ 'btn-gold': o.value === 'want' }"
              @click="addToShelf(o.value)"
            >
              {{ o.label }}
            </button>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-link { margin-top: 8px; }
.return-link { color: var(--accent-soft); text-decoration: none; font-size: 14px; }
.return-link:hover { color: var(--accent); }

.genre-chip {
  display: inline-block; margin: 4px 0 10px; padding: 3px 12px; font-size: 12px;
  border-radius: 999px; border: 1px solid rgba(212, 180, 119, .35); color: var(--accent-soft);
}
.author-line { font-size: 16px; color: var(--ink-soft, #C8C2B5); }
.author-link { color: var(--accent-soft); text-decoration: none; }
.author-link:hover { color: var(--accent); text-decoration: underline; }

.info-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px; margin-top: 26px;
}
.info-item {
  display: flex; flex-direction: column; gap: 6px; padding: 14px 16px;
  border: 1px solid var(--line); border-radius: 12px; background: var(--bg-card);
}
.info-lab { font-size: 12px; color: var(--muted); letter-spacing: .06em; }
.info-val { font-size: 15px; color: var(--ink); line-height: 1.5; }

.city-box {
  margin-top: 18px; padding: 16px; border: 1px solid rgba(212, 180, 119, .35);
  border-radius: 12px; background: var(--bg-sidebar);
  display: flex; flex-direction: column; gap: 8px; align-items: flex-start;
}
.city-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.city-name { font-family: Georgia, serif; font-size: 16px; color: var(--ink); }
.city-genre { font-size: 12px; color: var(--accent-soft); }
.city-summary { font-size: 13px; color: var(--muted); line-height: 1.6; }

.shelf-box {
  margin-top: 18px; padding: 16px; border: 1px solid var(--line);
  border-radius: 12px; background: var(--bg-card);
  display: flex; flex-direction: column; gap: 10px; align-items: flex-start;
}
.shelf-tip { font-size: 13px; color: var(--muted); }
.add-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.add-btn { height: 34px; padding: 0 16px; font-size: 13px; }
.btn-sm { height: 34px; padding: 0 14px; font-size: 13px; }

.status {
  display: inline-flex; align-items: center; gap: 6px;
  height: 30px; padding: 0 14px; font-size: 13px;
  border: 1px solid rgba(232, 224, 210, .1); border-radius: 999px;
  background: rgba(232, 224, 210, .05); color: var(--muted); cursor: pointer;
  transition: all .15s;
}
.status:hover { border-color: rgba(212, 180, 119, .45); }
.status.read { color: #7fc2a0; }
.status.reading { color: var(--accent-soft); }
.status.want { color: #b48ce0; }
.switch-hint { font-size: 12px; opacity: .7; }

.notfound { margin-top: 14px; }
</style>