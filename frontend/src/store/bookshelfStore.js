// =============================================================
// 书架统一数据模块（唯一数据源）
// - 首页书架侧栏（BookshelfSidebar）与书架页（BookshelfView）共用这一份数据
// - 添加 / 修改状态 / 删除 都必须通过本模块操作，改动后所有视图自动同步
// - 修改会自动持久化到 localStorage，刷新页面不丢失
// - 未来接入真实后端时：initBookshelf 换成接口拉取，增删改方法换成接口请求即可
// =============================================================
import { ref } from 'vue'
import { getShelfBooks } from '../api'
import { literaryCities } from '../api/mock'

const STORAGE_KEY = 'literary-atlas-bookshelf'

// 用户手动添加的书没有预设封面，按书名长度选择内置渐变色（本地模拟用）
const FALLBACK_COVERS = [
  ['#C4A35A', '#5C4326'],
  ['#5E7FA8', '#24364F'],
  ['#9A7BBF', '#3D2B54'],
  ['#C97B5A', '#55311F'],
  ['#6FA68F', '#23443A']
]

// 当前书架书籍列表（ref）：导入它的组件共享同一份数据，天然保持响应式同步
const books = ref([])
let inited = false

// 从 localStorage 恢复用户上次修改后的书架
function readCache() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) { return null }
}

// ---------- 书目地理位置自动匹配 ----------
// 索引：作品名 → 收录城市（含作者名 → 城市作后备）。数据来自 literaryCities 的作家作品表
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

/**
 * 补全书籍地理位置：手动添加 / 导入的书往往只有书名作者，
 * 按书名（其次作者名）关联到收录城市后补齐经纬度与国家码，
 * 使个性化地图能点亮对应国家并显示城市灯光。以后新增已读书目同样自动生效。
 */
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

// 对整份书架做一次地理补全（幂等，改动后写回缓存）
function enrichAll() {
  let changed = false
  for (const b of books.value) {
    const before = JSON.stringify([b.city, b.country, b.countryCode, b.lat, b.lng])
    enrichLocation(b)
    if (JSON.stringify([b.city, b.country, b.countryCode, b.lat, b.lng]) !== before) changed = true
  }
  if (changed) persist()
}

// 把当前书架写入 localStorage（保存失败不影响内存数据）
function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(books.value)) } catch (e) { /* 忽略 */ }
}

/**
 * 初始化书架：优先恢复本地保存的数据，否则经 API 层读取 mock
 * 幂等：首页侧栏和书架页都会调用，但只真正加载一次
 */
export async function initBookshelf() {
  if (inited) return
  books.value = readCache() || (await getShelfBooks())
  enrichAll()
  inited = true
}

/** 添加书籍（书名 / 作者 / 阅读状态） */
export function addBook({ title, author, status }) {
  const id = Date.now()
  const book = {
    id, title, author, status,
    cover: FALLBACK_COVERS[title.length % FALLBACK_COVERS.length],
    // 手动添加的书暂无地理位置：由 enrichLocation 按书名/作者自动匹配收录城市
    city: '', country: '', countryCode: '', lat: null, lng: null
  }
  enrichLocation(book)
  books.value.push(book)
  persist()
}

/** 修改阅读状态：'read'（已读）| 'reading'（在读）| 'want'（想读） */
export function updateBookStatus(id, status) {
  const b = books.value.find(x => x.id === id)
  if (b) { b.status = status; persist() }
}

/** 删除书籍 */
export function removeBook(id) {
  const i = books.value.findIndex(x => x.id === id)
  if (i >= 0) { books.value.splice(i, 1); persist() }
}

export { books }