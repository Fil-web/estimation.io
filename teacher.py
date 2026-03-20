from pathlib import Path
from uuid import uuid4

import pandas as pd

from db import UPLOADS_DIR, add_audit_log, add_report_history, get_connection, get_report_history_entries


def _get_report_row(cursor, report_id):
    report = cursor.execute(
        "SELECT id, user_id, period, status FROM reports WHERE id=?",
        (report_id,),
    ).fetchone()
    if not report:
        raise ValueError("Отчет не найден")
    return report


def _ensure_report_editable(cursor, report_id):
    report = _get_report_row(cursor, report_id)
    if report["status"] == "reviewed":
        raise ValueError("Отчет уже проверен и заблокирован для редактирования")
    return report


def get_teacher_reports(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            reports.id,
            reports.period,
            reports.status,
            reports.created_at,
            reports.submitted_at,
            COUNT(report_items.id) AS items_count,
            COALESCE(SUM(report_items.claimed_score), 0) AS claimed_points
        FROM reports
        LEFT JOIN report_items ON report_items.report_id = reports.id
        WHERE reports.user_id = ?
        GROUP BY reports.id, reports.period, reports.status, reports.created_at, reports.submitted_at
        ORDER BY reports.period DESC
        """,
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def create_report(user_id, period):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO reports (user_id, period, status)
        VALUES (?, ?, 'draft')
        """,
        (user_id, period.strip()),
    )
    conn.commit()
    report_id = cursor.execute(
        "SELECT id FROM reports WHERE user_id=? AND period=?",
        (user_id, period.strip()),
    ).fetchone()["id"]
    conn.close()
    add_report_history(report_id, user_id, "create_report", f"Создан отчет за период {period.strip()}")
    add_audit_log(user_id, "report", report_id, "create_report", f"Создан отчет за период {period.strip()}")
    return report_id


def get_report(report_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            reports.*,
            users.full_name,
            users.position,
            departments.name AS department_name
        FROM reports
        JOIN users ON users.id = reports.user_id
        LEFT JOIN departments ON departments.id = users.department_id
        WHERE reports.id = ?
        """,
        (report_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_report_form_data(report_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            criteria_groups.name AS group_name,
            criteria_groups.code AS group_code,
            criteria.id AS criteria_id,
            criteria.code,
            criteria.criterion_name,
            criteria.base,
            criteria.score,
            criteria.score_text,
            criteria.confirmation_type,
            report_items.id AS item_id,
            COALESCE(report_items.quantity, 0) AS quantity,
            COALESCE(report_items.teacher_comment, '') AS teacher_comment,
            COALESCE(report_items.attachment_name, '') AS attachment_name,
            COALESCE(report_items.attachment_path, '') AS attachment_path,
            COALESCE(report_items.claimed_score, 0) AS claimed_score,
            COALESCE(report_items.status, 'pending') AS item_status,
            COALESCE(report_items.review_comment, '') AS review_comment
        FROM criteria
        LEFT JOIN criteria_groups ON criteria_groups.id = criteria.group_id
        LEFT JOIN report_items
            ON report_items.criteria_id = criteria.id
            AND report_items.report_id = ?
        WHERE criteria.is_active = 1
        ORDER BY criteria_groups.code, criteria.code
        """,
        conn,
        params=(report_id,),
    )
    conn.close()
    return df


def _store_attachment(report_id, criteria_id, uploaded_file):
    report_dir = UPLOADS_DIR / f"report_{report_id}"
    report_dir.mkdir(parents=True, exist_ok=True)

    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    file_name = f"{criteria_id}_{uuid4().hex}_{safe_name}"
    file_path = report_dir / file_name
    file_path.write_bytes(uploaded_file.getbuffer())
    return safe_name, str(file_path)


def save_report_item(report_id, criteria_id, quantity, teacher_comment, uploaded_file=None):
    conn = get_connection()
    cursor = conn.cursor()
    report = _ensure_report_editable(cursor, report_id)

    criteria = cursor.execute(
        "SELECT score FROM criteria WHERE id=?",
        (criteria_id,),
    ).fetchone()
    claimed_score = float(quantity) * float(criteria["score"])

    existing = cursor.execute(
        """
        SELECT attachment_name, attachment_path
        FROM report_items
        WHERE report_id=? AND criteria_id=?
        """,
        (report_id, criteria_id),
    ).fetchone()

    attachment_name = existing["attachment_name"] if existing else None
    attachment_path = existing["attachment_path"] if existing else None

    if uploaded_file is not None:
        attachment_name, attachment_path = _store_attachment(report_id, criteria_id, uploaded_file)

    cursor.execute(
        """
        INSERT INTO report_items (
            report_id,
            criteria_id,
            quantity,
            teacher_comment,
            attachment_name,
            attachment_path,
            claimed_score,
            status,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        ON CONFLICT(report_id, criteria_id) DO UPDATE SET
            quantity=excluded.quantity,
            teacher_comment=excluded.teacher_comment,
            attachment_name=excluded.attachment_name,
            attachment_path=excluded.attachment_path,
            claimed_score=excluded.claimed_score,
            status='pending',
            review_comment=NULL,
            reviewed_by=NULL,
            reviewed_at=NULL,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            report_id,
            criteria_id,
            float(quantity),
            teacher_comment.strip(),
            attachment_name,
            attachment_path,
            claimed_score,
        ),
    )

    cursor.execute(
        "UPDATE reports SET status='draft', reviewer_comment=NULL, reviewer_id=NULL, reviewed_at=NULL WHERE id=?",
        (report_id,),
    )

    conn.commit()
    conn.close()
    add_audit_log(
        report["user_id"],
        "report",
        report_id,
        "save_item",
        f"Сохранен пункт {criteria_id} в отчете за период {report['period']}",
    )


def save_report_items_bulk(report_id, items_payload, actor_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    report = _ensure_report_editable(cursor, report_id)

    selected_ids = []
    changed_codes = []

    for item in items_payload:
        if not item["selected"]:
            continue

        criteria_id = int(item["criteria_id"])
        selected_ids.append(criteria_id)

        criteria = cursor.execute(
            "SELECT code, score FROM criteria WHERE id=?",
            (criteria_id,),
        ).fetchone()
        claimed_score = float(item["quantity"]) * float(criteria["score"])
        changed_codes.append(criteria["code"])

        existing = cursor.execute(
            """
            SELECT attachment_name, attachment_path
            FROM report_items
            WHERE report_id=? AND criteria_id=?
            """,
            (report_id, criteria_id),
        ).fetchone()

        attachment_name = existing["attachment_name"] if existing else None
        attachment_path = existing["attachment_path"] if existing else None

        if item["uploaded_file"] is not None:
            attachment_name, attachment_path = _store_attachment(
                report_id, criteria_id, item["uploaded_file"]
            )

        cursor.execute(
            """
            INSERT INTO report_items (
                report_id,
                criteria_id,
                quantity,
                teacher_comment,
                attachment_name,
                attachment_path,
                claimed_score,
                status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            ON CONFLICT(report_id, criteria_id) DO UPDATE SET
                quantity=excluded.quantity,
                teacher_comment=excluded.teacher_comment,
                attachment_name=excluded.attachment_name,
                attachment_path=excluded.attachment_path,
                claimed_score=excluded.claimed_score,
                status='pending',
                review_comment=NULL,
                reviewed_by=NULL,
                reviewed_at=NULL,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                report_id,
                criteria_id,
                float(item["quantity"]),
                item["teacher_comment"].strip(),
                attachment_name,
                attachment_path,
                claimed_score,
            ),
        )

    if selected_ids:
        placeholders = ",".join(["?"] * len(selected_ids))
        cursor.execute(
            f"DELETE FROM report_items WHERE report_id=? AND criteria_id NOT IN ({placeholders})",
            [report_id, *selected_ids],
        )
    else:
        cursor.execute("DELETE FROM report_items WHERE report_id=?", (report_id,))

    cursor.execute(
        """
        UPDATE reports
        SET status='draft', reviewer_comment=NULL, reviewer_id=NULL, reviewed_at=NULL
        WHERE id=?
        """,
        (report_id,),
    )

    conn.commit()
    conn.close()
    if actor_id is not None:
        details = (
            f"Автосохранение черновика. Выбрано пунктов: {len(selected_ids)}."
            + (f" Изменены критерии: {', '.join(changed_codes[:8])}" if changed_codes else "")
        )
        add_report_history(report_id, actor_id, "autosave_draft", details)
        add_audit_log(actor_id, "report", report_id, "autosave_draft", details)


def submit_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    report = _get_report_row(cursor, report_id)

    if report["status"] == "reviewed":
        conn.close()
        raise ValueError("Проверенный отчет нельзя отправить повторно")

    items_count = cursor.execute(
        "SELECT COUNT(*) AS total FROM report_items WHERE report_id=?",
        (report_id,),
    ).fetchone()["total"]

    if items_count == 0:
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE reports
        SET
            status='submitted',
            submitted_at=CURRENT_TIMESTAMP,
            reviewer_comment=NULL
        WHERE id=?
        """,
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_report_history(report_id, report["user_id"], "submit_report", "Отчет отправлен заведующему на проверку")
    add_audit_log(report["user_id"], "report", report_id, "submit_report", f"Отчет за период {report['period']} отправлен на проверку")
    return True


def get_attachment_bytes(path):
    file_path = Path(path)
    if not file_path.exists():
        return None
    return file_path.read_bytes()


def get_report_history(report_id):
    return get_report_history_entries(report_id)
