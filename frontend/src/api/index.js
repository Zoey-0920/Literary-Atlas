// 后端接口请求封装
// 后续接入队友的 FastAPI 后端时，只需在这个文件里对接即可

const BASE_URL = 'http://localhost:8000' // 后端地址（队友提供）

// 是否使用模拟数据：后端尚未完成阶段设为 true，接入后端后改为 false
export const USE_MOCK = true

/**
 * 通用请求函数
 * @param {string} path  接口路径，例如 '/api/books'
 * @param {object} options fetch 的配置项（method、body 等）
 * @returns {Promise<any>} 返回解析后的 JSON 数据
 */
export async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!res.ok) {
    throw new Error(`请求失败：${res.status}`)
  }
  return res.json()
}