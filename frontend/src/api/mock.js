// 模拟数据：后端完成前，前端先用这些数据开发页面
// 后续对接真实接口后，这个文件可以被删除

export const mockBooks = [
  {
    id: 1,
    title: '百年孤独',
    author: '加西亚·马尔克斯',
    country: '哥伦比亚',
    year: 1967,
    genre: '魔幻现实主义',
    place: '马孔多（虚构小镇，原型为阿拉卡塔卡）'
  },
  {
    id: 2,
    title: '巴黎圣母院',
    author: '维克多·雨果',
    country: '法国',
    year: 1831,
    genre: '浪漫主义',
    place: '法国 巴黎'
  },
  {
    id: 3,
    title: '白鲸',
    author: '赫尔曼·梅尔维尔',
    country: '美国',
    year: 1851,
    genre: '文学经典',
    place: '北大西洋'
  }
]

export const mockAuthors = [
  {
    id: 1,
    name: '加西亚·马尔克斯',
    birthPlace: '哥伦比亚 阿拉卡塔卡',
    works: ['百年孤独', '霍乱时期的爱情']
  }
]