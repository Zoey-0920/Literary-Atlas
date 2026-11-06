<script setup>
// 自绘 SVG 世界地图：等距圆柱投影 + 国界 + 真实深空星云背景 + 分层星点 + 奇幻漂浮大陆 + 发光粒子标记 + 缩放/拖动
// 视觉方向：奇幻宇宙风格（大陆像漂浮在星云中的奇幻世界轮廓）
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import worldGeo from '../assets/world.geo.json'
import starfieldUrl from '../assets/starfield-bg.jpg'
import nebulaUrl from '../assets/nebula-land.jpg'
import textureUrl from '../assets/land-texture.jpg'
import { mapStore } from '../store/mapStore'
import { getCities, getPlaceLiterature, USE_MOCK } from '../api'
import { books, initBookshelf } from '../store/bookshelfStore'

// 城市数据由 API 层异步提供；书架数据来自统一 store（与书架页共享同一份）
const cities = ref([])

const WORLD_W = 1000
const WORLD_H = 500
const MIN_Z = 1
const MAX_Z = 7

function project(lng, lat) {
  return [(lng + 180) / 360 * WORLD_W, (90 - lat) / 180 * WORLD_H]
}

function ringToPath(ring) {
  let d = ''
  for (let i = 0; i < ring.length; i++) {
    const x = (ring[i][0] + 180) / 360 * WORLD_W
    const y = (90 - ring[i][1]) / 180 * WORLD_H
    d += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2)
  }
  return d + 'Z'
}
function geometryToPath(g) {
  let out = ''
  if (g.type === 'Polygon') {
    for (const ring of g.coordinates) out += ringToPath(ring)
  } else if (g.type === 'MultiPolygon') {
    for (const poly of g.coordinates) for (const ring of poly) out += ringToPath(ring)
  }
  return out
}

const countryPaths = worldGeo.features.map(f => ({
  id: f.id,
  name: (f.properties && f.properties.name) || '',
  d: geometryToPath(f.geometry)
}))

// ---------- 夜地灯光：已移除装饰性灯点群；灯光 = 收录城市的交互标记（见 visibleMarkers） ----------

// 经纬网格：天球仪质感，克制地描出世界坐标（不写刻度文字）
const graticule = (() => {
  const lines = []
  for (let lng = -180; lng <= 180; lng += 30) {
    const x = (lng + 180) / 360 * WORLD_W
    lines.push({ kind: 'lon', x1: x, y1: 0, x2: x, y2: WORLD_H })
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const y = (90 - lat) / 180 * WORLD_H
    lines.push({ kind: 'lat', x1: 0, y1: y, x2: WORLD_W, y2: y })
  }
  return lines
})()

// 个人地图高亮国家
const readCodes = computed(() => {
  const s = new Set()
  for (const b of books.value) if (b.status === 'finished') s.add(b.countryCode)
  return s
})
function countryClass(c) {
  if (mapStore.mode === 'personal') {
    return readCodes.value.has(c.id) ? 'country is-lit' : 'country is-dim'
  }
  return 'country'
}

// 标记数据（所有城市始终显示：重要城市大光点，普通城市小光点，与参考图"密布光点"一致）
const markers = computed(() => {
  if (mapStore.mode === 'overview') {
    return cities.value.map(c => {
      const [x, y] = project(c.lng, c.lat)
      return { id: c.id, kind: c.important ? 'major' : 'minor', name: c.city, x, y, data: c }
    })
  }
  // 只显示有地理位置的书籍（手动添加的书 lat/lng 为 null，不参与地图展示）。
  // 同一真实地点（同坐标）只生成一个标记，把该地点的全部书籍收进 data.books，
  // 避免同位标记完全重叠、点击只能命中其中一本。
  const STATUS_PRIORITY = { finished: 3, reading: 2, want_to_read: 1 }
  const grouped = new Map()
  for (const b of books.value) {
    if (b.lat == null || b.lng == null) continue
    const key = b.lat + '|' + b.lng
    let g = grouped.get(key)
    if (!g) {
      const [x, y] = project(b.lng, b.lat)
      g = {
        id: 'loc-' + key.replace(/[.-]/g, '_'),
        kind: b.status,
        name: b.city,
        x, y,
        data: { city: b.city, country: b.country, books: [] }
      }
      grouped.set(key, g)
    }
    g.data.books.push(b)
    // 标记颜色取该地点下最高优先级的阅读状态：finished > reading > want_to_read
    if ((STATUS_PRIORITY[b.status] || 0) > (STATUS_PRIORITY[g.kind] || 0)) g.kind = b.status
  }
  return [...grouped.values()]
})

// 视图状态：缩放 + 中心
const wrapRef = ref(null)
const wrapSize = reactive({ w: 0, h: 0 })
const zoom = ref(1)
const center = reactive({ x: WORLD_W / 2, y: WORLD_H / 2 })

const view = computed(() => {
  const w = WORLD_W / zoom.value
  const h = WORLD_H / zoom.value
  return { x: center.x - w / 2, y: center.y - h / 2, w, h }
})
const viewBox = computed(() => `${view.value.x} ${view.value.y} ${view.value.w} ${view.value.h}`)

function clampCenter() {
  const w = WORLD_W / zoom.value
  const h = WORLD_H / zoom.value
  center.x = Math.max(w / 2, Math.min(WORLD_W - w / 2, center.x))
  center.y = Math.max(h / 2, Math.min(WORLD_H - h / 2, center.y))
}

const fit = computed(() => {
  if (!wrapSize.w || !wrapSize.h) return { s: 1, ox: 0, oy: 0 }
  const s = Math.min(wrapSize.w / view.value.w, wrapSize.h / view.value.h)
  const ox = (wrapSize.w - view.value.w * s) / 2
  const oy = (wrapSize.h - view.value.h * s) / 2
  return { s, ox, oy }
})

function screenPos(m) {
  const f = fit.value
  return { x: f.ox + (m.x - view.value.x) * f.s, y: f.oy + (m.y - view.value.y) * f.s }
}

const visibleMarkers = computed(() => {
  if (!wrapSize.w || !wrapSize.h) return []
  return markers.value
    .map(m => {
      const p = screenPos(m)
      return { ...m, sx: p.x, sy: p.y }
    })
    .filter(m => m.sx > -50 && m.sx < wrapSize.w + 50 && m.sy > -50 && m.sy < wrapSize.h + 50)
})

function zoomBy(factor) {
  zoom.value = Math.max(MIN_Z, Math.min(MAX_Z, zoom.value * factor))
  clampCenter()
}
function resetView() {
  zoom.value = 1
  center.x = WORLD_W / 2
  center.y = WORLD_H / 2
}

function onWheel(e) {
  if (!wrapRef.value) return
  closeClusterMenu()
  const rect = wrapRef.value.getBoundingClientRect()
  const fx = (e.clientX - rect.left) / rect.width
  const fy = (e.clientY - rect.top) / rect.height
  const v = view.value
  const geoX = v.x + fx * v.w
  const geoY = v.y + fy * v.h
  const factor = e.deltaY < 0 ? 1.25 : 1 / 1.25
  const newZoom = Math.max(MIN_Z, Math.min(MAX_Z, zoom.value * factor))
  const nw = WORLD_W / newZoom
  const nh = WORLD_H / newZoom
  center.x = geoX - fx * nw
  center.y = geoY - fy * nh
  zoom.value = newZoom
  clampCenter()
}

const dragging = ref(false)
// 拖拽防误触：pointer 移动超过阈值（3px）即视为拖拽，其后浏览器补发的 click 会被忽略
let dragMoved = false
let last = { x: 0, y: 0 }
function onPointerDown(e) {
  dragging.value = true
  dragMoved = false
  last = { x: e.clientX, y: e.clientY }
  if (e.currentTarget.setPointerCapture) e.currentTarget.setPointerCapture(e.pointerId)
}
function onPointerMove(e) {
  if (!dragging.value || !wrapRef.value) return
  // 先按屏幕像素判断是否真的在拖拽（3px 内的手抖不算拖拽）
  if (!dragMoved && (Math.abs(e.clientX - last.x) > 3 || Math.abs(e.clientY - last.y) > 3)) {
    dragMoved = true
  }
  const rect = wrapRef.value.getBoundingClientRect()
  const v = view.value
  const dx = (e.clientX - last.x) / rect.width * v.w
  const dy = (e.clientY - last.y) / rect.height * v.h
  center.x -= dx
  center.y -= dy
  last = { x: e.clientX, y: e.clientY }
  clampCenter()
}
function endDrag() { dragging.value = false }
// 点击地图空白处关闭弹窗；但刚拖动完浏览器补发的 click 要吞掉，避免误关
function onMapClick() {
  if (dragMoved) { dragMoved = false; return }
  closeClusterMenu()
  mapStore.selectedId = null
}

const selected = computed(() =>
  mapStore.selectedId ? markers.value.find(m => m.id === mapStore.selectedId) : null
)

// ---------- 近距离标记冲突处理 ----------
// 密集城市在低缩放下标记热区重叠，直接选择易误选相邻地点：
// 点击时若附近（屏幕像素距离）存在多个标记，先弹出候选列表由用户明确选择。
const CLUSTER_RADIUS = 20 // 屏幕像素：两标记中心距小于该值视为"过近"
const clusterMenu = ref(null) // { x, y, items: [marker] } | null

function closeClusterMenu() { clusterMenu.value = null }

function onMarkerClick(m) {
  const near = visibleMarkers.value.filter(o => {
    const dx = o.sx - m.sx
    const dy = o.sy - m.sy
    return dx * dx + dy * dy <= CLUSTER_RADIUS * CLUSTER_RADIUS
  })
  if (near.length <= 1) {
    // 孤立标记：保持原有行为（点击选中/再次点击关闭）
    closeClusterMenu()
    mapStore.selectedId = mapStore.selectedId === m.id ? null : m.id
    return
  }
  // 多个标记过近：展示候选列表（含被点中的那个），不直接选中
  clusterMenu.value = { x: m.sx, y: m.sy, items: near }
}

function chooseClusterItem(item) {
  closeClusterMenu()
  mapStore.selectedId = item.id
}

// 视图缩放、平移或模式切换后，候选列表的屏幕锚点已失效，直接关闭
watch([zoom, () => center.x, () => center.y, () => mapStore.mode], closeClusterMenu)

watch(() => mapStore.focusRequest, (req) => {
  if (!req) return
  mapStore.focusRequest = null
  let lat, lng, id, mode
  if (req.kind === 'city') {
    const c = cities.value.find(x => x.id === req.id)
    if (!c) return
    lat = c.lat; lng = c.lng; id = c.id; mode = 'overview'
  } else {
    const b = books.value.find(x => String(x.bookId ?? x.id) === String(req.id))
    if (!b) return
    // 手动添加的书没有地理位置，跳过定位（避免坐标为空导致地图出错）
    if (b.lat == null || b.lng == null) return
    lat = b.lat; lng = b.lng; mode = 'personal'
    // 聚合后的个人标记 id 由坐标派生（与 markers computed 的分组 key 一致）
    id = 'loc-' + (b.lat + '|' + b.lng).replace(/[.-]/g, '_')
  }
  if (mapStore.mode !== mode) mapStore.mode = mode
  const [x, y] = project(lng, lat)
  center.x = x
  center.y = y
  zoom.value = 5
  clampCenter()
  mapStore.selectedId = id
})

// 书籍弹窗的状态文案（状态值与后端一致）
const BOOK_STATUS_TEXT = { finished: '已读 · 阅读足迹', reading: '在读 · 阅读进行中', want_to_read: '想读 · 等待启程' }
function bookStatusText(s) { return BOOK_STATUS_TEXT[s] || s }

function popupStyle() {
  if (!selected.value) return {}
  const p = screenPos(selected.value)
  const cw = 320
  const ch = 320
  let left = p.x + 22
  let top = p.y - 16
  if (left + cw > wrapSize.w) left = p.x - cw - 22
  left = Math.max(10, Math.min(wrapSize.w - cw - 10, left))
  top = Math.max(10, Math.min(wrapSize.h - ch - 10, top))
  return { left: left + 'px', top: top + 'px' }
}

let ro
const loadState = ref('loading') // 'loading' | 'ready' | 'error'

async function loadCities() {
  loadState.value = 'loading'
  try {
    // 加载城市数据并初始化书架 store
    const [c] = await Promise.all([getCities(), initBookshelf()])
    cities.value = c
    loadState.value = 'ready'
    // 若从其他页面带来了定位请求（如作品详情页的"在地图中查看"），
    // 数据就绪后重新触发一次，确保 watch 执行定位
    if (mapStore.focusRequest) {
      const req = mapStore.focusRequest
      mapStore.focusRequest = null
      await nextTick()
      mapStore.focusRequest = req
    }
  } catch (e) {
    // 真实模式后端不可达：显示错误并提供重试，不静默回退 Mock
    loadState.value = 'error'
  }
}

// 城市弹窗的关联作品统一来源：Mock 取自作家作品表，真实模式取自地点关联作品接口
function cityWorks(d) {
  if (d.works && d.works.length) return d.works
  const out = []
  for (const a of d.authors || []) for (const w of a.works || []) out.push({ id: null, title: w })
  return out
}

// ---------- 城市弹窗关联作品：按需加载 ----------
// 地图初始化不再批量拉取各地点 /literature；弹窗打开时才请求单点，
// 成功结果由 API 层缓存（重复打开同一城市不发请求）；失败展示可重试状态，不静默回退 Mock
const litState = ref('idle') // 'idle' | 'loading' | 'ready' | 'error'（仅城市弹窗用）
const litWorks = ref([])

async function loadCityLiterature(d) {
  // Mock 模式：关联作品已在城市数据内（authors[].works），无需请求
  if (USE_MOCK) { litWorks.value = cityWorks(d); litState.value = 'ready'; return }
  litState.value = 'loading'
  litWorks.value = []
  try {
    litWorks.value = await getPlaceLiterature(d.id)
    litState.value = 'ready'
  } catch (e) {
    litState.value = 'error'
  }
}

function retryCityLiterature() {
  if (selected.value) loadCityLiterature(selected.value.data)
}

watch(() => mapStore.selectedId, (id) => {
  const m = id ? markers.value.find(x => x.id === id) : null
  // 仅城市标记（总览模式 major/minor）需要按需加载关联作品；书籍标记不涉及
  if (m && (m.kind === 'major' || m.kind === 'minor')) loadCityLiterature(m.data)
  else { litState.value = 'idle'; litWorks.value = [] }
})

onMounted(() => {
  loadCities()
  const measure = () => {
    if (wrapRef.value) {
      wrapSize.w = wrapRef.value.clientWidth
      wrapSize.h = wrapRef.value.clientHeight
    }
  }
  measure()
  nextTick(measure)
  ro = new ResizeObserver(measure)
  if (wrapRef.value) ro.observe(wrapRef.value)
})
onBeforeUnmount(() => { if (ro) ro.disconnect() })
</script>

<template>
  <div class="map-wrap" ref="wrapRef" @wheel.prevent="onWheel">
    <!-- 星空背景（与预览一致的银河底图；原始素材 cosmos-bg.jpg 保留在 assets 中） -->
    <div class="starfield" aria-hidden="true" :style="{ backgroundImage: 'url(' + starfieldUrl + ')' }"></div>

    <!-- 数据加载状态：加载中 / 加载失败（可重试），不静默使用空数据或 Mock -->
    <div v-if="loadState === 'loading'" class="map-state">正在加载地图数据…</div>
    <div v-else-if="loadState === 'error'" class="map-state map-state-err">
      <span>地图数据加载失败，无法连接后端服务</span>
      <button class="map-retry" @click="loadCities">重试</button>
    </div>

    <!-- 地图 -->
    <svg class="map-svg" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet"
      @click="onMapClick"
      @pointerdown="onPointerDown" @pointermove="onPointerMove"
      @pointerup="endDrag" @pointercancel="endDrag" @pointerleave="endDrag">
      <defs>
        <radialGradient id="la-ocean" cx="50%" cy="44%" r="74%">
          <stop offset="0%" stop-color="#0a1830" stop-opacity=".08" />
          <stop offset="55%" stop-color="#0a1526" stop-opacity=".14" />
          <stop offset="100%" stop-color="#050b16" stop-opacity=".28" />
        </radialGradient>
        <linearGradient id="la-land" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1c2a48" />
          <stop offset="50%" stop-color="#121e3a" />
          <stop offset="100%" stop-color="#0a1224" />
        </linearGradient>
        <radialGradient id="la-shade" cx="50%" cy="40%" r="74%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="55%" stop-color="#c9d3ea" />
          <stop offset="100%" stop-color="#6f7da0" />
        </radialGradient>
        <filter id="la-glow-blur" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
        <!-- 大陆遮罩：由 world.geo.json 所有多边形构成，是唯一的大陆边界依据 -->
        <clipPath id="la-landclip">
          <path v-for="c in countryPaths" :key="c.id" :d="c.d" />
        </clipPath>
      </defs>

      <rect class="ocean" x="0" y="0" :width="WORLD_W" :height="WORLD_H" />
      <g class="graticule" aria-hidden="true">
        <line v-for="(l, i) in graticule" :key="i" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" :class="l.kind" />
      </g>
      <!-- 柔和大边缘光：蓝白环境光 + 淡金点缀（独立绘制，位于大陆填充层之下） -->
      <g class="land-glow" aria-hidden="true" filter="url(#la-glow-blur)">
        <path v-for="c in countryPaths" :key="'glowA' + c.id" :d="c.d" />
      </g>
      <g class="land-glow-gold" aria-hidden="true" filter="url(#la-glow-blur)">
        <path v-for="c in countryPaths" :key="'glowG' + c.id" :d="c.d" />
      </g>
      <!-- 大陆填充：裁切基底 + 淡云雾 + 蓝色网格线（星图化大陆勾边） -->
      <g clip-path="url(#la-landclip)">
        <rect class="land-base" x="0" y="0" :width="WORLD_W" :height="WORLD_H" />
        <image class="land-nebula" :href="nebulaUrl" x="0" y="0" width="1000" height="500" preserveAspectRatio="xMidYMid slice" />
        <rect class="land-tint" x="0" y="0" :width="WORLD_W" :height="WORLD_H" />
        <image class="land-texture" :href="textureUrl" x="0" y="0" width="1000" height="500" preserveAspectRatio="none" />
        <g class="land-grid" aria-hidden="true">
          <line v-for="(l, i) in graticule" :key="'lg' + i" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" />
        </g>
        <rect class="land-shade" x="0" y="0" :width="WORLD_W" :height="WORLD_H" />
      </g>
      <!-- 国家边界：淡蓝细线勾边（星图大陆轮廓） -->
      <g class="world">
        <path v-for="c in countryPaths" :key="c.id" :d="c.d" :class="countryClass(c)" />
      </g>
    </svg>

    <!-- 暗角 + 细颗粒纹理（屏幕空间，增强纵深与材质） -->
    <div class="vignette" aria-hidden="true"></div>
    <div class="grain" aria-hidden="true"></div>

    <!-- 发光粒子标记：灯光随地图缩放微调大小（幅度为缩放增量的 1/10），文字标签反向缩放保持可读 -->
    <button v-for="m in visibleMarkers" :key="m.id"
      class="marker" :class="[m.kind, { 'is-active': m.id === mapStore.selectedId }]"
      :style="{ left: m.sx + 'px', top: m.sy + 'px', '--mk-scale': 1 + (zoom - 1) / 10 }"
      @click.stop="onMarkerClick(m)">
      <span class="halo"></span>
      <span class="core"></span>
      <span class="ring"></span>
      <span class="label">{{ m.name }}</span>
    </button>

    <!-- 近距离标记候选列表：多个地点重叠时，点击先列出附近地点，由用户明确选择 -->
    <transition name="pop">
      <div v-if="clusterMenu" class="cluster-menu"
        :style="{
          left: Math.max(8, Math.min(wrapSize.w - 240, clusterMenu.x - 12)) + 'px',
          top: Math.min(wrapSize.h - 150, clusterMenu.y + 14) + 'px'
        }">
        <p class="cluster-title">此区域有 {{ clusterMenu.items.length }} 个相近地点</p>
        <button v-for="it in clusterMenu.items" :key="it.id" class="cluster-item"
          @click.stop="chooseClusterItem(it)">
          <span class="ci-dot" :class="it.kind"></span>
          <span class="ci-name">{{ it.name }}</span>
          <span class="ci-country">{{ it.data.country }}</span>
        </button>
        <button class="cluster-cancel" @click.stop="closeClusterMenu">取消</button>
      </div>
    </transition>

    <!-- 信息面板 -->
    <transition name="pop">
      <aside v-if="selected" class="popup" :style="popupStyle()">
        <button class="popup-close" @click="mapStore.selectedId = null">×</button>
        <!-- 城市弹窗：总览模式下标记只有 major（重要）与 minor（普通）两类，都进入城市模板 -->
        <template v-if="selected.kind === 'major' || selected.kind === 'minor'">
          <div class="popup-top">
            <div class="popup-head">
              <p class="popup-city">{{ selected.data.city }}<span>{{ selected.data.country }}</span></p>
            </div>
          </div>
          <p v-if="selected.data.genre" class="popup-genre">文学流派 · {{ selected.data.genre }}</p>
          <p class="popup-summary">{{ selected.data.summary || '这座城市暂无简介。' }}</p>
          <div v-if="selected.data.authors && selected.data.authors.length" class="popup-auth-block">
            <p class="popup-section-title">代表作家</p>
            <div class="popup-auth-row">
              <span v-for="a in selected.data.authors.slice(0, 4)" :key="a.name" class="popup-author">
                <span class="av">{{ a.name.slice(0, 1) }}</span>
                <span class="av-name">{{ a.name }}</span>
              </span>
            </div>
          </div>
          <p v-if="litState === 'loading'" class="popup-works">正在加载关联作品…</p>
          <p v-else-if="litState === 'error'" class="popup-works">
            关联作品加载失败<button class="map-retry popup-retry" @click="retryCityLiterature">重试</button>
          </p>
          <p v-else-if="litWorks.length" class="popup-works">
            关联作品 · {{ litWorks.slice(0, 3).map(w => w.title).join('、') }} 等
          </p>
          <router-link class="popup-more" to="/works" @click="mapStore.selectedId = null">在阅读探索中查看 →</router-link>
        </template>
        <template v-else>
          <!-- 个人模式：同一地点聚合标记，展示该地点关联的全部书架书籍 -->
          <p class="popup-city">{{ selected.data.city }}<span>{{ selected.data.country }}</span></p>
          <div v-if="selected.data.books && selected.data.books.length" class="popup-booklist">
            <router-link v-for="bk in selected.data.books" :key="bk.bookId"
              class="popup-book" :to="'/works/' + bk.bookId" @click="mapStore.selectedId = null">
              <span class="pb-title">《{{ bk.title }}》</span>
              <span class="pb-status">{{ bookStatusText(bk.status) }}</span>
            </router-link>
          </div>
          <p v-else class="popup-status">暂无书籍关联该地点。</p>
          <router-link class="popup-more" to="/bookshelf" @click="mapStore.selectedId = null">在书架中管理 →</router-link>
        </template>
      </aside>
    </transition>

    <div class="zoom-controls">
      <button @click="zoomBy(1.4)" title="放大">＋</button>
      <button @click="zoomBy(1 / 1.4)" title="缩小">－</button>
      <button @click="resetView" title="复位视图">⟲</button>
    </div>

    <!-- 主题装饰：左上星盘（与满意版预览一致的细线三环） -->
    <div class="deco deco-astrolabe" aria-hidden="true"></div>

    <!-- 比例尺：线段长度随缩放比例同步伸缩（km 标签不变） -->
    <div class="scale-bar" aria-hidden="true">
      <span class="scale-line" :style="{ width: Math.round(180 * zoom) + 'px' }"></span>
      <span class="scale-label">0 — 3000 — 6000 km</span>
    </div>
  </div>
</template>

<style scoped>
.map-wrap {
  position: relative; width: 100%; height: 100%;
  overflow: hidden; cursor: grab; touch-action: none; user-select: none;
  background: #04070f;
}
.map-wrap:active { cursor: grabbing; }

/* ---- 数据加载状态 ---- */
.map-state {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  z-index: 30; display: flex; align-items: center; gap: 14px;
  padding: 12px 22px; border-radius: 10px;
  border: 1px solid rgba(212, 180, 119, .4); background: rgba(8, 14, 26, .92);
  font-size: 14px; color: var(--ink); backdrop-filter: blur(6px);
}
.map-state-err { border-color: rgba(226, 136, 127, .5); color: #e2a49c; }
.map-retry {
  height: 30px; padding: 0 14px; font-size: 13px; cursor: pointer;
  color: var(--accent-soft); background: transparent;
  border: 1px solid rgba(212, 180, 119, .5); border-radius: 999px;
}
.map-retry:hover { background: rgba(212, 180, 119, .15); }

/* ---- 宇宙背景素材（最底层，原图完整覆盖） ---- */
.starfield {
  position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-position: center; background-size: cover; background-repeat: no-repeat;
}

/* ---- 地图 ---- */
.map-svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; z-index: 2; }
.ocean { fill: url(#la-ocean); }
.graticule line { stroke: rgba(150, 180, 220, .06); stroke-width: .3; }
.graticule line.lat { stroke: rgba(150, 180, 220, .04); }
.land-glow path { fill: none; stroke: #8fb6ff; stroke-width: 3; stroke-linejoin: round; opacity: .22; }
.land-glow-gold path { fill: none; stroke: #e9cd96; stroke-width: 1.4; stroke-linejoin: round; opacity: .3; }
.land-base { fill: url(#la-land); }
.land-nebula { opacity: .45; pointer-events: none; }
.land-tint { fill: rgba(7, 13, 26, .4); pointer-events: none; }
.land-texture { mix-blend-mode: soft-light; opacity: .18; pointer-events: none; }
/* 大陆内部的蓝色网格线：星图化大陆勾边 */
.land-grid line { stroke: rgba(122, 168, 228, .13); stroke-width: .35; }
.land-shade { fill: url(#la-shade); mix-blend-mode: multiply; opacity: .4; pointer-events: none; }

/* 金色星座连线：已按需求移除灯光间虚线 */

/* 大陆边界与国界：暗金色勾勒（与预览一致的古典星图集风格） */
.world .country {
  fill: transparent;
  stroke: rgba(200, 162, 95, .52); stroke-width: .5;
  pointer-events: all;
  transition: opacity .25s ease, fill .25s ease;
}
.world .country.is-dim { fill: rgba(4, 7, 14, .22); stroke: rgba(150, 138, 108, .14); opacity: .6; }
.world .country.is-lit { fill: rgba(214, 180, 96, .07); stroke: rgba(240, 214, 160, .45); stroke-width: .4; }

/* ---- 暗角：直接套用满意版预览的 skydim 色调 ---- */
.vignette {
  position: absolute; inset: 0; pointer-events: none; z-index: 3;
  background:
    linear-gradient(180deg, rgba(4, 7, 15, .58) 0%, rgba(4, 7, 15, .26) 34%, rgba(4, 7, 15, .30) 62%, rgba(4, 7, 15, .60) 100%),
    radial-gradient(120% 90% at 50% 50%, transparent 55%, rgba(3, 5, 10, .42) 100%);
}
.grain {
  position: absolute; inset: 0; pointer-events: none; z-index: 3;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E");
  background-size: 160px 160px;
  mix-blend-mode: overlay; opacity: .06;
}

/* ---- 发光粒子标记 ---- */
.marker {
  position: absolute; transform: translate(-50%, -50%) scale(var(--mk-scale, 1));
  width: 0; height: 0; background: none; border: none; padding: 0;
  cursor: pointer; z-index: 5;
  --core: #f5dda6; --glow: rgba(146, 111, 58, .45); --halo: rgba(146, 111, 58, .34);
}
/* 想读状态：紫色核心光点（光晕统一暗金色） */
.marker.want { --core: #cdb4f2; --glow: rgba(146, 111, 58, .45); --halo: rgba(146, 111, 58, .32); }
/* 图例：想读作品的紫色圆点 */
.lg-dot-want { background: #b48ce0; }
.marker .core {
  position: absolute; left: 50%; top: 50%;
  width: 4.5px; height: 4.5px; margin: -2.25px 0 0 -2.25px; border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, #fff 0%, var(--core) 44%, transparent 100%);
  box-shadow: 0 0 3px 1px var(--core), 0 0 6px 1px var(--glow);
}
.marker .halo {
  position: absolute; left: 50%; top: 50%;
  width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%;
  background: radial-gradient(circle, var(--halo) 0%, transparent 62%);
}
.marker .ring {
  position: absolute; left: 50%; top: 50%;
  width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%;
  border: 1px solid rgba(170, 130, 66, .5); opacity: 0;
}
/* 灯光缩小后的可点击热区（透明，不显示）：适度扩大响应范围，
   过近标记由候选列表兜底，扩区不会挤占相邻地点的选择 */
.marker::after { content: ""; position: absolute; left: -13px; top: -13px; width: 26px; height: 26px; border-radius: 50%; }

.marker.major { --core: #fff6de; --glow: rgba(170, 130, 66, .5); --halo: rgba(170, 130, 66, .38); }
.marker.major .core { width: 6px; height: 6px; margin: -3px 0 0 -3px; }
.marker.major .halo { width: 15px; height: 15px; margin: -7.5px 0 0 -7.5px; }
.marker.major .ring { width: 15px; height: 15px; margin: -7.5px 0 0 -7.5px; }

/* 普通城市：更小的金色光点 */
.marker.minor { --core: #e9cf9c; --glow: rgba(146, 111, 58, .35); --halo: rgba(146, 111, 58, .28); }
.marker.minor .core { width: 4.5px; height: 4.5px; margin: -2.25px 0 0 -2.25px; }
.marker.minor .halo { width: 12px; height: 12px; margin: -6px 0 0 -6px; }
.marker.minor .ring { width: 12px; height: 12px; margin: -6px 0 0 -6px; }

.marker.finished { --core: #f2d9a4; --glow: rgba(160, 122, 62, .45); --halo: rgba(160, 122, 62, .32); }
.marker.reading { --core: #d7e8f8; --glow: rgba(146, 111, 58, .45); --halo: rgba(146, 111, 58, .32); }
.marker.reading .core { animation: twinkle 2.4s ease-in-out infinite; }
.marker.want_to_read { --core: #cdb4f2; --glow: rgba(146, 111, 58, .45); --halo: rgba(146, 111, 58, .32); }

.marker.is-active .ring { animation: ripple 2s ease-out infinite; }
.marker.is-active .halo { animation: pulse 2s ease-in-out infinite; }
@keyframes twinkle { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
@keyframes ripple { 0% { transform: scale(.5); opacity: .7; } 100% { transform: scale(2.6); opacity: 0; } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }

.marker .label {
  position: absolute; left: 50%; top: 18px;
  transform: translateX(-50%) scale(calc(1 / var(--mk-scale, 1))); transform-origin: 50% 0;
  white-space: nowrap; font-size: 12px; color: var(--ink);
  background: rgba(8, 15, 28, .88); border: 1px solid var(--line);
  padding: 2px 8px; border-radius: 2px; opacity: 0; pointer-events: none; transition: opacity .15s;
}
.marker:hover .label, .marker.is-active .label { opacity: 1; }

/* 弹窗：深蓝黑底 + 金色双线边框 + 四角角饰（古典质感） */
.popup {
  position: absolute; width: 320px; max-width: calc(100% - 20px); z-index: 20;
  background: rgba(8, 14, 26, .96); backdrop-filter: blur(10px);
  border: 1px solid rgba(212, 180, 119, .38); border-radius: 12px;
  padding: 18px 18px 14px; color: var(--ink);
  box-shadow: 0 18px 50px rgba(0, 0, 0, .65), 0 4px 18px rgba(0, 0, 0, .5);
}
.popup::before {
  content: ""; position: absolute; inset: 5px; border-radius: 8px;
  border: 1px solid rgba(212, 180, 119, .13); pointer-events: none;
}
.popup::after {
  content: ""; position: absolute; inset: 0; border-radius: 12px; pointer-events: none;
  --ck: rgba(224, 191, 130, .8);
  background:
    linear-gradient(var(--ck), var(--ck)) left 7px top 7px / 16px 1.5px,
    linear-gradient(var(--ck), var(--ck)) left 7px top 7px / 1.5px 16px,
    linear-gradient(var(--ck), var(--ck)) right 7px top 7px / 16px 1.5px,
    linear-gradient(var(--ck), var(--ck)) right 7px top 7px / 1.5px 16px,
    linear-gradient(var(--ck), var(--ck)) left 7px bottom 7px / 16px 1.5px,
    linear-gradient(var(--ck), var(--ck)) left 7px bottom 7px / 1.5px 16px,
    linear-gradient(var(--ck), var(--ck)) right 7px bottom 7px / 16px 1.5px,
    linear-gradient(var(--ck), var(--ck)) right 7px bottom 7px / 1.5px 16px;
  background-repeat: no-repeat;
}
.popup-close { position: absolute; top: 10px; right: 12px; background: none; border: none; color: var(--muted); font-size: 20px; cursor: pointer; line-height: 1; }
.popup-close:hover { color: var(--ink); }
.popup-city { font-family: Georgia, "Songti SC", serif; font-size: 19px; margin-bottom: 4px; padding-right: 18px; }
.popup-city span { font-size: 13px; color: var(--accent); margin-left: 8px; letter-spacing: .05em; }
.popup-summary { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
.popup-genre { font-size: 12px; color: var(--accent-soft); margin-bottom: 10px; }
.popup-top { display: flex; gap: 12px; align-items: flex-start; }
.popup-head { min-width: 0; flex: 1; }
.popup-head .popup-city { margin-bottom: 4px; }
.popup-head .popup-summary { margin-bottom: 0; }
.popup-section-title { font-size: 11px; letter-spacing: .08em; color: var(--muted); margin-bottom: 8px; }
.popup-auth-block { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
.popup-auth-row { display: flex; flex-wrap: wrap; gap: 8px 14px; }
.popup-author { display: inline-flex; align-items: center; gap: 6px; }
.av { width: 20px; height: 20px; border-radius: 50%; background: var(--accent); color: #171006; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; font-family: Georgia, serif; flex-shrink: 0; }
.av-name { font-size: 12px; color: var(--ink); white-space: nowrap; }
.popup-works { font-size: 12px; color: var(--muted); margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
/* 弹窗内联重试按钮：复用全局 map-retry 样式，仅收紧尺寸适配弹窗 */
.popup-retry { height: 24px; padding: 0 10px; font-size: 12px; margin-left: 10px; }
.popup-status { font-size: 13px; color: var(--accent-soft); margin-top: 8px; padding-top: 10px; border-top: 1px solid var(--line); }
.popup-more { display: inline-block; margin-top: 12px; font-size: 12px; color: var(--accent); }
.popup-more:hover { color: var(--accent-soft); }

/* ---- 个人模式地点弹窗：该地点关联的全部书架书籍列表 ---- */
.popup-booklist { margin-top: 8px; display: flex; flex-direction: column; }
.popup-book {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 8px 2px; border-bottom: 1px solid var(--line);
  font-size: 13px; color: var(--ink); text-decoration: none;
}
.popup-book:last-child { border-bottom: none; }
.popup-book:hover .pb-title { color: var(--accent); }
.pb-title { font-family: Georgia, 'Songti SC', serif; }
.pb-status { font-size: 12px; color: var(--accent-soft); white-space: nowrap; }

/* ---- 近距离标记候选列表：与弹窗一致的金边深蓝底古典质感 ---- */
.cluster-menu {
  position: absolute; z-index: 25; min-width: 180px; max-width: 230px;
  background: rgba(8, 14, 26, .96); backdrop-filter: blur(10px);
  border: 1px solid rgba(212, 180, 119, .38); border-radius: 10px;
  padding: 10px 10px 8px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, .6), 0 4px 14px rgba(0, 0, 0, .45);
}
.cluster-menu::before {
  content: ""; position: absolute; inset: 4px; border-radius: 7px;
  border: 1px solid rgba(212, 180, 119, .13); pointer-events: none;
}
.cluster-title { font-size: 11px; letter-spacing: .08em; color: var(--muted); margin-bottom: 6px; }
.cluster-item {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 6px 8px; background: transparent; border: none; border-radius: 6px;
  cursor: pointer; text-align: left; color: var(--ink);
}
.cluster-item:hover { background: rgba(212, 180, 119, .14); }
.ci-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  background: #f5dda6; box-shadow: 0 0 6px rgba(146, 111, 58, .8);
}
.ci-dot.minor { background: #e9cf9c; }
.ci-dot.want, .ci-dot.want_to_read { background: #cdb4f2; }
.ci-dot.reading { background: #d7e8f8; }
.ci-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ci-country { font-size: 11px; color: var(--accent); margin-left: auto; padding-left: 8px; white-space: nowrap; }
.cluster-cancel {
  margin-top: 6px; width: 100%; height: 26px; font-size: 12px;
  color: var(--muted); background: transparent;
  border: 1px solid var(--line); border-radius: 6px; cursor: pointer;
}
.cluster-cancel:hover { color: var(--ink); }

.zoom-controls { position: absolute; left: 16px; bottom: 16px; z-index: 15; display: flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(212, 180, 119, .4); border-radius: 6px; background: rgba(13, 25, 41, .85); }
.zoom-controls button { width: 34px; height: 34px; background: transparent; border: none; color: var(--ink); font-size: 16px; cursor: pointer; border-bottom: 1px solid var(--line); }
.zoom-controls button:last-child { border-bottom: none; }
.zoom-controls button:hover { background: rgba(212, 180, 119, .15); }

/* ---- 主题装饰：星盘 / 罗盘 / 行星地平线 ---- */
.deco { position: absolute; z-index: 4; pointer-events: none; }
.deco-astrolabe { left: -90px; top: -90px; width: 340px; height: 340px; border-radius: 50%; border: 1px solid rgba(217, 186, 130, .13); }
.deco-astrolabe::before { content: ""; position: absolute; inset: 34px; border-radius: 50%; border: 1px dashed rgba(217, 186, 130, .15); }
.deco-astrolabe::after { content: ""; position: absolute; inset: 84px; border-radius: 50%; border: 1px solid rgba(217, 186, 130, .09); }

/* ---- 比例尺 ---- */
.scale-bar { position: absolute; left: 50%; bottom: 14px; transform: translateX(-50%); z-index: 15; display: flex; align-items: center; gap: 10px; pointer-events: none; }
.scale-line { position: relative; display: block; width: 180px; height: 8px; border-bottom: 1px solid rgba(212, 180, 119, .55); transition: width .2s ease; }
.scale-line::before, .scale-line::after { content: ""; position: absolute; top: 0; bottom: 0; width: 1px; background: rgba(212, 180, 119, .8); }
.scale-line::before { left: 0; }
.scale-line::after { right: 0; }
.scale-label { font-size: 11px; letter-spacing: .12em; color: var(--muted); white-space: nowrap; }

.pop-enter-active, .pop-leave-active { transition: opacity .15s, transform .15s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(6px); }
</style>