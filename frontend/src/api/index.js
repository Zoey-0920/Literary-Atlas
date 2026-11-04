// =============================================================
// 统一 API 数据访问层
// - USE_MOCK = true  ：当前阶段，全部从本地模拟数据（./mock.js）读取
// - USE_MOCK = false ：前后端联调后，自动改走 request() 请求真实后端
// 页面和组件只 import 本文件导出的函数，不再直接依赖 mock.js
// =============================================================
import { literaryCities, shelfBooks, mockBooks, mockAuthors } from './mock'

const BASE_URL = 'http://localhost:8000' // 后端地址（占位，待与成员 B 确认）
export const USE_MOCK = true

// 后端接口路径占位表：路径与响应格式尚未与成员 B 确认，联调前需按真实接口文档修改
const ENDPOINTS = {
  cities: '/api/cities',
  works: '/api/works',
  workDetail: '/api/works', // 作品详情：调用时拼 /:id
  authors: '/api/authors',
  shelfBooks: '/api/bookshelf',
  shelfStats: '/api/bookshelf/stats',
  chat: '/api/ai/chat'      // ⚠️ AI 对话：路径与请求/响应结构均待与成员 B 确认，联调前需按接口文档修改
}

/**
 * 通用请求函数（接入真实后端后使用）
 * @param {string} path 接口路径
 * @param {object} options fetch 配置项（method、body 等）
 * @returns {Promise<any>} 返回解析后的 JSON 数据
 */
export async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!res.ok) throw new Error(`请求失败：${res.status}`)
  return res.json()
}

// 通用分发：Mock 阶段直接返回本地数据；USE_MOCK=false 时改走真实接口
async function dispatch(name, mockData) {
  if (USE_MOCK) return mockData
  return request(ENDPOINTS[name])
}

/** 获取全部文学城市（含其作家、代表作品等字段，结构与地图使用一致） */
export async function getCities() {
  return dispatch('cities', literaryCities)
}

/** 获取文学作品列表 */
export async function getWorks() {
  return dispatch('works', mockBooks)
}

/** 按 id 获取单部作品（未找到返回 null） */
export async function getWorkById(id) {
  if (USE_MOCK) return mockBooks.find(w => String(w.id) === String(id)) || null
  return request(ENDPOINTS.workDetail + '/' + id)
}

/** 获取作家数据 */
export async function getAuthors() {
  return dispatch('authors', mockAuthors)
}

/** 按 id 获取单名作家（未找到返回 null） */
export async function getAuthorById(id) {
  if (USE_MOCK) return mockAuthors.find(a => String(a.id) === String(id)) || null
  return request(ENDPOINTS.authors + '/' + id)
}

/** 获取个人书架书籍列表 */
export async function getShelfBooks() {
  return dispatch('shelfBooks', shelfBooks)
}

/**
 * 按书籍状态统计数量（已读 / 在读 / 想读）
 * @param {Array} books 书籍列表
 * @returns {{ read: number, reading: number, want: number }}
 */
export function countShelfStats(books) {
  const s = { read: 0, reading: 0, want: 0 }
  for (const b of books) {
    if (Object.prototype.hasOwnProperty.call(s, b.status)) s[b.status]++
  }
  return s
}

/**
 * 获取书架统计
 * Mock 阶段：按当前书籍列表实时统计（不再使用写死的统计数字）
 * 接入后端后：改走 /api/bookshelf/stats 接口
 * @param {Array} [books] 当前书籍列表，缺省时按 mock 列表统计
 */
export async function getShelfStats(books) {
  if (USE_MOCK) return countShelfStats(books || shelfBooks)
  return request(ENDPOINTS.shelfStats)
}

/**
 * 搜索文学相关内容（城市 / 国家 / 作家 / 作品，含书架书籍）
 * @param {string} keyword 搜索关键词
 * @returns {Promise<Array>} 分类结果列表，每项 { id, cat, title, sub, cityId? , bookId? }
 */
export async function searchLiterature(keyword) {
  const q = (keyword || '').trim().toLowerCase()
  if (!q) return []
  const groups = { city: [], country: [], author: [], work: [] }

  for (const c of literaryCities) {
    if (c.city.toLowerCase().includes(q)) groups.city.push({ id: c.id, title: c.city, sub: c.country, cityId: c.id })
    if (c.country.toLowerCase().includes(q)) groups.country.push({ id: 'cty-' + c.id, title: c.country, sub: '城市 · ' + c.city, cityId: c.id })
    for (const a of c.authors) {
      if (a.name.toLowerCase().includes(q)) groups.author.push({ id: a.name + c.id, title: a.name, sub: a.works.join(' · ') + ' · ' + c.city, cityId: c.id })
      for (const w of a.works) {
        if (w.toLowerCase().includes(q)) groups.work.push({ id: w + c.id, title: w, sub: a.name + ' · ' + c.city, cityId: c.id })
      }
    }
  }
  for (const b of shelfBooks) {
    if (b.title.toLowerCase().includes(q)) groups.work.push({ id: 'book-' + b.id, title: b.title, sub: b.author + ' · ' + b.country, bookId: b.id })
  }

  const flat = []
  const order = [['城市', groups.city], ['国家', groups.country], ['作家', groups.author], ['作品', groups.work]]
  for (const [cat, arr] of order) {
    for (const it of arr.slice(0, 4)) flat.push({ ...it, cat })
  }
  return flat.slice(0, 10)
}

/**
 * 发送 AI 对话消息（接口占位）
 *
 * ⚠️ 以下请求 / 响应结构均为前端建议草案，最终以成员 B 提供的接口文档为准：
 * @param {object} payload
 *   - message : string                      用户本次输入（必填）
 *   - history : Array<{ role, content }>    近几轮对话记录（可选，供 AI 上下文）
 *   - context : { read, reading, want }     个人阅读上下文，仅含书名数组，不含其他个人信息
 * @returns {Promise<{ reply: string }>} 建议响应结构：{ reply: 'AI 回复文本' }
 *
 * 当前 USE_MOCK = true，没有真实 AI 后端：
 * 不使用关键词匹配或预设答案伪装 AI 回复，直接抛错，由页面显示"接口待接入"提示。
 */
export async function sendChatMessage(payload) {
  if (USE_MOCK) throw new Error('AI 服务即将上线，当前暂无法回复消息')
  return request(ENDPOINTS.chat, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}