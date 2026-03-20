import sqlite3

import pandas as pd

from db import add_audit_log, get_audit_log_entries, get_connection


def create_department(name, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    department_name = name.strip()
    cursor.execute(
        "INSERT OR IGNORE INTO departments (name) VALUES (?)",
        (department_name,),
    )
    department = cursor.execute(
        "SELECT id, name FROM departments WHERE name=?",
        (department_name,),
    ).fetchone()
    conn.commit()
    conn.close()
    if department:
        add_audit_log(actor_id, "department", department["id"], "create_department", f"Добавлена кафедра: {department['name']}")


def get_departments():
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM departments ORDER BY name").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_user(username, password, role, full_name, department_id=None, position=None, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_username = username.strip()
        clean_full_name = full_name.strip()
        clean_position = (position or "").strip()
        cursor.execute(
            """
            INSERT INTO users (username, password, role, full_name, department_id, position)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                clean_username,
                password,
                role,
                clean_full_name,
                department_id,
                clean_position,
            ),
        )
        user_id = cursor.lastrowid
        department_name = None
        if department_id:
            department = cursor.execute("SELECT name FROM departments WHERE id=?", (department_id,)).fetchone()
            department_name = department["name"] if department else None
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "users.username" in str(exc):
            raise ValueError("Пользователь с таким логином уже существует") from exc
        raise
    finally:
        conn.close()
    add_audit_log(
        actor_id,
        "user",
        user_id,
        "create_user",
        f"Создан пользователь {clean_full_name} ({clean_username}), роль: {role}, кафедра: {department_name or 'не указана'}",
    )


def get_users():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            users.id,
            users.full_name,
            users.username,
            users.role,
            COALESCE(departments.name, 'Без кафедры') AS department,
            COALESCE(users.position, '') AS position,
            CASE
                WHEN COALESCE(users.password, '') = '' THEN 'Не задан'
                ELSE 'Задан'
            END AS password_status
        FROM users
        LEFT JOIN departments ON departments.id = users.department_id
        ORDER BY users.role, users.full_name, users.username
        """,
        conn,
    )
    conn.close()
    df["role"] = df["role"].replace(
        {
            "admin": "Администратор",
            "head": "Заведующий кафедрой",
            "teacher": "Преподаватель",
        }
    )
    return df


def get_user_options():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, username, COALESCE(full_name, username) AS display_name, role
        FROM users
        ORDER BY role, display_name
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_user_password(user_id, new_password, actor_id=None):
    if not new_password:
        raise ValueError("Пароль не должен быть пустым")

    conn = get_connection()
    cursor = conn.cursor()
    user = cursor.execute(
        "SELECT username, COALESCE(full_name, username) AS display_name FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    cursor.execute(
        "UPDATE users SET password=? WHERE id=?",
        (new_password, user_id),
    )
    conn.commit()
    conn.close()
    if user:
        add_audit_log(actor_id, "user", user_id, "set_password", f"Назначен новый пароль для {user['display_name']}")


def delete_user(user_id, current_admin_id=None, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT id, username, role FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not user:
        conn.close()
        raise ValueError("Пользователь не найден")

    if current_admin_id is not None and int(user["id"]) == int(current_admin_id):
        conn.close()
        raise ValueError("Нельзя удалить текущего пользователя")

    if user["role"] == "admin":
        admin_count = cursor.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role='admin'"
        ).fetchone()["total"]
        if admin_count <= 1:
            conn.close()
            raise ValueError("Нельзя удалить единственного администратора")

    cursor.execute("UPDATE criteria SET teacher_id=NULL WHERE teacher_id=?", (user_id,))
    cursor.execute("UPDATE reports SET reviewer_id=NULL WHERE reviewer_id=?", (user_id,))
    cursor.execute("UPDATE report_items SET reviewed_by=NULL WHERE reviewed_by=?", (user_id,))
    cursor.execute("UPDATE report_history SET actor_id=NULL WHERE actor_id=?", (user_id,))
    cursor.execute("UPDATE system_audit_log SET actor_id=NULL WHERE actor_id=?", (user_id,))
    cursor.execute("DELETE FROM reports WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    add_audit_log(actor_id, "user", user_id, "delete_user", f"Удален пользователь {user['username']}")


def get_criteria_groups():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, code, name, group_type FROM criteria_groups ORDER BY code"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_criteria_group(code, name, group_type="effectiveness", actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    group_code = code.strip()
    group_name = name.strip()
    cursor.execute(
        """
        INSERT INTO criteria_groups (code, name, group_type)
        VALUES (?, ?, ?)
        """,
        (group_code, group_name, group_type),
    )
    group_id = cursor.lastrowid
    conn.commit()
    conn.close()
    add_audit_log(actor_id, "criteria_group", group_id, "create_group", f"Создана группа {group_code} {group_name}")


def update_criteria_group(group_id, code, name, group_type="effectiveness", actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    group_code = code.strip()
    group_name = name.strip()
    cursor.execute(
        """
        UPDATE criteria_groups
        SET code=?, name=?, group_type=?
        WHERE id=?
        """,
        (group_code, group_name, group_type, group_id),
    )
    conn.commit()
    conn.close()
    add_audit_log(actor_id, "criteria_group", group_id, "update_group", f"Обновлена группа {group_code} {group_name}")


def delete_criteria_group(group_id, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    group = cursor.execute(
        "SELECT code, name FROM criteria_groups WHERE id=?",
        (group_id,),
    ).fetchone()
    linked_criteria = cursor.execute(
        "SELECT COUNT(*) AS total FROM criteria WHERE group_id=?",
        (group_id,),
    ).fetchone()["total"]
    if linked_criteria:
        conn.close()
        raise ValueError("Нельзя удалить группу, пока в ней есть критерии")

    cursor.execute("DELETE FROM criteria_groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()
    if group:
        add_audit_log(actor_id, "criteria_group", group_id, "delete_group", f"Удалена группа {group['code']} {group['name']}")


def create_criterion(group_id, code, name, base, score, score_text, confirmation_type, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    criterion_code = code.strip()
    criterion_name = name.strip()
    cursor.execute(
        """
        INSERT INTO criteria (group_id, code, criterion_name, base, score, score_text, confirmation_type, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            group_id,
            criterion_code,
            criterion_name,
            base.strip(),
            float(score),
            score_text.strip(),
            confirmation_type,
        ),
    )
    criterion_id = cursor.lastrowid
    conn.commit()
    conn.close()
    add_audit_log(actor_id, "criterion", criterion_id, "create_criterion", f"Создан критерий {criterion_code} {criterion_name}")


def update_criterion(criterion_id, group_id, code, name, base, score, score_text, confirmation_type, is_active, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    criterion_code = code.strip()
    criterion_name = name.strip()
    cursor.execute(
        """
        UPDATE criteria
        SET
            group_id=?,
            code=?,
            criterion_name=?,
            base=?,
            score=?,
            score_text=?,
            confirmation_type=?,
            is_active=?
        WHERE id=?
        """,
        (
            group_id,
            criterion_code,
            criterion_name,
            base.strip(),
            float(score),
            score_text.strip(),
            confirmation_type,
            1 if is_active else 0,
            criterion_id,
        ),
    )
    conn.commit()
    conn.close()
    add_audit_log(
        actor_id,
        "criterion",
        criterion_id,
        "update_criterion",
        f"Обновлен критерий {criterion_code} {criterion_name}, активен: {'да' if is_active else 'нет'}",
    )


def delete_criterion(criterion_id, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    criterion = cursor.execute(
        "SELECT code, criterion_name FROM criteria WHERE id=?",
        (criterion_id,),
    ).fetchone()
    used_in_reports = cursor.execute(
        "SELECT COUNT(*) AS total FROM report_items WHERE criteria_id=?",
        (criterion_id,),
    ).fetchone()["total"]
    if used_in_reports:
        conn.close()
        raise ValueError("Нельзя удалить критерий, который уже использовался в отчетах. Отключите его.")

    cursor.execute("DELETE FROM criteria WHERE id=?", (criterion_id,))
    conn.commit()
    conn.close()
    if criterion:
        add_audit_log(
            actor_id,
            "criterion",
            criterion_id,
            "delete_criterion",
            f"Удален критерий {criterion['code']} {criterion['criterion_name']}",
        )


def get_criteria_table():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            criteria.id,
            criteria.group_id,
            criteria.code,
            criteria.criterion_name,
            criteria.base,
            criteria.score,
            criteria.score_text,
            criteria.confirmation_type,
            criteria.is_active,
            criteria_groups.name AS group_name
        FROM criteria
        LEFT JOIN criteria_groups ON criteria_groups.id = criteria.group_id
        ORDER BY criteria_groups.code, criteria.code
        """,
        conn,
    )
    conn.close()
    df["confirmation_type"] = df["confirmation_type"].replace(
        {"file": "Файл", "text": "Текст"}
    )
    df["is_active"] = df["is_active"].replace({1: "Да", 0: "Нет"})
    return df


def get_all_criteria():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            reports.period,
            reports.status AS report_status,
            users.full_name,
            users.username,
            COALESCE(departments.name, 'Без кафедры') AS department,
            criteria_groups.name AS group_name,
            criteria.code,
            criteria.criterion_name,
            report_items.quantity,
            report_items.claimed_score,
            report_items.status AS item_status
        FROM report_items
        JOIN reports ON reports.id = report_items.report_id
        JOIN users ON users.id = reports.user_id
        LEFT JOIN departments ON departments.id = users.department_id
        JOIN criteria ON criteria.id = report_items.criteria_id
        LEFT JOIN criteria_groups ON criteria_groups.id = criteria.group_id
        ORDER BY reports.period DESC, users.full_name, criteria.code
        """,
        conn,
    )
    conn.close()
    df["report_status"] = df["report_status"].replace(
        {
            "draft": "Черновик",
            "returned": "На доработке",
            "submitted": "На проверке",
            "reviewed": "Проверен",
        }
    )
    df["item_status"] = df["item_status"].replace(
        {
            "pending": "Ожидает решения",
            "approved": "Подтвержден",
            "rejected": "Отклонен",
        }
    )
    return df


def get_admin_summary():
    conn = get_connection()
    cursor = conn.cursor()

    users_count = cursor.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    reports_count = cursor.execute("SELECT COUNT(*) AS total FROM reports").fetchone()["total"]
    submitted_count = cursor.execute(
        "SELECT COUNT(*) AS total FROM reports WHERE status='submitted'"
    ).fetchone()["total"]
    reviewed_count = cursor.execute(
        "SELECT COUNT(*) AS total FROM reports WHERE status='reviewed'"
    ).fetchone()["total"]

    conn.close()
    return {
        "users": users_count,
        "reports": reports_count,
        "submitted": submitted_count,
        "reviewed": reviewed_count,
    }


def get_audit_log(limit=200):
    return get_audit_log_entries(limit=limit)


def get_periods():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT period FROM reports ORDER BY period DESC"
    ).fetchall()
    conn.close()
    return [row["period"] for row in rows]


def calculate_payments(period):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            users.full_name,
            COALESCE(users.position, '') AS position,
            COALESCE(departments.name, 'Без кафедры') AS department,
            SUM(CASE WHEN report_items.status = 'approved' THEN report_items.claimed_score ELSE 0 END) AS total_points
        FROM reports
        JOIN users ON users.id = reports.user_id
        LEFT JOIN departments ON departments.id = users.department_id
        LEFT JOIN report_items ON report_items.report_id = reports.id
        WHERE reports.period = ? AND reports.status = 'reviewed'
        GROUP BY users.id, users.full_name, users.position, departments.name
        ORDER BY users.full_name
        """,
        conn,
        params=(period,),
    )
    conn.close()

    if df.empty:
        return df

    df["total_points"] = df["total_points"].fillna(0)
    return df


def build_order_html(period, payments_df):
    rows_html = []
    for index, row in payments_df.iterrows():
        rows_html.append(
            f"""
            <tr>
                <td>{index + 1}</td>
                <td>{row['full_name']}</td>
                <td>{row['position'] or '-'}</td>
                <td>{row['department']}</td>
                <td>{row['total_points']:.2f}</td>
            </tr>
            """
        )

    body = "\n".join(rows_html) or "<tr><td colspan='5'>Нет данных</td></tr>"

    return f"""
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>Приказ по стимулирующим выплатам</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .meta {{ text-align: right; margin-bottom: 20px; line-height: 1.5; }}
            h1, h2 {{ margin-bottom: 8px; }}
            p {{ margin: 4px 0 16px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
            th, td {{ border: 1px solid #444; padding: 8px; text-align: left; }}
            th {{ background: #f0f0f0; }}
            .signatures {{ margin-top: 28px; line-height: 1.8; }}
        </style>
    </head>
    <body>
        <div class="meta">
            <div>Читинский институт Байкальского государственного университета</div>
            <div>Проект документа от ____________</div>
        </div>
        <h1>Проект приказа</h1>
        <h2>Обобщенные сведения за период {period}</h2>
        <table>
            <thead>
                <tr>
                    <th>№</th>
                    <th>ФИО</th>
                    <th>Должность</th>
                    <th>Кафедра</th>
                    <th>Итоговые баллы</th>
                </tr>
            </thead>
            <tbody>{body}</tbody>
        </table>
        <div class="signatures">
            <div>Подготовил: ____________________</div>
            <div>Согласовано: ____________________</div>
        </div>
    </body>
    </html>
    """
