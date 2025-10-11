# frontend/summary.py
import pandas as pd
import streamlit as st
import altair as alt


def render_summary_panel(query_summary, get_period_range) -> None:
    st.subheader("📊 Summary")

    # ครอบสโคปโทนชมพูอ่อนเฉพาะบล็อกนี้ (ต้องมี CSS .summary-skin/.chart-card/.table-soft ใน inject_theme_css)
    st.markdown('<div class="summary-skin">', unsafe_allow_html=True)

    # เลือกช่วงเวลา
    period = st.selectbox("เลือกช่วงเวลา", ["daily", "weekly", "monthly"], index=2)

    # ช่อง department สำหรับ "กรองสรุป" (แยกกับช่องบนที่ Upload)
    summary_dept = st.text_input(
        "department",
        key="summary_department",
        value=st.session_state.get("summary_department", ""),
        placeholder="เช่น finance/marketing/hr",
    )

    if st.button("Get Summary"):
        # ดึงข้อมูล (ถ้าเว้นว่างให้ส่ง None)
        df = query_summary(period, summary_dept or None)
        if df.empty:
            st.info("ไม่มีข้อมูลในช่วงนี้")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # --- เตรียมข้อมูล ---
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0)
        df = df.dropna(subset=["date"])

        # --- ตัวเลขรวม + ช่วงวันที่ ---
        total = float(df["total"].sum())
        start, end = get_period_range(period)
        st.write(f"ช่วง: {start} – {end} | รายการ: {len(df)}")
        st.metric("รวมทั้งหมด (THB)", f"{total:,.2f}")

        # --- สรุปรายวันด้วย resample ---
        daily = (
            df.set_index("date")
            .resample("D")["total"]
            .sum()
            .rename("Total (THB)")
        )

        # เตรียมข้อมูลสำหรับ Altair
        df_plot = daily.reset_index().rename(columns={"date": "Date", "Total (THB)": "Total"})

        # --- กราฟ Altair: สีม่วง + ปรับความหนา ---
        if len(df_plot) <= 1:
            chart = (
                alt.Chart(df_plot)
                .mark_bar(
                    color="#d9a1ea",
                    size=36,  # ความหนาของแท่ง (ปรับได้)
                    cornerRadiusTopLeft=6,
                    cornerRadiusTopRight=6,
                )
                .encode(
                    x=alt.X("yearmonthdate(Date):O", title=""),
                    y=alt.Y("Total:Q", title="รวม (THB)"),
                    tooltip=[
                        alt.Tooltip("Date:T", title="วันที่"),
                        alt.Tooltip("Total:Q", title="รวม (THB)", format=",.2f"),
                    ],
                )
            )
        else:
            chart = (
                alt.Chart(df_plot)
                .mark_line(point=True, stroke="#d9a1ea", strokeWidth=3)
                .encode(
                    x=alt.X("Date:T", title=""),
                    y=alt.Y("Total:Q", title="รวม (THB)"),
                    tooltip=[
                        alt.Tooltip("Date:T", title="วันที่"),
                        alt.Tooltip("Total:Q", title="รวม (THB)", format=",.2f"),
                    ],
                )
            )

        # ทำพื้นหลังพล็อตอ่อนลง + ไม่มีกรอบ view
        chart = (
            chart
            .configure(background='transparent')  # นอกพื้นที่กราฟโปร่งใส
            .configure_view(
                fill='rgba(255, 240, 247, 0.75)',  # พื้นที่พล็อตชมพูอ่อน
                stroke=None
            )
            .configure_axis(
                gridColor='rgba(0,0,0,0.06)',
                domainColor='rgba(0,0,0,0.12)',
                labelColor='rgba(0,0,0,0.55)',
                titleColor='rgba(0,0,0,0.55)',
            )
        )

        # ✅ การ์ดโค้งมนห่อกราฟ
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.altair_chart(chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ✅ การ์ดโค้งมนห่อ DataFrame ให้สีอ่อนลง
        st.markdown('<div class="table-soft">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ปิดสโคปสไตล์
    st.markdown("</div>", unsafe_allow_html=True)