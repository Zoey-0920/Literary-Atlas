// =============================================================
// 统一 API 数据访问层（第一轮真实接口适配版）
// - VITE_API_BASE_URL 已配置 → 走真实后端（严格按根目录 docs/API.md）
// - 未配置（或 VITE_USE_MOCK=true）→ 走本地 Mock（./mock.js），开发回退用
// - 真实模式与 Mock 模式严格分离：真实模式失败时直接报错，绝不静默回退 Mock
// 页面和组件只 import 本文件导出的函数，不直接依赖 mock.js
// =============================================================
import { literaryCities, shelfBooks, mockBooks, mockAuthors } from './mock'

// ---------- 模式判定 ----------
const RAW_BASE = String(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
// 显式 VITE_USE_MOCK=true 可强制 Mock；否则仅当地址为空时使用 Mock
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || RAW_BASE === ''
const BASE_URL = RAW_BASE

// 阅读状态（与 docs/API.md 及数据库约束一致）
export const READING_STATUS = {
  WANT: 'want_to_read',
  READING: 'reading',
  FINISHED: 'finished'
}

// ---------- 错误类型 ----------
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function friendlyMessage(status, detail) {
  const d = detail ? String(detail) : ''
  if (status === 0) return '无法连接后端服务，请确认后端已启动、VITE_API_BASE_URL 配置正确且 CORS 已放行'
  if (status === 404) return d || '请求的资源不存在'
  if (status === 409) return d || '该作品已在书架中，无需重复添加'
  if (status === 422) return d ? `请求参数不合法：${d}` : '请求参数不合法'
  if (status === 502) return d || 'AI 上游模型服务出错，请稍后重试'
  return d || `请求失败（HTTP ${status}）`
}

// ---------- 通用请求 ----------
function qs(params = {}) {
  const s = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === '') continue
    s.set(k, String(v))
  }
  const str = s.toString()
  return str ? '?' + str : ''
}

/**
 * 通用请求函数（真实模式使用）
 * - 超时控制（AbortController）
 * - 解析 FastAPI 错误格式 { detail }
 * - 204 无响应体返回 null
 */
export async function request(path, { method = 'GET', body, timeout = 15000 } = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeout)
  let res
  try {
    res = await fetch(BASE_URL + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal
    })
  } catch (e) {
    clearTimeout(timer)
    throw new ApiError(0, friendlyMessage(0))
  }
  clearTimeout(timer)

  if (res.status === 204) return null
  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch (e) {
      throw new ApiError(res.status, `响应不是有效 JSON（HTTP ${res.status}）`)
    }
  }
  if (!res.ok) {
    const detail = data && data.detail !== undefined ? data.detail : null
    throw new ApiError(res.status, friendlyMessage(res.status, typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : null)))
  }
  return data
}

// 分页拉全量（limit 上限 100，按 offset 翻页）
async function pagedGet(path, extraParams = {}, cap = 2000) {
  const limit = 100
  let offset = 0
  let total = Infinity
  const items = []
  while (offset < Math.min(total, cap)) {
    const data = await request(`${path}${qs({ ...extraParams, limit, offset })}`)
    if (!data || !Array.isArray(data.items)) throw new ApiError(500, '接口响应格式不符合文档（缺少 items）')
    total = typeof data.total === 'number' ? data.total : items.length + data.items.length
    items.push(...data.items)
    if (data.items.length < limit) break
    offset += limit
  }
  return { total: items.length, items }
}

// 有限并发遍历
async function mapLimit(items, limit, fn) {
  const out = new Array(items.length)
  let i = 0
  async function worker() {
    while (i < items.length) {
      const idx = i++
      out[idx] = await fn(items[idx], idx)
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, worker))
  return out
}

// ---------- 国家中文名 → ISO3 映射（仅用于个人地图的国家高亮匹配） ----------
// docs/API.md 中没有该对照表，此映射为前端展示层的国家码补全，不涉及坐标编造
const COUNTRY_ISO = {
  '中国': 'CHN', '日本': 'JPN', '韩国': 'KOR', '朝鲜': 'PRK', '蒙古': 'MNG',
  '英国': 'GBR', '法国': 'FRA', '德国': 'DEU', '意大利': 'ITA', '西班牙': 'ESP',
  '葡萄牙': 'PRT', '荷兰': 'NLD', '比利时': 'BEL', '瑞士': 'CHE', '奥地利': 'AUT',
  '希腊': 'GRC', '爱尔兰': 'IRL', '冰岛': 'ISL', '挪威': 'NOR', '瑞典': 'SWE',
  '丹麦': 'DNK', '芬兰': 'FIN', '波兰': 'POL', '捷克': 'CZE', '匈牙利': 'HUN',
  '罗马尼亚': 'ROU', '俄罗斯': 'RUS', '俄国': 'RUS', '乌克兰': 'UKR', '土耳其': 'TUR', '格鲁吉亚': 'GEO',
  '伊朗': 'IRN', '伊拉克': 'IRQ', '埃及': 'EGY', '以色列': 'ISR', '沙特阿拉伯': 'SAU',
  '印度': 'IND', '巴基斯坦': 'PAK', '阿富汗': 'AFG', '哈萨克斯坦': 'KAZ',
  '越南': 'VNM', '泰国': 'THA', '缅甸': 'MMR', '印度尼西亚': 'IDN', '菲律宾': 'PHL',
  '马来西亚': 'MYS', '新加坡': 'SGP',
  '美国': 'USA', '加拿大': 'CAN', '墨西哥': 'MEX', '古巴': 'CUB',
  '哥伦比亚': 'COL', '阿根廷': 'ARG', '巴西': 'BRA', '智利': 'CHL', '秘鲁': 'PER',
  '委内瑞拉': 'VEN', '乌拉圭': 'URY', '玻利维亚': 'BOL', '厄瓜多尔': 'ECU',
  '南非': 'ZAF', '尼日利亚': 'NGA', '肯尼亚': 'KEN', '埃塞俄比亚': 'ETH', '加纳': 'GHA', '摩洛哥': 'MAR',
  '澳大利亚': 'AUS', '新西兰': 'NZL'
}
function toIso3(country) {
  if (!country) return null
  return COUNTRY_ISO[country] || null
}

function hasCoords(p) {
  if (!p) return false
  // 显式排除 null/undefined/空字符串，避免 Number(null)===0 把无坐标地点当成 (0,0)
  if (p.latitude == null || p.longitude == null) return false
  if (p.latitude === '' || p.longitude === '') return false
  const lat = Number(p.latitude)
  const lng = Number(p.longitude)
  return Number.isFinite(lat) && Number.isFinite(lng)
}

// 旧状态值 → 新状态值（兼容 localStorage 里的旧 Mock 缓存）
const LEGACY_STATUS = { read: 'finished', want: 'want_to_read' }
export function normalizeStatus(s) {
  return LEGACY_STATUS[s] || s
}

// 手动添加书籍的内置封面渐变（与 bookshelfStore 保持一致的演示样式）
const FALLBACK_COVERS = [
  ['#C4A35A', '#5C4326'],
  ['#5E7FA8', '#24364F'],
  ['#9A7BBF', '#3D2B54'],
  ['#C97B5A', '#55311F'],
  ['#6FA68F', '#23443A']
]
function pickCover(seed) {
  let h = 0
  const s = String(seed || '')
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return FALLBACK_COVERS[h % FALLBACK_COVERS.length]
}

// =============================================================
// Mock 模式实现
// =============================================================

// 城市视图模型附加统一的作品数组（供地图弹窗展示）
function mockCityVM(c) {
  const works = []
  for (const a of c.authors || []) for (const w of a.works || []) works.push({ id: null, title: w })
  return { ...c, works }
}

async function mockGetCities() {
  return literaryCities.map(mockCityVM)
}

async function mockGetWorks() {
  return mockBooks.map(b => ({ ...b, authors: [], places: [], genres: [] }))
}

async function mockGetWorkById(id) {
  const w = mockBooks.find(w => String(w.id) === String(id))
  return w ? { ...w, authors: [], places: [], genres: [] } : null
}

async function mockGetAuthors() {
  return mockAuthors.map(a => ({
    id: a.id, name: a.name, birthYear: null, deathYear: null, nationality: null, bio: null,
    birthPlace: a.birthPlace || null, birthPlaceId: null, birthCountry: null,
    works: (a.works || []).map(title => ({ id: null, title, genre: null })),
    places: []
  }))
}

async function mockGetAuthorById(id) {
  const all = await mockGetAuthors()
  return all.find(a => String(a.id) === String(id)) || null
}

async function mockGetShelfBooks() {
  return shelfBooks.map(b => ({ ...b, status: normalizeStatus(b.status), bookId: b.id }))
}

async function mockGetFootprint() {
  // 与真实接口同构：只统计已读、且书籍带有有效坐标的城市（不编造坐标）
  const finished = shelfBooks.map(b => ({ ...b, status: normalizeStatus(b.status) })).filter(b => b.status === READING_STATUS.FINISHED)
  const map = new Map()
  for (const b of finished) {
    if (!b.city || b.lat == null || b.lng == null) continue
    const key = b.city + '|' + (b.country || '')
    if (!map.has(key)) {
      map.set(key, {
        placeId: null, name: b.city, placeType: 'city',
        latitude: b.lat, longitude: b.lng,
        country: b.country || null, region: null, books: []
      })
    }
    map.get(key).books.push({ id: b.bookId || b.id, title: b.title })
  }
  // 命中 26 城库的补上城市 id，供"在世界地图中查看"定位
  const items = [...map.values()]
  for (const it of items) {
    const hit = literaryCities.find(c => c.city === it.name && (!it.country || c.country === it.country))
    if (hit) it.placeId = hit.id
  }
  return { total: items.length, items }
}

async function mockGetShelfStats(books) {
  return countShelfStats(books || shelfBooks)
}

// =============================================================
// 真实模式实现（严格按 docs/API.md）
// =============================================================

// 地点视图模型（来自作品详情 places / 作者 places）
function placeVM(p) {
  return {
    id: p.id, name: p.name, placeType: p.place_type, isFictional: !!p.is_fictional,
    latitude: p.latitude ?? null, longitude: p.longitude ?? null,
    country: p.country ?? null, region: p.region ?? null,
    relationType: p.relation_type ?? null, relationTypeLabel: p.relation_type_label ?? null,
    verificationStatus: p.verification_status ?? null, note: p.note ?? null
  }
}

// 作者视图模型（来自作品详情 authors）
function authorRefVM(a) {
  return {
    id: a.id, name: a.name,
    birthYear: a.birth_year ?? null, deathYear: a.death_year ?? null,
    nationality: a.nationality ?? null, bio: a.bio ?? null, role: a.role ?? null,
    places: (a.places || []).map(placeVM)
  }
}

// 作品详情 → 列表/详情统一视图模型
function bookVM(raw) {
  const authors = (raw.authors || []).map(authorRefVM)
  const places = (raw.places || []).map(placeVM)
  const genres = (raw.genres || []).map(g => ({ id: g.id, name: g.name, description: g.description ?? null }))
  // 派生展示字段（后端列表不返回作者/国家/流派，需要详情补全）
  const firstAuthor = authors[0] || null
  const firstRealPlace = places.find(p => !p.isFictional && p.country) || null
  const firstPlace = places[0] || null
  return {
    id: raw.id,
    title: raw.title,
    originalTitle: raw.original_title ?? null,
    language: raw.language ?? null,
    description: raw.description ?? null,
    source: raw.source ?? null,
    year: raw.publication_year ?? null,
    author: firstAuthor ? firstAuthor.name : null,
    country: (firstAuthor && firstAuthor.nationality) || (firstRealPlace && firstRealPlace.country) || null,
    genre: genres[0] ? genres[0].name : null,
    place: places.length ? places.map(p => p.name).join('、') : null,
    authors, places, genres
  }
}

// 作品详情缓存：getWorks / getAuthors / getShelfBooks 共用一份详情数据，避免重复请求
let worksDetailCache = null
function getAllBooksRaw() {
  if (!worksDetailCache) {
    worksDetailCache = (async () => {
      const { items } = await pagedGet('/api/books')
      const details = await mapLimit(items, 4, b => request(`/api/books/${b.id}`).catch(() => null))
      const m = new Map()
      for (const d of details) if (d && d.id != null) m.set(d.id, d)
      return m
    })().catch(e => { worksDetailCache = null; throw e })
  }
  return worksDetailCache
}

// 地点关联作品缓存（地图城市弹窗按需加载用）：
// 仅缓存成功结果；请求失败时移除缓存条目并抛错，由弹窗展示可重试状态（不静默吞错）
const placeLiteratureCache = new Map()
function getPlaceLiteratureRaw(placeId) {
  if (!placeLiteratureCache.has(placeId)) {
    placeLiteratureCache.set(placeId,
      request(`/api/places/${placeId}/literature`)
        .then(d => (d && Array.isArray(d.items) ? d.items : []))
        .catch(e => { placeLiteratureCache.delete(placeId); throw e })
    )
  }
  return placeLiteratureCache.get(placeId)
}

// 清空缓存（书架增删改后由 store 调用，保证下次拉到新数据）
export function clearApiCaches() {
  worksDetailCache = null
  authorsListCache = null
  placeLiteratureCache.clear()
}

async function realGetCities() {
  // 地图只显示真实且坐标有效的地点；虚构地点不参与（无坐标，后端也不会给）
  // 关联作品不在此批量拉取（否则地图初始化会对全部地点各发一次 /literature 请求），
  // 改为城市弹窗打开时按需加载（见 getPlaceLiterature）
  const { items } = await pagedGet('/api/places')
  const realWithCoords = items.filter(p => !p.is_fictional && p.place_type !== 'fictional' && hasCoords(p))
  return realWithCoords.map(p => ({
    id: p.id,
    city: p.name,
    country: p.country ?? null,
    region: p.region ?? null,
    lat: Number(p.latitude),
    lng: Number(p.longitude),
    summary: p.description ?? null,
    genre: null,
    important: false,
    authors: [], // 地点接口不提供作者信息，不编造
    works: []    // 关联作品由弹窗打开时按需加载
  }))
}

async function realGetWorks() {
  const m = await getAllBooksRaw()
  return [...m.values()].sort((a, b) => a.id - b.id).map(bookVM)
}

async function realGetWorkById(id) {
  try {
    const raw = await request(`/api/books/${id}`)
    return raw ? bookVM(raw) : null
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

// 作者列表缓存：GET /api/authors 单请求即可拿到全部作者（此前需遍历全部作品详情聚合）
let authorsListCache = null

// 真实模式作者列表：GET /api/authors（分页拉全量）
// 该响应不含 works/places，列表层保持视图模型同构；详情页由 realGetAuthorById 单独补全
async function realGetAuthors() {
  if (!authorsListCache) {
    authorsListCache = (async () => {
      const { items } = await pagedGet('/api/authors')
      return items.map(a => ({
        id: a.id, name: a.name,
        birthYear: a.birth_year ?? null, deathYear: a.death_year ?? null,
        nationality: a.nationality ?? null, bio: a.bio ?? null,
        birthPlace: null, birthPlaceId: null, birthCountry: null,
        works: [], places: []
      }))
    })().catch(e => { authorsListCache = null; throw e })
  }
  return authorsListCache
}

// 真实模式作者详情：GET /api/authors/{id}
// books[] 提供关联作品；作者地点/出生信息/作品流派不在该响应中，
// 仅追加请求"该作者自己的作品详情"（通常 1~3 次）补全，不再遍历全部作品
async function realGetAuthorById(id) {
  let raw = null
  try {
    raw = await request(`/api/authors/${id}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
  if (!raw) return null
  const vm = {
    id: raw.id, name: raw.name,
    birthYear: raw.birth_year ?? null, deathYear: raw.death_year ?? null,
    nationality: raw.nationality ?? null, bio: raw.bio ?? null,
    birthPlace: null, birthPlaceId: null, birthCountry: null,
    works: (raw.books || []).map(b => ({ id: b.id, title: b.title, genre: null })),
    places: []
  }
  const details = await mapLimit(vm.works.map(w => w.id), 4, bid => request(`/api/books/${bid}`).catch(() => null))
  const seenPlace = new Set()
  for (const d of details) {
    if (!d) continue
    const self = (d.authors || []).find(a => String(a.id) === String(vm.id))
    if (self) {
      for (const p of self.places || []) {
        // 同一地点可能带多种关系（创作地/生活地），按 地点+关系 去重
        const key = p.id + '|' + (p.relation_type || '')
        if (!seenPlace.has(key)) { seenPlace.add(key); vm.places.push(placeVM(p)) }
      }
    }
    // 关联作品补流派（作品详情 genres[0]），保持原有流派标签展示
    const w = vm.works.find(x => String(x.id) === String(d.id))
    if (w && !w.genre && Array.isArray(d.genres) && d.genres[0]) w.genre = d.genres[0].name
  }
  // 出生信息取自作者关联地点（relation_type=birthplace）
  const bp = vm.places.find(p => p.relationType === 'birthplace')
  if (bp) {
    vm.birthPlaceId = bp.id
    vm.birthPlace = bp.country ? `${bp.country} ${bp.name}` : bp.name
    vm.birthCountry = bp.country
  }
  return vm
}

// 书架视图模型：author / 地理信息来自作品详情（不使用 Mock 城市表补坐标）
function shelfRecordVM(record, bookDetail) {
  const detail = bookDetail ? bookVM(bookDetail) : null
  // 真实且坐标有效的关联地点（虚构地点不加坐标，不点亮地图）
  const realPlaces = detail ? detail.places.filter(p => !p.isFictional && Number.isFinite(p.latitude) && Number.isFinite(p.longitude)) : []
  // 定位地点：优先城市级地点（国家级/区域级地点不代表具体城市），其次任一真实有坐标地点
  const loc = realPlaces.find(p => p.placeType === 'city') || realPlaces[0] || null
  // 国家归属：关联地点的 country 字段常为空（如地点是国家/海域本身），
  // 依次回退：任一关联地点的 country → 作品主国家（bookVM 内作者国籍优先），保证个人地图国家高亮可用
  const countryName = (realPlaces.map(p => p.country).find(Boolean)) || (detail ? detail.country : null) || null
  return {
    id: record.id,             // 阅读记录 id（PATCH / DELETE 使用）
    bookId: record.book_id,    // 作品 id（跳转 / 定位使用）
    title: record.book_title,
    author: detail ? detail.author : null,
    status: record.status,
    rating: record.rating ?? null,
    progress: record.progress ?? null,
    note: record.note ?? null,
    city: loc ? loc.name : null,
    country: countryName,
    countryCode: toIso3(countryName),
    lat: loc ? loc.latitude : null,
    lng: loc ? loc.longitude : null,
    cover: pickCover(record.book_title)
  }
}

async function realGetShelfBooks() {
  const { items } = await pagedGet('/api/reading')
  // 只拉取书架记录实际引用的作品详情（书架为空则 0 次请求），
  // 不再通过 getAllBooksRaw 遍历全部作品
  const ids = [...new Set(items.map(r => r.book_id))]
  const details = await mapLimit(ids, 4, bid => request(`/api/books/${bid}`).catch(() => null))
  const m = new Map(details.filter(Boolean).map(d => [d.id, d]))
  return items.map(r => shelfRecordVM(r, m.get(r.book_id)))
}

async function realGetFootprint() {
  const data = await request('/api/reading/footprint')
  const items = (data && Array.isArray(data.items) ? data.items : []).map(it => ({
    placeId: it.place_id,
    name: it.name,
    placeType: it.place_type ?? null,
    latitude: it.latitude,
    longitude: it.longitude,
    country: it.country ?? null,
    region: it.region ?? null,
    books: (it.books || []).map(b => ({ id: b.id, title: b.title }))
  }))
  return { total: typeof (data && data.total) === 'number' ? data.total : items.length, items }
}

async function realGetShelfStats() {
  return request('/api/reading/statistics')
}

// 按书名精确查找已有作品（addBook 先查后建，避免重复创建）
async function findBookByTitleExact(title) {
  const data = await request(`/api/books${qs({ keyword: title, limit: 100 })}`)
  const items = data && Array.isArray(data.items) ? data.items : []
  return items.find(b => b.title === title) || null
}

// ---------- 对外统一入口（Mock / 真实自动分发） ----------

/** 获取全部文学城市（地图标记 + 弹窗数据）。真实模式：只返回真实且坐标有效的地点 */
export async function getCities() {
  return USE_MOCK ? mockGetCities() : realGetCities()
}

/** 获取文学作品列表 */
export async function getWorks() {
  return USE_MOCK ? mockGetWorks() : realGetWorks()
}

/** 按 id 获取单部作品（未找到返回 null，接口 404 也归一为 null） */
export async function getWorkById(id) {
  return USE_MOCK ? mockGetWorkById(id) : realGetWorkById(id)
}

/** 获取作家数据（真实模式：GET /api/authors 单请求全量；该端点暂未写入 docs/API.md） */
export async function getAuthors() {
  return USE_MOCK ? mockGetAuthors() : realGetAuthors()
}

/** 按 id 获取单名作家：GET /api/authors/{id}（未找到返回 null） */
export async function getAuthorById(id) {
  return USE_MOCK ? mockGetAuthorById(id) : realGetAuthorById(id)
}

/** 按 id 获取单条地点：GET /api/places/{id}（未找到返回 null；用于作者页出生地定位等单点查询） */
export async function getPlaceById(id) {
  if (USE_MOCK) {
    const c = literaryCities.find(x => String(x.id) === String(id))
    return c
      ? { id: c.id, name: c.city, place_type: 'city', is_fictional: 0, latitude: c.lat, longitude: c.lng, country: c.country, region: null, description: c.summary ?? null }
      : null
  }
  try {
    return await request(`/api/places/${id}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

/**
 * 按需获取单座地图城市的关联作品（城市弹窗打开时调用）：
 * Mock：直接取城市数据内 authors[].works（无网络请求）；
 * 真实：GET /api/places/{id}/literature，成功结果缓存（同一地点不重复请求），失败抛错可重试
 * @returns {Promise<Array<{ id: number|null, title: string }>>}
 */
export async function getPlaceLiterature(placeId) {
  if (USE_MOCK) {
    const c = literaryCities.find(x => String(x.id) === String(placeId))
    const out = []
    for (const a of (c && c.authors) || []) for (const t of a.works || []) out.push({ id: null, title: t })
    return out
  }
  const items = await getPlaceLiteratureRaw(placeId)
  return items.map(i => ({ id: i.book && i.book.id, title: (i.book && i.book.title) || '' })).filter(w => w.title)
}

/** 获取个人书架书籍列表 */
export async function getShelfBooks() {
  return USE_MOCK ? mockGetShelfBooks() : realGetShelfBooks()
}

/** 获取个人文学足迹（只含已读作品关联的真实有效坐标地点） */
export async function getFootprint() {
  return USE_MOCK ? mockGetFootprint() : realGetFootprint()
}

/**
 * 获取书架统计
 * Mock：按传入列表实时统计；真实：GET /api/reading/statistics
 * @returns {Promise<{ total: number, want_to_read: number, reading: number, finished: number }>}
 */
export async function getShelfStats(books) {
  return USE_MOCK ? mockGetShelfStats(books) : realGetShelfStats()
}

/**
 * 按书籍状态统计数量（想读 / 在读 / 已读）
 * 状态值与后端一致：want_to_read / reading / finished
 */
export function countShelfStats(books) {
  const s = { want_to_read: 0, reading: 0, finished: 0 }
  for (const b of books || []) {
    const st = normalizeStatus(b.status)
    if (Object.prototype.hasOwnProperty.call(s, st)) s[st]++
  }
  return s
}

/**
 * 清洗搜索关键词：去首尾空格、连续空白合并为单个空格（与后端归一化规则一致）
 */
export function normalizeSearchKeyword(keyword) {
  return (keyword || '').replace(/\s+/g, ' ').trim()
}

/**
 * 搜索文学相关内容（导航栏分类搜索，统一模糊检索）
 * 真实模式：GET /api/search?q= —— 后端统一模糊搜索作品/作者/地点/国家/文学流派，
 *           返回分组结果（含相关度排序与少量拼写容错，容错为兜底策略）
 * Mock 模式：在本地演示数据上做包含匹配（大小写不敏感），不编造数据
 */
export async function searchLiterature(keyword) {
  const q = normalizeSearchKeyword(keyword)
  if (!q) return []
  if (USE_MOCK) {
    const lq = q.toLowerCase()
    const groups = { city: [], country: [], author: [], work: [] }
    for (const c of literaryCities) {
      if (c.city.toLowerCase().includes(lq)) groups.city.push({ id: c.id, title: c.city, sub: c.country, cityId: c.id })
      if (c.country.toLowerCase().includes(lq)) groups.country.push({ id: 'cty-' + c.id, title: c.country, sub: '城市 · ' + c.city, cityId: c.id })
      for (const a of c.authors) {
        if (a.name.toLowerCase().includes(lq)) groups.author.push({ id: a.name + c.id, title: a.name, sub: a.works.join(' · ') + ' · ' + c.city, cityId: c.id })
        for (const w of a.works) {
          if (w.toLowerCase().includes(lq)) groups.work.push({ id: w + c.id, title: w, sub: a.name + ' · ' + c.city, cityId: c.id })
        }
      }
    }
    for (const b of shelfBooks) {
      if (b.title.toLowerCase().includes(lq)) groups.work.push({ id: 'book-' + b.id, title: b.title, sub: b.author + ' · ' + b.country, bookId: b.id })
    }
    const flat = []
    const order = [['城市', groups.city], ['国家', groups.country], ['作家', groups.author], ['作品', groups.work]]
    for (const [cat, arr] of order) {
      for (const it of arr.slice(0, 4)) flat.push({ ...it, cat })
    }
    return flat.slice(0, 10)
  }

  // 真实模式：统一模糊搜索接口（作品/作者/地点/国家/流派一次返回）
  const res = await request(`/api/search${qs({ q, per_group: 5 })}`).catch(() => null)
  if (!res || !res.groups) return []
  const g = res.groups
  const flat = []

  // 城市/地点（国家类型的地点已由后端归入 countries 分组）
  for (const p of (g.places || []).slice(0, 3)) {
    const subParts = [p.country, p.region].filter(Boolean)
    if (p.is_fictional) subParts.unshift('虚构地点')
    flat.push({ id: 'plc-' + p.id, title: p.name, sub: subParts.join(' · '), cityId: p.id, cat: '城市' })
  }
  // 国家（有 place_id 可定位地图；否则点击进入作品页按国家筛选）
  for (const c of (g.countries || []).slice(0, 2)) {
    flat.push({
      id: 'cty-' + (c.place_id ?? c.name),
      title: c.name,
      sub: (c.work_count ? c.work_count + ' 部相关作品' : '国家'),
      cityId: c.place_id ?? undefined,
      countryName: c.place_id ? undefined : c.name,
      cat: '国家'
    })
  }
  // 作家（点击进入作家详情页）
  for (const a of (g.authors || []).slice(0, 2)) {
    flat.push({
      id: 'au-' + a.id,
      title: a.name,
      sub: [a.nationality, (a.work_titles || []).slice(0, 2).join(' · ')].filter(Boolean).join(' · '),
      authorId: a.id,
      cat: '作家'
    })
  }
  // 作品（点击定位地图上的作品）
  for (const w of (g.works || []).slice(0, 3)) {
    flat.push({ id: 'book-' + w.id, title: w.title, sub: (w.authors || []).join(' · '), bookId: w.id, cat: '作品' })
  }
  // 文学类型（点击进入作品页按类型筛选）
  for (const ge of (g.genres || []).slice(0, 2)) {
    flat.push({ id: 'gn-' + ge.id, title: ge.name, sub: ge.work_count + ' 部作品', genreName: ge.name, cat: '类型' })
  }
  // 标记是否为容错兜底结果（供界面提示"已近似匹配"）
  if (res.fuzzy_fallback) {
    for (const it of flat) it.fuzzyFallback = true
  }
  return flat.slice(0, 12)
}

/**
 * 发送 AI 对话消息
 * 真实模式：POST /api/agent/chat，只传 { message }（第一版无历史/上下文字段）
 * Mock 模式：直接抛错，由页面显示"接口待接入"，不伪造 AI 回复
 * @returns {Promise<{ reply: string }>}
 */
export async function sendChatMessage({ message }) {
  const text = (message || '').trim()
  if (!text) throw new ApiError(422, '消息内容不能为空')
  if (USE_MOCK) throw new Error('AI 服务即将上线，当前暂无法回复消息')
  const data = await request('/api/agent/chat', { method: 'POST', body: { message: text }, timeout: 60000 })
  if (!data || typeof data.reply !== 'string') throw new ApiError(500, 'AI 返回内容为空或格式不正确')
  return { reply: data.reply }
}

// ---------- 书架写操作（真实模式由 bookshelfStore 调用） ----------

/** 按书名查找已有作品（真实模式） */
export async function findOrCreateBook(title) {
  const existing = await findBookByTitleExact(title)
  if (existing) return existing
  return request('/api/books', { method: 'POST', body: { title } })
}

/** 添加阅读记录：POST /api/reading（不传 user_id，由后端挂在演示用户下） */
export function addReading({ book_id, status }) {
  return request('/api/reading', { method: 'POST', body: { book_id, status } })
}

/** 修改阅读记录：PATCH /api/reading/{record_id}（不传 book_id） */
export function updateReading(recordId, patch) {
  return request(`/api/reading/${recordId}`, { method: 'PATCH', body: patch })
}

/** 删除阅读记录：DELETE /api/reading/{record_id} */
export function deleteReading(recordId) {
  return request(`/api/reading/${recordId}`, { method: 'DELETE' })
}

// ---------- 自主添加书籍（自定义作品，AI 辅助） ----------

/** AI 识别作品草案（只读不写库）：POST /api/custom-books/lookup
 *  AI 调用较慢（可能数十秒），这里独立设置 90s 超时，不影响其他接口的默认超时 */
export function lookupCustomBook(title, author) {
  const body = { title }
  const a = (author || '').trim()
  if (a) body.author = a
  return request('/api/custom-books/lookup', { method: 'POST', body, timeout: 90000 })
}

/** 保存自定义作品（用户确认后的草案）：POST /api/custom-books
 *  成功返回 201 与含 id 的完整作品详情；同名同作者重复返回 409 */
export function createCustomBook(payload) {
  return request('/api/custom-books', { method: 'POST', body: payload })
}

/** 删除自定义作品（仅 source='custom'，公共作品后端返回 403）：DELETE /api/custom-books/{id} */
export function deleteCustomBook(id) {
  return request(`/api/custom-books/${id}`, { method: 'DELETE' })
}
