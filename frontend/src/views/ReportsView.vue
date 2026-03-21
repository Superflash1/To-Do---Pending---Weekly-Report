<template>
  <el-card>
    <template #header>周报</template>
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

  <el-card style="margin-top: 16px">
    <el-table :data="reports" stripe>
      <el-table-column prop="period_start" label="开始" width="120" />
      <el-table-column prop="period_end" label="结束" width="120" />
      <el-table-column prop="generated_at" label="生成时间" />
      <el-table-column prop="content" label="内容" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'

const reports = ref<any[]>([])
const completedRange = ref<[string, string] | null>(null)

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

onMounted(load)
</script>