import sqlite3

import pandas as pd

from db import get_connection


def create_department(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO departments (name) VALUES (?)",
        (name.strip(),),
    )
    conn.commit()
    conn.close()


def get_departments():
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM departments ORDER BY name").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_user(username, password, role, full_name, department_id=None, position=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, password, role, full_name, department_id, position)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username.strip(),
                password,
                role,
                full_name.strip(),
                department_id,
                (position or "").strip(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "users.username" in str(exc):
            raise ValueError("Пользователь с таким логином уже существует") from exc
        raise
    finally:
        conn.close()


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
            COALESCE(users.position, '') AS position
        FROM users
        LEFT JOIN departments ON departments.id = users.department_id
        ORDER BY users.role, users.full_name, users.username
        """,
        conn,
    )
    conn.close()
    return df


def get_criteria_groups():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, code, name, group_type FROM criteria_groups ORDER BY code"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_criteria_group(code, name, group_type="effectiveness"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO criteria_groups (code, name, group_type)
        VALUES (?, ?, ?)
        """,
        (code.strip(), name.strip(), group_type),
    )
    conn.commit()
    conn.close()


def create_criterion(group_id, code, name, base, score, score_text, confirmation_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO criteria (group_id, code, criterion_name, base, score, score_text, confirmation_type, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            group_id,
            code.strip(),
            name.strip(),
            base.strip(),
            float(score),
            score_text.strip(),
            confirmation_type,
        ),
    )
    conn.commit()
    conn.close()


def get_criteria_table():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            criteria.id,
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


def get_periods():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT period FROM reports ORDER BY period DESC"
    ).fetchall()
    conn.close()
    return [row["period"] for row in rows]


def calculate_payments(period, point_cost):
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
    df["point_cost"] = float(point_cost)
    df["payment"] = df["total_points"] * float(point_cost)
    return df


def build_order_html(period, point_cost, payments_df):
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
                <td>{row['payment']:.2f}</td>
            </tr>
            """
        )

    body = "\n".join(rows_html) or "<tr><td colspan='6'>Нет данных</td></tr>"

    return f"""
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>Приказ по стимулирующим выплатам</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1, h2 {{ margin-bottom: 8px; }}
            p {{ margin: 4px 0 16px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
            th, td {{ border: 1px solid #444; padding: 8px; text-align: left; }}
            th {{ background: #f0f0f0; }}
        </style>
    </head>
    <body>
        <h1>Проект приказа</h1>
        <h2>О стимулирующих выплатах за период {period}</h2>
        <p>Стоимость одного балла: {float(point_cost):.2f} руб.</p>
        <table>
            <thead>
                <tr>
                    <th>№</th>
                    <th>ФИО</th>
                    <th>Должность</th>
                    <th>Кафедра</th>
                    <th>Итоговые баллы</th>
                    <th>Сумма выплаты</th>
                </tr>
            </thead>
            <tbody>{body}</tbody>
        </table>
    </body>
    </html>
    """
