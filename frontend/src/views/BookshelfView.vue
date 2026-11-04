<script setup>
// 完整书架页：添加书籍 / 修改阅读状态 / 评分·进度·笔记编辑 / 删除书籍 / 三种状态筛选
import { ref, computed, onMounted } from 'vue'
import {
  books, loading, error, shelfStats, statsError,
  initBookshelf, reloadBookshelf, addBook, updateBookStatus, updateBookMeta, removeBook
} from '../store/bookshelfStore'

const filter = ref('all')
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'finished', label: '已读' },
  { key: 'reading', label: '在读' },
  { key: 'want_to_read', label: '想读' }
]

// 状态下拉顺序与阅读流程一致：想读 → 在读 → 已读（状态值与后端一致）
const STATUS_OPTIONS = [
  { value: 'want_to_read', label: '想读' },
  { value: 'reading', label: '在读' },
  { value: 'finished', label: '已读' }
]
const STATUS_TEXT = { finished: '已读', reading: '在读', want_to_read: '想读' }

// 点击状态标签：在想读 → 在读 → 已读 → 想读 之间循环切换
const STATUS_ORDER = ['want_to_read', 'reading', 'finished']
async function cycleStatus(b) {
  const i = STATUS_ORDER.indexOf(b.status)
  try {
    await updateBookStatus(b.id, STATUS_ORDER[(i + 1) % STATUS_ORDER.length])
  } catch (e) {
    alert(e && e.message ? e.message : '更新阅读状态失败')
  }
}

// 与首页侧栏共用同一份 store 数据：这里任何操作，侧栏与统计都会自动同步
// 统计来自 store（真实模式 GET /api/reading/statistics，失败保留最近一次有效结果）
onMounted(() => { initBookshelf() })

const filteredBooks = computed(() =>
  filter.value === 'all' ? books.value : books.value.filter(b => b.status === filter.value)
)

function coverStyle(b) {
  return { background: `linear-gradient(150deg, ${b.cover[0]}, ${b.cover[1]})` }
}

// ---- 添加书籍 ----
const showForm = ref(false)
const adding = ref(false)
const form = ref({ title: '', author: '', status: 'want_to_read' })
async function submitAdd() {
  const title = form.value.title.trim()
  const author = form.value.author.trim()
  if (!title || !author) { alert('请填写书名和作者'); return }
  adding.value = true
  try {
    await addBook({ title, author, status: form.value.status })
    form.value = { title: '', author: '', status: 'want_to_read' }
    showForm.value = false
  } catch (e) {
    // 真实模式：409（已在书架）/ 422 / 网络失败等，直接展示后端信息，不回退 Mock
    alert(e && e.message ? e.message : '添加失败，请稍后重试')
  } finally {
    adding.value = false
  }
}

// ---- 阅读信息编辑（评分 / 进度 / 笔记） ----
const editingId = ref(null)              // 当前展开编辑的阅读记录 id（record_id）
const draft = ref({ rating: '', progress: '', note: '' })
const savingMeta = ref(false)
const metaMsg = ref('')

// 把记录当前值转成表单草稿（null → '' 便于控件绑定）
function metaDraft(b) {
  return {
    rating: b.rating == null ? '' : String(b.rating),
    progress: b.progress == null ? '' : String(b.progress),
    note: b.note == null ? '' : b.note
  }
}

function toggleMeta(b) {
  if (editingId.value === b.id) { editingId.value = null; return }
  editingId.value = b.id
  draft.value = metaDraft(b)
  metaMsg.value = ''
}

async function saveMeta(b) {
  const d = draft.value
  const cur = metaDraft(b)
  // 校验填写值的范围（允许为空）
  if (d.rating !== '' && !(Number(d.rating) >= 1 && Number(d.rating) <= 5)) { metaMsg.value = '评分需在 1～5 之间'; return }
  if (d.progress !== '') {
    const p = Number(d.progress)
    if (!Number.isFinite(p) || p < 0 || p > 100) { metaMsg.value = '进度需在 0～100 之间'; return }
  }
  // 只提交实际修改的字段：原值非空且被清空 → 提交 null；本来就为空且仍为空 → 不提交
  const patch = {}
  if (d.rating !== cur.rating) patch.rating = d.rating === '' ? null : Number(d.rating)
  if (d.progress !== cur.progress) patch.progress = d.progress === '' ? null : Number(d.progress)
  if (d.note !== cur.note) patch.note = d.note === '' ? null : d.note
  if (Object.keys(patch).length === 0) { metaMsg.value = '内容没有变化'; return }

  savingMeta.value = true
  metaMsg.value = ''
  try {
    await updateBookMeta(b.id, patch)   // b.id 是阅读记录 id
    metaMsg.value = '已保存'            // 失败时不进入这里，草稿保留
  } catch (e) {
    metaMsg.value = e && e.message ? e.message : '保存失败，请稍后重试'
  } finally {
    savingMeta.value = false
  }
}

// ---- 删除（简单确认） ----
async function onDelete(b) {
  if (!window.confirm(`确定要删除《${b.title}》吗？`)) return
  try {
    await removeBook(b.id)
  } catch (e) {
    alert(e && e.message ? e.message : '删除失败，请稍后重试')
  }
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <p class="eyebrow">Literary Atlas</p>
      <div class="head-row">
        <h1 class="page-title">我的书架</h1>
        <button class="btn btn-gold" @click="showForm = !showForm">＋ 添加书籍</button>
      </div>
    </div>

    <!-- 统计：真实模式读取 GET /api/reading/statistics；失败时保留最近一次有效结果并提示 -->
    <p v-if="statsError" class="stats-warn">统计暂时不可用（显示最近一次结果）：{{ statsError }}</p>
    <div class="stats">
      <div class="stat">
        <span class="stat-num">{{ shelfStats.total }}</span>
        <span class="stat-lab">总藏书</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ shelfStats.finished }}</span>
        <span class="stat-lab">已读</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ shelfStats.reading }}</span>
        <span class="stat-lab">在读</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ shelfStats.want_to_read }}</span>
        <span class="stat-lab">想读</span>
      </div>
    </div>

    <!-- 添加书籍表单 -->
    <form v-if="showForm" class="add-form" @submit.prevent="submitAdd">
      <label>书名
        <input v-model="form.title" type="text" placeholder="如：百年孤独" />
      </label>
      <label>作者
        <input v-model="form.author" type="text" placeholder="如：加西亚·马尔克斯" />
      </label>
      <label>状态
        <select v-model="form.status">
          <option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </label>
      <div class="form-actions">
        <button type="submit" class="btn btn-gold btn-sm" :disabled="adding">{{ adding ? '添加中…' : '确认添加' }}</button>
        <button type="button" class="btn btn-ghost-dark btn-sm" @click="showForm = false">取消</button>
      </div>
    </form>

    <!-- 状态筛选页签 -->
    <div class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: filter === t.key }"
        @click="filter = t.key"
      >
        {{ t.label }} <span class="tab-num">{{ t.key === 'all' ? shelfStats.total : shelfStats[t.key] }}</span>
      </button>
    </div>

    <!-- 加载 / 错误状态：真实模式后端不可达时提示，可重试，不静默回退 Mock -->
    <p v-if="loading && books.length === 0" class="empty">正在加载书架…</p>
    <div v-else-if="error && books.length === 0" class="err-box">
      <p class="err-text">书架加载失败：{{ error }}</p>
      <button class="btn btn-ghost-dark btn-sm" @click="reloadBookshelf">重试</button>
    </div>

    <!-- 书籍列表 -->
    <ul v-else class="book-list">
      <li v-for="b in filteredBooks" :key="b.id" class="book" :class="{ open: editingId === b.id }">
        <div class="book-main">
          <span class="cover" :style="coverStyle(b)">{{ b.title.slice(0, 1) }}</span>
          <div class="meta">
            <span class="book-title">{{ b.title }}</span>
            <span class="book-author">
              {{ b.author || '作者未知' }}
              <span v-if="b.rating != null" class="meta-hint">· {{ b.rating }} 分</span>
              <span v-if="b.progress != null" class="meta-hint">· {{ b.progress }}%</span>
            </span>
          </div>
          <button
            class="status"
            :class="b.status"
            type="button"
            title="点击切换阅读状态"
            @click="cycleStatus(b)"
          >
            <svg v-if="b.status === 'finished'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>
            <svg v-else-if="b.status === 'want_to_read'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>
            <span>{{ STATUS_TEXT[b.status] || b.status }}</span>
          </button>
          <button
            class="edit-toggle"
            :class="{ active: editingId === b.id }"
            type="button"
            title="编辑评分 / 进度 / 笔记"
            @click="toggleMeta(b)"
          >✎</button>
          <button class="del" title="删除这本书" @click="onDelete(b)">×</button>
        </div>

        <!-- 可折叠阅读信息编辑区：评分 1-5（可空）/ 进度 0-100（可空）/ 笔记（可空） -->
        <div v-if="editingId === b.id" class="meta-edit">
          <div class="meta-edit-row">
            <label>评分
              <select v-model="draft.rating">
                <option value="">未评分</option>
                <option v-for="n in 5" :key="n" :value="String(n)">{{ n }} 分</option>
              </select>
            </label>
            <label>进度（%）
              <input v-model="draft.progress" type="number" min="0" max="100" placeholder="0-100" />
            </label>
          </div>
          <label class="meta-edit-note">笔记
            <textarea v-model="draft.note" rows="2" maxlength="200" placeholder="记一点想法（可留空）"></textarea>
          </label>
          <div class="meta-edit-actions">
            <button type="button" class="btn btn-gold btn-sm" :disabled="savingMeta" @click="saveMeta(b)">
              {{ savingMeta ? '保存中…' : '保存' }}
            </button>
            <button type="button" class="btn btn-ghost-dark btn-sm" @click="editingId = null">收起</button>
            <span class="meta-msg" :class="{ ok: metaMsg === '已保存' }">{{ metaMsg }}</span>
          </div>
        </div>
      </li>
    </ul>

    <p v-if="!loading && !error && filteredBooks.length === 0" class="empty">这一栏还没有书，点右上角「添加书籍」试试。</p>

    <p class="back">
      <router-link to="/" class="btn btn-ghost-dark">返回世界地图</router-link>
    </p>
  </div>
</template>

<style scoped>
.head-row {
  display: flex; align-items: flex-end; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-top: 8px;
}
.head-row .page-title { margin-top: 0; }

.btn-sm { height: 34px; padding: 0 14px; font-size: 13px; }

/* 统计卡片 */
.stats {
  display: flex; gap: 14px; margin-top: 22px; flex-wrap: wrap;
}
.stat {
  flex: 1; min-width: 120px; display: flex; flex-direction: column; gap: 4px;
  padding: 14px 16px; border: 1px solid rgba(210, 175, 110, .3); border-radius: 12px;
  background: rgba(6, 12, 22, .78);
}
.stat-num { font-family: Georgia, serif; font-size: 26px; color: var(--ink); }
.stat-lab { font-size: 12px; color: var(--muted); letter-spacing: .08em; }

/* 添加表单 */
.add-form {
  margin-top: 18px; padding: 16px; border: 1px solid rgba(212, 180, 119, .35);
  border-radius: 12px; background: var(--bg-sidebar);
  display: flex; flex-direction: column; gap: 12px;
}
.add-form label {
  display: flex; flex-direction: column; gap: 6px;
  font-size: 12px; color: var(--muted);
}
.add-form input, .add-form select {
  height: 36px; padding: 0 10px; font-size: 14px; color: var(--ink);
  background: #0A1420; border: 1px solid var(--line); border-radius: 10px; outline: none;
}
.add-form input:focus, .add-form select:focus { border-color: var(--accent); }
.form-actions { display: flex; gap: 10px; }

/* 页签 */
.tabs { display: flex; gap: 10px; margin: 26px 0 14px; flex-wrap: wrap; }
.tab {
  height: 32px; padding: 0 16px; font-size: 13px; border-radius: 999px;
  border: 1px solid rgba(210, 175, 110, .45); color: #C9AB72; background: rgba(3, 6, 12, .85);
  cursor: pointer; transition: all .15s;
}
.tab:hover { border-color: rgba(246, 225, 170, .8); color: #E9D5A0; }
.tab.active { background: rgba(3, 6, 12, .92); border-color: rgba(246, 225, 170, .95); color: #F0DCAB; box-shadow: 0 0 12px rgba(243, 226, 179, .22), inset 0 0 10px rgba(217, 186, 130, .08); }
.tab-num { font-family: Georgia, serif; margin-left: 4px; opacity: .75; }

/* 列表 */
.book-list { list-style: none; display: flex; flex-direction: column; gap: 10px; }
.book {
  display: flex; flex-direction: column; gap: 0;
  padding: 12px 14px; border: 1px solid rgba(210, 175, 110, .28); border-radius: 12px;
  background: rgba(6, 12, 22, .78); transition: border-color .15s;
}
.book:hover, .book.open { border-color: rgba(212, 180, 119, .35); }
.book-main { display: flex; align-items: center; gap: 14px; }

.cover {
  position: relative; overflow: hidden;
  width: 42px; height: 58px; flex-shrink: 0; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-family: Georgia, serif; font-size: 19px; color: rgba(232, 224, 210, .92);
  box-shadow: inset 0 0 0 1px rgba(232, 224, 210, .12), 0 2px 7px rgba(0, 0, 0, .42);
}
.cover::before {
  content: ''; position: absolute; left: 3px; top: 4px; bottom: 4px; width: 1px;
  background: rgba(255, 255, 255, .3);
}

.meta { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.book-title { font-size: 15px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.book-author { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meta-hint { color: #C9AB72; }

/* 阅读信息编辑入口按钮 */
.edit-toggle {
  width: 30px; height: 30px; flex-shrink: 0;
  border: 1px solid var(--line); border-radius: 10px; background: transparent;
  color: var(--muted); font-size: 14px; line-height: 1; cursor: pointer; transition: all .15s;
}
.edit-toggle:hover, .edit-toggle.active { color: #E3C78E; border-color: rgba(212, 180, 119, .55); }

/* 可折叠阅读信息编辑区（沿用添加表单的视觉语言） */
.meta-edit {
  margin-top: 12px; padding: 12px; display: flex; flex-direction: column; gap: 10px;
  border: 1px solid rgba(212, 180, 119, .25); border-radius: 10px;
  background: var(--bg-sidebar);
}
.meta-edit label {
  display: flex; flex-direction: column; gap: 5px;
  font-size: 12px; color: var(--muted);
}
.meta-edit select, .meta-edit input, .meta-edit textarea {
  padding: 7px 10px; font-size: 14px; color: var(--ink); font-family: inherit;
  background: #0A1420; border: 1px solid var(--line); border-radius: 8px; outline: none;
}
.meta-edit select:focus, .meta-edit input:focus, .meta-edit textarea:focus { border-color: var(--accent); }
.meta-edit textarea { resize: vertical; }
.meta-edit-row { display: flex; gap: 12px; flex-wrap: wrap; }
.meta-edit-row label { flex: 1; min-width: 130px; }
.meta-edit-note { width: 100%; }
.meta-edit-actions { display: flex; align-items: center; gap: 10px; }
.meta-msg { font-size: 12px; color: #e2a49c; }
.meta-msg.ok { color: #7fc2a0; }

/* 统计接口失败提示（书架数据不受影响） */
.stats-warn { margin-top: 14px; font-size: 12px; color: #C9AB72; opacity: .85; }

/* 状态标签：点击循环切换阅读状态 */
.status {
  display: inline-flex; align-items: center; gap: 5px; flex-shrink: 0;
  height: 28px; padding: 0 10px; font-size: 12px;
  border: 1px solid rgba(232, 224, 210, .1); border-radius: 999px;
  background: rgba(232, 224, 210, .05); color: var(--muted);
  cursor: pointer; transition: all .15s;
}
.status:hover { border-color: rgba(212, 180, 119, .45); }
.status svg { width: 13px; height: 13px; flex-shrink: 0; }
.status.read { color: #7fc2a0; }
.status.finished { color: #7fc2a0; }
.status.reading { color: var(--accent-soft); }
.status.want { color: #b48ce0; }
.status.want_to_read { color: #b48ce0; }

/* 加载 / 错误状态 */
.err-box {
  padding: 30px 0; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.err-text { color: #e2a49c; font-size: 14px; }

.del {
  width: 30px; height: 30px; flex-shrink: 0;
  border: 1px solid var(--line); border-radius: 10px; background: transparent;
  color: var(--muted); font-size: 16px; line-height: 1; cursor: pointer; transition: all .15s;
}
.del:hover { color: #e2887f; border-color: rgba(226, 136, 127, .5); }

.empty { padding: 40px 0; text-align: center; color: var(--muted); font-size: 14px; }
.back { margin-top: 28px; padding-bottom: 40px; }
</style>