<script setup>
// 右侧个人书架：统计 + 筛选页签 + 书籍列表
import { ref, computed, onMounted } from 'vue'
import { focusTarget } from '../store/mapStore'
import {
  books, loading, error, shelfStats, statsError,
  initBookshelf, updateBookStatus, reloadBookshelf
} from '../store/bookshelfStore'

const filter = ref('all')
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'finished', label: '已读' },
  { key: 'reading', label: '在读' },
  { key: 'want_to_read', label: '想读' }
]
const STATUS_TEXT = { finished: '已读', reading: '在读', want_to_read: '想读' }

// 书架唯一数据源在 bookshelfStore：侧栏与书架页共用，
// 任何页面的增删改操作，这里都会自动同步
// 统计来自 store（真实模式 GET /api/reading/statistics，失败保留最近一次有效结果）
onMounted(() => { initBookshelf() })

const filteredBooks = computed(() =>
  filter.value === 'all' ? books.value : books.value.filter(b => b.status === filter.value)
)

function coverStyle(b) {
  return { background: `linear-gradient(150deg, ${b.cover[0]}, ${b.cover[1]})` }
}

// 点击状态标签：在想读 → 在读 → 已读 → 想读 之间循环切换
const STATUS_ORDER = ['want_to_read', 'reading', 'finished']
const cyclingId = ref(null) // 正在切换的记录 id：请求期间拦截重复点击
async function cycleStatus(b) {
  if (cyclingId.value != null) return
  cyclingId.value = b.id
  try {
    const i = STATUS_ORDER.indexOf(b.status)
    await updateBookStatus(b.id, STATUS_ORDER[(i + 1) % STATUS_ORDER.length])
  } catch (e) {
    // 失败不伪装成功：store 未执行 load()，列表仍显示原状态；明确提示错误原因
    alert(e && e.message ? e.message : '更新阅读状态失败')
  } finally {
    cyclingId.value = null
  }
}

// 点击书籍：定位到该书关联地点（bookId 为后端作品 id，Mock 模式回退到本地 id）
function locate(b) {
  focusTarget('book', b.bookId ?? b.id)
}
</script>

<template>
  <aside class="shelf">
    <header class="shelf-head">
      <div class="head-emblem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3c2.5 2.6 4 5.6 4 9s-1.5 6.4-4 9" />
          <path d="M12 12l4-2.5" />
        </svg>
      </div>
      <div class="head-text">
        <h2 class="shelf-title">我的书架</h2>
        <p class="shelf-sub">MY BOOKSHELF</p>
      </div>
    </header>

    <div class="shelf-stats">
      <div class="stat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        <span class="stat-num">{{ shelfStats.finished }}</span>
        <span class="stat-lab">已读</span>
      </div>
      <div class="stat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6C10 4.5 7.5 4 5 4v14c2.5 0 5 .5 7 2 2-1.5 4.5-2 7-2V4c-2.5 0-5 .5-7 2z"/><path d="M12 6v14"/></svg>
        <span class="stat-num">{{ shelfStats.reading }}</span>
        <span class="stat-lab">在读</span>
      </div>
      <div class="stat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        <span class="stat-num">{{ shelfStats.want_to_read }}</span>
        <span class="stat-lab">想读</span>
      </div>
    </div>
    <p v-if="statsError" class="stats-warn">统计暂时不可用：{{ statsError }}</p>

    <div class="shelf-tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: filter === t.key }"
        @click="filter = t.key"
      >{{ t.label }}</button>
    </div>

    <div class="shelf-body">
      <!-- 加载 / 错误状态：真实模式后端不可达时提示，可重试，不静默回退 Mock -->
      <p v-if="loading && books.length === 0" class="shelf-state">正在加载书架…</p>
      <div v-else-if="error" class="shelf-state shelf-error">
        <span>书架加载失败：{{ error }}</span>
        <button class="shelf-retry" @click="reloadBookshelf">重试</button>
      </div>
      <ul v-else class="book-list">
        <li v-for="b in filteredBooks" :key="b.id" class="book" @click="locate(b)">
          <span class="cover" :style="coverStyle(b)">{{ b.title.slice(0, 1) }}</span>
          <span class="meta">
            <span class="book-title">{{ b.title }}</span>
            <span class="book-author">{{ b.author || '作者未知' }}</span>
          </span>
          <span
            class="status"
            :class="[b.status, { busy: cyclingId === b.id }]"
            role="button"
            title="点击切换阅读状态"
            @click.stop="cycleStatus(b)"
          >
            <svg v-if="b.status === 'finished'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>
            <svg v-else-if="b.status === 'want_to_read'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>
            <span>{{ STATUS_TEXT[b.status] || b.status }}</span>
          </span>
        </li>
      </ul>
      <p v-if="!loading && !error && filteredBooks.length === 0" class="shelf-state">这一栏还没有书。</p>
    </div>

    <footer class="shelf-foot">
      <router-link to="/bookshelf" class="all-link">查看全部书籍 →</router-link>
    </footer>
  </aside>
</template>

<style scoped>
.shelf {
  display: flex; flex-direction: column; height: 100%;
  background: rgba(6, 11, 20, .88); border-left: 1px solid rgba(210, 175, 110, .28);
}

.shelf-head {
  display: flex; align-items: center; gap: 12px;
  padding: 18px 18px 14px; border-bottom: 1px solid var(--line);
}
.head-emblem { color: var(--accent); width: 34px; height: 34px; flex-shrink: 0; }
.head-emblem svg { width: 100%; height: 100%; }
.head-text { min-width: 0; }
.shelf-title { font-family: Georgia, "Songti SC", serif; font-size: 19px; color: var(--ink); line-height: 1.15; }
.shelf-sub { font-size: 10px; letter-spacing: .22em; color: var(--muted); margin-top: 2px; }

.shelf-stats {
  display: flex; gap: 10px; padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}
.stat {
  flex: 1; display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border: 1px solid var(--line); border-radius: 10px;
  color: var(--muted);
}
.stat svg { width: 18px; height: 18px; color: var(--accent); flex-shrink: 0; }
.stat-num { font-family: Georgia, serif; font-size: 18px; color: var(--ink); }
.stat-lab { font-size: 11px; }

.shelf-tabs { display: flex; gap: 8px; padding: 12px 18px 8px; }
.tab {
  flex: 1; height: 30px; font-size: 12px; border-radius: 999px;
  border: 1px solid rgba(210, 175, 110, .45); color: #C9AB72; background: rgba(3, 6, 12, .85);
  cursor: pointer; transition: all .15s;
}
.tab:hover { border-color: rgba(246, 225, 170, .8); color: #E9D5A0; }
.tab.active { background: rgba(3, 6, 12, .92); border-color: rgba(246, 225, 170, .95); color: #F0DCAB; box-shadow: 0 0 12px rgba(243, 226, 179, .22), inset 0 0 10px rgba(217, 186, 130, .08); }

.shelf-body { flex: 1; overflow: auto; padding: 4px 0 10px; }
.book-list { list-style: none; }
.book { display: flex; align-items: center; gap: 12px; padding: 10px 18px; cursor: pointer; transition: background .15s; }
.book:hover { background: rgba(200, 169, 110, .07); }

.cover {
  position: relative; overflow: hidden;
  width: 38px; height: 52px; flex-shrink: 0; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-family: Georgia, serif; font-size: 17px; color: rgba(232, 224, 210, .92);
  box-shadow: inset 0 0 0 1px rgba(232, 224, 210, .12), 0 2px 7px rgba(0, 0, 0, .42);
}
.cover::before {
  content: ''; position: absolute; left: 3px; top: 4px; bottom: 4px; width: 1px;
  background: rgba(255, 255, 255, .3);
}
.cover::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(115deg, rgba(255, 255, 255, .18) 0%, transparent 30%, transparent 68%, rgba(0, 0, 0, .2) 100%);
  pointer-events: none;
}

.meta { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.book-title { font-size: 14px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.book-author { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.status { display: flex; align-items: center; gap: 4px; font-size: 11px; flex-shrink: 0; }
.status svg { width: 14px; height: 14px; }
.status.read { color: #7fc2a0; }
.status.finished { color: #7fc2a0; }
.status.reading { color: var(--accent-soft); }
.status.want { color: #b48ce0; }
.status.want_to_read { color: #b48ce0; }
/* 状态标签可点击切换 */
.status { cursor: pointer; }
.status:hover { border-color: rgba(212, 180, 119, .45); }
/* 切换请求进行中：降低透明度并禁用手型，防止误判已切换 */
.status.busy { opacity: .45; cursor: wait; }

/* 统计接口失败提示（列表数据不受影响） */
.stats-warn { padding: 8px 18px 0; font-size: 11px; color: #C9AB72; opacity: .85; }

/* 加载 / 错误状态 */
.shelf-state { padding: 24px 18px; font-size: 13px; color: var(--muted); text-align: center; }
.shelf-error { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #e2a49c; }
.shelf-retry {
  height: 28px; padding: 0 14px; font-size: 12px; cursor: pointer;
  color: var(--accent-soft); background: transparent;
  border: 1px solid rgba(212, 180, 119, .5); border-radius: 999px;
}
.shelf-retry:hover { background: rgba(212, 180, 119, .15); }

.shelf-foot { padding: 14px 18px; border-top: 1px solid var(--line); }
.all-link { display: flex; align-items: center; justify-content: center; height: 40px; font-size: 13px; color: #E3C78E; background: rgba(3, 6, 12, .85); border: 1px solid rgba(210, 175, 110, .55); border-radius: 10px; transition: all .15s; }
.all-link:hover { background: rgba(3, 6, 12, .95); color: #F0DCAB; border-color: rgba(246, 225, 170, .95); box-shadow: 0 0 14px rgba(243, 226, 179, .2); }
</style>