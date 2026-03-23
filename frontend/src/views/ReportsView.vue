<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-title">生成周报</div>
      </template>
      <el-form inline>
        <el-form-item label="完成时间范围">
          <el-date-picker
            v-model="completedRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            unlink-panels
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="generate">生成周报</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-title">历史周报</div>
      </template>
      <el-table :data="reports" stripe>
        <el-table-column prop="period_start" label="开始" width="120" />
        <el-table-column prop="period_end" label="结束" width="120" />
        <el-table-column prop="generated_at" label="生成时间" width="200" />
        <el-table-column label="内容预览" min-width="320">
          <template #default="scope">
            <div class="ellipsis-text">{{ scope.row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-space>
              <el-button size="small" @click="openDetail(scope.row)">查看</el-button>
              <el-popconfirm title="确认删除该周报？" @confirm="removeReport(scope.row.id)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="detailVisible" title="周报详情" width="760px">
      <div class="detail-box">
        {{ detailContent }}
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'

const reports = ref<any[]>([])
const completedRange = ref<[string, string] | null>(null)
const detailVisible = ref(false)
const detailContent = ref('')

const load = async () => {
  const { data } = await api.get('/api/reports/weekly')
  reports.value = data
}

const generate = async () => {
  const payload = completedRange.value
    ? {
        completed_start_date: completedRange.value[0],
        completed_end_date: completedRange.value[1],
      }
    : {}

  await api.post('/api/reports/weekly/generate', payload)
  ElMessage.success('周报已生成')
  load()
}

const openDetail = (row: any) => {
  detailContent.value = row?.content || ''
  detailVisible.value = true
}

const removeReport = async (id: number) => {
  await api.delete(`/api/reports/weekly/${id}`)
  ElMessage.success('周报已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
:deep(.el-form-item) {
  margin-bottom: 12px;
}

:deep(.el-table .cell) {
  line-height: 1.6;
}

.ellipsis-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-box {
  white-space: pre-wrap;
  line-height: 1.8;
  max-height: 60vh;
  overflow: auto;
  color: var(--mx-text-normal);
}
</style>