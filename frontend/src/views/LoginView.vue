<template>
  <div class="login-page">
    <div class="lightbeam beam-a"></div>
    <div class="lightbeam beam-b"></div>
    <div class="lightbeam beam-c"></div>

    <el-card class="login-card">
      <div class="brand-mini">明心</div>
      <h1>知是行之始，行是知之成</h1>
      <p>连接待读、待办、周报与提醒，形成你的知行闭环。</p>

      <el-form :model="form" label-position="top" class="login-form">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="you@example.com" size="large" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            size="large"
          />
        </el-form-item>

        <el-form-item label="昵称（仅注册可选）">
          <el-input v-model="form.display_name" placeholder="你的显示名称" size="large" />
        </el-form-item>

        <div class="login-actions">
          <el-button type="primary" size="large" @click="login">进入明心</el-button>
          <el-button size="large" @click="register">注册账号</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const form = reactive({ email: '', password: '', display_name: '' })

const getErrorMessage = (error: any, fallback: string) => {
  return error?.response?.data?.detail || error?.message || fallback
}

const register = async () => {
  const payload = {
    email: form.email.trim(),
    password: form.password,
    display_name: form.display_name.trim(),
  }

  if (!payload.email || !payload.password) {
    ElMessage.warning('请先填写邮箱和密码')
    return
  }

  if (payload.password.length < 6) {
    ElMessage.warning('密码至少需要 6 位')
    return
  }

  try {
    await api.post('/api/auth/register', payload)
    ElMessage.success('注册成功，请登录')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '注册失败'))
  }
}

const login = async () => {
  const payload = { email: form.email.trim(), password: form.password }

  if (!payload.email || !payload.password) {
    ElMessage.warning('请先填写邮箱和密码')
    return
  }

  try {
    const { data } = await api.post('/api/auth/login', payload)
    localStorage.setItem('token', data.access_token)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '登录失败'))
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  width: min(96vw, 1140px);
  min-height: 76vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: min(92vw, 520px);
  border-radius: 22px !important;
  z-index: 2;
  position: relative;
  overflow: hidden;
}

.login-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border: 1px solid var(--mx-border);
  pointer-events: none;
}

.brand-mini {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  color: var(--mx-text-muted);
  border: 1px solid var(--mx-border);
  background: rgba(255, 255, 255, 0.2);
  font-size: 12px;
  margin-bottom: 10px;
}

h1 {
  margin: 0;
  font-size: 26px;
  line-height: 1.3;
  color: var(--mx-text-strong);
}

p {
  margin: 10px 0 18px;
  color: var(--mx-text-muted);
  line-height: 1.7;
}

.login-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.lightbeam {
  position: absolute;
  border-radius: 999px;
  filter: blur(50px);
  opacity: 0.35;
}

.beam-a {
  width: 300px;
  height: 300px;
  left: 6%;
  top: 8%;
  background: rgba(120, 120, 120, 0.3);
}

.beam-b {
  width: 240px;
  height: 240px;
  right: 10%;
  top: 12%;
  background: rgba(90, 90, 90, 0.28);
}

.beam-c {
  width: 260px;
  height: 260px;
  right: 24%;
  bottom: 6%;
  background: rgba(140, 140, 140, 0.22);
}
</style>