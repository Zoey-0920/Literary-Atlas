// 应用入口文件：创建 Vue 实例并挂载到页面
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css' // 引入全局样式

const app = createApp(App)

app.use(router)  // 注册路由，让页面支持地址跳转
app.mount('#app') // 挂载到 index.html 中的 #app 节点