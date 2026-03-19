import streamlit as st

from admin import (
    build_order_html,
    calculate_payments,
    get_admin_summary,
    get_all_criteria,
    get_periods,
)


def require_admin():
    user = st.session_state.get("user")
    if not user:
        st.switch_page("app.py")
    if user["role"] != "admin":
        st.error("Доступ только для администратора")
        st.stop()


require_admin()

st.title("Дашборд администратора")

summary = get_admin_summary()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Пользователи", summary["users"])
col2.metric("Отчеты", summary["reports"])
col3.metric("На проверке", summary["submitted"])
col4.metric("Проверено", summary["reviewed"])

st.divider()
st.subheader("Расчет стимулирующих выплат")

periods = get_periods()
if periods:
    selected_period = st.selectbox("Период", options=periods, index=0)
else:
    selected_period = None
    st.info("Пока нет отправленных отчетов")
point_cost = st.number_input("Стоимость одного балла", min_value=0.0, value=50.0, step=10.0)

if selected_period:
    payments_df = calculate_payments(selected_period, point_cost)
    if payments_df.empty:
        st.info("Для выбранного периода пока нет проверенных отчетов")
    else:
        st.dataframe(payments_df, use_container_width=True, hide_index=True)
        total_points = payments_df["total_points"].sum()
        total_payment = payments_df["payment"].sum()
        sum_col1, sum_col2 = st.columns(2)
        sum_col1.metric("Всего баллов", f"{total_points:.2f}")
        sum_col2.metric("Общая сумма выплат", f"{total_payment:.2f} руб.")

        order_html = build_order_html(selected_period, point_cost, payments_df)
        st.download_button(
            "Скачать проект приказа (HTML)",
            data=order_html,
            file_name=f"prikaz_{selected_period}.html",
            mime="text/html",
        )

st.divider()
st.subheader("Сводка по всем заявленным критериям")
all_items_df = get_all_criteria()
if all_items_df.empty:
    st.info("Данные появятся после заполнения отчетов преподавателями")
else:
    st.dataframe(all_items_df, use_container_width=True, hide_index=True)
