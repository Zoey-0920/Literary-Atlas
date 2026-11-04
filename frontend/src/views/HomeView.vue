<script setup>
// 首页：中央地图主区（顶部融合导航悬浮其上）+ 右侧书架
import LiteraryMap from '../components/LiteraryMap.vue'
import BookshelfSidebar from '../components/BookshelfSidebar.vue'
import NavBar from '../components/NavBar.vue'
</script>

<template>
  <div class="atlas">
    <div class="atlas-map">
      <LiteraryMap />
      <NavBar />
    </div>
    <BookshelfSidebar class="atlas-shelf" />
  </div>
</template>

<style scoped>
.atlas { position: absolute; inset: 0; display: flex; }
.atlas-map { flex: 1; min-width: 0; position: relative; }
.atlas-shelf { width: 320px; flex-shrink: 0; }
@media (max-width: 900px) {
  .atlas-shelf { width: 280px; }
}
@media (max-width: 760px) {
  .atlas-shelf { display: none; }
}
</style>