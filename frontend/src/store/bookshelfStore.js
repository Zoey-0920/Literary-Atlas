// =============================================================
// 书架统一数据模块（唯一数据源）
// - 首页书架侧栏（BookshelfSidebar）与书架页（BookshelfView）共用这一份数据
// - 添加 / 修改状态 / 删除 都必须通过本模块操作，改动后所有视图自动同步
// - Mock 模式：localStorage 持久化（键 literary-atlas-bookshelf）
// - 真实模式：以 /api/reading 后端数据为准，本地不持久化，失败时报错不静默回退
// =============================================================
import { ref } from 'vue'
import {
  USE_MOCK, READING_STATUS, normalizeStatus,
  getShelfBooks, findOrCreateBook, addReading, updateReading, deleteReading, clearApiCaches,
  getShelfStats
} from '../api'
import { literaryCities } from '../api/mock'

const STORAGE_KEY = 'literary-atlas-bookshelf'

// 用户手动添加的书没有预设封面，按书名散列选择内置渐变色（本地模拟用）
const FALLBACK_COVERS = [
  ['#C4A35A', '#5C4326'],
  ['#5E7FA8', '#24364F'],
  ['#9A7BBF', '#3D2B54'],
  ['#C97B5A', '#55311F'],
  ['#6FA68F', '#23443A']
]

// 当前书架书籍列表（ref）：导入它的组件共享同一份数据，天然保持响应式同步
const books = ref([])
const loading = ref(false)   // 真实模式加载中
const error = ref(null)      // 最近一次加载/操作错误信息
let inited = false
let loadSeq = 0

// ---------- 统计（真实模式 GET /api/reading/statistics；Mock 本地计算） ----------

// 最近一次有效统计：请求失败时保留旧值不清空，页面据此降级显示
const shelfStats = ref({ total: 0, want_to_read: 0, reading: 0, finished: 0 })
const statsError = ref(null) // 统计请求失败提示（书架数据不受影响）
let statsSeq = 0

async function loadStats() {
  const seq = ++statsSeq
  try {
    const s = await getShelfStats(books.value)
    if (seq !== statsSeq) return
    shelfStats.value = {
      total: Number(s && s.total) || 0,
      want_to_read: Number(s && s.want_to_read) || 0,
      reading: Number(s && s.reading) || 0,
      finished: Number(s && s.finished) || 0
    }
    statsError.value = null
  } catch (e) {
    if (seq !== statsSeq) return
    // 统计失败只提示，保留最近一次有效结果，不影响书架列表
    statsError.value = e && e.message ? e.message : '阅读统计加载失败'
  }
}

// ---------- Mock 模式：本地缓存与地理补全 ----------

// 从 localStorage 恢复用户上次修改后的书架（仅 Mock 模式）
function readCache() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const list = JSON.parse(raw)
    // 兼容旧缓存的状态值（read/want → finished/want_to_read）
    for (const b of list) if (b && b.status) b.status = normalizeStatus(b.status)
    return list
  } catch (e) { return null }
}

// 索引：作品名 → 收录城市（含作者名 → 城市作后备）。数据来自 literaryCities 的作家作品表
// 仅 Mock 模式使用；真实模式的书架地理信息一律来自后端作品详情的关联地点
const WORK_CITY_INDEX = (() => {
  const m = new Map()
  for (const c of literaryCities) {
    for (const a of c.authors || []) {
      for (const w of a.works || []) if (!m.has(w)) m.set(w, c)
      if (a.name && !m.has(a.name)) m.set(a.name, c)
    }
  }
  return m
})()

function enrichLocation(b) {
  if (b.lat != null && b.lng != null && b.countryCode) return b
  const hit = WORK_CITY_INDEX.get(b.title) || WORK_CITY_INDEX.get(b.author)
  if (!hit) return b
  if (b.city == null || b.city === '') b.city = hit.city
  if (b.country == null || b.country === '') b.country = hit.country
  if (b.countryCode == null || b.countryCode === '') b.countryCode = hit.countryCode
  if (b.lat == null) b.lat = hit.lat
  if (b.lng == null) b.lng = hit.lng
  return b
}

function enrichAll() {
  for (const b of books.value) enrichLocation(b)
}

function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(books.value)) } catch (e) { /* 忽略 */ }
}

// ---------- 加载 ----------

async function load() {
  const seq = ++loadSeq
  loading.value = true
  error.value = null
  try {
    const list = await getShelfBooks()
    if (seq !== loadSeq) return
    books.value = list
    if (USE_MOCK) { enrichAll(); persist() }
    // 书架数据变化后同步刷新统计（真实模式走 /api/reading/statistics）；
    // 不 await：统计失败不影响书架展示，错误记录在 statsError
    loadStats()
  } catch (e) {
    if (seq !== loadSeq) return
    // 真实模式后端不可达：记录错误供页面展示，不静默回退 Mock
    error.value = e && e.message ? e.message : '加载书架失败'
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

/**
 * 初始化书架（幂等：首页侧栏和书架页都会调用，但只真正加载一次）
 * Mock 模式优先恢复本地缓存；真实模式直接拉取 /api/reading
 */
export async function initBookshelf() {
  if (inited) return
  inited = true
  if (USE_MOCK) {
    const cache = readCache()
    if (cache) { books.value = cache; enrichAll(); loadStats(); return }
  }
  await load()
}

/** 手动重新加载（错误横幅的"重试"按钮使用） */
export function reloadBookshelf() {
  inited = true
  return load()
}

// ---------- 增删改 ----------

/** 添加书籍（书名 / 作者 / 阅读状态） */
export async function addBook({ title, author, status }) {
  const t = String(title || '').trim()
  if (!t) throw new Error('书名不能为空')

  if (USE_MOCK) {
    const book = {
      id: Date.now(), title: t, author: String(author || '').trim(),
      status: normalizeStatus(status) || READING_STATUS.WANT,
      cover: FALLBACK_COVERS[t.length % FALLBACK_COVERS.length],
      // 手动添加的书暂无地理位置：由 enrichLocation 按书名/作者自动匹配收录城市
      city: '', country: '', countryCode: '', lat: null, lng: null
    }
    enrichLocation(book)
    books.value.push(book)
    persist()
    return
  }

  // 真实模式：先按书名查已有作品，没有才创建（避免重复建书），再添加阅读记录
  // 不传 user_id：后端统一挂在演示用户下
  try {
    const created = await findOrCreateBook(t)
    await addReading({ book_id: created.id, status: normalizeStatus(status) || READING_STATUS.WANT })
    clearApiCaches()
    await load()
  } catch (e) {
    throw e  // 409（已在书架）/ 422 / 网络错误等由页面展示 message
  }
}

/** 修改阅读状态：want_to_read（想读）| reading（在读）| finished（已读） */
export async function updateBookStatus(id, status) {
  if (USE_MOCK) {
    const b = books.value.find(x => x.id === id)
    if (b) { b.status = normalizeStatus(status); persist() }
    return
  }
  // 真实模式：PATCH /api/reading/{record_id}（不传 book_id）
  error.value = null
  try {
    await updateReading(id, { status: normalizeStatus(status) })
    await load()
  } catch (e) {
    error.value = e && e.message ? e.message : '更新阅读状态失败'
    throw e
  }
}

/** 删除书籍（真实模式按阅读记录 id 删除） */
export async function removeBook(id) {
  if (USE_MOCK) {
    const i = books.value.findIndex(x => x.id === id)
    if (i >= 0) { books.value.splice(i, 1); persist() }
    return
  }
  error.value = null
  try {
    await deleteReading(id)
    clearApiCaches()
    await load()
  } catch (e) {
    error.value = e && e.message ? e.message : '删除书籍失败'
    throw e
  }
}

/**
 * 修改阅读信息（评分 rating 1-5 / 进度 progress 0-100 / 笔记 note）
 * @param {number} id 阅读记录 id（record_id，非 book_id）
 * @param {object} patch 只包含本次实际修改的字段；
 *   调用方负责 diff：未修改的字段不要放进 patch，用户明确清空的字段才传 null
 * 失败时保留当前书架状态（load 不会执行），错误向上抛给页面展示
 */
export async function updateBookMeta(id, patch) {
  if (!patch || Object.keys(patch).length === 0) return
  if (USE_MOCK) {
    const b = books.value.find(x => x.id === id)
    if (b) {
      if ('rating' in patch) b.rating = patch.rating
      if ('progress' in patch) b.progress = patch.progress
      if ('note' in patch) b.note = patch.note
      persist()
    }
    return
  }
  // 真实模式：PATCH /api/reading/{record_id}，只提交 patch 中的字段
  error.value = null
  try {
    await updateReading(id, patch)
    clearApiCaches()
    await load()   // 成功后刷新书架（load 内部同步刷新统计）
  } catch (e) {
    error.value = e && e.message ? e.message : '保存阅读信息失败'
    throw e
  }
}

export { books, loading, error, shelfStats, statsError }
