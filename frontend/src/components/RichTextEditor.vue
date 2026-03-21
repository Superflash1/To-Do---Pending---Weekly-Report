<template>
  <div class="editor-shell">
    <div class="editor-toolbar">
      <el-button size="small" @click="exec('toggleBold')"><b>B</b></el-button>
      <el-button size="small" @click="exec('toggleItalic')"><i>I</i></el-button>
      <el-button size="small" @click="exec('toggleBulletList')">• 列表</el-button>
      <el-button size="small" @click="exec('toggleHeading', { level: 2 })">H2</el-button>
      <el-button size="small" @click="exec('toggleCodeBlock')">代码块</el-button>
      <el-button size="small" @click="exec('toggleBlockquote')">引用</el-button>
    </div>

    <editor-content class="rich-editor" :editor="editor" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Image from '@tiptap/extension-image'
import MarkdownIt from 'markdown-it'
import TurndownService from 'turndown'

type UploadFn = (file: File) => Promise<string>

const props = defineProps<{
  markdown: string
  placeholder?: string
  uploadImage?: UploadFn
}>()

const emit = defineEmits<{
  (e: 'update:markdown', value: string): void
  (e: 'update:html', value: string): void
}>()

const md = new MarkdownIt({ html: true, linkify: true, breaks: true })
const turndown = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' })

const renderMarkdown = (value: string) => {
  if (!value?.trim()) return '<p></p>'
  return md.render(value)
}

const emitSnapshot = () => {
  const html = editor.getHTML()
  const markdown = turndown.turndown(html)
  emit('update:html', html)
  emit('update:markdown', markdown)
}

const handlePasteImage = async (event: ClipboardEvent) => {
  if (!props.uploadImage) return
  const items = event.clipboardData?.items
  if (!items?.length) return

  const imageItems = Array.from(items).filter((item) => item.type.startsWith('image/'))
  if (!imageItems.length) return

  event.preventDefault()

  for (const item of imageItems) {
    const file = item.getAsFile()
    if (!file) continue
    const url = await props.uploadImage(file)
    editor.chain().focus().setImage({ src: url, alt: file.name }).run()
  }
  emitSnapshot()
}

const editor = new Editor({
  content: renderMarkdown(props.markdown),
  extensions: [
    StarterKit,
    Image,
    Placeholder.configure({
      placeholder: props.placeholder || '输入 Markdown（所见即所得）...',
    }),
  ],
  editorProps: {
    handlePaste: (_, event) => {
      handlePasteImage(event)
      return false
    },
  },
  onUpdate: emitSnapshot,
})

watch(
  () => props.markdown,
  (next) => {
    const nextHtml = renderMarkdown(next)
    if (nextHtml !== editor.getHTML()) {
      editor.commands.setContent(nextHtml, false)
    }
  },
)

const exec = (command: string, payload?: Record<string, unknown>) => {
  const chain = editor.chain().focus()
  ;(chain as any)[command](payload).run()
}

onBeforeUnmount(() => {
  editor.destroy()
})
</script>

<style scoped>
.editor-shell {
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.rich-editor :deep(.tiptap) {
  min-height: 260px;
  padding: 12px;
  outline: none;
}

.rich-editor :deep(.tiptap p) {
  margin: 8px 0;
}

.rich-editor :deep(.tiptap h1),
.rich-editor :deep(.tiptap h2),
.rich-editor :deep(.tiptap h3) {
  margin: 12px 0 8px;
}

.rich-editor :deep(.tiptap ul),
.rich-editor :deep(.tiptap ol) {
  padding-left: 24px;
}

.rich-editor :deep(.tiptap img) {
  max-width: 100%;
  border-radius: 8px;
}
</style>
