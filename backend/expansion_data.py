"""Literary Atlas 第一版 50 部作品扩充数据。

本文件仅存放数据，不执行任何导入。数据由 `import_expansion.py` 读取并写入数据库。

结构与 seed.py 的 SEED_DATA 一致：
- books / authors / genres / places 为「基础实体」，按自然键（title / name）查重。
- book_authors / book_genres / book_places 为「关联表」，通过 book_title / author_name /
  genre_name / place_name 引用基础实体。

数据规则（与 DATA_EXPANSION_PLAN.md 第 9 节一致）：
- 不确定的年份一律 None，不写「未知」；约略年代写入 description。
- source / source_name / source_url / note 一律 None，不编造来源。
- 虚构地点 is_fictional=1、place_type='fictional'，经纬度必为 None。
- 真实地点坐标仅取自 docs/PLACE_COORDINATES_REVIEW.md 已核实项（Wikidata 实测），
  由 _VERIFIED_COORDS 按名称注入；8 个待人工确认项保持 None。

注意：本文件包含 6 部复用作品与已有作者/地点/流派，导入脚本按自然键复用，不会重复插入。
"""

from __future__ import annotations


def _book(title, original_title, language, publication_year, description):
    return {
        "title": title,
        "original_title": original_title,
        "language": language,
        "publication_year": publication_year,
        "description": description,
        "source": None,
    }


def _author(name, birth_year, death_year, nationality, bio):
    return {
        "name": name,
        "birth_year": birth_year,
        "death_year": death_year,
        "nationality": nationality,
        "bio": bio,
    }


def _genre(name, description):
    return {"name": name, "description": description}


# 已核实坐标表（来源：docs/PLACE_COORDINATES_REVIEW.md；坐标经 Wikidata API 实测，
# 注释中 QID 可复核）。未列入的地点（8 个待人工确认项）保持 None。
_VERIFIED_COORDS = {
    # --- city P1：直接关联作品（24）---
    "莫斯科": (55.7506, 37.6175),          # Q649
    "圣彼得堡": (59.9500, 30.3167),        # Q656
    "伦敦": (51.5072, -0.1275),            # Q84
    "洛阳": (34.6587, 112.4245),           # Q187136
    "许昌": (34.0244, 113.8201),           # Q404529
    "成都": (30.6600, 104.0633),           # Q30002
    "北京": (39.9040, 116.4075),           # Q956
    "上海": (31.2325, 121.4692),           # Q8686
    "京都": (35.0116, 135.7681),           # Q34600
    "越后汤泽": (36.9341, 138.8174),       # Q1204269（汤泽町）
    "东京": (35.6894, 139.6917),           # Q1490
    "孟买": (19.0758, 72.8775),            # Q1156
    "德里": (28.6667, 77.2167),            # Q1353
    "巴格达": (33.3153, 44.3661),          # Q1530
    "开罗": (30.0444, 31.2358),            # Q85
    "达喀尔": (14.6726, -17.4320),         # Q3718
    "卡塔赫纳": (10.4236, -75.5253),       # Q657461
    "布宜诺斯艾利斯": (-34.5997, -58.3819),  # Q1486
    "里约热内卢": (-22.9111, -43.2056),    # Q8678
    "巴黎": (48.8567, 2.3522),             # Q90
    "都柏林": (53.3497, -6.2603),          # Q1761
    "吕贝克": (53.8697, 10.6864),          # Q2843
    "达沃斯": (46.8091, 9.8398),           # Q68097
    "辛辛那提": (39.1000, -84.5125),       # Q43196
    # --- city P2：作者足迹锚点（5）---
    "阿拉卡塔卡": (10.5911, -74.1850),     # Q624492
    "墨西哥城": (19.3538, -99.1359),       # Q1489
    "奥克帕克": (41.8883, -87.7894),       # Q331397
    "莫蒂哈里": (26.6500, 84.9167),        # Q1774606
    "佛罗伦萨": (43.7714, 11.2542),        # Q2044
    # --- country（11）---
    "俄罗斯": (66.4167, 94.2500),          # Q159
    "古巴": (22.0000, -79.5000),           # Q241
    "中国": (35.8447, 103.4519),           # Q148
    "越南": (16.0000, 108.0000),           # Q881
    "印度尼西亚": (-2.0000, 118.0000),     # Q252
    "印度": (22.8000, 83.0000),            # Q668
    "南非": (-29.0000, 24.0000),           # Q258
    "尼日利亚": (9.0000, 8.0000),          # Q1033
    "哥伦比亚": (4.0000, -73.2500),        # Q739
    "智利": (-33.0000, -71.0000),          # Q298
    "海地": (19.0000, -72.8000),           # Q790
    # --- region（15）---
    "爪哇": (-7.3117, 109.4183),           # Q3757
    "北方邦": (26.8500, 80.9100),          # Q1498
    "伊萨卡": (38.4167, 20.6667),          # Q187471
    "拉曼恰": (39.4011, -3.0150),          # Q844209
    "诺曼底": (49.1223, -0.4366),          # Q15878
    "英格兰": (53.0000, -1.0000),          # Q21
    "赫特福德郡": (51.8294, -0.2183),      # Q67532100
    "肯特": (51.1900, 0.7300),             # Q23298
    "特兰西瓦尼亚": (46.7667, 23.5833),    # Q39473
    "纽约长岛": (40.7889, -73.2335),       # Q18438
    "南塔克特岛": (41.2768, -70.0909),     # Q49149
    "俄克拉荷马": (35.5000, -98.0000),     # Q1649
    "加利福尼亚": (37.0000, -120.0000),    # Q99
    "俄亥俄": (40.5000, -82.5000),         # Q1397
    "阿拉巴马州": (32.7000, -86.7000),     # Q173
}


def _real(name, place_type, country=None, region=None, description=None):
    lat, lng = _VERIFIED_COORDS.get(name, (None, None))
    return {
        "name": name,
        "place_type": place_type,
        "is_fictional": 0,
        "latitude": lat,
        "longitude": lng,
        "country": country,
        "region": region,
        "parent_place_id": None,
        "description": description,
    }


def _fictional(name, description):
    return {
        "name": name,
        "place_type": "fictional",
        "is_fictional": 1,
        "latitude": None,
        "longitude": None,
        "country": None,
        "region": None,
        "parent_place_id": None,
        "description": description,
    }


EXPANSION_DATA = {
    # ------------------------------------------------------------------
    # 12 个流派（6 现有 + 6 新增）
    # ------------------------------------------------------------------
    "genres": [
        _genre("魔幻现实主义", "将现实与奇幻融合的文学流派。"),
        _genre("现实主义", "真实反映社会生活的文学流派。"),
        _genre("现代主义", "注重形式实验与主观体验的文学流派。"),
        _genre("反乌托邦", "描绘极权、压抑的未来社会的文学流派。"),
        _genre("史诗", "长篇叙事诗歌体裁，以重大历史或传奇为题材。"),
        _genre("章回体小说", "中国传统分章回叙事的长篇小说体裁。"),
        _genre("古典物语", "日本古典长篇叙事文学体裁。"),
        _genre("历史演义小说", "以历史为题材、虚实结合的章回体长篇小说。"),
        _genre("浪漫主义", "注重情感、想象与个性表达的文学流派。"),
        _genre("哥特小说", "以神秘、恐怖、超自然氛围为特征的文学类型。"),
        _genre("后殖民文学", "反映殖民历史及其影响的文学。"),
        _genre("民间故事集", "汇集民间传说与故事的文学形式。"),
    ],

    # ------------------------------------------------------------------
    # 46 位作者（6 现有 + 39 新增 + 1 佚名）
    # ------------------------------------------------------------------
    "authors": [
        # --- 现有 6 位（复用；曹雪芹生卒年最终改为 NULL）---
        _author("加夫列尔·加西亚·马尔克斯", 1927, 2014, "哥伦比亚", "哥伦比亚作家。"),
        _author("列夫·托尔斯泰", 1828, 1910, "俄国", "俄国作家。"),
        _author("乔治·奥威尔", 1903, 1950, "英国", "英国作家。"),
        _author("但丁·阿利吉耶里", 1265, 1321, "意大利", "意大利诗人。"),
        _author("曹雪芹", None, None, "中国",
                "清代小说家；生卒年约 1715—1763，为推定值。"),
        _author("欧内斯特·海明威", 1899, 1961, "美国", "美国作家。"),
        # --- 新增 39 位 ---
        _author("罗贯中", None, None, "中国", "中国元末明初小说家；生卒年不详。"),
        _author("老舍", 1899, 1966, "中国", "中国现代作家。"),
        _author("巴金", 1904, 2005, "中国", "中国现代作家。"),
        _author("茅盾", 1896, 1981, "中国", "中国现代作家。"),
        _author("王安忆", 1954, None, "中国", "中国当代作家。"),
        _author("紫式部", None, None, "日本",
                "日本平安时代女作家；生卒年不详（约 973—1014，待核实）。"),
        _author("川端康成", 1899, 1972, "日本", "日本作家。"),
        _author("夏目漱石", 1867, 1916, "日本", "日本作家。"),
        _author("村上春树", 1949, None, "日本", "日本作家。"),
        _author("芥川龙之介", 1892, 1927, "日本", "日本作家。"),
        _author("阮攸", 1766, 1820, "越南", "越南诗人。"),
        _author("普拉姆迪亚·阿南达·杜尔", 1925, 2006, "印度尼西亚", "印度尼西亚作家。"),
        _author("普列姆昌德", 1880, 1936, "印度", "印度作家。"),
        _author("萨尔曼·鲁西迪", 1947, None, "英国", "英国印度裔作家。"),
        _author("毗耶娑", None, None, "古印度",
                "古印度传说人物，《摩诃婆罗多》传统归属作者；身份与生卒年无法可靠确定。"),
        _author("纳吉布·马哈福兹", 1911, 2006, "埃及", "埃及作家。"),
        _author("钦努阿·阿契贝", 1930, 2013, "尼日利亚", "尼日利亚作家。"),
        _author("艾伦·佩顿", 1903, 1988, "南非", "南非作家。"),
        _author("玛丽亚玛·巴", 1929, 1981, "塞内加尔", "塞内加尔作家。"),
        _author("奇玛曼达·恩戈兹·阿迪契", 1977, None, "尼日利亚", "尼日利亚作家。"),
        _author("豪尔赫·路易斯·博尔赫斯", 1899, 1986, "阿根廷", "阿根廷作家。"),
        _author("马查多·德·阿西斯", 1839, 1908, "巴西", "巴西作家。"),
        _author("伊莎贝尔·阿连德", 1942, None, "智利", "智利作家。"),
        _author("阿莱霍·卡彭铁尔", 1904, 1980, "古巴", "古巴作家。"),
        _author("荷马", None, None, "古希腊",
                "古希腊诗人；传统归属作者，生平与生卒年无法可靠确定。"),
        _author("米格尔·德·塞万提斯", 1547, 1616, "西班牙", "西班牙作家。"),
        _author("费奥多尔·陀思妥耶夫斯基", 1821, 1881, "俄国", "俄国作家。"),
        _author("维克多·雨果", 1802, 1885, "法国", "法国作家。"),
        _author("居斯塔夫·福楼拜", 1821, 1880, "法国", "法国作家。"),
        _author("简·奥斯汀", 1775, 1817, "英国", "英国作家。"),
        _author("查尔斯·狄更斯", 1812, 1870, "英国", "英国作家。"),
        _author("詹姆斯·乔伊斯", 1882, 1941, "爱尔兰", "爱尔兰作家。"),
        _author("托马斯·曼", 1875, 1955, "德国", "德国作家。"),
        _author("布拉姆·斯托克", 1847, 1912, "爱尔兰", "爱尔兰作家。"),
        _author("F. 司各特·菲茨杰拉德", 1896, 1940, "美国", "美国作家。"),
        _author("赫尔曼·梅尔维尔", 1819, 1891, "美国", "美国作家。"),
        _author("约翰·斯坦贝克", 1902, 1968, "美国", "美国作家。"),
        _author("哈珀·李", 1926, 2016, "美国", "美国作家。"),
        _author("托妮·莫里森", 1931, 2019, "美国", "美国作家。"),
        # --- 佚名（《一千零一夜》无单一作者）---
        _author("佚名", None, None, None, "阿拉伯民间故事集，多源编纂，非单一作者。"),
    ],

    # ------------------------------------------------------------------
    # 71 个地点（14 虚构 + 57 真实；含 6 虚构 + 4 真实复用）
    # ------------------------------------------------------------------
    "places": [
        # --- 虚构地点（复用 6）---
        _fictional("马孔多", "《百年孤独》虚构小镇。"),
        _fictional("大洋国", "《一九八四》虚构国家。"),
        _fictional("地狱", "《神曲》叙事空间。"),
        _fictional("炼狱", "《神曲》叙事空间。"),
        _fictional("天堂", "《神曲》叙事空间。"),
        _fictional("大观园", "《红楼梦》虚构园林。"),
        # --- 虚构地点（新增 8）---
        _fictional("乌姆奥菲亚村", "《瓦解》虚构伊博村落。"),
        _fictional("梅科姆镇", "《杀死一只知更鸟》虚构小镇。"),
        _fictional("俱卢之野", "《摩诃婆罗多》史诗战场（神话空间）。"),
        _fictional("德古拉城堡", "《德古拉》虚构城堡。"),
        _fictional("永镇", "《包法利夫人》虚构小镇。"),
        _fictional("西卵", "《了不起的盖茨比》虚构区域。"),
        _fictional("东卵", "《了不起的盖茨比》虚构区域。"),
        _fictional("大洋国伦敦", "《一九八四》虚构国家大洋国内的伦敦。"),
        # --- 真实地点（复用 4）---
        _real("俄罗斯", "country", description="国家。"),
        _real("莫斯科", "city", country="俄罗斯", description="城市。"),
        _real("圣彼得堡", "city", country="俄罗斯", description="城市。"),
        _real("伦敦", "city", country="英国", description="城市。"),
        # --- 真实地点（新增 53）---
        _real("中国", "country", description="国家。"),
        _real("洛阳", "city", country="中国", description="城市。"),
        _real("许昌", "city", country="中国", description="城市。"),
        _real("成都", "city", country="中国", description="城市。"),
        _real("建业", "city", country="中国", description="城市（今南京，三国时期古称建业）。"),
        _real("北京", "city", country="中国", description="城市。"),
        _real("上海", "city", country="中国", description="城市。"),
        _real("京都", "city", country="日本", description="城市。"),
        _real("越后汤泽", "city", country="日本", region="新潟", description="城镇。"),
        _real("东京", "city", country="日本", description="城市。"),
        _real("越南", "country", description="国家。"),
        _real("印度尼西亚", "country", description="国家。"),
        _real("爪哇", "region", country="印度尼西亚", description="岛屿。"),
        _real("印度", "country", description="国家。"),
        _real("北方邦", "region", country="印度", description="印度邦。"),
        _real("孟买", "city", country="印度", description="城市。"),
        _real("德里", "city", country="印度", description="城市。"),
        _real("巴格达", "city", country="伊拉克", description="城市。"),
        _real("波斯", "region", description="历史地区（今伊朗）。"),
        _real("开罗", "city", country="埃及", description="城市。"),
        _real("南非", "country", description="国家。"),
        _real("达喀尔", "city", country="塞内加尔", description="城市。"),
        _real("尼日利亚", "country", description="国家。"),
        _real("比夫拉", "region", country="尼日利亚", description="历史地区。"),
        _real("哥伦比亚", "country", description="国家。"),
        _real("卡塔赫纳", "city", country="哥伦比亚", description="城市。"),
        _real("布宜诺斯艾利斯", "city", country="阿根廷", description="城市。"),
        _real("里约热内卢", "city", country="巴西", description="城市。"),
        _real("智利", "country", description="国家。"),
        _real("海地", "country", description="国家。"),
        _real("特洛伊", "city", description="古代城邦（今土耳其 Hisarlik 遗址）。"),
        _real("伊萨卡", "region", country="希腊", description="岛屿。"),
        _real("地中海", "region", description="海域。"),
        _real("拉曼恰", "region", country="西班牙", description="地区。"),
        _real("巴黎", "city", country="法国", description="城市。"),
        _real("诺曼底", "region", country="法国", description="地区。"),
        _real("英格兰", "region", country="英国", description="地区。"),
        _real("赫特福德郡", "region", country="英国", description="郡。"),
        _real("肯特", "region", country="英国", description="郡。"),
        _real("都柏林", "city", country="爱尔兰", description="城市。"),
        _real("吕贝克", "city", country="德国", description="城市。"),
        _real("达沃斯", "city", country="瑞士", description="城市。"),
        _real("特兰西瓦尼亚", "region", country="罗马尼亚", description="历史地区。"),
        _real("纽约长岛", "region", country="美国", description="地区。"),
        _real("南塔克特岛", "region", country="美国", description="岛屿。"),
        _real("太平洋海域", "region", description="海域。"),
        _real("俄克拉荷马", "region", country="美国", description="州。"),
        _real("加利福尼亚", "region", country="美国", description="州。"),
        _real("俄亥俄", "region", country="美国", description="州。"),
        _real("辛辛那提", "city", country="美国", description="城市。"),
        _real("阿拉巴马州", "region", country="美国", description="州。"),
        _real("古巴近海", "region", description="古巴附近海域。"),
        _real("加勒比海", "region", description="海域。"),
    ],

    # ------------------------------------------------------------------
    # 50 部作品（6 复用 + 44 新增）
    # ------------------------------------------------------------------
    "books": [
        _book("红楼梦", None, "中文", 1791,
              "曹雪芹章回体小说，中国古典文学高峰。"),
        _book("三国演义", None, "中文", None,
              "罗贯中历史演义小说，讲述三国时期群雄争霸；成书年代约 14 世纪（待核实）。"),
        _book("骆驼祥子", None, "中文", 1937,
              "老舍长篇小说，描写北京人力车夫的命运。"),
        _book("家", None, "中文", 1933,
              "巴金「激流三部曲」第一部，描写封建大家庭的衰败。"),
        _book("子夜", None, "中文", 1933,
              "茅盾长篇小说，描写 20 世纪 30 年代上海民族工业。"),
        _book("长恨歌", None, "中文", 1995,
              "王安忆长篇小说，描写上海女性王琦瑶的一生。"),
        _book("源氏物语", "源氏物語", "古典日语", None,
              "紫式部所作日本古典物语，约成书于 1008 年（待核实）。"),
        _book("雪国", "雪国", "日语", 1937,
              "川端康成中篇小说。"),
        _book("我是猫", "吾輩は猫である", "日语", 1905,
              "夏目漱石长篇小说；分卷连载，首卷出版于 1905 年，1905—1906 年陆续出版。"),
        _book("挪威的森林", "ノルウェイの森", "日语", 1987,
              "村上春树长篇小说。"),
        _book("罗生门", "羅生門", "日语", 1915,
              "芥川龙之介短篇小说。"),
        _book("金云翘传", "Truyện Kiều", "越南语", None,
              "阮攸叙事长诗；成书约 1820 年（待核实）。"),
        _book("人世间", "Bumi Manusia", "印尼语", 1980,
              "普拉姆迪亚·阿南达·杜尔长篇小说；首卷出版于 1980 年，1980—1988 年陆续出版。"),
        _book("戈丹", "Godaan", "印地语/乌尔都语", 1936,
              "普列姆昌德长篇小说。"),
        _book("午夜之子", "Midnight's Children", "英语", 1981,
              "萨尔曼·鲁西迪长篇小说。"),
        _book("摩诃婆罗多", "Mahabharata", "梵语", None,
              "古印度史诗；成书约前 4 世纪至 4 世纪（待核实）。"),
        _book("一千零一夜", "Alf Layla wa-Layla", "阿拉伯语", None,
              "阿拉伯民间故事集；成书于 8—14 世纪（待核实），多源编纂。"),
        _book("开罗三部曲", "Al-Thulathiya", "阿拉伯语", 1956,
              "纳吉布·马哈福兹长篇小说三部曲；首部出版于 1956 年，1956—1957 年陆续出版。"),
        _book("瓦解", "Things Fall Apart", "英语", 1958,
              "钦努阿·阿契贝长篇小说。"),
        _book("哭泣的大地", "Cry, the Beloved Country", "英语", 1948,
              "艾伦·佩顿长篇小说；初版 1948 年。"),
        _book("漫长的信", "Une si longue lettre", "法语", 1979,
              "玛丽亚玛·巴书信体小说。"),
        _book("半轮黄日", "Half of a Yellow Sun", "英语", 2006,
              "奇玛曼达·恩戈兹·阿迪契长篇小说。"),
        _book("百年孤独", "Cien años de soledad", "西班牙语", 1967,
              "加西亚·马尔克斯代表作，魔幻现实主义经典。"),
        _book("霍乱时期的爱情", "El amor en los tiempos del cólera", "西班牙语", 1985,
              "加西亚·马尔克斯长篇小说。"),
        _book("阿莱夫", "El Aleph", "西班牙语", 1949,
              "豪尔赫·路易斯·博尔赫斯短篇小说集。"),
        _book("布拉斯·库巴斯死后的回忆", "Memórias Póstumas de Brás Cubas", "葡萄牙语", 1881,
              "马查多·德·阿西斯长篇小说。"),
        _book("幽灵之家", "La casa de los espíritus", "西班牙语", 1982,
              "伊莎贝尔·阿连德长篇小说。"),
        _book("人间王国", "El reino de este mundo", "西班牙语", 1949,
              "阿莱霍·卡彭铁尔长篇小说。"),
        _book("伊利亚特", "Iliad", "古希腊语", None,
              "荷马史诗；约成书于前 8 世纪（待核实）。"),
        _book("奥德赛", "Odyssey", "古希腊语", None,
              "荷马史诗；约成书于前 8 世纪（待核实）。"),
        _book("神曲", "La Divina Commedia", "意大利语", 1472,
              "但丁的叙事长诗，分地狱、炼狱、天堂三篇。"),
        _book("堂吉诃德", "Don Quijote de la Mancha", "西班牙语", 1605,
              "塞万提斯长篇小说；首卷出版于 1605 年，1605/1615 年分两部出版。"),
        _book("战争与和平", "Война и мир", "俄语", 1869,
              "托尔斯泰长篇小说，以拿破仑战争为背景。"),
        _book("罪与罚", "Преступление и наказание", "俄语", 1866,
              "陀思妥耶夫斯基长篇小说。"),
        _book("安娜·卡列尼娜", "Анна Каренина", "俄语", 1877,
              "托尔斯泰长篇小说。"),
        _book("悲惨世界", "Les Misérables", "法语", 1862,
              "维克多·雨果长篇小说。"),
        _book("包法利夫人", "Madame Bovary", "法语", 1857,
              "福楼拜长篇小说。"),
        _book("傲慢与偏见", "Pride and Prejudice", "英语", 1813,
              "简·奥斯汀长篇小说。"),
        _book("远大前程", "Great Expectations", "英语", 1861,
              "查尔斯·狄更斯长篇小说。"),
        _book("尤利西斯", "Ulysses", "英语", 1922,
              "詹姆斯·乔伊斯长篇小说。"),
        _book("布登勃洛克一家", "Buddenbrooks", "德语", 1901,
              "托马斯·曼长篇小说。"),
        _book("魔山", "Der Zauberberg", "德语", 1924,
              "托马斯·曼长篇小说。"),
        _book("德古拉", "Dracula", "英语", 1897,
              "布拉姆·斯托克哥特小说。"),
        _book("一九八四", "Nineteen Eighty-Four", "英语", 1949,
              "乔治·奥威尔的反乌托邦小说。"),
        _book("了不起的盖茨比", "The Great Gatsby", "英语", 1925,
              "F. 司各特·菲茨杰拉德长篇小说。"),
        _book("白鲸", "Moby-Dick", "英语", 1851,
              "赫尔曼·梅尔维尔长篇小说。"),
        _book("愤怒的葡萄", "The Grapes of Wrath", "英语", 1939,
              "约翰·斯坦贝克长篇小说。"),
        _book("杀死一只知更鸟", "To Kill a Mockingbird", "英语", 1960,
              "哈珀·李长篇小说。"),
        _book("宠儿", "Beloved", "英语", 1987,
              "托妮·莫里森长篇小说。"),
        _book("老人与海", "The Old Man and the Sea", "英语", 1952,
              "海明威的中篇小说。"),
    ],

    # ------------------------------------------------------------------
    # 关联关系
    # ------------------------------------------------------------------
    "book_authors": [
        {"book_title": "红楼梦", "author_name": "曹雪芹", "role": "author"},
        {"book_title": "三国演义", "author_name": "罗贯中", "role": "author"},
        {"book_title": "骆驼祥子", "author_name": "老舍", "role": "author"},
        {"book_title": "家", "author_name": "巴金", "role": "author"},
        {"book_title": "子夜", "author_name": "茅盾", "role": "author"},
        {"book_title": "长恨歌", "author_name": "王安忆", "role": "author"},
        {"book_title": "源氏物语", "author_name": "紫式部", "role": "author"},
        {"book_title": "雪国", "author_name": "川端康成", "role": "author"},
        {"book_title": "我是猫", "author_name": "夏目漱石", "role": "author"},
        {"book_title": "挪威的森林", "author_name": "村上春树", "role": "author"},
        {"book_title": "罗生门", "author_name": "芥川龙之介", "role": "author"},
        {"book_title": "金云翘传", "author_name": "阮攸", "role": "author"},
        {"book_title": "人世间", "author_name": "普拉姆迪亚·阿南达·杜尔", "role": "author"},
        {"book_title": "戈丹", "author_name": "普列姆昌德", "role": "author"},
        {"book_title": "午夜之子", "author_name": "萨尔曼·鲁西迪", "role": "author"},
        {"book_title": "摩诃婆罗多", "author_name": "毗耶娑", "role": "author"},
        {"book_title": "一千零一夜", "author_name": "佚名", "role": "author"},
        {"book_title": "开罗三部曲", "author_name": "纳吉布·马哈福兹", "role": "author"},
        {"book_title": "瓦解", "author_name": "钦努阿·阿契贝", "role": "author"},
        {"book_title": "哭泣的大地", "author_name": "艾伦·佩顿", "role": "author"},
        {"book_title": "漫长的信", "author_name": "玛丽亚玛·巴", "role": "author"},
        {"book_title": "半轮黄日", "author_name": "奇玛曼达·恩戈兹·阿迪契", "role": "author"},
        {"book_title": "百年孤独", "author_name": "加夫列尔·加西亚·马尔克斯", "role": "author"},
        {"book_title": "霍乱时期的爱情", "author_name": "加夫列尔·加西亚·马尔克斯", "role": "author"},
        {"book_title": "阿莱夫", "author_name": "豪尔赫·路易斯·博尔赫斯", "role": "author"},
        {"book_title": "布拉斯·库巴斯死后的回忆", "author_name": "马查多·德·阿西斯", "role": "author"},
        {"book_title": "幽灵之家", "author_name": "伊莎贝尔·阿连德", "role": "author"},
        {"book_title": "人间王国", "author_name": "阿莱霍·卡彭铁尔", "role": "author"},
        {"book_title": "伊利亚特", "author_name": "荷马", "role": "author"},
        {"book_title": "奥德赛", "author_name": "荷马", "role": "author"},
        {"book_title": "神曲", "author_name": "但丁·阿利吉耶里", "role": "author"},
        {"book_title": "堂吉诃德", "author_name": "米格尔·德·塞万提斯", "role": "author"},
        {"book_title": "战争与和平", "author_name": "列夫·托尔斯泰", "role": "author"},
        {"book_title": "罪与罚", "author_name": "费奥多尔·陀思妥耶夫斯基", "role": "author"},
        {"book_title": "安娜·卡列尼娜", "author_name": "列夫·托尔斯泰", "role": "author"},
        {"book_title": "悲惨世界", "author_name": "维克多·雨果", "role": "author"},
        {"book_title": "包法利夫人", "author_name": "居斯塔夫·福楼拜", "role": "author"},
        {"book_title": "傲慢与偏见", "author_name": "简·奥斯汀", "role": "author"},
        {"book_title": "远大前程", "author_name": "查尔斯·狄更斯", "role": "author"},
        {"book_title": "尤利西斯", "author_name": "詹姆斯·乔伊斯", "role": "author"},
        {"book_title": "布登勃洛克一家", "author_name": "托马斯·曼", "role": "author"},
        {"book_title": "魔山", "author_name": "托马斯·曼", "role": "author"},
        {"book_title": "德古拉", "author_name": "布拉姆·斯托克", "role": "author"},
        {"book_title": "一九八四", "author_name": "乔治·奥威尔", "role": "author"},
        {"book_title": "了不起的盖茨比", "author_name": "F. 司各特·菲茨杰拉德", "role": "author"},
        {"book_title": "白鲸", "author_name": "赫尔曼·梅尔维尔", "role": "author"},
        {"book_title": "愤怒的葡萄", "author_name": "约翰·斯坦贝克", "role": "author"},
        {"book_title": "杀死一只知更鸟", "author_name": "哈珀·李", "role": "author"},
        {"book_title": "宠儿", "author_name": "托妮·莫里森", "role": "author"},
        {"book_title": "老人与海", "author_name": "欧内斯特·海明威", "role": "author"},
    ],

    "book_genres": [
        {"book_title": "红楼梦", "genre_name": "章回体小说"},
        {"book_title": "三国演义", "genre_name": "历史演义小说"},
        {"book_title": "三国演义", "genre_name": "章回体小说"},
        {"book_title": "骆驼祥子", "genre_name": "现实主义"},
        {"book_title": "家", "genre_name": "现实主义"},
        {"book_title": "子夜", "genre_name": "现实主义"},
        {"book_title": "长恨歌", "genre_name": "现实主义"},
        {"book_title": "源氏物语", "genre_name": "古典物语"},
        {"book_title": "雪国", "genre_name": "现代主义"},
        {"book_title": "我是猫", "genre_name": "现实主义"},
        {"book_title": "挪威的森林", "genre_name": "现代主义"},
        {"book_title": "罗生门", "genre_name": "现代主义"},
        {"book_title": "金云翘传", "genre_name": "古典物语"},
        {"book_title": "人世间", "genre_name": "现实主义"},
        {"book_title": "戈丹", "genre_name": "现实主义"},
        {"book_title": "午夜之子", "genre_name": "后殖民文学"},
        {"book_title": "午夜之子", "genre_name": "魔幻现实主义"},
        {"book_title": "摩诃婆罗多", "genre_name": "史诗"},
        {"book_title": "一千零一夜", "genre_name": "民间故事集"},
        {"book_title": "开罗三部曲", "genre_name": "现实主义"},
        {"book_title": "瓦解", "genre_name": "后殖民文学"},
        {"book_title": "瓦解", "genre_name": "现实主义"},
        {"book_title": "哭泣的大地", "genre_name": "现实主义"},
        {"book_title": "漫长的信", "genre_name": "现实主义"},
        {"book_title": "半轮黄日", "genre_name": "后殖民文学"},
        {"book_title": "半轮黄日", "genre_name": "现实主义"},
        {"book_title": "百年孤独", "genre_name": "魔幻现实主义"},
        {"book_title": "霍乱时期的爱情", "genre_name": "魔幻现实主义"},
        {"book_title": "阿莱夫", "genre_name": "现代主义"},
        {"book_title": "布拉斯·库巴斯死后的回忆", "genre_name": "现实主义"},
        {"book_title": "幽灵之家", "genre_name": "魔幻现实主义"},
        {"book_title": "人间王国", "genre_name": "魔幻现实主义"},
        {"book_title": "伊利亚特", "genre_name": "史诗"},
        {"book_title": "奥德赛", "genre_name": "史诗"},
        {"book_title": "神曲", "genre_name": "史诗"},
        {"book_title": "堂吉诃德", "genre_name": "现实主义"},
        {"book_title": "战争与和平", "genre_name": "现实主义"},
        {"book_title": "罪与罚", "genre_name": "现实主义"},
        {"book_title": "安娜·卡列尼娜", "genre_name": "现实主义"},
        {"book_title": "悲惨世界", "genre_name": "浪漫主义"},
        {"book_title": "悲惨世界", "genre_name": "现实主义"},
        {"book_title": "包法利夫人", "genre_name": "现实主义"},
        {"book_title": "傲慢与偏见", "genre_name": "浪漫主义"},
        {"book_title": "远大前程", "genre_name": "现实主义"},
        {"book_title": "尤利西斯", "genre_name": "现代主义"},
        {"book_title": "布登勃洛克一家", "genre_name": "现实主义"},
        {"book_title": "魔山", "genre_name": "现代主义"},
        {"book_title": "德古拉", "genre_name": "哥特小说"},
        {"book_title": "一九八四", "genre_name": "反乌托邦"},
        {"book_title": "了不起的盖茨比", "genre_name": "现代主义"},
        {"book_title": "白鲸", "genre_name": "现实主义"},
        {"book_title": "愤怒的葡萄", "genre_name": "现实主义"},
        {"book_title": "杀死一只知更鸟", "genre_name": "现实主义"},
        {"book_title": "宠儿", "genre_name": "后殖民文学"},
        {"book_title": "宠儿", "genre_name": "现代主义"},
        {"book_title": "老人与海", "genre_name": "现代主义"},
    ],

    "book_places": [
        {"book_title": "红楼梦", "place_name": "大观园", "relation_type": "setting"},
        {"book_title": "三国演义", "place_name": "中国", "relation_type": "setting"},
        {"book_title": "三国演义", "place_name": "洛阳", "relation_type": "setting"},
        {"book_title": "三国演义", "place_name": "许昌", "relation_type": "setting"},
        {"book_title": "三国演义", "place_name": "成都", "relation_type": "setting"},
        {"book_title": "三国演义", "place_name": "建业", "relation_type": "setting"},
        {"book_title": "骆驼祥子", "place_name": "北京", "relation_type": "setting"},
        {"book_title": "家", "place_name": "成都", "relation_type": "setting"},
        {"book_title": "子夜", "place_name": "上海", "relation_type": "setting"},
        {"book_title": "长恨歌", "place_name": "上海", "relation_type": "setting"},
        {"book_title": "源氏物语", "place_name": "京都", "relation_type": "setting"},
        {"book_title": "雪国", "place_name": "越后汤泽", "relation_type": "setting"},
        {"book_title": "我是猫", "place_name": "东京", "relation_type": "setting"},
        {"book_title": "挪威的森林", "place_name": "东京", "relation_type": "setting"},
        {"book_title": "罗生门", "place_name": "京都", "relation_type": "setting"},
        {"book_title": "金云翘传", "place_name": "越南", "relation_type": "setting"},
        {"book_title": "人世间", "place_name": "印度尼西亚", "relation_type": "setting"},
        {"book_title": "人世间", "place_name": "爪哇", "relation_type": "setting"},
        {"book_title": "戈丹", "place_name": "印度", "relation_type": "setting"},
        {"book_title": "戈丹", "place_name": "北方邦", "relation_type": "setting"},
        {"book_title": "午夜之子", "place_name": "孟买", "relation_type": "setting"},
        {"book_title": "午夜之子", "place_name": "德里", "relation_type": "setting"},
        {"book_title": "午夜之子", "place_name": "印度", "relation_type": "setting"},
        {"book_title": "摩诃婆罗多", "place_name": "俱卢之野", "relation_type": "setting"},
        {"book_title": "一千零一夜", "place_name": "巴格达", "relation_type": "setting"},
        {"book_title": "一千零一夜", "place_name": "波斯", "relation_type": "setting"},
        {"book_title": "一千零一夜", "place_name": "开罗", "relation_type": "setting"},
        {"book_title": "一千零一夜", "place_name": "印度", "relation_type": "setting"},
        {"book_title": "开罗三部曲", "place_name": "开罗", "relation_type": "setting"},
        {"book_title": "瓦解", "place_name": "乌姆奥菲亚村", "relation_type": "setting"},
        {"book_title": "哭泣的大地", "place_name": "南非", "relation_type": "setting"},
        {"book_title": "漫长的信", "place_name": "达喀尔", "relation_type": "setting"},
        {"book_title": "半轮黄日", "place_name": "尼日利亚", "relation_type": "setting"},
        {"book_title": "半轮黄日", "place_name": "比夫拉", "relation_type": "setting"},
        {"book_title": "百年孤独", "place_name": "马孔多", "relation_type": "setting"},
        {"book_title": "霍乱时期的爱情", "place_name": "哥伦比亚", "relation_type": "setting"},
        {"book_title": "霍乱时期的爱情", "place_name": "卡塔赫纳", "relation_type": "setting"},
        {"book_title": "阿莱夫", "place_name": "布宜诺斯艾利斯", "relation_type": "setting"},
        {"book_title": "布拉斯·库巴斯死后的回忆", "place_name": "里约热内卢", "relation_type": "setting"},
        {"book_title": "幽灵之家", "place_name": "智利", "relation_type": "setting"},
        {"book_title": "人间王国", "place_name": "海地", "relation_type": "setting"},
        {"book_title": "伊利亚特", "place_name": "特洛伊", "relation_type": "setting"},
        {"book_title": "奥德赛", "place_name": "伊萨卡", "relation_type": "setting"},
        {"book_title": "奥德赛", "place_name": "地中海", "relation_type": "setting"},
        {"book_title": "神曲", "place_name": "地狱", "relation_type": "setting"},
        {"book_title": "神曲", "place_name": "炼狱", "relation_type": "setting"},
        {"book_title": "神曲", "place_name": "天堂", "relation_type": "setting"},
        {"book_title": "堂吉诃德", "place_name": "拉曼恰", "relation_type": "setting"},
        {"book_title": "战争与和平", "place_name": "俄罗斯", "relation_type": "setting"},
        {"book_title": "战争与和平", "place_name": "莫斯科", "relation_type": "setting"},
        {"book_title": "战争与和平", "place_name": "圣彼得堡", "relation_type": "setting"},
        {"book_title": "罪与罚", "place_name": "圣彼得堡", "relation_type": "setting"},
        {"book_title": "安娜·卡列尼娜", "place_name": "圣彼得堡", "relation_type": "setting"},
        {"book_title": "安娜·卡列尼娜", "place_name": "莫斯科", "relation_type": "setting"},
        {"book_title": "悲惨世界", "place_name": "巴黎", "relation_type": "setting"},
        {"book_title": "包法利夫人", "place_name": "诺曼底", "relation_type": "setting"},
        {"book_title": "包法利夫人", "place_name": "永镇", "relation_type": "setting"},
        {"book_title": "傲慢与偏见", "place_name": "英格兰", "relation_type": "setting"},
        {"book_title": "傲慢与偏见", "place_name": "赫特福德郡", "relation_type": "setting"},
        {"book_title": "远大前程", "place_name": "伦敦", "relation_type": "setting"},
        {"book_title": "远大前程", "place_name": "肯特", "relation_type": "setting"},
        {"book_title": "尤利西斯", "place_name": "都柏林", "relation_type": "setting"},
        {"book_title": "布登勃洛克一家", "place_name": "吕贝克", "relation_type": "setting"},
        {"book_title": "魔山", "place_name": "达沃斯", "relation_type": "setting"},
        {"book_title": "德古拉", "place_name": "特兰西瓦尼亚", "relation_type": "setting"},
        {"book_title": "德古拉", "place_name": "德古拉城堡", "relation_type": "setting"},
        {"book_title": "一九八四", "place_name": "大洋国", "relation_type": "setting"},
        {"book_title": "一九八四", "place_name": "大洋国伦敦", "relation_type": "setting"},
        {"book_title": "了不起的盖茨比", "place_name": "纽约长岛", "relation_type": "setting"},
        {"book_title": "了不起的盖茨比", "place_name": "西卵", "relation_type": "setting"},
        {"book_title": "了不起的盖茨比", "place_name": "东卵", "relation_type": "setting"},
        {"book_title": "白鲸", "place_name": "南塔克特岛", "relation_type": "setting"},
        {"book_title": "白鲸", "place_name": "太平洋海域", "relation_type": "setting"},
        {"book_title": "愤怒的葡萄", "place_name": "俄克拉荷马", "relation_type": "setting"},
        {"book_title": "愤怒的葡萄", "place_name": "加利福尼亚", "relation_type": "setting"},
        {"book_title": "杀死一只知更鸟", "place_name": "梅科姆镇", "relation_type": "setting"},
        {"book_title": "杀死一只知更鸟", "place_name": "阿拉巴马州", "relation_type": "setting"},
        {"book_title": "宠儿", "place_name": "俄亥俄", "relation_type": "setting"},
        {"book_title": "宠儿", "place_name": "辛辛那提", "relation_type": "setting"},
        {"book_title": "老人与海", "place_name": "古巴近海", "relation_type": "setting"},
        {"book_title": "老人与海", "place_name": "加勒比海", "relation_type": "setting"},
    ],
}
