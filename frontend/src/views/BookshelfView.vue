<script setup>
// 完整书架页：添加书籍 / 修改阅读状态 / 删除书籍 / 三种状态筛选 / 动态统计
import { ref, computed, onMounted } from 'vue'
import { countShelfStats } from '../api'
import { books, initBookshelf, addBook, updateBookStatus, removeBook } from '../store/bookshelfStore'

const filter = ref('all')
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'read', label: '已读' },
  { key: 'reading', label: '在读' },
  { key: 'want', label: '想读' }
]

// 状态下拉顺序与阅读流程一致：想读 → 在读 → 已读
const STATUS_OPTIONS = [
  { value: 'want', label: '想读' },
  { value: 'reading', label: '在读' },
  { value: 'read', label: '已读' }
]
const STATUS_TEXT = { read: '已读', reading: '在读', want: '想读' }

// 点击状态标签：在想读 → 在读 → 已读 → 想读 之间循环切换
const STATUS_ORDER = ['want', 'reading', 'read']
function cycleStatus(b) {
  const i = STATUS_ORDER.indexOf(b.status)
  updateBookStatus(b.id, STATUS_ORDER[(i + 1) % STATUS_ORDER.length])
}

// 与首页侧栏共用同一份 store 数据：这里任何操作，侧栏与统计都会自动同步
onMounted(() => { initBookshelf() })

// 统计动态计算：总藏书量 + 三种状态数量，全部来自实际书籍列表
const stats = computed(() => ({ total: books.value.length, ...countShelfStats(books.value) }))

const filteredBooks = computed(() =>
  filter.value === 'all' ? books.value : books.value.filter(b => b.status === filter.value)
)

function coverStyle(b) {
  return { background: `linear-gradient(150deg, ${b.cover[0]}, ${b.cover[1]})` }
}

// ---- 添加书籍 ----
const showForm = ref(false)
const form = ref({ title: '', author: '', status: 'want' })
function submitAdd() {
  const title = form.value.title.trim()
  const author = form.value.author.trim()
  if (!title || !author) { alert('请填写书名和作者'); return }
  addBook({ title, author, status: form.value.status })
  form.value = { title: '', author: '', status: 'want' }
  showForm.value = false
}

// ---- 删除（简单确认） ----
function onDelete(b) {
  if (window.confirm(`确定要删除《${b.title}》吗？`)) removeBook(b.id)
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

    <!-- 动态统计：总藏书量 + 三种状态，全部由实际书籍列表计算 -->
    <div class="stats">
      <div class="stat">
        <span class="stat-num">{{ stats.total }}</span>
        <span class="stat-lab">总藏书</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ stats.read }}</span>
        <span class="stat-lab">已读</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ stats.reading }}</span>
        <span class="stat-lab">在读</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ stats.want }}</span>
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
        <button type="submit" class="btn btn-gold btn-sm">确认添加</button>
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
        {{ t.label }} <span class="tab-num">{{ t.key === 'all' ? stats.total : stats[t.key] }}</span>
      </button>
    </div>

    <!-- 书籍列表 -->
    <ul class="book-list">
      <li v-for="b in filteredBooks" :key="b.id" class="book">
        <span class="cover" :style="coverStyle(b)">{{ b.title.slice(0, 1) }}</span>
        <div class="meta">
          <span class="book-title">{{ b.title }}</span>
          <span class="book-author">{{ b.author }}</span>
        </div>
        <button
          class="status"
          :class="b.status"
          type="button"
          title="点击切换阅读状态"
          @click="cycleStatus(b)"
        >
          <svg v-if="b.status === 'read'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>
          <svg v-else-if="b.status === 'want'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>
          <span>{{ STATUS_TEXT[b.status] }}</span>
        </button>
        <button class="del" title="删除这本书" @click="onDelete(b)">×</button>
      </li>
    </ul>

    <p v-if="filteredBooks.length === 0" class="empty">这一栏还没有书，点右上角「添加书籍」试试。</p>

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
  display: flex; align-items: center; gap: 14px;
  padding: 12px 14px; border: 1px solid rgba(210, 175, 110, .28); border-radius: 12px;
  background: rgba(6, 12, 22, .78); transition: border-color .15s;
}
.book:hover { border-color: rgba(212, 180, 119, .35); }

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
.status.reading { color: var(--accent-soft); }
.status.want { color: #b48ce0; }

.del {
  width: 30px; height: 30px; flex-shrink: 0;
  border: 1px solid var(--line); border-radius: 10px; background: transparent;
  color: var(--muted); font-size: 16px; line-height: 1; cursor: pointer; transition: all .15s;
}
.del:hover { color: #e2887f; border-color: rgba(226, 136, 127, .5); }

.empty { padding: 40px 0; text-align: center; color: var(--muted); font-size: 14px; }
.back { margin-top: 28px; padding-bottom: 40px; }
</style>