<template>
  <div class="dashboard-page page">
    <el-card class="hero-card">
      <div class="hero-top">
        <div>
          <div class="hero-badge">明心 · 知行指挥台</div>
          <h2 class="page-title">今日知行节奏</h2>
          <p class="page-subtitle">把待读转行动、把行动沉淀成周报，让每周都有可见成长。</p>
        </div>
      </div>

      <div class="pipeline">
        <button class="pipe-node" type="button" @click="goTo('/links')">
          <span>待读池</span>
          <strong>{{ linkStats.total }}</strong>
        </button>
        <div class="pipe-arrow">→</div>
        <button class="pipe-node" type="button" @click="goTo('/todos')">
          <span>待办池</span>
          <strong>{{ todoStats.total }}</strong>
        </button>
        <div class="pipe-arrow">→</div>
        <button class="pipe-node" type="button" @click="goTo('/reports')">
          <span>周报候选</span>
          <strong>{{ todoStats.done }}</strong>
        </button>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card class="stat-card clickable-card" @click="goTo('/links')">
          <template #header>
            <div class="section-title">待读池状态</div>
          </template>

          <div class="stat-grid">
            <div class="stat-item">
              <span>总链接</span>
              <strong>{{ linkStats.total }}</strong>
            </div>
            <div class="stat-item">
              <span>未读</span>
              <strong>{{ linkStats.unread }}</strong>
            </div>
            <div class="stat-item">
              <span>已读</span>
              <strong>{{ linkStats.read }}</strong>
            </div>
            <div class="stat-item">
              <span>归档</span>
              <strong>{{ linkStats.archived }}</strong>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="stat-card clickable-card" @click="goTo('/todos')">
          <template #header>
            <div class="section-title">待办池状态</div>
          </template>

          <div class="stat-grid">
            <div class="stat-item">
              <span>总任务</span>
              <strong>{{ todoStats.total }}</strong>
            </div>
            <div class="stat-item">
              <span>待办</span>
              <strong>{{ todoStats.todo }}</strong>
            </div>
            <div class="stat-item">
              <span>进行中</span>
              <strong>{{ todoStats.inProgress }}</strong>
            </div>
            <div class="stat-item">
              <span>已完成</span>
              <strong>{{ todoStats.done }}</strong>
            </div>
          </div>

          <div class="progress-wrap">
            <div class="progress-label">知行完成率：{{ completionRate }}%</div>
            <el-progress :percentage="completionRate" :stroke-width="10" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

type LinkItem = {
  status: 'unread' | 'read' | 'ignored'
  is_archived?: boolean
}

type TodoItem = {
  status: 'todo' | 'in_progress' | 'done'
}

const router = useRouter()

const links = ref<LinkItem[]>([])
const todos = ref<TodoItem[]>([])

const goTo = (path: string) => {
  router.push(path)
}

const load = async () => {
  const [linksRes, todosRes] = await Promise.all([api.get('/api/links'), api.get('/api/todos')])
  links.value = linksRes.data || []
  todos.value = todosRes.data || []
}

const linkStats = computed(() => {
  const total = links.value.length
  const unread = links.value.filter((i) => i.status === 'unread').length
  const read = links.value.filter((i) => i.status === 'read').length
  const archived = links.value.filter((i) => i.is_archived).length
  return { total, unread, read, archived }
})

const todoStats = computed(() => {
  const total = todos.value.length
  const todo = todos.value.filter((i) => i.status === 'todo').length
  const inProgress = todos.value.filter((i) => i.status === 'in_progress').length
  const done = todos.value.filter((i) => i.status === 'done').length
  return { total, todo, inProgress, done }
})

const completionRate = computed(() => {
  if (!todoStats.value.total) return 0
  return Math.round((todoStats.value.done / todoStats.value.total) * 100)
})

onMounted(load)
</script>

<style scoped>
.hero-card {
  position: relative;
  overflow: hidden;
}

.hero-card::before {
  content: '';
  position: absolute;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  right: -70px;
  top: -110px;
  background: radial-gradient(circle, rgba(0, 0, 0, 0.16), rgba(0, 0, 0, 0));
  pointer-events: none;
}

.hero-badge {
  display: inline-block;
  margin-bottom: 10px;
  padding: 5px 12px;
  border: 1px solid var(--mx-border);
  border-radius: 999px;
  color: var(--mx-text-muted);
  font-size: 12px;
  background: rgba(255, 255, 255, 0.22);
}

.pipeline {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pipe-node {
  min-width: 130px;
  padding: 11px 14px;
  border: 1px solid var(--mx-border);
  background: rgba(255, 255, 255, 0.16);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.pipe-node:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.2);
  border-color: var(--mx-border-strong);
}

.pipe-node:focus-visible {
  outline: 2px solid rgba(120, 120, 120, 0.42);
  outline-offset: 2px;
}

.pipe-node span {
  font-size: 12px;
  color: var(--mx-text-muted);
}

.pipe-node strong {
  font-size: 24px;
  color: var(--mx-text-strong);
}

.pipe-arrow {
  color: var(--mx-text-muted);
  font-weight: 700;
}

.section-title {
  font-weight: 700;
  color: var(--mx-text-strong);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--mx-border);
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item span {
  color: var(--mx-text-muted);
  font-size: 13px;
}

.stat-item strong {
  color: var(--mx-text-strong);
  font-size: 23px;
}

.progress-wrap {
  margin-top: 14px;
}

.progress-label {
  margin-bottom: 8px;
  color: var(--mx-text-muted);
}

.clickable-card {
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background-color 160ms ease;
}

.clickable-card:hover {
  transform: translateY(-1px);
}
</style>