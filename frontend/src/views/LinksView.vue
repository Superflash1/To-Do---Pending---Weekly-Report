<template>
  <div class="page">
    <el-card>
      <h2 class="page-title">待读池</h2>
      <p class="page-subtitle">收集有价值输入，把外部灵感转成可执行线索</p>
    </el-card>

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
        <el-table-column prop="name" label="标签名" min-width="220" />
        <el-table-column prop="description" label="说明" min-width="260" />
        <el-table-column label="操作" width="240">
          <template #default="scope">
            <el-space>
              <el-button size="small" @click="openEditTag(scope.row)">编辑</el-button>
              <el-popconfirm title="删除后会保留链接，但清空它们的标签，确认？" @confirm="removeTag(scope.row.id)">
                <template #reference>
                  <el-button size="small" type="danger" plain>删除标签</el-button>
                </template>
              </el-popconfirm>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-for="group in groupedLinks" :key="group.tagName">
      <template #header>
        <div class="card-title">{{ group.tagName }}</div>
      </template>
      <el-table :data="group.items" stripe>
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="链接" min-width="280">
          <template #default="scope">
            <a :href="scope.row.url" target="_blank" rel="noreferrer">{{ scope.row.url }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-select
              :model-value="scope.row.status"
              size="small"
              style="width: 100px"
              @change="(val) => patchLink(scope.row.id, { status: val })"
            >
              <el-option value="unread" label="未读" />
              <el-option value="read" label="已读" />
              <el-option value="ignored" label="忽略" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="180">
          <template #default="scope">
            <el-select
              :model-value="scope.row.category_id"
              size="small"
              style="width: 160px"
              placeholder="选择标签"
              @change="(val) => patchLink(scope.row.id, { category_id: val })"
            >
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="scope">
            <el-tag size="small" :type="scope.row.classification_source === 'manual' ? 'success' : 'info'">
              {{ scope.row.classification_source === 'manual' ? '人工' : 'AI' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320">
          <template #default="scope">
            <el-space>
              <el-button
                v-if="!scope.row.category_name || scope.row.category_name === '未分类' || scope.row.category_name === '未打标签'"
                size="small"
                type="primary"
                plain
                @click="reclassifyLink(scope.row.id)"
              >
                重新分类
              </el-button>
              <el-button
                size="small"
                :type="scope.row.is_archived ? 'warning' : 'info'"
                plain
                @click="toggleArchive(scope.row)"
              >
                {{ scope.row.is_archived ? '取消归档' : '归档' }}
              </el-button>
              <el-popconfirm title="永久删除该链接？该操作不可恢复" @confirm="deleteLink(scope.row.id)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
import { ElMessage } from 'element-plus'
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
  ElMessage.success('已更新')
  await load()
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
.section-tip {
  margin: 0 0 12px;
  color: var(--mx-text-muted);
  font-size: 13px;
}

:deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-table .cell) {
  line-height: 1.6;
}
</style>