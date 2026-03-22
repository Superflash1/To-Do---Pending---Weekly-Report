<template>
  <div class="app-shell" :class="[`theme-${theme}`]">
    <div class="bg-noise"></div>
    <div class="bg-spot spot-a"></div>
    <div class="bg-spot spot-b"></div>

    <template v-if="loggedIn">
      <section class="brand-hero glass-panel">
        <div class="brand-main">
          <div class="brand-dot"></div>
          <div>
            <div class="brand">明心</div>
            <div class="brand-sub">明心 · 知行控制台</div>
          </div>
        </div>
        <div class="brand-tags">
          <span>To-Do</span>
          <span>To-Read</span>
          <span>To-Report</span>
          <span>Inspire</span>
        </div>
      </section>

      <header class="top-nav glass-panel">
        <el-menu router mode="horizontal" :default-active="activePath" class="nav-menu">
          <el-menu-item index="/">指挥台</el-menu-item>
          <el-menu-item index="/links">待读池</el-menu-item>
          <el-menu-item index="/todos">待办池</el-menu-item>
          <el-menu-item index="/reports">周报引擎</el-menu-item>
          <el-menu-item index="/settings">提醒中枢</el-menu-item>
        </el-menu>

        <div class="actions-wrap">
          <el-button class="theme-btn" @click="toggleTheme">
            {{ theme === 'light' ? '切换暗色' : '切换浅色' }}
          </el-button>
          <el-button type="danger" class="logout-btn" @click="logout">退出</el-button>
        </div>
      </header>

      <main class="page-wrap">
        <router-view />
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
  padding: 14px 16px 18px;
  position: relative;
  overflow: hidden;
}

.bg-noise {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(128, 128, 128, 0.08) 0.5px, transparent 0.5px);
  background-size: 3px 3px;
  opacity: 0.2;
  pointer-events: none;
}

.bg-spot {
  position: absolute;
  border-radius: 999px;
  filter: blur(60px);
  pointer-events: none;
}

.spot-a {
  width: 380px;
  height: 380px;
  left: -120px;
  top: -120px;
  background: rgba(120, 120, 120, 0.12);
}

.spot-b {
  width: 320px;
  height: 320px;
  right: -80px;
  top: 10%;
  background: rgba(80, 80, 80, 0.1);
}

.brand-hero {
  width: min(1280px, 100%);
  margin: 0 auto 10px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  position: relative;
  z-index: 2;
  overflow: hidden;
  animation: heroFloatIn 620ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.brand-hero::before,
.brand-hero::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
}

.brand-hero::before {
  width: 220px;
  height: 220px;
  right: -76px;
  top: -118px;
  background: radial-gradient(circle, rgba(130, 130, 130, 0.2), rgba(130, 130, 130, 0));
  animation: pulseDrift 7.5s ease-in-out infinite;
}

.brand-hero::after {
  width: 140px;
  height: 140px;
  left: 32%;
  bottom: -84px;
  background: radial-gradient(circle, rgba(80, 80, 80, 0.14), rgba(80, 80, 80, 0));
  animation: pulseDrift 9s ease-in-out infinite reverse;
}

.brand-main {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: var(--mx-text-strong);
  box-shadow: 0 0 0 5px rgba(120, 120, 120, 0.2);
  animation: dotBreath 2.8s ease-in-out infinite;
}

.brand {
  font-size: 24px;
  font-weight: 750;
  color: var(--mx-text-strong);
  line-height: 1.1;
  letter-spacing: 0.01em;
  background: linear-gradient(110deg, var(--mx-text-strong) 15%, rgba(128, 128, 128, 0.9) 48%, var(--mx-text-strong) 82%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  background-size: 220% 100%;
  animation: wordShimmer 6.2s linear infinite;
}

.brand-sub {
  font-size: 12px;
  color: var(--mx-text-muted);
  margin-top: 2px;
}

.brand-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  position: relative;
  z-index: 1;
}

.brand-tags span {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--mx-border);
  color: var(--mx-text-muted);
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.14);
  transform: translateY(0);
  transition: transform 260ms ease, background-color 260ms ease, border-color 260ms ease;
}

.brand-tags span:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.24);
  border-color: var(--mx-border-strong);
}

.brand-tags span:nth-child(1) {
  animation: chipRise 700ms cubic-bezier(0.2, 0.8, 0.2, 1) 60ms both;
}

.brand-tags span:nth-child(2) {
  animation: chipRise 700ms cubic-bezier(0.2, 0.8, 0.2, 1) 120ms both;
}

.brand-tags span:nth-child(3) {
  animation: chipRise 700ms cubic-bezier(0.2, 0.8, 0.2, 1) 180ms both;
}

.brand-tags span:nth-child(4) {
  animation: chipRise 700ms cubic-bezier(0.2, 0.8, 0.2, 1) 240ms both;
}

.top-nav {
  width: min(1280px, 100%);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  position: sticky;
  top: 10px;
  z-index: 20;
}

.nav-menu {
  flex: 1;
  border-bottom: none;
  background: transparent;
}

:deep(.nav-menu.el-menu--horizontal > .el-menu-item) {
  border-bottom: none;
  border-radius: 999px;
  margin-right: 4px;
  color: var(--mx-text-muted);
  height: 36px;
  line-height: 36px;
  font-size: 15px;
  font-weight: 650;
  padding: 0 12px;
  position: relative;
  overflow: hidden;
  transition: color 220ms ease, background-color 220ms ease, transform 220ms ease, box-shadow 220ms ease;
}

:deep(.nav-menu.el-menu--horizontal > .el-menu-item::after) {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border: 1px solid transparent;
  transition: border-color 220ms ease;
  pointer-events: none;
}

:deep(.nav-menu.el-menu--horizontal > .el-menu-item:hover) {
  color: var(--mx-text-normal);
  background: var(--mx-pill-hover);
  transform: translateY(-1px);
}

:deep(.nav-menu.el-menu--horizontal > .el-menu-item:hover::after) {
  border-color: var(--mx-border);
}

:deep(.nav-menu.el-menu--horizontal > .el-menu-item.is-active) {
  color: var(--mx-text-strong);
  background: var(--mx-pill-active);
  box-shadow: inset 0 0 0 1px var(--mx-border-strong), 0 6px 14px rgba(0, 0, 0, 0.08);
}

.actions-wrap {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.theme-btn {
  min-width: 94px;
}

.page-wrap {
  margin: 12px auto 0;
  width: min(1280px, 100%);
  position: relative;
  z-index: 2;
}

.login-wrap {
  min-height: calc(100vh - 40px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
}

@keyframes heroFloatIn {
  0% {
    opacity: 0;
    transform: translateY(-8px) scale(0.995);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes dotBreath {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 5px rgba(120, 120, 120, 0.18);
  }
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 0 8px rgba(120, 120, 120, 0.12);
  }
}

@keyframes wordShimmer {
  0% {
    background-position: 200% 50%;
  }
  100% {
    background-position: -20% 50%;
  }
}

@keyframes pulseDrift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.9;
  }
  50% {
    transform: translate3d(0, 10px, 0) scale(1.05);
    opacity: 0.5;
  }
}

@keyframes chipRise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .brand-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .top-nav {
    flex-wrap: wrap;
  }

  .actions-wrap {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>