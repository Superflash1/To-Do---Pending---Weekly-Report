<template>
  <div class="page logs-page">
    <el-card>
      <template #header>
        <div class="logs-header">
          <div>
            <div class="title">后端日志</div>
            <div class="sub">显示最近 {{ linesLimit }} 行（总计 {{ totalLines }} 行）</div>
          </div>
          <el-space>
            <el-input-number v-model="linesLimit" :min="50" :max="2000" :step="50" size="small" />
            <el-switch v-model="autoRefresh" active-text="自动刷新" inactive-text="手动" />
            <el-button @click="loadLogs" :loading="loading">刷新</el-button>
          </el-space>
        </div>
      </template>

      <el-empty v-if="!loading && !logLines.length" description="暂无日志" :image-size="80" />

      <pre v-else class="logs-console">{{ logLines.join('\n') }}</pre>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const logLines = ref<string[]>([])
const totalLines = ref(0)
const linesLimit = ref(300)
const autoRefresh = ref(true)
const loading = ref(false)
let timer: number | null = null

const clearTimer = () => {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

const startTimer = () => {
  clearTimer()
  if (!autoRefresh.value) return
  timer = window.setInterval(() => {
    void loadLogs(true)
  }, 3000)
}

const loadLogs = async (silent = false) => {
  loading.value = !silent
  try {
    const { data } = await api.get('/api/system/logs', {
      params: { lines: linesLimit.value },
    })
    logLines.value = data.lines || []
    totalLines.value = data.total || 0
  } catch {
    if (!silent) {
      ElMessage.error('加载日志失败')
    }
  } finally {
    loading.value = false
  }
}

watch(autoRefresh, () => {
  startTimer()
})

watch(linesLimit, () => {
  void loadLogs(true)
})

onMounted(async () => {
  await loadLogs()
  startTimer()
})

onBeforeUnmount(() => {
  clearTimer()
})
</script>

<style scoped>
.logs-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.title {
  font-size: 16px;
  font-weight: 700;
  color: var(--mx-text-strong);
}

.sub {
  font-size: 12px;
  color: var(--mx-text-muted);
  margin-top: 2px;
}

.logs-console {
  margin: 0;
  width: 100%;
  min-height: 520px;
  max-height: calc(100vh - 240px);
  overflow: auto;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--mx-border);
  background: rgba(20, 20, 24, 0.92);
  color: #d9e1ee;
  font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
