from db import get_connection


def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    user = cursor.execute(
        """
        SELECT
            users.id,
            users.username,
            users.role,
            users.full_name,
            users.department_id,
            users.position,
            departments.name AS department_name
        FROM users
        LEFT JOIN departments ON departments.id = users.department_id
        WHERE users.username = ? AND users.password = ?
        """,
        (username, password),
    ).fetchone()
    conn.close()
    return dict(user) if user else None
