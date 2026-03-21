<template>
  <el-container style="min-height: 100vh">
    <el-aside v-if="loggedIn" width="220px" style="background: #1f2937; color: white">
      <div style="padding: 20px; font-weight: 700">第二大脑工具</div>
      <el-menu router background-color="#1f2937" text-color="#fff" active-text-color="#ffd04b">
        <el-menu-item index="/">仪表盘</el-menu-item>
        <el-menu-item index="/links">链接池</el-menu-item>
        <el-menu-item index="/todos">待办池</el-menu-item>
        <el-menu-item index="/reports">周报</el-menu-item>
        <el-menu-item index="/settings">设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header v-if="loggedIn" style="display:flex; justify-content:flex-end; align-items:center; gap:10px;">
        <el-button type="danger" plain @click="logout">退出登录</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loggedIn = computed(() => !!localStorage.getItem('token'))

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>