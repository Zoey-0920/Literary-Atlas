<script setup>
// AI 文学助手页：完整聊天界面
// - 当前 USE_MOCK = true，后端 AI 接口未接入：发送后由 API 层抛错，页面显示错误 + 重试
// - 不伪造 AI 回复；页面顶部有常驻"演示/接口待接入"提示条
// - 请求时附带的个人上下文仅含已读/在读/想读书名数组，来自 bookshelfStore，不发送其他个人信息
import { ref, reactive, onMounted, nextTick } from 'vue'
import { sendChatMessage, USE_MOCK } from '../api'
import { books, initBookshelf } from '../store/bookshelfStore'

// 推荐问题（点击直接发送）
const SUGGESTIONS = [
  '《百年孤独》与哥伦比亚的关系是什么？',
  '巴黎在世界文学中有哪些代表作品？',
  '根据我的已读书籍推荐下一本书。',
  '比较《1984》和《美丽新世界》的文学主题。'
]

const draft = ref('')          // 输入框内容
const sending = ref(false)     // 请求进行中（防重复提交）
const listEl = ref(null)       // 消息列表 DOM（用于滚动）
// 对话记录：{ role: 'user'|'ai', text, state: 'ok'|'loading'|'error' }
const messages = reactive([])

onMounted(() => { initBookshelf() }) // 幂等：确保个人上下文数据就绪

// 个人阅读上下文：仅书名数组（不含其他信息），随请求发送供 AI 参考
function shelfContext() {
  const by = s => books.value.filter(b => b.status === s).map(b => b.title)
  return { read: by('read'), reading: by('reading'), want: by('want') }
}

// 近几轮成功对话（作为 history 传给后端，格式待与成员 B 确认）
function recentHistory() {
  return messages
    .filter(m => m.state === 'ok')
    .slice(-6)
    .map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }))
}

// 发送消息；pushUser=false 时用于"重试"，不再重复添加用户气泡
async function send(text, pushUser = true) {
  const t = (text || '').trim()
  if (!t || sending.value) return   // 空消息 / 请求中：直接忽略
  if (pushUser) messages.push({ role: 'user', text: t, state: 'ok' })
  draft.value = ''                  // 发送后清空输入框
  sending.value = true
  scrollBottom()
  // AI 回复气泡：先显示加载中
  const aiMsg = reactive({ role: 'ai', text: '', state: 'loading' })
  messages.push(aiMsg)
  try {
    const res = await sendChatMessage({
      message: t,
      history: recentHistory(),
      context: shelfContext()
    })
    aiMsg.text = res.reply
    aiMsg.state = 'ok'
  } catch (e) {
    aiMsg.text = e.message || '请求失败，请稍后重试'
    aiMsg.state = 'error'
  } finally {
    sending.value = false
    scrollBottom()
  }
}

// 重试：找到错误气泡前最近的用户消息，移除错误气泡后重新请求
function retry(msg) {
  const i = messages.indexOf(msg)
  for (let j = i - 1; j >= 0; j--) {
    if (messages[j].role === 'user') {
      const text = messages[j].text
      messages.splice(i, 1)
      send(text, false)
      return
    }
  }
}

// Enter 发送、Shift+Enter 换行
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send(draft.value)
  }
}

// 新消息后自动滚动到底部
function scrollBottom() {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <h1 class="page-title">AI 阅读探索</h1>
      <p class="intro">与 AI 助手聊聊作品、作家与阅读地图，它会结合你的阅读记录给出回答。</p>
    </div>

    <!-- 服务状态提示：AI 接口未接入期间显示（正式文案，不暴露开发细节） -->
    <div v-if="USE_MOCK" class="demo-banner">
      AI 智能问答服务即将上线，当前暂无法回复消息，敬请期待。
    </div>

    <div class="chat-box">
      <!-- 消息列表 -->
      <div ref="listEl" class="msg-list">
        <!-- 空对话：欢迎语 + 推荐问题 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-mark">✦</div>
          <p class="welcome-title">你好，我是你的阅读探索助手</p>
          <p class="welcome-sub">可以从下面的问题开始，也可以直接输入任何文学话题：</p>
          <div class="sug-grid">
            <button v-for="q in SUGGESTIONS" :key="q" class="sug-card" @click="send(q)">
              {{ q }}
            </button>
          </div>
        </div>

        <!-- 消息气泡 -->
        <template v-for="(m, i) in messages" :key="i">
          <div :class="['bubble', m.role === 'user' ? 'bubble-user' : 'bubble-ai']">
            <template v-if="m.role === 'user'">{{ m.text }}</template>
            <template v-else>
              <span v-if="m.state === 'loading'" class="loading-dots">正在思考…</span>
              <template v-else-if="m.state === 'error'">
                <span class="err-text">{{ m.text }}</span>
                <button class="retry-btn" @click="retry(m)">重试</button>
              </template>
              <template v-else>{{ m.text }}</template>
            </template>
          </div>
        </template>
      </div>

      <!-- 输入区 -->
      <div class="input-row">
        <textarea
          v-model="draft"
          class="chat-input"
          rows="2"
          placeholder="输入你的问题…（Enter 发送，Shift + Enter 换行）"
          @keydown="onKeydown"
        ></textarea>
        <button
          class="btn btn-gold send-btn"
          :disabled="sending || draft.trim() === ''"
          @click="send(draft)"
        >
          {{ sending ? '发送中…' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.intro { margin-top: 10px; font-size: 14px; color: var(--muted); }

/* 演示状态提示条 */
.demo-banner {
  margin-top: 18px; padding: 10px 14px;
  border: 1px dashed rgba(212, 180, 119, .45); border-radius: 10px;
  background: rgba(212, 180, 119, .08);
  font-size: 13px; color: var(--accent-soft);
}

/* 聊天主体 */
.chat-box {
  margin-top: 18px; height: calc(100vh - 300px); min-height: 400px;
  display: flex; flex-direction: column;
  border: 1px solid var(--line); border-radius: 12px;
  background: var(--bg-card); overflow: hidden;
}
.msg-list { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }

/* 空对话欢迎区 */
.welcome { margin: auto; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.welcome-mark { font-size: 30px; color: var(--accent-soft); }
.welcome-title { font-family: Georgia, serif; font-size: 19px; color: var(--ink); }
.welcome-sub { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
.sug-grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 280px)); gap: 10px; }
.sug-card {
  padding: 10px 14px; text-align: left; font-size: 13px; line-height: 1.5;
  color: var(--ink); background: rgba(212, 180, 119, .06);
  border: 1px solid var(--line); border-radius: 10px; cursor: pointer;
}
.sug-card:hover { border-color: var(--accent); color: var(--accent); }

/* 气泡 */
.bubble { max-width: 72%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.bubble-user {
  align-self: flex-end; color: var(--ink);
  background: rgba(212, 180, 119, .16); border: 1px solid rgba(212, 180, 119, .4);
  border-bottom-right-radius: 4px;
}
.bubble-ai {
  align-self: flex-start; color: var(--ink);
  background: var(--bg-sidebar); border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
}

/* 加载 / 错误 / 重试 */
.loading-dots { color: var(--muted); }
.err-text { color: #d98a7a; }
.retry-btn {
  margin-left: 10px; padding: 2px 12px; font-size: 12px; cursor: pointer;
  color: var(--accent-soft); background: transparent;
  border: 1px solid rgba(212, 180, 119, .5); border-radius: 999px;
}
.retry-btn:hover { background: rgba(212, 180, 119, .15); }

/* 输入区 */
.input-row { display: flex; gap: 10px; padding: 14px; border-top: 1px solid var(--line); background: var(--bg-sidebar); }
.chat-input {
  flex: 1; resize: none; padding: 10px 12px; font-size: 14px; line-height: 1.5;
  color: var(--ink); background: var(--bg-card);
  border: 1px solid var(--line); border-radius: 10px; outline: none;
}
.chat-input:focus { border-color: rgba(212, 180, 119, .55); }
.send-btn { align-self: flex-end; min-width: 84px; }
.send-btn:disabled { opacity: .45; cursor: not-allowed; }
</style>