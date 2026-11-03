<script setup>
// 首页：展示品牌介绍 + 四大功能入口
const features = [
  {
    to: '/map',
    icon: '◈',
    title: '世界文学地图',
    desc: '在世界地图上探索作品与作家，发现文学与地点的联系。'
  },
  {
    to: '/works',
    icon: '❖',
    title: '作品探索',
    desc: '浏览作品、作家与文学流派，查阅创作地与故事发生地。'
  },
  {
    to: '/footprint',
    icon: '⌂',
    title: '我的文学足迹',
    desc: '记录阅读经历，生成属于你的个人文学足迹地图。'
  },
  {
    to: '/ai',
    icon: '✦',
    title: 'AI 文学探索',
    desc: '向 AI 提问，探索文学知识，获取专属阅读推荐。'
  }
]
</script>

<template>
  <div class="home">
    <!-- ============ 首屏：品牌与核心理念 ============ -->
    <section class="hero">
      <div class="container hero-inner">
        <div class="hero-text">
          <p class="hero-eyebrow">LITERARY ATLAS · 世界文学地理探索</p>
          <h1 class="hero-title">以阅读之名，<br />丈量世界文学的版图</h1>
          <p class="hero-sub">
            阅读是一段旅程。Literary Atlas 以地理空间为线索，
            带你发现文学作品、作家与流派，在世界的版图上重走文学的足迹。
          </p>
          <div class="hero-actions">
            <router-link to="/map" class="btn btn-gold">开始探索地图</router-link>
            <router-link to="/works" class="btn btn-ghost">浏览作品</router-link>
          </div>
        </div>

        <!-- 装饰：罗盘 + 经纬线，营造地图/档案氛围 -->
        <div class="hero-visual" aria-hidden="true">
          <svg viewBox="0 0 320 320" class="compass">
            <circle cx="160" cy="160" r="150" class="ring" />
            <circle cx="160" cy="160" r="112" class="ring ring-2" />
            <circle cx="160" cy="160" r="74" class="ring ring-3" />
            <!-- 经纬线示意 -->
            <ellipse cx="160" cy="160" rx="150" ry="56" class="lat" />
            <ellipse cx="160" cy="160" rx="56" ry="150" class="lat" />
            <!-- 罗盘指针 -->
            <polygon points="160,40 176,160 160,176 144,160" class="needle needle-n" />
            <polygon points="160,280 144,160 160,144 176,160" class="needle needle-s" />
            <polygon points="40,160 160,144 160,176" class="needle needle-w" />
            <polygon points="280,160 160,144 160,176" class="needle needle-e" />
            <circle cx="160" cy="160" r="6" class="hub" />
            <text x="160" y="26" class="mark">N</text>
          </svg>
        </div>
      </div>
    </section>

    <!-- ============ 四大功能入口 ============ -->
    <section class="features">
      <div class="container">
        <h2 class="section-title">从这里出发</h2>
        <p class="section-sub">选择一条路径，开始你的文学地理探索。</p>
        <div class="feature-grid">
          <router-link
            v-for="f in features"
            :key="f.to"
            :to="f.to"
            class="feature-card"
          >
            <span class="feature-icon">{{ f.icon }}</span>
            <h3 class="feature-title">{{ f.title }}</h3>
            <p class="feature-desc">{{ f.desc }}</p>
            <span class="feature-arrow">→</span>
          </router-link>
        </div>
      </div>
    </section>

    <!-- ============ 理念说明 ============ -->
    <section class="about">
      <div class="container about-inner">
        <h2 class="section-title">一个文学的地理坐标</h2>
        <p class="section-sub">把每一本书，放回它诞生的地方。</p>
        <p class="about-text">
          Literary Atlas 不是旅游指南，也不是图书商城。我们将文学作品、
          作家与真实地点相互关联：你可以在世界地图上发现一部小说发生在哪里，
          也可以记录自己读过的书，生成一张只属于你的文学足迹地图。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ---- 首屏 Hero ---- */
.hero {
  background: var(--deep);
  color: var(--paper);
  padding: 88px 0 96px;
  position: relative;
  overflow: hidden;
}
/* 经纬网格背景纹理，呼应“地图”主题 */
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
}
.hero-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 48px;
  position: relative;
}
.hero-eyebrow {
  color: var(--gold-soft);
  letter-spacing: 0.28em;
  font-size: 13px;
  margin-bottom: 20px;
}
.hero-title {
  color: var(--paper);
  font-size: 48px;
  line-height: 1.25;
  margin-bottom: 24px;
}
.hero-sub {
  color: rgba(246, 241, 231, 0.72);
  font-size: 16px;
  max-width: 520px;
  margin-bottom: 36px;
}
.hero-actions {
  display: flex;
  gap: 16px;
}

/* ---- 罗盘装饰 ---- */
.hero-visual {
  flex-shrink: 0;
}
.compass {
  width: 300px;
  height: 300px;
}
.ring {
  fill: none;
  stroke: rgba(217, 185, 138, 0.35);
  stroke-width: 1;
}
.ring-2 { stroke: rgba(217, 185, 138, 0.22); }
.ring-3 { stroke: rgba(217, 185, 138, 0.18); }
.lat {
  fill: none;
  stroke: rgba(217, 185, 138, 0.18);
  stroke-width: 1;
}
.needle { fill: var(--gold); }
.needle-n { fill: var(--gold); }
.needle-s,
.needle-w,
.needle-e { fill: rgba(193, 155, 89, 0.45); }
.hub { fill: var(--paper); }
.mark {
  fill: var(--gold-soft);
  font-size: 16px;
  font-family: Georgia, serif;
  text-anchor: middle;
}

/* ---- 功能入口 ---- */
.features {
  padding: 72px 0;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
.feature-card {
  background: var(--paper-3);
  border: 1px solid var(--line);
  border-top: 3px solid var(--gold);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
  position: relative;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(20, 29, 51, 0.10);
  border-color: var(--gold-soft);
}
.feature-icon {
  font-size: 26px;
  color: var(--gold-deep);
}
.feature-title {
  font-size: 19px;
}
.feature-desc {
  font-size: 14px;
  color: var(--muted);
  flex: 1;
}
.feature-arrow {
  color: var(--gold-deep);
  font-size: 18px;
}

/* ---- 理念 ---- */
.about {
  background: var(--paper-2);
  padding: 72px 0;
}
.about-inner {
  max-width: 720px;
}
.about-text {
  font-size: 16px;
  color: var(--ink);
}

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .hero-inner {
    flex-direction: column;
    text-align: center;
  }
  .hero-sub {
    margin-left: auto;
    margin-right: auto;
  }
  .hero-actions {
    justify-content: center;
  }
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .hero-title {
    font-size: 34px;
  }
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>