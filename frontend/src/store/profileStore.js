// 用户资料数据模块：个人中心的唯一数据源
// - localStorage 持久化（键名 literary-atlas-profile），刷新后不丢失
// - 组件不直接操作 localStorage，统一通过本模块读写
// - ⚠️ 当前为本地演示资料，不代表真实登录用户；未来接入后端时
//   只需把 loadProfile / saveProfile 换成接口请求，组件层零改动
import { ref } from 'vue'

const STORAGE_KEY = 'literary-atlas-profile'

// 预设头像标识（具体图形由页面层渲染为金色简笔画 SVG：蓝底金线）
export const AVATARS = ['compass', 'book', 'globe', 'map', 'quill', 'telescope']

// 默认演示资料（joinedAt 为演示数据，非可靠注册时间）
const DEFAULT_PROFILE = {
  nickname: '星际读者',
  bio: '在文学星图上，一格一格点亮我读过的世界。',
  avatar: 'compass',
  joinedAt: '2026-11-03'
}

// 模块级共享 ref：个人中心与未来其他引用处共享同一份数据
const profile = ref({ ...DEFAULT_PROFILE })

// 从 localStorage 恢复，没有则用默认演示资料
function loadProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const saved = JSON.parse(raw)
      // 兼容旧缓存：头像标识不在预设列表（如早期 emoji 版本）时回退默认
      if (saved.avatar && !AVATARS.includes(saved.avatar)) saved.avatar = DEFAULT_PROFILE.avatar
      profile.value = { ...DEFAULT_PROFILE, ...saved }
    }
  } catch (e) {
    profile.value = { ...DEFAULT_PROFILE }
  }
}

// 保存当前资料到 localStorage
function saveProfile() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile.value))
}

// 初始化（幂等）：已加载过则不再重复读
let inited = false
export function initProfile() {
  if (!inited) {
    loadProfile()
    inited = true
  }
}

// 更新资料：校验昵称非空，成功返回 true，失败返回 false
export function updateProfile(patch) {
  if (!patch.nickname || !patch.nickname.trim()) return false
  profile.value = {
    ...profile.value,
    nickname: patch.nickname.trim(),
    bio: (patch.bio || '').trim(),
    avatar: patch.avatar || profile.value.avatar
  }
  saveProfile()
  return true
}

// 重置为默认演示资料（编辑取消时若从未保存过可用）
export function resetProfile() {
  profile.value = { ...DEFAULT_PROFILE }
  saveProfile()
}

export { profile }
