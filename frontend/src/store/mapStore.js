// 全局共享状态：地图模式、当前选中标记、定位请求
import { reactive } from 'vue'

export const mapStore = reactive({
  mode: 'overview',   // 'overview' 总览地图 | 'personal' 个人地图
  selectedId: 'paris', // 当前打开信息卡的标记 id（默认打开巴黎，与参考图一致）
  focusRequest: null  // { kind, id, ts } 用于搜索/书架点击后的定位
})

// 切换地图模式（会清除当前选中的标记）
export function setMode(mode) {
  if (mapStore.mode !== mode) {
    mapStore.mode = mode
    mapStore.selectedId = null
  }
}

// 请求地图定位到某个目标：kind 为 'city' 或 'book'
export function focusTarget(kind, id) {
  mapStore.focusRequest = { kind, id, ts: Date.now() }
}