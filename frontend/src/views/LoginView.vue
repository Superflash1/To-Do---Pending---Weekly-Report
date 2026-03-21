<template>
  <el-row justify="center" style="margin-top: 120px">
    <el-col :span="8">
      <el-card>
        <template #header>登录 / 注册</template>
        <el-form :model="form" label-width="80px">
          <el-form-item label="邮箱">
            <el-input v-model="form.email" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password />
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="form.display_name" />
          </el-form-item>
          <el-space>
            <el-button type="primary" @click="register">注册</el-button>
            <el-button type="success" @click="login">登录</el-button>
          </el-space>
        </el-form>
      </el-card>
    </el-col>
  </el-row>
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