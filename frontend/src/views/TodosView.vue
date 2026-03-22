<template>
  <el-row :gutter="16" class="todo-page">
    <el-col :span="8" class="left-col">
      <el-card class="left-card">
        <template #header>
          <div class="header-row">
            <span>待办列表</span>
            <el-button size="small" type="primary" @click="addTodo">新增</el-button>
          </div>
        </template>

        <div class="todo-list">
          <template v-for="group in groupedTodos" :key="group.tag">
            <button class="group-title" type="button" @click="toggleGroup(group.tag)">
              <span>#{{ group.tag }}</span>
              <span class="group-meta">
                <span class="group-count">{{ group.items.length }}</span>
                <span class="group-toggle">{{ isGroupCollapsed(group.tag) ? '展开' : '收起' }}</span>
              </span>
            </button>

            <div v-show="!isGroupCollapsed(group.tag)">
              <div
                v-for="t in group.items"
                :key="t.id"
                class="todo-item"
                :class="{ active: selected?.id === t.id }"
                @click="selectTodo(t.id)"
              >
                <el-icon
                  class="status-icon"
                  :class="{ done: t.status === 'done' }"
                  @click.stop="toggleDone(t)"
                >
                  <CircleCheckFilled v-if="t.status === 'done'" />
                  <CircleCheck v-else />
                </el-icon>

                <div class="todo-meta">
                  <div class="todo-title" :class="{ done: t.status === 'done' }">{{ t.title }}</div>
                  <div class="todo-sub">
                    <el-tag size="small" effect="plain">{{ statusLabel(t.status) }}</el-tag>
                    <span v-if="t.due_date" class="due-date">截止 {{ t.due_date }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <el-empty v-if="!todos.length" description="暂无待办" :image-size="80" />
        </div>
      </el-card>
    </el-col>

    <el-col :span="16" class="right-col">
      <el-card v-if="selected" class="right-card">
        <template #header>
          <div class="header-row">
            <span>任务详情</span>
            <el-space size="small">
              <el-text size="small" :type="saveStatusType">{{ saveStatusText }}</el-text>
              <el-text v-if="lastSavedAt" size="small" type="info">{{ lastSavedAt }}</el-text>
            </el-space>
          </div>
        </template>

        <el-form label-width="90px">
          <el-form-item label="标题">
            <el-input v-model="selected.title" />
          </el-form-item>

          <el-form-item label="状态">
            <el-segmented v-model="selected.status" :options="statusOptions" />
          </el-form-item>

          <el-form-item label="截止日期">
            <el-date-picker
              v-model="selected.due_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择截止日期"
              clearable
            />
          </el-form-item>

          <el-form-item label="标签">
            <div class="tag-editor">
              <el-select
                v-model="selectedTag"
                filterable
                allow-create
                default-first-option
                :reserve-keyword="false"
                placeholder="选择或输入一个标签"
                class="tag-select"
              >
                <el-option
                  v-for="tag in existingTags"
                  :key="tag"
                  :label="`#${tag}`"
                  :value="tag"
                />
              </el-select>
              <el-text type="info" size="small">单个待办仅支持 1 个标签</el-text>
            </div>
          </el-form-item>

          <el-divider>描述</el-divider>

          <RichTextEditor
            v-model:markdown="contentMarkdown"
            @update:html="onEditorHtmlUpdate"
            :upload-image="uploadAndGetImageUrl"
          />
        </el-form>
      </el-card>

      <el-empty v-else description="请选择左侧待办" />
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleCheckFilled } from '@element-plus/icons-vue'
import api from '../api'
import RichTextEditor from '../components/RichTextEditor.vue'

type Todo = {
  id: number
  title: string
  status: 'todo' | 'in_progress' | 'done'
  due_date: string | null
  tags: string[]
}

const todos = ref<Todo[]>([])
const selected = ref<Todo | null>(null)
const selectedTag = ref('未分类')
const collapsedGroups = ref<Record<string, boolean>>({})
const contentMarkdown = ref('')
const contentRichtext = ref('')
const autoSaveTimer = ref<number | null>(null)
const isHydrating = ref(false)
const saveState = ref<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle')
const lastSavedAt = ref('')

const statusOptions = [
  { label: '待办', value: 'todo' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'done' },
]

const statusLabel = (status: string) => {
  if (status === 'done') return '已完成'
  if (status === 'in_progress') return '进行中'
  return '待办'
}

const normalizeTag = (value: string) => value.trim().replace(/^#/, '') || '未分类'

const displayTag = (tags: string[] | undefined): string => {
  const first = tags?.[0]?.trim()
  return first || '未分类'
}

const dueSortValue = (dueDate: string | null): number => {
  if (!dueDate) return Number.POSITIVE_INFINITY
  const value = Date.parse(dueDate)
  return Number.isNaN(value) ? Number.POSITIVE_INFINITY : value
}

const existingTags = computed(() => {
  const tags = new Set<string>()
  for (const todo of todos.value) {
    tags.add(displayTag(todo.tags))
  }
  if (!tags.size) {
    tags.add('未分类')
  }
  return Array.from(tags).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
})

const groupedTodos = computed(() => {
  const map = new Map<string, Todo[]>()

  for (const todo of todos.value) {
    const tag = displayTag(todo.tags)
    if (!map.has(tag)) {
      map.set(tag, [])
    }
    map.get(tag)!.push(todo)
  }

  const groups = Array.from(map.entries()).map(([tag, items]) => ({
    tag,
    items: [...items].sort((a, b) => {
      const dueDiff = dueSortValue(a.due_date) - dueSortValue(b.due_date)
      if (dueDiff !== 0) return dueDiff
      return a.id - b.id
    }),
  }))

  groups.sort((a, b) => a.tag.localeCompare(b.tag, 'zh-Hans-CN'))

  const uncategorizedIndex = groups.findIndex((g) => g.tag === '未分类')
  if (uncategorizedIndex > 0) {
    const [uncategorized] = groups.splice(uncategorizedIndex, 1)
    groups.unshift(uncategorized)
  }

  for (const group of groups) {
    group.items.sort((a, b) => {
      if (a.status !== b.status) {
        if (a.status === 'done') return 1
        if (b.status === 'done') return -1
      }
      const dueDiff = dueSortValue(a.due_date) - dueSortValue(b.due_date)
      if (dueDiff !== 0) return dueDiff
      return a.id - b.id
    })
  }

  return groups
})

const saveStatusText = computed(() => {
  if (!selected.value) return '未选择任务'
  if (saveState.value === 'saving') return '保存中...'
  if (saveState.value === 'saved') return '已保存'
  if (saveState.value === 'error') return '保存失败'
  if (saveState.value === 'dirty') return '有未保存更改'
  return '待编辑'
})

const saveStatusType = computed(() => {
  if (saveState.value === 'saving') return 'warning'
  if (saveState.value === 'saved') return 'success'
  if (saveState.value === 'error') return 'danger'
  if (saveState.value === 'dirty') return 'warning'
  return 'info'
})

const isGroupCollapsed = (tag: string) => Boolean(collapsedGroups.value[tag])

const toggleGroup = (tag: string) => {
  collapsedGroups.value = {
    ...collapsedGroups.value,
    [tag]: !collapsedGroups.value[tag],
  }
}

const onEditorHtmlUpdate = (html: string) => {
  contentRichtext.value = html
}

const load = async () => {
  const { data } = await api.get('/api/todos')
  todos.value = data
}

const formatNow = () =>
  new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

const addTodo = async () => {
  const { data } = await api.post('/api/todos', { title: `新待办 ${Date.now()}`, tags: ['未分类'] })
  await load()
  await selectTodo(data.id)
}

const selectTodo = async (id: number) => {
  isHydrating.value = true
  const { data } = await api.get(`/api/todos/${id}`)
  selected.value = data.todo
  selectedTag.value = displayTag(data.todo?.tags)
  contentMarkdown.value = data.content?.content_markdown || ''
  contentRichtext.value = data.content?.content_richtext || ''
  saveState.value = 'idle'
  isHydrating.value = false
}

const toggleDone = async (todo: Todo) => {
  const target = todo.status === 'done' ? 'todo' : 'done'
  await api.patch(`/api/todos/${todo.id}`, { status: target })
  await load()
  if (selected.value?.id === todo.id) {
    await selectTodo(todo.id)
  }
}

const save = async (silent = false) => {
  if (!selected.value) return

  const currentId = selected.value.id
  saveState.value = 'saving'

  try {
    await api.patch(`/api/todos/${currentId}`, {
      title: selected.value.title,
      status: selected.value.status,
      due_date: selected.value.due_date,
      tags: [normalizeTag(selectedTag.value)],
      content_markdown: contentMarkdown.value,
      content_richtext: contentRichtext.value,
    })

    await load()
    saveState.value = 'saved'
    lastSavedAt.value = `上次保存 ${formatNow()}`

    if (!silent) {
      ElMessage.success('已保存')
    }
  } catch (error) {
    saveState.value = 'error'
    throw error
  }
}

const scheduleAutoSave = () => {
  if (isHydrating.value || !selected.value) return

  saveState.value = 'dirty'

  if (autoSaveTimer.value) {
    window.clearTimeout(autoSaveTimer.value)
  }

  autoSaveTimer.value = window.setTimeout(async () => {
    try {
      await save(true)
    } catch {
      ElMessage.error('自动保存失败')
    }
  }, 600)
}

const uploadAndGetImageUrl = async (file: File): Promise<string> => {
  if (!selected.value) throw new Error('请先选择待办')

  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post(`/api/todos/${selected.value.id}/images`, formData)
  ElMessage.success('图片上传成功')
  return data.url
}

watch(
  [
    () => selected.value?.title,
    () => selected.value?.status,
    () => selected.value?.due_date,
    selectedTag,
    contentMarkdown,
    contentRichtext,
  ],
  () => {
    scheduleAutoSave()
  },
)

onMounted(load)
</script>

<style scoped>
.todo-page {
  height: calc(100vh - 146px);
}

.left-col,
.right-col,
.left-card,
.right-card {
  height: 100%;
}

.todo-list {
  max-height: calc(100vh - 252px);
  overflow: auto;
  padding-right: 4px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.todo-item {
  display: flex;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
}

.todo-item:hover,
.todo-item.active {
  background: rgba(255, 255, 255, 0.16);
  border-color: var(--mx-border);
}

.status-icon {
  margin-top: 2px;
  color: var(--mx-text-muted);
}

.status-icon.done {
  color: var(--mx-success);
}

.todo-meta {
  flex: 1;
  min-width: 0;
}

.todo-title {
  font-weight: 500;
  word-break: break-word;
}

.todo-title.done {
  text-decoration: line-through;
  color: var(--mx-text-muted);
}

.todo-sub {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-title {
  width: 100%;
  font-size: 13px;
  color: var(--mx-text-normal);
  font-weight: 600;
  margin: 12px 0 6px;
  padding: 6px 8px;
  border: 1px solid var(--mx-border);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.group-title:first-child {
  margin-top: 0;
}

.group-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.group-count {
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: rgba(120, 120, 120, 0.22);
  color: var(--mx-text-normal);
  font-size: 12px;
  line-height: 20px;
  text-align: center;
  padding: 0 6px;
}

.group-toggle {
  font-size: 12px;
  color: var(--mx-text-muted);
}

.due-date {
  font-size: 12px;
  color: var(--mx-text-muted);
}

.tag-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  width: 100%;
}
</style>