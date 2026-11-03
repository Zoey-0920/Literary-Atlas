import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置文件：负责开发服务器与构建相关设置
export default defineConfig({
  plugins: [vue()], // 启用对 .vue 单文件组件的支持
  server: {
    port: 5173,      // 前端开发地址端口
    open: false      // 启动后不自动打开浏览器，手动打开更方便照教程操作
  }
})