<template>
  <div class="page links-layout">
    <section class="left-panel">
      <el-card>
        <template #header>
          <div class="card-title">批量导入</div>
        </template>
        <el-form>
          <el-form-item label="批量链接（每行一个）">
            <el-input type="textarea" v-model="urlText" :rows="4" />
          </el-form-item>
          <el-space wrap>
            <el-button type="primary" @click="submitBatch">批量添加</el-button>
            <el-button :disabled="selectedLinkIds.length === 0" @click="batchReclassifyLinks">
              批量重新 AI 分类
            </el-button>
            <el-button @click="load">刷新</el-button>
            <el-switch
              v-model="showArchived"
              active-text="显示归档"
              inactive-text="隐藏归档"
              @change="load"
            />
          </el-space>
        </el-form>
      </el-card>

      <el-card>
        <template #header>
          <div class="card-title">标签管理</div>
        </template>
        <p class="section-tip">标签用于组织链接分组，删除标签不会删除链接本身。</p>
        <el-form inline style="margin-bottom: 12px">
          <el-form-item label="新增标签">
            <el-input v-model="newTag.name" placeholder="标签名" style="width: 180px" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="newTag.description" placeholder="说明(可选)" style="width: 260px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="addTag">新增标签</el-button>
          </el-form-item>
        </el-form>
        <el-table :data="categories" stripe>
          <el-table-column label="标签" min-width="170">
            <template #default="scope">
              <div class="tag-name-cell">
                <div class="tag-name">{{ scope.row.name }}</div>
                <div v-if="scope.row.description" class="tag-desc">{{ scope.row.description }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="128" fixed="right">
            <template #default="scope">
              <el-space size="small">
                <el-button size="small" text @click="openEditTag(scope.row)">编辑</el-button>
                <el-popconfirm title="删除后会保留链接，但清空它们的标签，确认？" @confirm="removeTag(scope.row.id)">
                  <template #reference>
                    <el-button size="small" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <section class="right-panel">
      <el-card v-for="group in groupedLinks" :key="group.tagName">
        <template #header>
          <div class="group-header">
            <div class="card-title">{{ group.tagName }}</div>
            <el-tag type="info" effect="plain">{{ group.items.length }} 条</el-tag>
          </div>
        </template>

        <div class="link-card-list">
          <article v-for="item in group.items" :key="item.id" class="link-card-item">
            <div class="link-card-main">
              <el-checkbox
                :model-value="selectedLinkIds.includes(item.id)"
                @change="(val) => toggleLinkSelected(item.id, val as boolean)"
              />
              <div class="link-content">
                <div class="title-line">{{ item.title || '未命名链接' }}</div>
                <a class="url-line" :href="item.url" target="_blank" rel="noreferrer">{{ item.url }}</a>
                <div class="meta-line">
                  <el-tag size="small" :type="classificationSourceTagType(item.classification_source)">
                    {{ classificationSourceLabel(item.classification_source) }}
                  </el-tag>
                  <el-select
                    :model-value="item.status"
                    size="small"
                    style="width: 96px"
                    @change="(val) => patchLink(item.id, { status: val })"
                  >
                    <el-option value="unread" label="未读" />
                    <el-option value="read" label="已读" />
                    <el-option value="ignored" label="忽略" />
                  </el-select>
                  <el-select
                    :model-value="item.category_id"
                    size="small"
                    style="width: 140px"
                    placeholder="标签"
                    @change="(val) => patchLink(item.id, { category_id: val })"
                  >
                    <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="op-cell">
              <el-button size="small" text type="primary" @click="reclassifyLink(item.id)">重分</el-button>
              <el-button
                size="small"
                text
                :type="item.is_archived ? 'warning' : 'info'"
                @click="toggleArchive(item)"
              >
                {{ item.is_archived ? '取消归档' : '归档' }}
              </el-button>
              <el-popconfirm title="永久删除该链接？该操作不可恢复" @confirm="deleteLink(item.id)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </article>
        </div>
      </el-card>
    </section>

    <el-dialog v-model="tagDialogVisible" title="编辑标签" width="520px">
      <el-form label-width="90px">
        <el-form-item label="标签名">
          <el-input v-model="editingTag.name" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editingTag.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTag">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

type LinkItem = {
  id: number
  url: string
  title: string
  status: string
  category_id: number | null
  category_name: string | null
  classification_source: string
  classification_confidence: number | null
  created_at?: string
  is_archived?: boolean
}

type LinkCategory = {
  id: number
  name: string
  description: string
}

const urlText = ref('')
const links = ref<LinkItem[]>([])
const categories = ref<LinkCategory[]>([])
const showArchived = ref(false)
const newTag = ref({ name: '', description: '' })

const tagDialogVisible = ref(false)
const selectedLinkIds = ref<number[]>([])
const editingTag = ref<{ id: number | null; name: string; description: string }>({
  id: null,
  name: '',
  description: '',
})

const loadCategories = async () => {
  const { data } = await api.get('/api/link-categories')
  categories.value = data
}

const addTag = async () => {
  const name = newTag.value.name.trim()
  if (!name) {
    ElMessage.warning('请先输入标签名')
    return
  }
  await api.post('/api/link-categories', {
    name,
    description: newTag.value.description.trim(),
  })
  ElMessage.success('标签已新增')
  newTag.value = { name: '', description: '' }
  await loadCategories()
}

const load = async () => {
  const { data } = await api.get('/api/links')
  const filtered = (data as LinkItem[]).filter((i) => (showArchived.value ? true : !i.is_archived))
  links.value = filtered
  selectedLinkIds.value = []
}

const classificationSourceLabel = (source: string) => {
  if (source === 'manual') return '人工'
  if (source === 'queued') return '排队中'
  if (source === 'fallback_retrying') return '回退重试'
  if (source === 'fallback_failed') return '回退失败'
  if (source === 'ai') return 'AI'
  return source || '未知'
}

const classificationSourceTagType = (source: string) => {
  if (source === 'manual') return 'success'
  if (source === 'queued') return 'warning'
  if (source === 'fallback_retrying') return 'warning'
  if (source === 'fallback_failed') return 'danger'
  return 'info'
}

const groupedLinks = computed(() => {
  const map = new Map<string, LinkItem[]>()

  for (const item of links.value) {
    const tagName = (item.category_name || '未打标签').trim()
    if (!map.has(tagName)) map.set(tagName, [])
    map.get(tagName)!.push(item)
  }

  return Array.from(map.entries())
    .sort((a, b) => a[0].localeCompare(b[0], 'zh-CN'))
    .map(([tagName, items]) => ({
      tagName,
      items: [...items].sort((a, b) => {
        const at = a.created_at ? new Date(a.created_at).getTime() : 0
        const bt = b.created_at ? new Date(b.created_at).getTime() : 0
        return bt - at
      }),
    }))
})

const submitBatch = async () => {
  const urls = urlText.value
    .split('\n')
    .map((i) => i.trim())
    .filter(Boolean)
  if (!urls.length) return
  await api.post('/api/links/batch', { urls })
  ElMessage.success('添加成功')
  urlText.value = ''
  await loadCategories()
  await load()
}

const patchLink = async (id: number, payload: Record<string, any>) => {
  await api.patch(`/api/links/${id}`, payload)
  const target = links.value.find((item) => item.id === id)
  if (target) {
    Object.assign(target, payload)
    if (typeof payload.category_id !== 'undefined') {
      const category = categories.value.find((c) => c.id === payload.category_id)
      target.category_name = category?.name || null
    }
  }
  ElMessage.success('已更新')
}

const toggleArchive = async (row: LinkItem) => {
  await patchLink(row.id, { is_archived: !row.is_archived })
}

const deleteLink = async (id: number) => {
  await api.delete(`/api/links/${id}`)
  ElMessage.success('链接已永久删除')
  await load()
}

const reclassifyLink = async (id: number) => {
  await api.post(`/api/links/${id}/reclassify`)
  ElMessage.success('重新分类完成')
  await loadCategories()
  await load()
}

const toggleLinkSelected = (id: number, checked: boolean) => {
  if (checked) {
    if (!selectedLinkIds.value.includes(id)) {
      selectedLinkIds.value = [...selectedLinkIds.value, id]
    }
    return
  }

  selectedLinkIds.value = selectedLinkIds.value.filter((linkId) => linkId !== id)
}

const batchReclassifyLinks = async () => {
  if (!selectedLinkIds.value.length) {
    ElMessage.warning('请先选择要重新 AI 分类的链接')
    return
  }

  try {
    await ElMessageBox.confirm(
      `将对 ${selectedLinkIds.value.length} 条链接执行重新 AI 分类，是否继续？`,
      '批量重新 AI 分类',
      {
        type: 'warning',
        confirmButtonText: '继续',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  const ids = [...selectedLinkIds.value]
  const concurrency = 4
  let successCount = 0
  let failCount = 0

  for (let i = 0; i < ids.length; i += concurrency) {
    const chunk = ids.slice(i, i + concurrency)
    const results = await Promise.allSettled(chunk.map((id) => api.post(`/api/links/${id}/reclassify`)))

    for (const result of results) {
      if (result.status === 'fulfilled') {
        successCount += 1
      } else {
        failCount += 1
      }
    }
  }

  if (failCount === 0) {
    ElMessage.success(`批量重新分类完成：成功 ${successCount} 条`)
  } else {
    ElMessage.warning(`批量重新分类完成：成功 ${successCount} 条，失败 ${failCount} 条`)
  }

  await loadCategories()
  await load()
}

const openEditTag = (row: LinkCategory) => {
  editingTag.value = { id: row.id, name: row.name, description: row.description || '' }
  tagDialogVisible.value = true
}

const saveTag = async () => {
  if (!editingTag.value.id) return
  await api.patch(`/api/link-categories/${editingTag.value.id}`, {
    name: editingTag.value.name,
    description: editingTag.value.description,
  })
  ElMessage.success('标签已保存')
  tagDialogVisible.value = false
  await loadCategories()
  await load()
}

const removeTag = async (id: number) => {
  await api.delete(`/api/link-categories/${id}`)
  ElMessage.success('标签已删除，原链接已变为未打标签')
  await loadCategories()
  await load()
}

onMounted(async () => {
  await loadCategories()
  await load()
})
</script>

<style scoped>
.links-layout {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  align-items: start;
  gap: 16px;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.section-tip {
  margin: 0 0 12px;
  color: var(--mx-text-muted);
  font-size: 13px;
}

.tag-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tag-name {
  color: var(--mx-text-strong);
  font-weight: 600;
}

.tag-desc {
  color: var(--mx-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

:deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-table .cell) {
  line-height: 1.6;
}


.title-line {
  font-weight: 600;
  color: var(--mx-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.url-line {
  display: block;
  margin-top: 2px;
  color: var(--mx-text-muted);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.link-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.link-card-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--mx-border);
  background: rgba(255, 255, 255, 0.12);
}

.link-card-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.link-content {
  min-width: 0;
  flex: 1;
}

.meta-line {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.op-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

:deep(.op-cell .el-button + .el-button) {
  margin-left: 0;
}

@media (max-width: 1200px) {
  .links-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .link-card-item {
    flex-direction: column;
  }

  .op-cell {
    width: 100%;
  }
}
</style>