<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-title">系统配置</div>
      </template>

      <el-form label-width="220px" class="settings-form">
        <el-divider content-position="left">偏好设置</el-divider>
        <el-form-item label="未读链接提醒阈值">
          <el-input-number v-model="prefs.unread_link_threshold" :min="1" />
        </el-form-item>
        <el-form-item label="周报触发星期(0-6)">
          <el-input-number v-model="prefs.weekly_report_day_of_week" :min="0" :max="6" />
        </el-form-item>
        <el-form-item label="周报提示词模板">
          <el-input
            v-model="prefs.weekly_report_prompt_template"
            type="textarea"
            :rows="5"
            placeholder="可用变量：{completed_start_date}、{completed_end_date}、{completed_range_text}"
          />
          <div class="hint">
            可用变量：<code>{completed_start_date}</code>（完成事项起始日期）、<code>{completed_end_date}</code>（完成事项结束日期）、<code>{completed_range_text}</code>（日期范围文本）。
            系统会在调用模型前自动替换这些变量。
          </div>
        </el-form-item>
        <el-form-item label="链接分类提示词模板">
          <el-input
            v-model="prefs.link_classification_prompt_template"
            type="textarea"
            :rows="7"
            placeholder="可用变量：{existing_tags}、{title}、{summary}"
          />
          <div class="hint">
            可用变量：<code>{existing_tags}</code>（当前已有标签列表）、<code>{title}</code>（链接标题）、<code>{summary}</code>（链接摘要）。
            系统会在调用模型前自动替换这些变量。
          </div>
        </el-form-item>
        <el-form-item label="时区">
          <el-input v-model="prefs.timezone" />
        </el-form-item>
        <el-space>
          <el-button type="primary" @click="savePrefs">保存偏好</el-button>
        </el-space>

        <el-divider content-position="left">SMTP 配置</el-divider>
        <el-form-item label="SMTP Host">
          <el-input v-model="smtp.smtp_host" />
        </el-form-item>
        <el-form-item label="SMTP Port">
          <el-input-number v-model="smtp.smtp_port" :min="1" />
        </el-form-item>
        <el-form-item label="SMTP Username">
          <el-input v-model="smtp.smtp_username" />
        </el-form-item>
        <el-form-item label="SMTP Password">
          <el-input v-model="smtp.smtp_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Use SSL">
          <el-switch v-model="smtp.smtp_use_ssl" />
        </el-form-item>
        <el-form-item label="From Email">
          <el-input v-model="smtp.smtp_from_email" />
        </el-form-item>
        <el-form-item label="From Name">
          <el-input v-model="smtp.smtp_from_name" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="smtp.is_enabled" />
        </el-form-item>
        <el-space wrap>
          <el-button type="primary" @click="saveSmtp">保存SMTP</el-button>
          <el-button @click="testEmail">发送SMTP测试邮件</el-button>
          <el-button @click="sendUpcoming">发送未来7日提醒</el-button>
          <el-button @click="sendUnread">发送未读链接提醒</el-button>
        </el-space>

        <el-divider content-position="left">大模型 API 配置</el-divider>
        <el-form-item label="当前供应商">
          <el-select v-model="llm.active_provider" style="width: 320px">
            <el-option label="OpenAI Compatible" value="openai_compatible" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Qwen" value="qwen" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">OpenAI Compatible</el-divider>
        <el-form-item label="启用 OpenAI Compatible">
          <el-switch v-model="llm.providers.openai_compatible.enabled" />
        </el-form-item>
        <el-form-item label="OpenAI Base URL">
          <el-input v-model="llm.providers.openai_compatible.api_base_url" />
        </el-form-item>
        <el-form-item label="OpenAI API Key">
          <el-input v-model="llm.providers.openai_compatible.api_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="OpenAI Model">
          <el-input v-model="llm.providers.openai_compatible.model" />
        </el-form-item>

        <el-divider content-position="left">DeepSeek</el-divider>
        <el-form-item label="启用 DeepSeek">
          <el-switch v-model="llm.providers.deepseek.enabled" />
        </el-form-item>
        <el-form-item label="DeepSeek Base URL">
          <el-input v-model="llm.providers.deepseek.api_base_url" />
        </el-form-item>
        <el-form-item label="DeepSeek API Key">
          <el-input v-model="llm.providers.deepseek.api_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="DeepSeek Model">
          <el-input v-model="llm.providers.deepseek.model" />
        </el-form-item>

        <el-divider content-position="left">Qwen</el-divider>
        <el-form-item label="启用 Qwen">
          <el-switch v-model="llm.providers.qwen.enabled" />
        </el-form-item>
        <el-form-item label="Qwen Base URL">
          <el-input v-model="llm.providers.qwen.api_base_url" />
        </el-form-item>
        <el-form-item label="Qwen API Key">
          <el-input v-model="llm.providers.qwen.api_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="Qwen Model">
          <el-input v-model="llm.providers.qwen.model" />
        </el-form-item>

        <el-space>
          <el-button type="primary" @click="saveLlm">保存大模型配置</el-button>
        </el-space>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const prefs = reactive({
  unread_link_threshold: 30,
  weekly_report_day_of_week: 5,
  weekly_report_prompt_template:
    '请基于 {completed_range_text} 内已完成事项，生成简洁执行版周报，突出关键产出、风险与下周计划。',
  link_classification_prompt_template:
    '你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；只有都不匹配时才创建新标签。链接标题：{title}；链接摘要：{summary}。输出JSON: {"category":"...","confidence":0-1,"reason":"..."}',
  timezone: 'Asia/Shanghai',
})

const smtp = reactive({
  smtp_host: '',
  smtp_port: 465,
  smtp_username: '',
  smtp_password: '',
  smtp_use_ssl: true,
  smtp_from_email: '',
  smtp_from_name: 'Second Brain Tool',
  is_enabled: false,
})

const llm = reactive({
  active_provider: 'openai_compatible',
  providers: {
    openai_compatible: {
      enabled: false,
      api_base_url: 'https://api.openai.com/v1',
      api_key: '',
      model: 'gpt-5.3-codex',
    },
    deepseek: {
      enabled: false,
      api_base_url: 'https://api.deepseek.com/v1',
      api_key: '',
      model: 'deepseek-chat',
    },
    qwen: {
      enabled: false,
      api_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      api_key: '',
      model: 'qwen-plus',
    },
  },
})

const loadPrefs = async () => {
  const { data } = await api.get('/api/users/me/preferences')
  Object.assign(prefs, data)
}

const loadSmtp = async () => {
  const { data } = await api.get('/api/users/me/smtp-settings')
  Object.assign(smtp, data)
}

const loadLlm = async () => {
  const { data } = await api.get('/api/users/me/llm-settings')
  Object.assign(llm, data)
}
const savePrefs = async () => {
  await api.put('/api/users/me/preferences', prefs)
  ElMessage.success('偏好已保存')
}

const saveSmtp = async () => {
  await api.put('/api/users/me/smtp-settings', smtp)
  ElMessage.success('SMTP已保存')
}

const saveLlm = async () => {
  await api.put('/api/users/me/llm-settings', llm)
  ElMessage.success('大模型配置已保存')
}

const testEmail = async () => {
  await api.post('/api/notifications/test-email')
  ElMessage.success('测试邮件已触发')
}

const sendUpcoming = async () => {
  await api.post('/api/notifications/send-upcoming')
  ElMessage.success('未来7日提醒已触发')
}

const sendUnread = async () => {
  await api.post('/api/notifications/send-unread-links')
  ElMessage.success('未读链接提醒已触发')
}

onMounted(async () => {
  await loadPrefs()
  await loadSmtp()
  await loadLlm()
})
</script>

<style scoped>
.settings-form {
  max-width: 1100px;
}

:deep(.settings-form .el-divider__text) {
  font-weight: 700;
  color: var(--mx-text-strong);
}

:deep(.settings-form .el-form-item) {
  margin-bottom: 16px;
}

.hint {
  margin-top: 6px;
  color: var(--mx-text-muted);
  font-size: 12px;
  line-height: 1.7;
}
</style>