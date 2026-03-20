from datetime import datetime

import pandas as pd

from db import add_audit_log, add_report_history, get_connection, get_report_history_entries


def get_head_reports(head_user_id):
    conn = get_connection()
    head = conn.execute(
        "SELECT department_id FROM users WHERE id=?",
        (head_user_id,),
    ).fetchone()

    if not head or head["department_id"] is None:
        conn.close()
        return pd.DataFrame()

    df = pd.read_sql_query(
        """
        SELECT
            reports.id,
            reports.period,
            reports.status,
            reports.submitted_at,
            users.full_name,
            COALESCE(users.position, '') AS position,
            COUNT(report_items.id) AS items_count,
            COALESCE(SUM(report_items.claimed_score), 0) AS claimed_points
        FROM reports
        JOIN users ON users.id = reports.user_id
        LEFT JOIN report_items ON report_items.report_id = reports.id
        WHERE users.department_id = ? AND reports.status IN ('submitted', 'returned', 'reviewed')
        GROUP BY reports.id, reports.period, reports.status, reports.submitted_at, users.full_name, users.position
        ORDER BY reports.status, reports.submitted_at DESC
        """,
        conn,
        params=(head["department_id"],),
    )
    conn.close()
    return df


def get_report_review_data(report_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            report_items.id,
            COALESCE(criteria_groups.name, 'Без группы') AS group_name,
            criteria.code,
            criteria.criterion_name,
            criteria.base,
            criteria.score,
            criteria.score_text,
            report_items.quantity,
            report_items.teacher_comment,
            report_items.attachment_name,
            report_items.attachment_path,
            report_items.claimed_score,
            report_items.status,
            COALESCE(report_items.review_comment, '') AS review_comment
        FROM report_items
        JOIN criteria ON criteria.id = report_items.criteria_id
        LEFT JOIN criteria_groups ON criteria_groups.id = criteria.group_id
        WHERE report_items.report_id = ?
        ORDER BY criteria_groups.code, criteria.code
        """,
        conn,
        params=(report_id,),
    )
    conn.close()
    return df


def review_report_item(item_id, action, review_comment, head_user_id):
    status = "approved" if action == "Подтвердить" else "rejected"

    conn = get_connection()
    cursor = conn.cursor()
    item = cursor.execute(
        """
        SELECT report_items.report_id, reports.status AS report_status
        FROM report_items
        JOIN reports ON reports.id = report_items.report_id
        WHERE report_items.id=?
        """,
        (item_id,),
    ).fetchone()
    if not item:
        conn.close()
        raise ValueError("Пункт отчета не найден")
    if item["report_status"] == "reviewed":
        conn.close()
        raise ValueError("Проверенный отчет заблокирован для изменений")
    report_id = item["report_id"]
    cursor.execute(
        """
        UPDATE report_items
        SET
            status=?,
            review_comment=?,
            reviewed_by=?,
            reviewed_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (status, review_comment.strip(), head_user_id, item_id),
    )
    conn.commit()
    conn.close()
    add_report_history(
        report_id,
        head_user_id,
        "review_item",
        f"Пункт #{item_id}: {status}. {review_comment.strip()}".strip(),
    )
    add_audit_log(head_user_id, "report", report_id, "review_item", f"Проверен пункт #{item_id}: {status}")


def bulk_review_report_items(report_id, item_ids, action, review_comment, head_user_id):
    if not item_ids:
        return 0

    status = "approved" if action == "Подтвердить" else "rejected"
    conn = get_connection()
    cursor = conn.cursor()
    report = cursor.execute("SELECT status FROM reports WHERE id=?", (report_id,)).fetchone()
    if not report:
        conn.close()
        raise ValueError("Отчет не найден")
    if report["status"] == "reviewed":
        conn.close()
        raise ValueError("Проверенный отчет заблокирован для изменений")
    placeholders = ",".join(["?"] * len(item_ids))
    cursor.execute(
        f"""
        UPDATE report_items
        SET
            status=?,
            review_comment=?,
            reviewed_by=?,
            reviewed_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        WHERE report_id=? AND id IN ({placeholders})
        """,
        [status, review_comment.strip(), head_user_id, report_id, *item_ids],
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    add_report_history(
        report_id,
        head_user_id,
        "bulk_review",
        f"Массовое действие: {status}. Изменено пунктов: {affected}. {review_comment.strip()}".strip(),
    )
    add_audit_log(head_user_id, "report", report_id, "bulk_review", f"Массовая проверка: {status}, пунктов {affected}")
    return affected


def finalize_report_review(report_id, head_user_id, reviewer_comment):
    conn = get_connection()
    cursor = conn.cursor()
    report = cursor.execute("SELECT status FROM reports WHERE id=?", (report_id,)).fetchone()
    if not report:
        conn.close()
        raise ValueError("Отчет не найден")
    if report["status"] == "reviewed":
        conn.close()
        return True

    pending = cursor.execute(
        "SELECT COUNT(*) AS total FROM report_items WHERE report_id=? AND status='pending'",
        (report_id,),
    ).fetchone()["total"]

    if pending:
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE reports
        SET
            status='reviewed',
            reviewer_id=?,
            reviewer_comment=?,
            reviewed_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (head_user_id, reviewer_comment.strip(), report_id),
    )
    conn.commit()
    conn.close()
    add_report_history(report_id, head_user_id, "finalize_review", "Проверка отчета завершена")
    add_audit_log(head_user_id, "report", report_id, "finalize_review", "Отчет переведен в статус 'Проверен'")
    return True


def return_report_for_revision(report_id, head_user_id, reviewer_comment):
    comment_text = reviewer_comment.strip()
    if not comment_text:
        raise ValueError("Укажите комментарий для возврата на доработку")

    conn = get_connection()
    cursor = conn.cursor()
    report = cursor.execute(
        "SELECT status FROM reports WHERE id=?",
        (report_id,),
    ).fetchone()
    if not report:
        conn.close()
        raise ValueError("Отчет не найден")
    if report["status"] == "reviewed":
        conn.close()
        raise ValueError("Проверенный отчет нельзя вернуть на доработку")

    cursor.execute(
        """
        UPDATE reports
        SET
            status='returned',
            reviewer_id=?,
            reviewer_comment=?,
            reviewed_at=NULL
        WHERE id=?
        """,
        (head_user_id, comment_text, report_id),
    )
    cursor.execute(
        """
        UPDATE report_items
        SET
            status='pending',
            review_comment=NULL,
            reviewed_by=NULL,
            reviewed_at=NULL,
            updated_at=CURRENT_TIMESTAMP
        WHERE report_id=?
        """,
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_report_history(report_id, head_user_id, "return_for_revision", f"Отчет возвращен на доработку. {comment_text}")
    add_audit_log(head_user_id, "report", report_id, "return_for_revision", "Отчет возвращен на доработку")
    return True


def get_head_reviewed_periods(head_user_id):
    conn = get_connection()
    head = conn.execute(
        "SELECT department_id FROM users WHERE id=?",
        (head_user_id,),
    ).fetchone()

    if not head or head["department_id"] is None:
        conn.close()
        return []

    rows = conn.execute(
        """
        SELECT DISTINCT reports.period
        FROM reports
        JOIN users ON users.id = reports.user_id
        WHERE users.department_id = ? AND reports.status = 'reviewed'
        ORDER BY reports.period DESC
        """,
        (head["department_id"],),
    ).fetchall()
    conn.close()
    return [row["period"] for row in rows]


def _normalize_teacher_scope(selected_teacher_ids=None):
    if not selected_teacher_ids:
        return "all"
    return ",".join(str(int(teacher_id)) for teacher_id in sorted(set(selected_teacher_ids)))


def _get_or_create_service_note_number(cursor, department_id, period, teacher_scope):
    existing = cursor.execute(
        """
        SELECT note_number
        FROM service_note_registry
        WHERE department_id = ? AND period = ? AND teacher_scope = ?
        """,
        (department_id, period, teacher_scope),
    ).fetchone()
    if existing:
        return existing["note_number"]

    next_number = cursor.execute(
        "SELECT COALESCE(MAX(note_number), 0) + 1 AS next_number FROM service_note_registry"
    ).fetchone()["next_number"]
    cursor.execute(
        """
        INSERT INTO service_note_registry (department_id, period, teacher_scope, note_number)
        VALUES (?, ?, ?, ?)
        """,
        (department_id, period, teacher_scope, next_number),
    )
    return next_number


def get_service_note_context(head_user_id, period, selected_teacher_ids=None, register_number=True):
    conn = get_connection()
    head = conn.execute(
        """
        SELECT users.full_name, departments.id AS department_id, departments.name AS department_name
        FROM users
        LEFT JOIN departments ON departments.id = users.department_id
        WHERE users.id=?
        """,
        (head_user_id,),
    ).fetchone()

    if not head or head["department_id"] is None:
        conn.close()
        return None

    teacher_scope = _normalize_teacher_scope(selected_teacher_ids)
    note_number = None
    if register_number:
        note_number = _get_or_create_service_note_number(
            conn.cursor(),
            head["department_id"],
            period,
            teacher_scope,
        )

    rows = conn.execute(
        """
        SELECT
            users.id AS user_id,
            users.full_name,
            COALESCE(users.position, '') AS position,
            criteria.code,
            criteria.criterion_name,
            COALESCE(report_items.teacher_comment, '') AS teacher_comment,
            report_items.quantity,
            report_items.claimed_score
        FROM reports
        JOIN users ON users.id = reports.user_id
        JOIN report_items ON report_items.report_id = reports.id
        JOIN criteria ON criteria.id = report_items.criteria_id
        WHERE users.department_id = ?
          AND reports.period = ?
          AND reports.status = 'reviewed'
          AND report_items.status = 'approved'
        ORDER BY users.full_name, criteria.code
        """,
        (head["department_id"], period),
    ).fetchall()

    teachers = []
    grouped = {}
    for row in rows:
        if selected_teacher_ids and int(row["user_id"]) not in {int(item) for item in selected_teacher_ids}:
            continue
        teacher = grouped.setdefault(
            row["user_id"],
            {
                "user_id": row["user_id"],
                "full_name": row["full_name"],
                "position": row["position"],
                "items": [],
                "total_points": 0.0,
            },
        )
        teacher["items"].append(
            {
                "code": row["code"],
                "criterion_name": row["criterion_name"],
                "teacher_comment": row["teacher_comment"],
                "quantity": row["quantity"],
                "claimed_score": row["claimed_score"],
            }
        )
        teacher["total_points"] += float(row["claimed_score"] or 0)

    teachers = list(grouped.values())
    conn.commit()
    conn.close()

    return {
        "department_name": head["department_name"] or "_________________",
        "period": period,
        "teachers": teachers,
        "head_name": head["full_name"] or "",
        "note_number": note_number,
        "note_date": datetime.now().strftime("%d.%m.%Y"),
        "teacher_scope": teacher_scope,
    }


def build_service_note_html(context):
    if not context:
        return ""

    def cell_content(item):
        text_parts = [f"<div><strong>{item['code']}</strong></div>"]
        if item["teacher_comment"]:
            text_parts.append(f"<div>{item['teacher_comment']}</div>")
        else:
            text_parts.append(f"<div>{item['criterion_name']}</div>")
        text_parts.append(f"<div class='muted'>Количество: {item['quantity']}</div>")
        return "".join(text_parts)

    teacher_rows = []
    for index, teacher in enumerate(context["teachers"], start=1):
        chunks = [
            teacher["items"][chunk_start:chunk_start + 6]
            for chunk_start in range(0, len(teacher["items"]), 6)
        ] or [[]]

        for chunk_index, chunk in enumerate(chunks):
            cells = []
            for item in chunk:
                cells.append(f"<td>{cell_content(item)}</td>")
                cells.append(f"<td>{float(item['claimed_score']):.2f}</td>")

            for _ in range(6 - len(chunk)):
                cells.append("<td></td><td></td>")

            prefix = ""
            suffix = ""
            if chunk_index == 0:
                rowspan = len(chunks)
                prefix = (
                    f"<td rowspan='{rowspan}'>{index}</td>"
                    f"<td rowspan='{rowspan}'>{teacher['full_name']}</td>"
                    f"<td rowspan='{rowspan}'>{teacher['position'] or '-'}</td>"
                )
                suffix = f"<td rowspan='{rowspan}'>{teacher['total_points']:.2f}</td>"

            teacher_rows.append(f"<tr>{prefix}{''.join(cells)}{suffix}</tr>")

    body = "\n".join(teacher_rows) or "<tr><td colspan='16'>Нет утвержденных данных за выбранный период</td></tr>"

    headers = "".join(
        f"<th colspan='2'>{label}</th>"
        for label in [
            "Первый показатель",
            "Второй показатель",
            "Третий показатель",
            "Четвертый показатель",
            "Пятый показатель",
            "Шестой показатель",
        ]
    )
    subheaders = "".join(
        "<th>Отметка о выполнении, комментарии</th><th>Количество баллов балльно-рейтинговой системы</th>"
        for _ in range(6)
    )

    return f"""
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>Служебная записка</title>
        <style>
            body {{ font-family: 'Times New Roman', serif; margin: 32px; color: #111; }}
            .recipient {{ margin-bottom: 28px; line-height: 1.5; }}
            h1 {{ text-align: center; font-size: 22px; margin: 0; }}
            .meta {{ text-align: right; margin-bottom: 20px; line-height: 1.5; }}
            .subtitle {{ text-align: center; margin: 10px 0 22px; line-height: 1.4; }}
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }}
            th, td {{ border: 1px solid #222; padding: 6px; vertical-align: top; }}
            th {{ text-align: center; font-weight: 700; }}
            .muted {{ color: #444; font-size: 11px; }}
            .signatures {{ margin-top: 28px; line-height: 1.8; }}
        </style>
    </head>
    <body>
        <div class="meta">
            <div>Читинский институт Байкальского государственного университета</div>
            <div>Служебная записка № {context['note_number']} от {context['note_date']}</div>
        </div>
        <div class="recipient">
            <div>Первому заместителю директора</div>
            <div>ЧИ ФГБОУ ВО «БГУ»</div>
            <div>Н.В. Раевскому</div>
        </div>
        <h1>СЛУЖЕБНАЯ ЗАПИСКА</h1>
        <div class="subtitle">
            Обобщенные сведения о выполнении преподавателями кафедры {context['department_name']}
            критериев эффективности научно-образовательной деятельности для расчета стимулирующих выплат
            за {context['period']} учебный год
        </div>
        <table>
            <thead>
                <tr>
                    <th rowspan="2">№</th>
                    <th rowspan="2">ФИО преподавателя кафедры</th>
                    <th rowspan="2">Должность</th>
                    {headers}
                    <th rowspan="2">Итоговая сумма баллов балльно-рейтинговой системы</th>
                </tr>
                <tr>{subheaders}</tr>
            </thead>
            <tbody>{body}</tbody>
        </table>
        <div class="signatures">
            <div>Заведующий кафедрой ____________ /{context['head_name'] or '____________________'}/</div>
            <div>Согласовано:</div>
            <div>Начальник отдела учебно-методического и информационного обеспечения ____________</div>
            <div>Главный специалист по кадрам ____________</div>
        </div>
    </body>
    </html>
    """


def get_report_history(report_id):
    return get_report_history_entries(report_id)
