import sqlite3
from pathlib import Path

DB_NAME = "database.db"
UPLOADS_DIR = Path("uploads")

GROUP_SEEDS = [
    ("1", "Укрепление кадрового потенциала", "effectiveness"),
    ("2", "Развитие образовательной деятельности", "effectiveness"),
    ("3", "Научно-исследовательская деятельность", "effectiveness"),
    ("4", "Молодежная политика и воспитательная работа", "effectiveness"),
    ("5", "Привлечение талантливой молодежи и профориентационная работа", "effectiveness"),
    ("6", "Медийная активность", "effectiveness"),
]

CRITERIA_SEEDS = [
    ("1", "1.1", "Защита докторской диссертации для соискателя", "Одна защита", 200, "200", "file"),
    ("1", "1.2", "Защита докторской диссертации для научного консультанта соискателя", "Одна защита", 100, "100", "file"),
    ("1", "1.3", "Защита кандидатской диссертации для соискателя", "Одна защита", 100, "100", "file"),
    ("1", "1.4", "Защита кандидатской диссертации для научного руководителя соискателя", "Одна защита", 100, "100", "file"),
    ("1", "1.5", "Присвоение ученого звания профессора ВАК МНиВО РФ", "Одно звание", 150, "150", "file"),
    ("1", "1.6", "Присвоение ученого звания доцента ВАК МНиВО РФ", "Одно звание", 150, "150", "file"),
    ("1", "1.7", "Рейтинг преподавателя по результатам анкетирования студентов", "Рейтинг 42-45", 10, "10", "text"),
    ("1", "1.8", "Работа независимым экспертом в государственных комиссиях", "Отчетный период", 10, "10", "file"),
    ("1", "1.9", "Повышение квалификации преподавателем", "Каждые 18 часов", 5, "по 5 за каждые 18 часов", "file"),
    ("1", "1.10", "Профессиональная переподготовка", "Одна программа", 150, "от 50 до 150", "file"),
    ("2", "2.1", "Издание учебника", "Один учебник", 200, "200 на коллектив авторов", "file"),
    ("2", "2.2", "Издание учебных и учебно-методических пособий", "Одно издание", 80, "80 на коллектив авторов", "file"),
    ("2", "2.3", "Издание учебных наглядных пособий и рабочих тетрадей", "Один п.л.", 8, "8 на коллектив авторов", "file"),
    ("2", "2.4", "Повторное издание учебно-методической литературы с доработкой", "Один п.л.", 1, "1 на коллектив авторов", "file"),
    ("2", "2.5", "Разработка новых учебных планов по ФГОС ВО", "Два плана", 80, "80 на коллектив авторов", "file"),
    ("2", "2.6", "Разработка рабочих программ дисциплин, практик и ГИА", "Одна программа", 3, "3 на коллектив авторов", "file"),
    ("2", "2.7", "Актуализация программ для смежных профилей и направлений", "Одна программа", 1, "1 на коллектив авторов", "file"),
    ("2", "2.8", "Создание электронного учебного курса по дисциплине", "Одна программа", 100, "100-40 на коллектив авторов", "file"),
    ("2", "2.9", "Создание онлайн-курса по ДПО или переподготовке", "Одна программа", 200, "200-100 на коллектив авторов", "file"),
    ("2", "2.10", "ВКР на отлично с актом внедрения под научным руководством", "Одна работа", 5, "5", "file"),
    ("3", "3.1", "Выполнение НИР по темам с госрегистрацией", "Один п.л. отчета", 20, "20 на коллектив авторов", "file"),
    ("3", "3.2", "Хоздоговорная или НИР до одного млн рублей для руководителя", "Календарный год", 20, "20", "file"),
    ("3", "3.3", "Хоздоговорная или НИР свыше одного млн рублей для руководителя", "Календарный год", 40, "40", "file"),
    ("3", "3.4", "Хоздоговорная или НИР для исполнителя", "Календарный год", 10, "10", "file"),
    ("3", "3.5", "Издание монографии", "Одна монография", 100, "100", "file"),
    ("3", "3.6", "Публикация статьи в изданиях ВАК", "Одна статья", 30, "30 на коллектив авторов", "file"),
    ("3", "3.7", "Публикация статьи в Web of Science, Scopus или ядре РИНЦ", "Одна статья", 60, "60 на коллектив авторов", "file"),
    ("3", "3.8", "Публикация статьи в РИНЦ", "Одна статья", 10, "10 на коллектив авторов", "file"),
    ("3", "3.9", "Получение патента или свидетельства на программу для ЭВМ", "Один документ", 40, "40 на коллектив авторов", "file"),
    ("3", "3.10", "Подача заявки на финансируемую НИР федерального уровня", "Одна заявка", 20, "20 на коллектив авторов", "file"),
    ("3", "3.11", "Подача заявки на региональные гранты", "Одна заявка", 10, "10 на коллектив авторов", "file"),
    ("3", "3.12", "Организация международной или всероссийской конференции для руководителя оргкомитета", "Одно мероприятие", 50, "50", "file"),
    ("3", "3.13", "Организация международной или всероссийской конференции для секций и оргкомитета", "Одно мероприятие", 25, "25", "file"),
    ("3", "3.14", "Организация региональной научной конференции для руководителя оргкомитета", "Одно мероприятие", 10, "10", "file"),
    ("3", "3.15", "Организация региональной научной конференции для секций и оргкомитета", "Одно мероприятие", 5, "5", "file"),
    ("3", "3.16", "Организация региональных студенческих научных мероприятий для руководителя оргкомитета", "Одно мероприятие", 10, "10", "file"),
    ("3", "3.17", "Организация региональных студенческих научных мероприятий для секций и оргкомитета", "Одно мероприятие", 5, "5", "file"),
    ("3", "3.18", "Руководство подготовкой студенческих докладов на конференцию", "Один доклад", 1, "1", "file"),
    ("3", "3.19", "Руководство призовыми студенческими докладами", "Один доклад", 2, "2", "file"),
    ("4", "4.1", "Подготовка команды или студентов-призеров всероссийского уровня", "Одно призовое место", 10, "10", "file"),
    ("4", "4.2", "Подготовка команды или студентов-призеров регионального уровня", "Одно призовое место", 5, "5", "file"),
    ("4", "4.3", "Организация студенческих конкурсов и соревнований всероссийского уровня", "Одно мероприятие", 20, "20", "file"),
    ("4", "4.4", "Организация студенческих конкурсов и соревнований регионального уровня", "Одно мероприятие", 10, "10", "file"),
    ("4", "4.5", "Работа куратором студенческой группы", "Учебный год", 30, "30", "file"),
    ("4", "4.6", "Работа куратором группы колледжа", "Учебный год", 50, "50", "file"),
    ("5", "5.1", "Разработка программ дополнительного довузовского образования", "Одна программа", 100, "100-40 на коллектив авторов", "file"),
    ("5", "5.2", "Мероприятия для выявления и привлечения талантливой молодежи", "Одно мероприятие", 50, "50", "file"),
    ("5", "5.3", "Проведение профориентационного мероприятия в черте города", "Одно мероприятие", 25, "25 на коллектив сотрудников", "file"),
    ("5", "5.4", "Проведение профориентационного мероприятия за чертой города", "Одно мероприятие", 60, "60 на коллектив сотрудников", "file"),
    ("5", "5.5", "Привлечение абитуриента с заключением договора", "1 абитуриент", 25, "25", "file"),
    ("6", "6.1", "Публикация статьи об институте в СМИ Забайкальского края", "1 статья", 10, "10", "file"),
    ("6", "6.2", "Предоставление поста для социальных сетей", "1 пост", 5, "5", "file"),
    ("6", "6.3", "Предоставление информации для поста в социальных сетях", "1 пост", 2, "2", "file"),
]


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(cursor, table_name):
    row = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(cursor, table_name, column_name):
    columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def _ensure_column(cursor, table_name, column_name, definition):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _create_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT,
            department_id INTEGER,
            position TEXT,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            group_type TEXT DEFAULT 'effectiveness'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            criterion_name TEXT,
            value REAL,
            group_id INTEGER,
            code TEXT UNIQUE,
            base TEXT,
            score REAL DEFAULT 0,
            score_text TEXT,
            confirmation_type TEXT DEFAULT 'file',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (teacher_id) REFERENCES users(id),
            FOREIGN KEY (group_id) REFERENCES criteria_groups(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at TEXT,
            reviewed_at TEXT,
            reviewer_id INTEGER,
            reviewer_comment TEXT,
            UNIQUE(user_id, period),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (reviewer_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS report_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            criteria_id INTEGER NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            teacher_comment TEXT,
            attachment_name TEXT,
            attachment_path TEXT,
            claimed_score REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            review_comment TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(report_id, criteria_id),
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY (criteria_id) REFERENCES criteria(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS report_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            actor_id INTEGER,
            action_type TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS service_note_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            teacher_scope TEXT NOT NULL,
            note_number INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(department_id, period, teacher_scope),
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            action_type TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (actor_id) REFERENCES users(id)
        )
        """
    )


def _migrate_legacy_schema(cursor):
    if _table_exists(cursor, "users"):
        _ensure_column(cursor, "users", "full_name", "TEXT")
        _ensure_column(cursor, "users", "department_id", "INTEGER")
        _ensure_column(cursor, "users", "position", "TEXT")

    if _table_exists(cursor, "criteria"):
        _ensure_column(cursor, "criteria", "group_id", "INTEGER")
        _ensure_column(cursor, "criteria", "code", "TEXT")
        _ensure_column(cursor, "criteria", "base", "TEXT")
        _ensure_column(cursor, "criteria", "score", "REAL DEFAULT 0")
        _ensure_column(cursor, "criteria", "score_text", "TEXT")
        _ensure_column(cursor, "criteria", "confirmation_type", "TEXT DEFAULT 'file'")
        _ensure_column(cursor, "criteria", "is_active", "INTEGER DEFAULT 1")


def _seed_reference_data(cursor):
    for code, name, group_type in GROUP_SEEDS:
        existing_group = cursor.execute(
            "SELECT id FROM criteria_groups WHERE code=?",
            (code,),
        ).fetchone()
        if existing_group:
            cursor.execute(
                """
                UPDATE criteria_groups
                SET name=?, group_type=?
                WHERE code=?
                """,
                (name, group_type, code),
            )
        else:
            cursor.execute(
                """
                INSERT INTO criteria_groups (code, name, group_type)
                VALUES (?, ?, ?)
                """,
                (code, name, group_type),
            )

    group_map = {
        row["code"]: row["id"]
        for row in cursor.execute("SELECT id, code FROM criteria_groups").fetchall()
    }

    for group_code, code, name, base, score, score_text, confirmation_type in CRITERIA_SEEDS:
        existing_criterion = cursor.execute(
            "SELECT id FROM criteria WHERE code=?",
            (code,),
        ).fetchone()
        params = (
            group_map[group_code],
            name,
            base,
            score,
            score_text,
            confirmation_type,
            code,
        )
        if existing_criterion:
            cursor.execute(
                """
                UPDATE criteria
                SET
                    group_id=?,
                    criterion_name=?,
                    base=?,
                    score=?,
                    score_text=?,
                    confirmation_type=?,
                    is_active=1
                WHERE code=?
                """,
                params,
            )
        else:
            cursor.execute(
                """
                INSERT INTO criteria (
                    group_id,
                    code,
                    criterion_name,
                    base,
                    score,
                    score_text,
                    confirmation_type,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    group_map[group_code],
                    code,
                    name,
                    base,
                    score,
                    score_text,
                    confirmation_type,
                ),
            )


def _seed_defaults(cursor):
    cursor.execute(
        "INSERT OR IGNORE INTO departments (name) VALUES (?)",
        ("Кафедра по умолчанию",),
    )
    department = cursor.execute(
        "SELECT id FROM departments WHERE name=?",
        ("Кафедра по умолчанию",),
    ).fetchone()

    existing_admin = cursor.execute(
        "SELECT id, full_name, department_id, position FROM users WHERE username=?",
        ("admin",),
    ).fetchone()
    if existing_admin:
        cursor.execute(
            """
            UPDATE users
            SET
                password=?,
                role='admin',
                full_name=COALESCE(NULLIF(full_name, ''), ?),
                department_id=COALESCE(department_id, ?),
                position=COALESCE(NULLIF(position, ''), ?)
            WHERE username=?
            """,
            ("admin", "Администратор", department["id"], "Администратор", "admin"),
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (username, password, role, full_name, department_id, position)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("admin", "admin", "admin", "Администратор", department["id"], "Администратор"),
        )


def init_db():
    UPLOADS_DIR.mkdir(exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    _create_tables(cursor)
    _migrate_legacy_schema(cursor)
    _seed_reference_data(cursor)
    _seed_defaults(cursor)

    conn.commit()
    conn.close()


def add_report_history(report_id, actor_id, action_type, details=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO report_history (report_id, actor_id, action_type, details)
        VALUES (?, ?, ?, ?)
        """,
        (report_id, actor_id, action_type, details.strip()),
    )
    conn.commit()
    conn.close()


def get_report_history_entries(report_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            report_history.id,
            report_history.action_type,
            COALESCE(report_history.details, '') AS details,
            report_history.created_at,
            COALESCE(users.full_name, users.username, 'Система') AS actor_name
        FROM report_history
        LEFT JOIN users ON users.id = report_history.actor_id
        WHERE report_history.report_id = ?
        ORDER BY report_history.created_at DESC, report_history.id DESC
        """,
        (report_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_audit_log(actor_id, entity_type, entity_id, action_type, details=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO system_audit_log (actor_id, entity_type, entity_id, action_type, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            actor_id,
            entity_type.strip(),
            str(entity_id).strip() if entity_id is not None else None,
            action_type.strip(),
            details.strip(),
        ),
    )
    conn.commit()
    conn.close()


def get_audit_log_entries(limit=200):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            system_audit_log.id,
            system_audit_log.entity_type,
            COALESCE(system_audit_log.entity_id, '') AS entity_id,
            system_audit_log.action_type,
            COALESCE(system_audit_log.details, '') AS details,
            system_audit_log.created_at,
            COALESCE(users.full_name, users.username, 'Система') AS actor_name
        FROM system_audit_log
        LEFT JOIN users ON users.id = system_audit_log.actor_id
        ORDER BY system_audit_log.created_at DESC, system_audit_log.id DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
