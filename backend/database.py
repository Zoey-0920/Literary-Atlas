"""Literary Atlas 数据库初始化模块。

本模块使用 Python 标准库 sqlite3 连接 SQLite 数据库，
提供数据库连接，并负责创建业务数据表。
"""

import sqlite3
from pathlib import Path

# 数据库文件所在目录 = 本文件（database.py）所在目录，即 backend/
# 使用 __file__ 定位，确保无论从哪个工作目录启动后端，
# 都能稳定定位到 backend/literary_atlas.db
BASE_DIR = Path(__file__).resolve().parent

# 数据库文件的完整路径
DB_PATH = BASE_DIR / "literary_atlas.db"

# 建表语句集合（按依赖顺序：先父表，后关联表）
# 全部使用 IF NOT EXISTS，保证重复执行不会覆盖已有数据
_SCHEMA_STATEMENTS = [
    # 1. books：文学作品（不存正文，只存元数据）
    """
    CREATE TABLE IF NOT EXISTS books (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        title            TEXT NOT NULL,
        original_title   TEXT,
        language         TEXT,
        publication_year INTEGER,
        description      TEXT,
        source           TEXT,
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at       TEXT
    )
    """,
    # 2. authors：作家
    """
    CREATE TABLE IF NOT EXISTS authors (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        birth_year INTEGER,
        death_year INTEGER,
        nationality TEXT,
        bio        TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT
    )
    """,
    # 3. places：地点（现实 / 虚构，支持层级与经纬度约束）
    """
    CREATE TABLE IF NOT EXISTS places (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        place_type      TEXT NOT NULL,
        is_fictional    INTEGER NOT NULL DEFAULT 0,
        latitude        REAL,
        longitude       REAL,
        country         TEXT,
        region          TEXT,
        parent_place_id INTEGER,
        description     TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at      TEXT,
        FOREIGN KEY (parent_place_id) REFERENCES places(id) ON DELETE SET NULL,
        CHECK (is_fictional IN (0, 1)),
        CHECK (place_type IN ('country', 'city', 'region', 'fictional')),
        -- 纬度范围
        CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
        -- 经度范围
        CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),
        -- 经纬度必须同时为空或同时填写
        CHECK ((latitude IS NULL AND longitude IS NULL)
               OR (latitude IS NOT NULL AND longitude IS NOT NULL)),
        -- 虚构地点不能填写经纬度
        CHECK (NOT (is_fictional = 1
                    AND (latitude IS NOT NULL OR longitude IS NOT NULL))),
        -- place_type 与 is_fictional 保持一致
        CHECK ((place_type = 'fictional' AND is_fictional = 1)
               OR (place_type <> 'fictional' AND is_fictional = 0))
    )
    """,
    # 4. genres：文学流派
    """
    CREATE TABLE IF NOT EXISTS genres (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT
    )
    """,
    # 5. book_authors：作品 ↔ 作家（多对多）
    """
    CREATE TABLE IF NOT EXISTS book_authors (
        book_id    INTEGER NOT NULL,
        author_id  INTEGER NOT NULL,
        role       TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (book_id, author_id),
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE,
        CHECK (role IS NULL OR role IN ('author', 'translator', 'editor'))
    )
    """,
    # 6. book_places：作品 ↔ 地点（核心关联表）
    """
    CREATE TABLE IF NOT EXISTS book_places (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id             INTEGER NOT NULL,
        place_id            INTEGER NOT NULL,
        relation_type       TEXT NOT NULL,
        source_name         TEXT,
        source_url          TEXT,
        note                TEXT,
        verification_status TEXT NOT NULL DEFAULT 'unverified',
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT,
        UNIQUE (book_id, place_id, relation_type),
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        CHECK (relation_type IN ('setting', 'depiction')),
        CHECK (verification_status IN ('verified', 'unverified', 'disputed'))
    )
    """,
    # 7. book_genres：作品 ↔ 流派（多对多）
    """
    CREATE TABLE IF NOT EXISTS book_genres (
        book_id    INTEGER NOT NULL,
        genre_id   INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (book_id, genre_id),
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
    )
    """,
    # 8. author_places：作家 ↔ 地点（关联）
    """
    CREATE TABLE IF NOT EXISTS author_places (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id           INTEGER NOT NULL,
        place_id            INTEGER NOT NULL,
        relation_type       TEXT NOT NULL,
        source_name         TEXT,
        source_url          TEXT,
        note                TEXT,
        verification_status TEXT NOT NULL DEFAULT 'unverified',
        start_year          INTEGER,
        end_year            INTEGER,
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT,
        UNIQUE (author_id, place_id, relation_type),
        FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        CHECK (relation_type IN ('birthplace', 'residence', 'creation')),
        CHECK (verification_status IN ('verified', 'unverified', 'disputed'))
    )
    """,
    # 9. reading_records：个人阅读记录
    """
    CREATE TABLE IF NOT EXISTS reading_records (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        book_id     INTEGER NOT NULL,
        status      TEXT NOT NULL,
        rating      INTEGER,
        progress    INTEGER,
        started_at  TEXT,
        finished_at TEXT,
        note        TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT,
        UNIQUE (user_id, book_id),
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
        CHECK (status IN ('want_to_read', 'reading', 'finished')),
        CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
        CHECK (progress IS NULL OR (progress BETWEEN 0 AND 100))
    )
    """,
]


def get_db_connection():
    """建立并返回一个 SQLite 数据库连接对象。

    返回的连接使用 sqlite3.Row 作为行工厂，
    这样查询结果可以通过字段名称读取，例如 row["name"]。
    同时启用外键约束（SQLite 默认不强制外键）。

    注意：连接使用完毕后，需要由调用者调用 close() 关闭。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite 默认不强制外键，必须在每个连接中显式开启
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    """对旧版数据库做最小迁移，补齐后续新增的列。

    通过 PRAGMA table_info 检查列是否存在，幂等且不覆盖已有数据。
    目前仅用于 reading_records 表新增 progress（阅读进度百分比）列。
    """
    cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(reading_records)").fetchall()
    }
    if "progress" not in cols:
        conn.execute("ALTER TABLE reading_records ADD COLUMN progress INTEGER")


def init_db():
    """初始化数据库：创建所有业务数据表。

    使用 CREATE TABLE IF NOT EXISTS，因此可以重复执行而不覆盖已有数据。
    """
    conn = get_db_connection()
    try:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        _migrate(conn)
        conn.commit()
    finally:
        # 无论是否发生异常，都确保连接被关闭，释放资源
        conn.close()