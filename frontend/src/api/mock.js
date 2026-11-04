// 模拟数据：后端完成前，前端先用这些数据开发页面
// 后续对接真实接口后，这个文件可以被删除

/* =========================================================
   文学城市（总览地图标记）
   lat/lng 为真实经纬度，countryCode 为 ISO 三位码（个人地图国家高亮匹配）
   genre 为文学流派，important 为全球视图下优先展示的重要文学城市
   ========================================================= */
export const literaryCities = [
  {
    id: 'paris', city: '巴黎', country: '法国', countryCode: 'FRA', lat: 48.8566, lng: 2.3522,
    genre: '浪漫主义 · 存在主义', important: true,
    summary: '法国文学的中心，浪漫主义与存在主义的交汇地。',
    authors: [
      { name: '维克多·雨果', works: ['巴黎圣母院', '悲惨世界'] },
      { name: '马塞尔·普鲁斯特', works: ['追忆似水年华'] },
      { name: '阿尔贝·加缪', works: ['局外人', '鼠疫'] }
    ]
  },
  {
    id: 'london', city: '伦敦', country: '英国', countryCode: 'GBR', lat: 51.5074, lng: -0.1278,
    genre: '文艺复兴 · 维多利亚小说', important: true,
    summary: '从莎士比亚到狄更斯，英语文学的重镇。',
    authors: [
      { name: '威廉·莎士比亚', works: ['哈姆雷特', '麦克白'] },
      { name: '查尔斯·狄更斯', works: ['雾都孤儿', '双城记'] },
      { name: '弗吉尼亚·伍尔芙', works: ['达洛维夫人'] }
    ]
  },
  {
    id: 'dublin', city: '都柏林', country: '爱尔兰', countryCode: 'IRL', lat: 53.3498, lng: -6.2603,
    genre: '现代主义', important: false,
    summary: '乔伊斯与王尔德的故乡。',
    authors: [
      { name: '詹姆斯·乔伊斯', works: ['尤利西斯', '都柏林人'] },
      { name: '奥斯卡·王尔德', works: ['道林·格雷的画像'] }
    ]
  },
  {
    id: 'petersburg', city: '圣彼得堡', country: '俄罗斯', countryCode: 'RUS', lat: 59.9311, lng: 30.3609,
    genre: '俄国现实主义', important: true,
    summary: '俄罗斯文学的北方之都。',
    authors: [
      { name: '费奥多尔·陀思妥耶夫斯基', works: ['罪与罚', '白痴'] },
      { name: '亚历山大·普希金', works: ['叶甫盖尼·奥涅金'] }
    ]
  },
  {
    id: 'moscow', city: '莫斯科', country: '俄罗斯', countryCode: 'RUS', lat: 55.7558, lng: 37.6173,
    genre: '俄国现实主义', important: true,
    summary: '托尔斯泰与契诃夫笔下的俄罗斯腹地。',
    authors: [
      { name: '列夫·托尔斯泰', works: ['战争与和平', '安娜·卡列尼娜'] },
      { name: '安东·契诃夫', works: ['樱桃园', '套中人'] },
      { name: '米哈伊尔·布尔加科夫', works: ['大师与玛格丽特'] }
    ]
  },
  {
    id: 'madrid', city: '马德里', country: '西班牙', countryCode: 'ESP', lat: 40.4168, lng: -3.7038,
    genre: '黄金时代 · 现代主义', important: false,
    summary: '塞万提斯与《堂吉诃德》的国度。',
    authors: [
      { name: '米格尔·德·塞万提斯', works: ['堂吉诃德'] },
      { name: '费德里科·加西亚·洛尔迦', works: ['吉普赛谣曲集'] }
    ]
  },
  {
    id: 'prague', city: '布拉格', country: '捷克', countryCode: 'CZE', lat: 50.0755, lng: 14.4378,
    genre: '表现主义 · 存在主义', important: true,
    summary: '卡夫卡与昆德拉的文学之城。',
    authors: [
      { name: '弗兰兹·卡夫卡', works: ['变形记', '城堡'] },
      { name: '米兰·昆德拉', works: ['不能承受的生命之轻'] }
    ]
  },
  {
    id: 'newyork', city: '纽约', country: '美国', countryCode: 'USA', lat: 40.7128, lng: -74.006,
    genre: '迷惘的一代 · 爵士时代', important: true,
    summary: '爵士时代的喧嚣与迷惘一代的舞台。',
    authors: [
      { name: '弗朗西斯·菲茨杰拉德', works: ['了不起的盖茨比'] },
      { name: 'J.D.塞林格', works: ['麦田里的守望者'] }
    ]
  },
  {
    id: 'colombia', city: '阿拉卡塔卡', country: '哥伦比亚', countryCode: 'COL', lat: 10.59, lng: -74.19,
    genre: '魔幻现实主义', important: true,
    summary: '马孔多的原型，马尔克斯的故乡。',
    authors: [
      { name: '加西亚·马尔克斯', works: ['百年孤独', '霍乱时期的爱情'] }
    ]
  },
  {
    id: 'tokyo', city: '东京', country: '日本', countryCode: 'JPN', lat: 35.6762, lng: 139.6503,
    genre: '日本现代文学', important: true,
    summary: '从紫式部到村上春树的东亚文脉。',
    authors: [
      { name: '川端康成', works: ['雪国', '伊豆的舞女'] },
      { name: '村上春树', works: ['挪威的森林', '海边的卡夫卡'] }
    ]
  },
  {
    id: 'beijing', city: '北京', country: '中国', countryCode: 'CHN', lat: 39.9042, lng: 116.4074,
    genre: '古典文学 · 现代文学', important: true,
    summary: '曹雪芹、老舍与鲁迅的文学现场。',
    authors: [
      { name: '曹雪芹', works: ['红楼梦'] },
      { name: '老舍', works: ['骆驼祥子', '茶馆'] },
      { name: '鲁迅', works: ['呐喊', '彷徨'] }
    ]
  },
  {
    id: 'cairo', city: '开罗', country: '埃及', countryCode: 'EGY', lat: 30.0444, lng: 31.2357,
    genre: '阿拉伯现代主义', important: false,
    summary: '马哈福兹笔下的开罗三部曲。',
    authors: [
      { name: '纳吉布·马哈福兹', works: ['开罗三部曲'] }
    ]
  },
  {
    id: 'istanbul', city: '伊斯坦布尔', country: '土耳其', countryCode: 'TUR', lat: 41.0082, lng: 28.9784,
    genre: '土耳其现代文学', important: false,
    summary: '帕慕克笔下横跨欧亚的呼愁之城。',
    authors: [
      { name: '奥尔罕·帕慕克', works: ['我的名字叫红', '伊斯坦布尔：一座城市的记忆'] }
    ]
  },
  {
    id: 'rio', city: '里约热内卢', country: '巴西', countryCode: 'BRA', lat: -22.9068, lng: -43.1729,
    genre: '拉丁美洲魔幻现实主义', important: false,
    summary: '拉丁美洲文学的热带底色。',
    authors: [
      { name: '保罗·科埃略', works: ['牧羊少年奇幻之旅'] }
    ]
  },
  {
    id: 'vienna', city: '维也纳', country: '奥地利', countryCode: 'AUT', lat: 48.2082, lng: 16.3738,
    genre: '世纪末现代主义', important: false,
    summary: '茨威格笔下繁华而忧伤的昨日世界。',
    authors: [
      { name: '斯蒂芬·茨威格', works: ['昨日的世界', '一个陌生女人的来信'] }
    ]
  },
  {
    id: 'athens', city: '雅典', country: '希腊', countryCode: 'GRC', lat: 37.9838, lng: 23.7275,
    genre: '西方古典文学', important: false,
    summary: '荷马史诗与西方文学的原点。',
    authors: [
      { name: '荷马', works: ['伊利亚特', '奥德赛'] }
    ]
  },
  {
    id: 'shanghai', city: '上海', country: '中国', countryCode: 'CHN', lat: 31.2304, lng: 121.4737,
    genre: '海派文学', important: false,
    summary: '张爱玲与王安忆笔下的摩登都市。',
    authors: [
      { name: '张爱玲', works: ['倾城之恋', '金锁记'] },
      { name: '王安忆', works: ['长恨歌'] }
    ]
  },
  {
    id: 'kyoto', city: '京都', country: '日本', countryCode: 'JPN', lat: 35.0116, lng: 135.7681,
    genre: '日本古典文学', important: false,
    summary: '紫式部写下《源氏物语》的平安京。',
    authors: [{ name: '紫式部', works: ['源氏物语'] }]
  },
  {
    id: 'seoul', city: '首尔', country: '韩国', countryCode: 'KOR', lat: 37.5665, lng: 126.978,
    genre: '韩国现代文学', important: false,
    summary: '韩国现代文学与世界对话的窗口。',
    authors: [{ name: '韩江', works: ['素食者'] }]
  },
  {
    id: 'mumbai', city: '孟买', country: '印度', countryCode: 'IND', lat: 19.076, lng: 72.8777,
    genre: '南亚文学', important: false,
    summary: '鲁西迪与印度英语文学的重镇。',
    authors: [{ name: '萨尔曼·鲁西迪', works: ['午夜之子'] }]
  },
  {
    id: 'tehran', city: '德黑兰', country: '伊朗', countryCode: 'IRN', lat: 35.6892, lng: 51.389,
    genre: '波斯文学', important: false,
    summary: '从菲尔多西到当代伊朗小说。',
    authors: [{ name: '菲尔多西', works: ['列王纪'] }]
  },
  {
    id: 'capetown', city: '开普敦', country: '南非', countryCode: 'ZAF', lat: -33.9249, lng: 18.4241,
    genre: '非洲现代文学', important: false,
    summary: '库切与戈迪默笔下的南非。',
    authors: [
      { name: 'J.M.库切', works: ['耻'] },
      { name: '纳丁·戈迪默', works: ['七月的人民'] }
    ]
  },
  {
    id: 'buenosaires', city: '布宜诺斯艾利斯', country: '阿根廷', countryCode: 'ARG', lat: -34.6037, lng: -58.3816,
    genre: '拉美文学', important: false,
    summary: '博尔赫斯的小径分岔的花园。',
    authors: [{ name: '豪尔赫·路易斯·博尔赫斯', works: ['小径分岔的花园'] }]
  },
  {
    id: 'mexicocity', city: '墨西哥城', country: '墨西哥', countryCode: 'MEX', lat: 19.4326, lng: -99.1332,
    genre: '拉美文学', important: false,
    summary: '帕斯与墨西哥现代诗歌。',
    authors: [
      { name: '奥克塔维奥·帕斯', works: ['太阳石'] },
      { name: '胡安·鲁尔福', works: ['佩德罗·巴拉莫'] }
    ]
  },
  {
    id: 'sydney', city: '悉尼', country: '澳大利亚', countryCode: 'AUS', lat: -33.8688, lng: 151.2093,
    genre: '大洋洲文学', important: false,
    summary: '怀特与澳大利亚文学的南方之光。',
    authors: [{ name: '帕特里克·怀特', works: ['人树'] }]
  },
  {
    id: 'toronto', city: '多伦多', country: '加拿大', countryCode: 'CAN', lat: 43.6532, lng: -79.3832,
    genre: '加拿大文学', important: false,
    summary: '阿特伍德与加拿大文学的坐标。',
    authors: [{ name: '玛格丽特·阿特伍德', works: ['使女的故事'] }]
  }
]

/* =========================================================
   阅读书架：状态值与后端一致（want_to_read / reading / finished）
   cover 为封面渐变色（演示数据，明确标记）
   ========================================================= */
export const shelfBooks = [
  {
    id: 1, title: '百年孤独', author: '加西亚·马尔克斯', status: 'finished',
    city: '阿拉卡塔卡', country: '哥伦比亚', countryCode: 'COL', lat: 10.59, lng: -74.19,
    cover: ['#8a7b3a', '#3c2a1c']
  },
  {
    id: 2, title: '追风筝的人', author: '卡勒德·胡赛尼', status: 'reading',
    city: '喀布尔', country: '阿富汗', countryCode: 'AFG', lat: 34.5553, lng: 69.2075,
    cover: ['#3a6b9d', '#c9843a']
  },
  {
    id: 3, title: '1984', author: '乔治·奥威尔', status: 'finished',
    city: '伦敦', country: '英国', countryCode: 'GBR', lat: 51.5074, lng: -0.1278,
    cover: ['#6e1f22', '#2a2a33']
  },
  {
    id: 4, title: '小王子', author: '安托万·德·圣埃克苏佩里', status: 'finished',
    city: '巴黎', country: '法国', countryCode: 'FRA', lat: 48.8566, lng: 2.3522,
    cover: ['#2a5d8a', '#8ecfe0']
  },
  {
    id: 5, title: '月亮与六便士', author: '毛姆', status: 'want_to_read',
    city: '伦敦', country: '英国', countryCode: 'GBR', lat: 51.5074, lng: -0.1278,
    cover: ['#1c2340', '#d4b477']
  }
]

// 书架统计（演示数据：列表仅展示部分，总量见此处）
/* =========================================================
   遗留演示统计（当前 API 层不再读取，仅为旧引用兼容保留）
   状态键已与后端枚举对齐：finished / reading / want_to_read
   ========================================================= */
export const shelfStats = { finished: 12, reading: 3, want_to_read: 5 }

/* 原有演示数据（作品 / 作家列表向后兼容） */
export const mockBooks = [
  { id: 1, title: '百年孤独', author: '加西亚·马尔克斯', country: '哥伦比亚', year: 1967, genre: '魔幻现实主义', place: '马孔多（虚构小镇，原型为阿拉卡塔卡）' },
  { id: 2, title: '巴黎圣母院', author: '维克多·雨果', country: '法国', year: 1831, genre: '浪漫主义', place: '法国 巴黎' },
  { id: 3, title: '白鲸', author: '赫尔曼·梅尔维尔', country: '美国', year: 1851, genre: '文学经典', place: '北大西洋' }
]

export const mockAuthors = [
  { id: 1, name: '加西亚·马尔克斯', birthPlace: '哥伦比亚 阿拉卡塔卡', works: ['百年孤独', '霍乱时期的爱情'] }
]