<script setup>
// 作品详情页：展示作品信息、作者入口、关联地点与地图定位、添加/查看书架状态
// - 真实模式：GET /api/books/{id}（含 authors / genres / places），只用后端真实字段
// - 只有真实且坐标有效的地点才提供地图定位；虚构地点只做文本展示，不添加坐标
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getWorkById, getAuthors, getCities } from '../api'
import { books, initBookshelf, addBook, updateBookStatus } from '../store/bookshelfStore'
import { focusTarget } from '../store/mapStore'

const route = useRoute()
const router = useRouter()

const work = ref(null)      // 当前作品
const author = ref(null)    // 匹配到的作家（用于跳转作者详情）
const city = ref(null)      // 可定位的关联地点（真实且坐标有效时才有）
const otherPlaces = ref([]) // 作品其余关联地点（文本展示）
const notFound = ref(false)
const loading = ref(true)
const loadError = ref('')

const STATUS_TEXT = { finished: '已读', reading: '在读', want_to_read: '想读' }
// 添加到书架时可选状态（顺序与阅读流程一致，状态值与后端一致）
const ADD_OPTIONS = [
  { value: 'want_to_read', label: '想读' },
  { value: 'reading', label: '在读' },
  { value: 'finished', label: '已读' }
]

async function load() {
  loading.value = true
  loadError.value = ''
  notFound.value = false
  try {
    const [w, authors, cities] = await Promise.all([
      getWorkById(String(route.params.id)),
      getAuthors(),
      getCities()
    ])
    if (!w) { notFound.value = true; work.value = null; return }
    work.value = w
    // 作家关联：详情自带 authors（真实模式）优先；Mock 数据回退到作家库匹配
    author.value = (w.authors && w.authors[0]) || null
      || authors.find(a => (a.works || []).some(x => (x.title || x) === w.title))
      || (w.author ? authors.find(a => a.name === w.author) : null)
      || null
    // 关联地点：真实模式展示作品 places；只给"真实且有有效坐标"的地点提供定位入口
    if (w.places && w.places.length) {
      const locatable = w.places.find(p => !p.isFictional && Number.isFinite(p.latitude) && Number.isFinite(p.longitude))
      city.value = locatable
        ? { id: locatable.id, city: locatable.name, country: locatable.country, genre: null, summary: locatable.note || null }
        : null
      otherPlaces.value = w.places
    } else {
      // Mock 兼容：按城市库的代表作品/地点文本匹配（与旧行为一致）
      city.value = cities.find(c => c.authors.some(a => (a.works || []).includes(w.title)))
        || (w.place ? cities.find(c => w.place.includes(c.city)) : null)
        || null
      otherPlaces.value = []
    }
    initBookshelf()
  } catch (e) {
    // 真实模式后端不可达：展示错误并可重试，不静默回退 Mock
    loadError.value = (e && e.message) || '作品详情加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)

// 是否已在书架（按书名判断，防止重复添加）
const shelfBook = computed(() =>
  work.value ? books.value.find(b => b.title === work.value.title) || null : null
)

// 地点胶囊列表：排除已经单独展示的可定位地点，避免重复
const displayPlaces = computed(() =>
  otherPlaces.value.filter(p => !city.value || p.id !== city.value.id)
)

const adding = ref(false)
async function addToShelf(status) {
  if (!work.value || adding.value) return
  adding.value = true
  try {
    await addBook({ title: work.value.title, author: work.value.author, status })
  } catch (e) {
    alert(e && e.message ? e.message : '添加失败，请稍后重试')
  } finally {
    adding.value = false
  }
}

// 在地图中查看：先写入定位请求，再回到首页由地图响应（仅限有真实坐标的地点）
function viewOnMap() {
  if (!city.value) return
  focusTarget('city', city.value.id)
  router.push('/')
}

// 已在书架时：点击状态标签循环切换（与书架页行为一致）
const STATUS_ORDER = ['want_to_read', 'reading', 'finished']
async function cycleStatus() {
  const b = shelfBook.value
  if (!b) return
  const i = STATUS_ORDER.indexOf(b.status)
  try {
    await updateBookStatus(b.id, STATUS_ORDER[(i + 1) % STATUS_ORDER.length])
  } catch (e) {
    alert(e && e.message ? e.message : '更新阅读状态失败')
  }
}
</script>

<template>
  <div class="container">
    <!-- 加载中 -->
    <div v-if="loading" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">正在加载作品详情…</h1>
    </div>

    <!-- 加载失败（真实模式后端不可达等） -->
    <div v-else-if="loadError" class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">作品详情加载失败</h1>
      <p class="notfound">{{ loadError }}</p>
      <p class="notfound"><button class="btn btn-ghost-dark btn-sm" @click="load">重试</button></p>
      <p class="notfound">
        <router-link to="/works" class="return-link">← 返回作品探索</router-link>
      </p>
    </div>

    <!-- 未找到作品 -->
    <div v-else-if="notFound" class="page-head">
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
            <router-link :to="`/authors/${author.id}`" class="author-link">{{ work.author || '作者未知' }}</router-link>
          </template>
          <template v-else>{{ work.author || '作者未知' }}</template>
        </p>
      </div>

      <!-- 基本信息：只显示数据中实际存在的字段 -->
      <div class="info-grid">
        <div v-if="work.originalTitle" class="info-item">
          <span class="info-lab">原名</span>
          <span class="info-val">{{ work.originalTitle }}</span>
        </div>
        <div v-if="work.country" class="info-item">
          <span class="info-lab">国家 / 地区</span>
          <span class="info-val">{{ work.country }}</span>
        </div>
        <div v-if="work.year" class="info-item">
          <span class="info-lab">首次出版年份</span>
          <span class="info-val">{{ work.year }}</span>
        </div>
        <div v-if="work.language" class="info-item">
          <span class="info-lab">原著语言</span>
          <span class="info-val">{{ work.language }}</span>
        </div>
        <div v-if="work.genre" class="info-item">
          <span class="info-lab">文学流派</span>
          <span class="info-val">{{ work.genre }}</span>
        </div>
        <div v-if="work.description" class="info-item">
          <span class="info-lab">内容简介</span>
          <span class="info-val">{{ work.description }}</span>
        </div>
      </div>

      <!-- 关联地点：有真实坐标的地点提供定位入口；虚构地点只做文本展示，不添加坐标 -->
      <div v-if="city || otherPlaces.length" class="city-box">
        <template v-if="city">
          <div class="city-head">
            <span class="city-name">坐标：{{ city.city }}<template v-if="city.country">（{{ city.country }}）</template></span>
          </div>
          <p v-if="city.summary" class="city-summary">{{ city.summary }}</p>
          <button class="btn btn-gold btn-sm" @click="viewOnMap">在世界地图中查看</button>
        </template>
        <div v-if="displayPlaces.length" class="place-chips">
          <span v-for="p in displayPlaces" :key="p.id" class="place-chip">
            {{ p.name }}<template v-if="p.relationTypeLabel"> · {{ p.relationTypeLabel }}</template><template v-if="p.isFictional"> · 虚构</template>
          </span>
        </div>
        <p v-if="!city && otherPlaces.length" class="city-summary">以上地点暂无有效坐标，暂不提供地图定位。</p>
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
            {{ STATUS_TEXT[shelfBook.status] || shelfBook.status }}
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
              :class="{ 'btn-gold': o.value === 'want_to_read' }"
              :disabled="adding"
              @click="addToShelf(o.value)"
            >
              {{ o.label }}
            </button>
          </div>
          <p v-if="adding" class="shelf-tip">正在添加到书架…</p>
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
.city-summary { font-size: 13px; color: var(--muted); line-height: 1.6; }
.place-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.place-chip {
  font-size: 12px; color: var(--ink); padding: 2px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: rgba(212, 180, 119, .08);
}

.shelf-box {
  margin-top: 18px; padding: 16px; border: 1px solid var(--line);
  border-radius: 12px; background: var(--bg-card);
  display: flex; flex-direction: column; gap: 10px; align-items: flex-start;
}
.shelf-tip { font-size: 13px; color: var(--muted); }
.add-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.add-btn { height: 34px; padding: 0 16px; font-size: 13px; }
.add-btn:disabled { opacity: .5; cursor: not-allowed; }
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
.status.finished { color: #7fc2a0; }
.status.reading { color: var(--accent-soft); }
.status.want { color: #b48ce0; }
.status.want_to_read { color: #b48ce0; }
.switch-hint { font-size: 12px; opacity: .7; }

.notfound { margin-top: 14px; }
</style>
