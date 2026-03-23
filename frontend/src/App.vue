<template>
  <div class="app-shell" :class="[`theme-${theme}`]">
    <div class="bg-noise"></div>

    <template v-if="loggedIn">
      <aside class="side-nav glass-panel">
        <section class="brand-hero">
          <div class="brand-mark">明</div>
          <div class="brand-meta">
            <div class="brand">明心</div>
            <div class="brand-sub">知行控制台</div>
          </div>
        </section>

        <el-menu router mode="vertical" :default-active="activePath" class="nav-menu">
          <el-menu-item index="/">指挥台</el-menu-item>
          <el-menu-item index="/links">待读池</el-menu-item>
          <el-menu-item index="/todos">待办池</el-menu-item>
          <el-menu-item index="/reports">周报引擎</el-menu-item>
          <el-menu-item index="/settings">提醒中枢</el-menu-item>
          <el-menu-item index="/logs">后端日志</el-menu-item>
        </el-menu>

        <section class="actions-wrap">
          <el-button class="theme-btn" @click="toggleTheme">
            {{ theme === 'light' ? '切换暗色' : '切换浅色' }}
          </el-button>
          <el-button type="danger" class="logout-btn" @click="logout">退出</el-button>
        </section>
      </aside>

      <main class="main-shell">
        <section class="page-wrap">
          <router-view />
        </section>
      </main>
    </template>

    <template v-else>
      <main class="login-wrap">
        <router-view />
      </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

const loggedIn = computed(() => !!localStorage.getItem('token'))
const activePath = computed(() => route.path)

const theme = ref<'light' | 'dark'>('light')

const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', theme.value)
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  theme.value = saved === 'dark' ? 'dark' : 'light'
  applyTheme()
})

watch(theme, () => {
  localStorage.setItem('theme', theme.value)
  applyTheme()
})

const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 12px;
  position: relative;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 12px;
}

.bg-noise {
  position: fixed;
  inset: 0;
  background-image: radial-gradient(rgba(128, 128, 128, 0.08) 0.5px, transparent 0.5px);
  background-size: 3px 3px;
  opacity: 0.14;
  pointer-events: none;
}

.side-nav {
  position: sticky;
  top: 12px;
  height: calc(100vh - 24px);
  padding: 12px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brand-hero {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(145deg, var(--mx-text-strong), rgba(80, 80, 80, 0.88));
  color: var(--mx-bg-0);
  display: grid;
  place-items: center;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.2);
}

.brand-meta {
  min-width: 0;
}

.brand {
  font-size: 18px;
  font-weight: 750;
  color: var(--mx-text-strong);
  line-height: 1.2;
}

.brand-sub {
  margin-top: 1px;
  font-size: 12px;
  color: var(--mx-text-muted);
}

.nav-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

:deep(.nav-menu .el-menu-item) {
  margin: 0 0 6px;
  height: 38px;
  line-height: 38px;
  border-radius: 10px;
  color: var(--mx-text-muted);
  font-weight: 650;
  transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
}

:deep(.nav-menu .el-menu-item:hover) {
  color: var(--mx-text-normal);
  background: var(--mx-pill-hover);
  transform: translateX(1px);
}

:deep(.nav-menu .el-menu-item.is-active) {
  color: var(--mx-text-strong);
  background: var(--mx-pill-active);
  box-shadow: inset 0 0 0 1px var(--mx-border-strong);
}

.actions-wrap {
  margin-top: auto;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
}

:deep(.actions-wrap .el-button + .el-button) {
  margin-left: 0;
}

.theme-btn,
.logout-btn {
  width: 100% !important;
  height: 38px;
  margin: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-shell {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.page-wrap {
  min-width: 0;
}

.login-wrap {
  min-height: calc(100vh - 40px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
  grid-column: 1 / -1;
}

@media (max-width: 1024px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .side-nav {
    position: static;
    height: auto;
  }

  .actions-wrap {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
