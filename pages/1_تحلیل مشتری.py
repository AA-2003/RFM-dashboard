import streamlit as st
import os
import sys
import plotly.express as px
import pandas as pd
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.load_data import BigQueryExecutor, exacute_query
from utils.funcs import convert_df, convert_df_to_excel
from utils.auth import login

def to_sql_list(values):
    return ', '.join(f"'{v}'" for v in values)

def customer_analyze():
    col1, col2 = st.columns(2)

    # --- Column 1: Filters ---
    with col1:
        # VIP Filter
        vip_options = ['Non-VIP', 'Bronze VIP', 'Silver VIP', 'Gold VIP']
        vip_status = st.checkbox("انتخاب تمام وضعیت‌هایVIP", value=True, key='vips_checkbox')
        vip_values = vip_options if vip_status else st.multiselect(
            "انتخاب وضعیت VIP:", options=vip_options, default=[], key='vips_multiselect_selectbox'
        )
        if not vip_values:
            vip_values = vip_options

        # Blacklist Filter
        blacklist_options = ['non-blacklist', 'blacklist']
        black_list_status = st.checkbox("انتخاب تمام وضعیت‌های بلک لیست", value=True, key='blacklists_checkbox')
        black_list_values = blacklist_options if black_list_status else st.multiselect(
            "انتخاب وضعیت بلک لیست:", options=blacklist_options, key='blacklist_multiselect_selectbox'
        )
        if not black_list_values:
            black_list_values = blacklist_options

        # Segmentation Filter
        segment_options = [
            'At Risk ✨ Potential', 'At Risk ❤️ Loyal Customers', 'At Risk 👑 Champions',
            'At Risk 💰 Big Spender', 'At Risk 🔒 Reliable Customers', 'At Risk �️️ Low Value',
            'At Risk 🧐 Curious Customers', 'Lost ✨ Potential', 'Lost ❤️ Loyal Customers',
            'Lost 👑 Champions', 'Lost 💰 Big Spender', 'Lost 🔒 Reliable Customers', 'Lost 🗑️ Low Value',
            'Lost 🧐 Curious Customers', 'New 🧐 Curious Customers',  '✨ Potential', '❤️ Loyal Customers',
            '👑 Champions', '💰 Big Spender', '🔒 Reliable Customers', '🗑️ Low Value', '🧐 Curious Customers'
        ]
        segment_status = st.checkbox("انتخاب تمام سگمنت‌ها", value=True, key='segments_checkbox')
        segment_values = segment_options if segment_status else st.multiselect(
            "انتخاب سگمنت:", options=segment_options, default=[segment_options[0]], key='segment_multiselect_selectbox'
        )
        if not segment_values:
            segment_values = segment_options

        # Date Filters
        with BigQueryExecutor() as bq:
            max_min_check_in = bq.exacute_query(
                "Select max(Checkin_date) as max, min(Checkin_date) as min from `customerhealth-crm-warehouse.didar_data.deals`"
            )

        st.subheader("انتخاب بازه زمانی ورود: ")
        checkin_config = Config(
            always_open=False,
            dark_mode=True,
            locale="fa",
            minimum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_check_in['min'].iloc[0]).date()),
            maximum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_check_in['max'].iloc[0]).date()),
            color_primary="#ff4b4b",
            color_primary_light="#ff9494",
            selection_mode="range",
            placement="bottom",
            disabled=True
        )
        check_in_values = datepicker_component(config=checkin_config)
        checkin_start_date = (
            check_in_values['from'].togregorian()
            if check_in_values and 'from' in check_in_values and check_in_values['from'] is not None
            else pd.to_datetime(max_min_check_in['min'].iloc[0]).date()
        )
        checkin_end_date = (
            check_in_values['to'].togregorian()
            if check_in_values and 'to' in check_in_values and check_in_values['to'] is not None
            else pd.to_datetime(max_min_check_in['max'].iloc[0]).date()
        )

    # --- Column 2: Filters ---
    with col2:
        # Product Data
        products = exacute_query("SELECT * FROM `customerhealth-crm-warehouse.didar_data.Products`")
        complex_options = [b for b in products['Building_name'].unique().tolist() if b != 'not_a_building']
        tip_options = products[products['Building_name'] != 'not_a_building']['ProductName'].unique().tolist()

        # Resident Complex/Tip Filter
        resident_complex_status = st.checkbox("انتخاب تمام مجتمع ها(مقیم) ", value=True, key='resident_complex_checkbox')
        if resident_complex_status:
            resident_tip_values = tip_options
        else:
            resident_complex_values = st.multiselect(
                "انتخاب مجتمع مقیم:", options=complex_options, default=[], key='resident_complex_multiselect_selectbox'
            )
            cols = st.columns([1, 4])
            with cols[1]:
                resident_tip_options = products[
                    (products['Building_name'] != 'not_a_building') &
                    (products['Building_name'].isin(resident_complex_values))
                ]['ProductName'].unique().tolist()
                resident_tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='resident_tips_checkbox')
                if resident_tip_status:
                    resident_tip_values = resident_tip_options
                else:
                    resident_tip_values = st.multiselect(
                        "انتخاب تیپ مقمم :", options=resident_tip_options, default=[], key='residen_tip_multiselect_selectbox'
                    )
                if not resident_tip_values:
                    resident_tip_values = resident_tip_options

        # Monthly Filter
        montly_status = st.checkbox("ماهانه و غیرماهانه", value=True, key='monthly_checkbox')
        if montly_status:
            montly_values = ["ماهانه", "غیر ماهانه"]
            monthly_limit = 15
        else:
            montly_values = st.selectbox(
                "انتخاب وضعیت :", options=["ماهانه", "غیر ماهانه"], key='monthly_multiselect_selectbox'
            )
            monthly_limit = st.number_input(
                "مینیمم میانگین اقامت برای اینکه مهمان ماهانه محسوب شود را وارد کنید:",
                min_value=0, value=15, step=1, key='min_nights_filter'
            )
        if not montly_values:
            montly_values = ["ماهانه", "غیر ماهانه"]
        elif isinstance(montly_values, str):
            montly_values = [montly_values]

        # Is Staying Filter
        is_staying = st.checkbox('هم مقیم و هم غیرمقیم', value=True, key='is_staying_checkbox')
        if is_staying:
            is_staying_values = ["مقیم", "غیر مقیم"]
        else:
            is_staying_values = st.selectbox(
                "انتخاب وضعیت اقامت:", options=["مقیم", "غیر مقیم"], key='is_staying_selectbox'
            )
        if not is_staying_values:
            is_staying_values = ["مقیم", "غیر مقیم"]
        elif isinstance(is_staying_values, str):
            is_staying_values = [is_staying_values]

        # Happy Call Filter
        happycall_status = st.checkbox("فقط مشتریانی که تماس هپی‌کال موفق داشته‌اند؟", value=False, key='happycall_status')
        if happycall_status:
            happycall_value = "(c.customer_nps IS NOT NULL OR  c.customer_amneties_score IS NOT NULL OR c.customer_staff_score IS NOT NULL)"
            cols = st.columns(2)
            with cols[0]:
                nps_min = st.number_input("حداقل میانگین NPS", min_value=-100, max_value=100, value=-100, key='nps_min')
                cleanness_min = st.number_input("حداقل میانگین امتیاز نظافت", min_value=0, max_value=5, value=0, key='cleanness_min')
                personnel_min = st.number_input("حداقل میانگین امتیاز پرسنل", min_value=0, max_value=5, value=0, key='personnel_min')
            with cols[1]:
                nps_max = st.number_input("حداکثر میانگین NPS", min_value=-100, max_value=100, value=100, key='nps_max')
                cleanness_max = st.number_input("حداکثر میانگین امتیاز نظافت", min_value=0, max_value=5, value=5, key='cleanness_max')
                personnel_max = st.number_input("حداکثر میانگین امتیاز پرسنل", min_value=0, max_value=5, value=5, key='personnel_max')
        else:
            happycall_value = ''
            nps_min = nps_max = cleanness_min = cleanness_max = personnel_min = personnel_max = None

        if happycall_status:
            happycall_filter = f"""
                AND {happycall_value}
                AND c.customer_nps >= {nps_min} AND c.customer_nps <= {nps_max}
                AND c.customer_amneties_score >= {cleanness_min} AND c.customer_amneties_score <= {cleanness_max}
                AND c.customer_staff_score >= {personnel_min} AND c.customer_staff_score <= {personnel_max}
            """
        else:
            happycall_filter = ""

        # --- Query Construction ---
        query = f"""
        SELECT *
        FROM (
            SELECT *,
                (total_nights / frequency) AS average_stay,
                CASE
                    WHEN (total_nights / frequency) >= {monthly_limit} THEN "ماهانه"
                    ELSE "غیر ماهانه"
                END AS monthly_status,
                CASE
                    WHEN last_checkin < CURRENT_DATE() AND last_checkout > CURRENT_DATE() THEN 'مقیم'
                    ELSE 'غیر مقیم'
                END AS is_staying,
                CASE 
                    WHEN last_name LIKE '%*%' THEN 'blacklist'
                    ELSE 'non-blacklist'
                END AS blacklist_status,
                CASE
                    WHEN last_name LIKE '%💎%' THEN 'Gold VIP'
                    WHEN last_name LIKE '%⭐%' THEN 'Silver VIP'
                    WHEN last_name LIKE '%💠%' THEN 'Bronze VIP'
                    ELSE 'Non-VIP'
                END AS vip_status
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE rfm_segment IN ({to_sql_list(segment_values)})
        ) t
        WHERE vip_status IN ({to_sql_list(vip_values)})
            AND blacklist_status IN ({to_sql_list(black_list_values)})
            AND monthly_status IN ({to_sql_list(montly_values)})
            AND is_staying IN ({to_sql_list(is_staying_values)})
            AND customer_id IN (
                SELECT DISTINCT d.Customer_id
                FROM `customerhealth-crm-warehouse.didar_data.deals` d
                INNER JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                    ON d.Product_code = p.ProductCode
                INNER JOIN `customerhealth-crm-warehouse.didar_data.RFM_segments` r
                    ON d.Customer_id = r.customer_id
                INNER JOIN `customerhealth-crm-warehouse.CHS.CHS_components` c
                    ON c.Customer_ID = d.Customer_id
                WHERE
                    p.ProductName IN ({to_sql_list(resident_tip_values)})
                    AND d.Checkin_date >= DATE('{checkin_start_date}') AND d.Checkin_date <= DATE('{checkin_end_date}')
                    AND d.Status = 'Won'
                    {happycall_filter}
            )
        """

    # --- Query Execution and Display ---
    if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
        with BigQueryExecutor() as bq_executor:
            data = bq_executor.exacute_query(query)
            CHS_data = bq_executor.exacute_query(f"""
                select * from `customerhealth-crm-warehouse.CHS.CHS_components`
                where Customer_ID in ({', '.join(str(i) for i in data['customer_id'].unique())})
            """) if data is not None and not data.empty else None

        if data is None or data.empty:
            st.info('هیچ داده ای با فیلترهای اعمال شده وجود ندارد!!!')
        else:
            final_data = pd.merge(
                data,
                CHS_data[['Customer_ID', 'customer_nps', 'customer_amneties_score', 'customer_staff_score']],
                left_on='customer_id', right_on='Customer_ID', how='left'
            ).drop(columns='Customer_ID')
            column_map = {
                'customer_id': 'شناسه مشتری',
                'first_name': 'نام',
                'last_name': 'نام خانوادگی',
                'phone_number': 'شماره تماس',
                'recency': 'تازگی خرید',
                'frequency': 'تعداد خرید',
                'monetary': 'مبلغ کل خرید',
                'total_nights': 'تعداد شب اقامت',
                'last_reserve_date': 'تاریخ آخرین رزرو',
                'last_checkin': 'تاریخ آخرین ورود',
                'last_checkout': 'تاریخ آخرین خروج',
                'favorite_product': 'محصول مورد علاقه',
                'last_product': 'آخرین محصول',
                'rfm_segment': 'سگمنت RFM',
                'average_stay': 'میانگین مدت اقامت',
                'monthly_status': 'وضعیت ماهانه',
                'is_staying': 'وضعیت اقامت',
                'blacklist_status': 'وضعیت بلک‌لیست',
                'vip_status': 'وضعیت VIP',
                'customer_nps': 'امتیاز NPS مشتری',
                'customer_amneties_score': 'امتیاز امکانات مشتری',
                'customer_staff_score': 'امتیاز پرسنل مشتری'
            }
            persian_final_data = final_data.rename(columns=column_map)
            st.write(persian_final_data)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="دانلود داده‌ها به صورت CSV",
                    data=convert_df(final_data),
                    file_name='rfm_segmentation.csv',
                    mime='text/csv',
                )
            with col2:
                st.download_button(
                    label="دانلود داده‌ها به صورت اکسل",
                    data=convert_df_to_excel(final_data),
                    file_name='rfm_segmentation.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

def main():
    st.set_page_config(page_title="تحلیل مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل مشتری")

    if 'auth' in st.session_state and st.session_state.auth:
        role = st.session_state.get('role', 'user')
        if role == 'admin':
            tabs = st.tabs(["دیتای بخش‌بندی مشتریان", "نمودار پراکندگی سه بعدی", "سایر"])
            with tabs[0]:
                customer_analyze()
            with tabs[1]:
                st.subheader("نمودار پراکندگی سه بعدی متریک‌های بخش‌بندی")
                with BigQueryExecutor() as bq_exacutor:
                    rfm = bq_exacutor.exacute_query("""
                        select customer_id, first_name, last_name, total_nights, frequency, monetary, rfm_segment
                        from `customerhealth-crm-warehouse.didar_data.RFM_segments`
                        WHERE last_name IS NOT NULL
                    """)
                if rfm is None or rfm.empty:
                    st.info("مشکلی در بارگذاری داده های پیش امده است!!!")
                else:
                    fig3d = px.scatter_3d(
                        rfm,
                        x='total_nights', y='frequency', z='monetary',
                        color='rfm_segment', hover_data=['customer_id', 'first_name', 'last_name']
                    )
                    fig3d.update_layout(
                        scene=dict(
                            xaxis_title='total_nights',
                            yaxis_title='Frequency',
                            zaxis_title='Monetary'
                        ),
                        legend_title='RFM Segments'
                    )
                    st.plotly_chart(fig3d)
            with tabs[2]:
                st.text('در حال اماده سازی ...')
        else:
            customer_analyze()
    else:
        login()

if __name__ == "__main__":
    main()