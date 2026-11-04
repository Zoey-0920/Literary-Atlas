<template>
  <div class="abm-overlay" @click.self="tryClose">
    <div class="abm-panel" role="dialog" aria-modal="true" aria-label="添加书籍">

      <header class="abm-head">
        <div>
          <p class="abm-eyebrow">Literary Atlas</p>
          <h3 class="abm-title">添加书籍</h3>
        </div>
        <button class="abm-x" type="button" :disabled="busy" aria-label="关闭" @click="tryClose">×</button>
      </header>

      <!-- ============ 第一步：输入书籍信息 ============ -->
      <section v-if="step === 'input'" class="abm-body">
        <p class="abm-hint">
          输入书名（作者选填），AI 将根据已有文学知识识别作品并提取文学关联地点，
          结果需经你确认后才会保存。识别基于模型知识，非互联网实时核实。
        </p>

        <label class="abm-field">
          <span class="abm-label">书名 <i class="abm-req">必填</i></span>
          <input v-model.trim="form.title" type="text" placeholder="例如：月亮与六便士"
                 :disabled="busy" @keyup.enter="submitLookup" />
        </label>

        <label class="abm-field">
          <span class="abm-label">作者 <i class="abm-opt">选填，同名作品时帮助 AI 判断</i></span>
          <input v-model.trim="form.author" type="text" placeholder="例如：毛姆"
                 :disabled="busy" @keyup.enter="submitLookup" />
        </label>

        <!-- AI 失败 / 无法识别：降级提示，保留输入 -->
        <p v-if="aiFailMsg" class="abm-banner abm-banner-error">
          {{ aiFailMsg }}
          <button class="abm-link" type="button" :disabled="saving" @click="saveBasicOnly">
            仅保存书名和作者
          </button>
        </p>

        <div class="abm-actions">
          <button class="abm-btn abm-btn-primary" type="button"
                  :disabled="busy || !form.title" @click="submitLookup">
            {{ lookingUp ? 'AI 检索中…' : 'AI 检索并添加' }}
          </button>
        </div>
        <p v-if="lookingUp" class="abm-waiting">AI 正在识别作品并提取文学地点，通常需要 10–40 秒，请勿关闭窗口…</p>
      </section>

      <!-- ============ 重复作品 ============ -->
      <section v-else-if="step === 'duplicate'" class="abm-body">
        <p class="abm-banner abm-banner-warn">
          作品库已收录《{{ dup.title }}》，无需重复添加。
        </p>
        <div class="abm-dup-card">
          <p class="abm-dup-title">《{{ dup.title }}》</p>
          <p class="abm-dup-meta">
            {{ dup.authors && dup.authors.length ? dup.authors.join(' / ') : '作者未录' }}
            <span class="abm-tag">{{ dup.is_public ? '公共精选' : '自定义' }}</span>
          </p>
        </div>

        <div v-if="possible && possible.length > 1" class="abm-possible">
          <p class="abm-label">同名作品还包括：</p>
          <ul>
            <li v-for="p in possible" :key="p.book_id">
              《{{ p.title }}》 id:{{ p.book_id }}
              <span v-if="p.authors && p.authors.length">{{ p.authors.join(' / ') }}</span>
              <span v-else>作者未录</span>
            </li>
          </ul>
        </div>

        <div class="abm-actions">
          <button class="abm-btn abm-btn-primary" type="button" :disabled="joining" @click="joinExisting">
            {{ joining ? '加入中…' : '加入现有书架' }}
          </button>
          <button class="abm-btn" type="button" :disabled="busy" @click="backToInput">返回修改</button>
        </div>
        <p v-if="joinMsg" class="abm-banner abm-banner-error">{{ joinMsg }}</p>
      </section>

      <!-- ============ 同名歧义：选择候选 ============ -->
      <section v-else-if="step === 'ambiguous'" class="abm-body">
        <p class="abm-banner abm-banner-warn">
          「{{ form.title }}」对应多部作品，AI 无法确定你指的是哪一本。请从下方选择，或补充作者后重新检索。
        </p>
        <ul class="abm-candidates">
          <li v-for="(c, i) in candidates" :key="i">
            <button class="abm-cand" type="button" :disabled="busy" @click="pickCandidate(c)">
              <span class="abm-cand-title">《{{ c.title || '未知书名' }}》</span>
              <span class="abm-cand-meta">
                {{ c.author || '作者未知' }}<template v-if="c.year"> · {{ c.year }}</template>
              </span>
            </button>
          </li>
        </ul>
        <div class="abm-actions">
          <button class="abm-btn" type="button" :disabled="busy" @click="backToInput">返回修改</button>
        </div>
      </section>

      <!-- ============ 第二步：确认 AI 草案 ============ -->
      <section v-else-if="step === 'confirm'" class="abm-body">
        <p class="abm-hint">
          以下信息由 AI 识别生成（未联网核实），请核对并修正后再保存。
          <span class="abm-em">带 * 字段可编辑</span>。
        </p>

        <div class="abm-grid">
          <label class="abm-field">
            <span class="abm-label">书名 *</span>
            <input v-model.trim="edit.title" type="text" :disabled="saving" />
          </label>
          <label class="abm-field">
            <span class="abm-label">作者</span>
            <input v-model.trim="edit.author" type="text" :disabled="saving" />
          </label>
          <label class="abm-field">
            <span class="abm-label">国家或地区</span>
            <input v-model.trim="edit.country" type="text" :disabled="saving" />
          </label>
          <label class="abm-field">
            <span class="abm-label">作品类型</span>
            <input v-model.trim="edit.genre" type="text" :disabled="saving" />
          </label>
        </div>

        <label class="abm-field">
          <span class="abm-label">简介</span>
          <textarea v-model="edit.description" rows="3" :disabled="saving"
                    placeholder="暂无简介"></textarea>
        </label>

        <div class="abm-places">
          <p class="abm-label">文学关联地点（{{ edit.places.length }}）</p>
          <p v-if="!edit.places.length" class="abm-muted">
            AI 未识别到可靠的文学关联地点，可跳过地点直接保存。
          </p>
          <div v-for="(p, i) in edit.places" :key="i" class="abm-place">
            <input v-model.trim="p.name" class="abm-place-name" type="text" :disabled="saving" />
            <select v-model="p.relation_type" class="abm-place-rel" :disabled="saving">
              <option value="setting">故事发生地</option>
              <option value="depiction">文学描写地</option>
            </select>
            <span v-if="p.is_fictional" class="abm-badge abm-badge-fic">虚构地点</span>
            <span v-else-if="p.match_status === 'reused'" class="abm-badge abm-badge-ok">已定位</span>
            <span v-else-if="p.match_status === 'exists_no_coords'" class="abm-badge abm-badge-pending">
              已找到地点，暂无可靠坐标
            </span>
            <span v-else class="abm-badge abm-badge-pending">新地点·待核实，暂不显示地图标记</span>
            <button class="abm-place-del" type="button" :disabled="saving"
                    aria-label="移除地点" @click="edit.places.splice(i, 1)">移除</button>
          </div>
          <p class="abm-muted">
            坐标由系统根据现有地点库自动匹配，无法核实的地点不会显示地图标记。
          </p>
        </div>

        <p v-if="saveMsg" class="abm-banner abm-banner-error">{{ saveMsg }}</p>

        <div class="abm-actions">
          <button class="abm-btn abm-btn-primary" type="button"
                  :disabled="saving || !edit.title" @click="confirmSave">
            {{ saving ? '保存中…' : '确认保存并加入书架' }}
          </button>
          <button class="abm-btn" type="button" :disabled="saving" @click="backToInput">返回</button>
        </div>
      </section>

      <!-- ============ 已保存但加入书架失败：明确告知 ============ -->
      <section v-else-if="step === 'partial'" class="abm-body">
        <p class="abm-banner abm-banner-warn">{{ partialMsg }}</p>
        <div class="abm-actions">
          <button class="abm-btn abm-btn-primary" type="button" @click="finish">完成</button>
        </div>
      </section>

    </div>
  </div>
</template>

<script setup>
// 添加书籍弹窗：AI 辅助识别 → 用户确认 → 保存自定义作品 → 加入现有书架。
// 数据流：lookupCustomBook（只读草案）→ 用户确认/修正 → createCustomBook（正式保存）
//        → bookshelfStore.addBook（复用现有书架添加逻辑）。
// 本组件不实现任何书架/阅读逻辑，全部复用 store 与 api 层。
import { reactive, ref, computed } from 'vue'
import { lookupCustomBook, createCustomBook, READING_STATUS } from '../api'
import { addBook } from '../store/bookshelfStore'

const emit = defineEmits(['close', 'saved'])

// ---------- 状态 ----------
const step = ref('input')          // input | duplicate | ambiguous | confirm | partial
const form = reactive({ title: '', author: '' })   // 第一步的输入（保留用户原始输入）
const edit = reactive({ title: '', author: '', country: '', genre: '', description: '', places: [] })

const lookingUp = ref(false)
const saving = ref(false)
const joining = ref(false)
const busy = computed(() => lookingUp.value || saving.value || joining.value)

const aiFailMsg = ref('')          // AI 失败 / 无法识别时的降级提示（第一步内显示）
const saveMsg = ref('')            // 确认页内的错误提示
const joinMsg = ref('')            // 重复页内"加入书架"的失败提示
const partialMsg = ref('')         // 已保存但加入书架失败时的告知

const dup = ref(null)              // 命中的已有作品
const possible = ref([])           // 同名候选（信息展示）
const candidates = ref([])         // AI 歧义候选

// ---------- 第一步：发起 AI 检索 ----------
async function submitLookup() {
  if (!form.title || lookingUp.value || saving.value) return
  aiFailMsg.value = ''
  lookingUp.value = true
  try {
    const res = await lookupCustomBook(form.title, form.author)
    if (res && res.duplicate) {
      // 已收录：展示已有作品，引导加入书架（不重复创建）
      dup.value = res.duplicate
      possible.value = res.possible_duplicates || []
      step.value = 'duplicate'
      return
    }
    const draft = (res && res.draft) || {}
    if (draft.ambiguous && Array.isArray(draft.candidates) && draft.candidates.length) {
      // 同名歧义：让用户点选候选后再检索（补充候选中的作者信息）
      candidates.value = draft.candidates
      step.value = 'ambiguous'
      return
    }
    if (draft.found) {
      openConfirm(draft)
      return
    }
    // AI 明确表示无法识别：降级
    aiFailMsg.value = 'AI 未能识别该作品。你可以核对书名后重试，或仅保存书名和作者。'
  } catch (e) {
    aiFailMsg.value = `AI 检索暂不可用：${(e && e.message) || '未知错误'}。可稍后重试，或仅保存书名和作者。`
  } finally {
    lookingUp.value = false
  }
}

// 歧义候选点选：带上候选的作者信息重新检索，帮助 AI 精确识别
async function pickCandidate(c) {
  if (busy.value) return
  form.title = c.title || form.title
  if (c.author) form.author = c.author
  await submitLookup()
}

// ---------- 第二步：进入确认页（允许修改） ----------
function openConfirm(draft) {
  edit.title = draft.title || form.title
  edit.author = draft.author || form.author || ''
  edit.country = draft.country || ''
  edit.genre = draft.genre || ''
  edit.description = draft.description || ''
  edit.places = (draft.places || []).map(p => ({
    name: p.name || '',
    country: p.country || '',
    relation_type: p.relation_type === 'depiction' ? 'depiction' : 'setting',
    is_fictional: !!p.is_fictional,
    match_status: p.match_status || 'new'
  }))
  saveMsg.value = ''
  step.value = 'confirm'
}

// ---------- 保存与加入书架 ----------
function toPayload() {
  // 只提交后端支持的字段；地点只提交四个字段，不提交任何坐标信息
  return {
    title: edit.title,
    author: edit.author || null,
    country: edit.country || null,
    genre: edit.genre || null,
    description: edit.description || null,
    places: edit.places
      .filter(p => p.name)
      .map(p => ({
        name: p.name,
        country: p.country || null,
        relation_type: p.relation_type,
        is_fictional: p.is_fictional
      }))
  }
}

// 保存成功后加入现有书架（复用 store 现有添加逻辑；已在书架中视为成功）
async function joinShelf(created) {
  try {
    await addBook({ title: created.title, status: READING_STATUS.WANT })
    return true
  } catch (e) {
    const msg = (e && e.message) || '未知错误'
    if (String(msg).includes('已在书架')) return true // 重复添加视为已在书架
    return msg
  }
}

async function confirmSave() {
  if (!edit.title || saving.value) return
  saveMsg.value = ''
  saving.value = true
  try {
    const created = await createCustomBook(toPayload())
    emit('saved') // 作品已入库，立即通知父页面刷新列表
    const shelf = await joinShelf(created)
    if (shelf === true) {
      finish()
    } else {
      partialMsg.value = `《${created.title}》已保存到作品库，但加入书架失败：${shelf}。你可以在书架页手动添加。`
      step.value = 'partial'
    }
  } catch (e) {
    saveMsg.value = `保存失败：${(e && e.message) || '未知错误'}`
  } finally {
    saving.value = false
  }
}

// AI 不可用时的降级：只保存书名与作者，不创建地点/流派等无法确认的信息
async function saveBasicOnly() {
  if (!form.title || saving.value) return
  saveMsg.value = ''
  saving.value = true
  try {
    const created = await createCustomBook({
      title: form.title,
      author: form.author || null
    })
    emit('saved')
    const shelf = await joinShelf(created)
    if (shelf === true) {
      finish()
    } else {
      partialMsg.value = `《${created.title}》已保存到作品库，但加入书架失败：${shelf}。你可以在书架页手动添加。`
      step.value = 'partial'
    }
  } catch (e) {
    aiFailMsg.value = `保存失败：${(e && e.message) || '未知错误'}`
  } finally {
    saving.value = false
  }
}

// 重复页：把已有作品加入书架（复用现有添加逻辑）
async function joinExisting() {
  if (!dup.value || joining.value) return
  joinMsg.value = ''
  joining.value = true
  try {
    await addBook({ title: dup.value.title, status: READING_STATUS.WANT })
    finish()
  } catch (e) {
    joinMsg.value = `加入书架失败：${(e && e.message) || '未知错误'}`
  } finally {
    joining.value = false
  }
}

// ---------- 返回 / 关闭 ----------
function backToInput() {
  step.value = 'input'
  aiFailMsg.value = ''
  saveMsg.value = ''
}
function tryClose() {
  if (busy.value) return // 检索/保存过程中禁止关闭，避免状态混乱
  emit('close')
}
function finish() {
  emit('saved')
  emit('close')
}
</script>

<style scoped>
/* 沿用全局暗色星空 + 强调金风格（变量取自 assets/styles/main.css） */
.abm-overlay {
  position: fixed; inset: 0; z-index: 90;
  background: rgba(3, 8, 16, 0.72);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.abm-panel {
  width: min(620px, 100%);
  max-height: min(84vh, 760px);
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(13, 22, 36, 0.98), rgba(8, 14, 24, 0.98));
  border: 1px solid rgba(212, 180, 119, 0.28);
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
  padding: 22px 24px 24px;
  color: var(--ink);
}
.abm-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.abm-eyebrow { margin: 0; color: var(--accent); font-size: 11px; letter-spacing: .2em; text-transform: uppercase; }
.abm-title { margin: 4px 0 0; font-family: Georgia, 'Songti SC', serif; font-size: 22px; }
.abm-x {
  border: 1px solid var(--line); background: transparent; color: var(--muted);
  width: 30px; height: 30px; border-radius: 50%; font-size: 16px; line-height: 1; cursor: pointer;
}
.abm-x:hover:not(:disabled) { color: var(--ink); border-color: var(--accent-deep); }

.abm-body { display: flex; flex-direction: column; gap: 14px; }
.abm-hint, .abm-muted { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.6; }
.abm-em { color: var(--accent-soft); }

.abm-field { display: flex; flex-direction: column; gap: 6px; }
.abm-label { color: var(--accent-soft); font-size: 12px; letter-spacing: .05em; }
.abm-req { color: #d98a7a; font-style: normal; margin-left: 4px; font-size: 11px; }
.abm-opt { color: var(--muted); font-style: normal; margin-left: 6px; font-size: 11px; }

.abm-field input, .abm-field textarea {
  background: rgba(6, 12, 22, 0.85);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
  padding: 9px 12px;
  font-size: 14px;
  font-family: inherit;
}
.abm-field input:focus, .abm-field textarea:focus {
  outline: none; border-color: var(--accent-deep);
  box-shadow: 0 0 0 2px rgba(212, 180, 119, 0.15);
}
.abm-field textarea { resize: vertical; }
.abm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.abm-banner {
  margin: 0; padding: 10px 12px; border-radius: 8px; font-size: 13px; line-height: 1.6;
}
.abm-banner-error {
  background: rgba(150, 60, 50, 0.18);
  border: 1px solid rgba(217, 138, 122, 0.4);
  color: #e8b3a6;
}
.abm-banner-warn {
  background: rgba(212, 180, 119, 0.12);
  border: 1px solid rgba(212, 180, 119, 0.35);
  color: var(--accent-soft);
}
.abm-link {
  background: none; border: none; color: var(--accent); cursor: pointer;
  font-size: 13px; text-decoration: underline; padding: 0 2px;
}

.abm-actions { display: flex; gap: 10px; margin-top: 2px; flex-wrap: wrap; }
.abm-btn {
  border: 1px solid var(--line); background: rgba(6, 12, 22, 0.7); color: var(--ink);
  border-radius: 999px; padding: 9px 18px; font-size: 14px; cursor: pointer;
}
.abm-btn:hover:not(:disabled) { border-color: var(--accent-deep); }
.abm-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.abm-btn-primary {
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  border-color: transparent; color: #1a2233; font-weight: 600;
}
.abm-waiting { margin: 0; color: var(--accent-soft); font-size: 13px; }

/* 重复作品 */
.abm-dup-card {
  border: 1px solid rgba(212, 180, 119, 0.3);
  border-radius: 10px; padding: 14px 16px;
  background: rgba(6, 12, 22, 0.6);
}
.abm-dup-title { margin: 0 0 6px; font-family: Georgia, 'Songti SC', serif; font-size: 18px; }
.abm-dup-meta { margin: 0; color: var(--muted); font-size: 13px; display: flex; gap: 8px; align-items: center; }
.abm-tag {
  border: 1px solid var(--accent-deep); color: var(--accent-soft);
  border-radius: 999px; padding: 1px 8px; font-size: 11px;
}
.abm-possible ul { margin: 6px 0 0; padding-left: 18px; color: var(--muted); font-size: 13px; line-height: 1.8; }

/* 歧义候选 */
.abm-candidates { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.abm-cand {
  width: 100%; text-align: left; cursor: pointer;
  background: rgba(6, 12, 22, 0.6); border: 1px solid var(--line); border-radius: 10px;
  padding: 10px 14px; color: var(--ink); display: flex; flex-direction: column; gap: 2px;
}
.abm-cand:hover:not(:disabled) { border-color: var(--accent-deep); }
.abm-cand:disabled { opacity: 0.6; cursor: not-allowed; }
.abm-cand-title { font-family: Georgia, 'Songti SC', serif; font-size: 15px; }
.abm-cand-meta { color: var(--muted); font-size: 12px; }

/* 地点列表 */
.abm-places { display: flex; flex-direction: column; gap: 8px; }
.abm-place {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  background: rgba(6, 12, 22, 0.5); border: 1px solid var(--line);
  border-radius: 10px; padding: 8px 10px;
}
.abm-place-name {
  flex: 1 1 150px; min-width: 120px;
  background: transparent; border: none; border-bottom: 1px dashed var(--line);
  color: var(--ink); padding: 4px 2px; font-size: 14px;
}
.abm-place-name:focus { outline: none; border-bottom-color: var(--accent-deep); }
.abm-place-rel {
  background: rgba(6, 12, 22, 0.9); border: 1px solid var(--line); color: var(--ink);
  border-radius: 6px; padding: 4px 6px; font-size: 12px;
}
.abm-badge {
  border-radius: 999px; padding: 2px 9px; font-size: 11px; white-space: nowrap;
}
.abm-badge-ok { background: rgba(110, 166, 143, 0.18); border: 1px solid rgba(110, 166, 143, 0.5); color: #9fd0ba; }
.abm-badge-pending { background: rgba(212, 180, 119, 0.12); border: 1px solid rgba(212, 180, 119, 0.35); color: var(--accent-soft); }
.abm-badge-fic { background: rgba(154, 123, 191, 0.16); border: 1px solid rgba(154, 123, 191, 0.45); color: #c3a8e0; }
.abm-place-del {
  background: none; border: none; color: var(--muted); font-size: 12px;
  cursor: pointer; text-decoration: underline; padding: 2px;
}
.abm-place-del:hover:not(:disabled) { color: #e8b3a6; }

@media (max-width: 560px) {
  .abm-grid { grid-template-columns: 1fr; }
}
</style>
