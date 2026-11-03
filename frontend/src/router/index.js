// 路由配置：定义页面地址（URL）与对应组件之间的映射关系
import { createRouter, createWebHistory } from 'vue-router'

// 各页面组件
import HomeView from '../views/HomeView.vue'
import WorldMapView from '../views/WorldMapView.vue'
import WorksView from '../views/WorksView.vue'
import AuthorDetailView from '../views/AuthorDetailView.vue'
import BookshelfView from '../views/BookshelfView.vue'
import FootprintView from '../views/FootprintView.vue'
import AiExploreView from '../views/AiExploreView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/map', name: 'map', component: WorldMapView },
  { path: '/works', name: 'works', component: WorksView },
  // 作家详情页：:id 是动态参数，例如 /authors/3 表示查看 id 为 3 的作家
  { path: '/authors/:id', name: 'author', component: AuthorDetailView },
  { path: '/bookshelf', name: 'bookshelf', component: BookshelfView },
  { path: '/footprint', name: 'footprint', component: FootprintView },
  { path: '/ai', name: 'ai', component: AiExploreView }
]

const router = createRouter({
  history: createWebHistory(), // 使用 HTML5 history 模式（地址里没有 # 号）
  routes
})

export default router