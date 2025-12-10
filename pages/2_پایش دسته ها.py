import streamlit as st
import pandas as pd
import os
import sys
import plotly.express as px

# Add path and imports
sys.path.append(os.path.abspath(".."))

from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_queries, exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def main():
    st.set_page_config(page_title="تحلیل زمانی", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader("توزیع بخش‌بندی مشتریان در طول زمان")

    if 'auth' in st.session_state and st.session_state.auth:
        # Aggregate segment data for plotting, cache in session state
        #  This block loads and normalizes segment counts for each time period, caching the result for performance.
        if 'rfms_segment_normalized' not in st.session_state:
            query = """
            WITH all_segments AS (
                SELECT customer_id, rfm_segment, '1-this month' AS quarter FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                UNION ALL
                SELECT customer_id, rfm_segment, '2-3 month ago' AS quarter FROM `customerhealth-crm-warehouse.didar_data.RFM_segments_three_months_before`
                UNION ALL
                SELECT customer_id, rfm_segment, '3-6 month ago' AS quarter FROM `customerhealth-crm-warehouse.didar_data.RFM_segments_six_months_before`
                UNION ALL
                SELECT customer_id, rfm_segment, '4-9 month ago' AS quarter FROM `customerhealth-crm-warehouse.didar_data.RFM_segments_nine_months_before`
                UNION ALL
                SELECT customer_id, rfm_segment, '5-12 month ago' AS quarter FROM `customerhealth-crm-warehouse.didar_data.RFM_segments_one_year_before`
            )
            SELECT
                quarter,
                rfm_segment,
                COUNT(customer_id) AS count
            FROM all_segments
            WHERE NOT (rfm_segment LIKE '%Lost%' OR rfm_segment LIKE '%Risk%')
            GROUP BY quarter, rfm_segment
            """
            segment_counts = exacute_queries([query])[0]
            #  Calculate total customers per quarter for normalization
            total_per_quarter = segment_counts.groupby('quarter')['count'].sum().reset_index()
            total_per_quarter.rename(columns={'count': 'total'}, inplace=True)
            #  Merge to get normalized percentage per segment per quarter
            segment_normalized = pd.merge(segment_counts, total_per_quarter, on='quarter')
            segment_normalized['percentage'] = segment_normalized['count'] / segment_normalized['total']
            segment_normalized = segment_normalized.sort_values(by='quarter', ascending=False)
            st.session_state['rfms_segment_normalized'] = segment_normalized
        else:
            segment_normalized = st.session_state['rfms_segment_normalized'].copy()

        if segment_normalized is None or segment_normalized.empty:
            st.info("مشکلی در بارگذاری داده ها پیش امده است!!")
        else:
            #  User can choose to plot absolute count or normalized percentage
            y_axis_option = st.selectbox(
                "نمایش بر اساس:",
                options=["تعداد", "نرمال شده"],
                index=1
            )
            y_col = 'count' if y_axis_option == "تعداد" else 'percentage'
            y_title = 'تعداد مشتریان' if y_axis_option == "تعداد" else 'درصد مشتریان'

            #  Plot line chart of segment distribution over time
            fig = px.line(
                segment_normalized,
                x='quarter',
                y=y_col,
                color='rfm_segment',
                markers=True,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(
                title={
                    'text': 'تغییرات  در طول زمان',
                    'x': 1,
                    'xanchor': 'right',
                    'yanchor': 'top'
                },
                xaxis_title='دوره',
                yaxis_title=y_title,
                legend_title='RFM Segment'
            )
            st.plotly_chart(fig)

        st.write('---')
        st.subheader('بررسی تغییر یک سگمنت در طول زمان')

        months = ['این ماه', 'سه ماه پیش', 'شش ماه پیش', 'نه ماه پیش', 'دوازده ماه پیش']
        segments = [
            'At Risk ✨ Potential', 'At Risk ❤️ Loyal Customers', 'At Risk 👑 Champions',
            'At Risk 💰 Big Spender', 'At Risk 🔒 Reliable Customers', 'At Risk �️️ Low Value',
            'At Risk 🧐 Curious Customers', 'Lost ✨ Potential', 'Lost ❤️ Loyal Customers',
            'Lost 👑 Champions', 'Lost 💰 Big Spender', 'Lost 🔒 Reliable Customers', 'Lost 🗑️ Low Value',
            'Lost 🧐 Curious Customers', 'New 🧐 Curious Customers',  '✨ Potential', '❤️ Loyal Customers',
            '👑 Champions', '💰 Big Spender', '🔒 Reliable Customers', '🗑️ Low Value', '🧐 Curious Customers'
        ]
        cols = st.columns([2, 2])
        with cols[0]:
            period1 = st.selectbox("دوره اول را انتخاب کنید:", months, key="period1")
            segment1 = st.selectbox("سگمنت اول را انتخاب کنید:", segments, key="segment1")
        with cols[1]:
            period2 = st.selectbox("دوره دوم را انتخاب کنید:", months, key="period2")
            segment2 = st.selectbox("سگمنت دوم را انتخاب کنید:", ['All'] + segments, key="segment2")

        #  Map Persian period names to BigQuery table names and order
        period_map = {
            'این ماه': 'customerhealth-crm-warehouse.didar_data.RFM_segments',
            'سه ماه پیش': 'customerhealth-crm-warehouse.didar_data.RFM_segments_three_months_before',
            'شش ماه پیش': 'customerhealth-crm-warehouse.didar_data.RFM_segments_six_months_before',
            'نه ماه پیش': 'customerhealth-crm-warehouse.didar_data.RFM_segments_nine_months_before',
            'دوازده ماه پیش': 'customerhealth-crm-warehouse.didar_data.RFM_segments_one_year_before'
        }
        period_number_map = {
            'این ماه': 0,
            'سه ماه پیش': 1,
            'شش ماه پیش': 2,
            'نه ماه پیش': 3,
            'دوازده ماه پیش': 4
        }

        if st.button("اجرا", key='calculate_button'):
            #  Ensure period1 is before period2 (lower number means more recent)
            if period_number_map.get(period1, -1) <= period_number_map.get(period2, -1):
                st.warning("دوره اول باید قبل از دوره دوم باشد")
            else:
                #  If 'All' is selected, compare to all segments in period2
                selected_segments2 = segments if segment2 == 'All' else segment2
                rfm_id_1 = period_map.get(period1)
                rfm_id_2 = period_map.get(period2)
                #  Get customer IDs in period1 with selected segment1
                ids_query = f"""
                    SELECT customer_id, rfm_segment FROM `{rfm_id_1}`
                    WHERE rfm_segment = '{segment1}'
                """
                ids = exacute_query(ids_query)
                if ids is None or ids.empty:
                    st.info("مشکلی در بارگذاری داده ها پیش آمده است!!!")
                    return

                #  Prepare SQL list of customer IDs for next query
                id_list_sql = ', '.join(str(i) for i in ids['customer_id'].values.tolist())
                if isinstance(selected_segments2, str):
                    #  Query for a single segment in period2
                    df2_query = f"""
                        SELECT * FROM `{rfm_id_2}`
                        WHERE rfm_segment = '{selected_segments2}'
                        AND customer_id IN ({id_list_sql})
                    """
                else:
                    #  Query for all segments in period2
                    segments2 = ', '.join(f"'{i}'" for i in selected_segments2)
                    df2_query = f"""
                        SELECT * FROM `{rfm_id_2}`
                        WHERE rfm_segment IN ({segments2})
                        AND customer_id IN ({id_list_sql})
                    """
                df2 = exacute_query(df2_query)
                if df2 is None or df2.empty:
                    st.info("مشکلی در بارگذاری داده ها پیش آمده است!!!")
                    return
                
                #  Calculate distribution of segments in period2 for selected customers
                if len(selected_segments2)!= 1:
                    seg2_dist = df2['rfm_segment'].value_counts().reset_index()
                    seg2_dist.columns = ['rfm_segment', 'count']

                    st.subheader("توزیع سگمنت مشتریان انتخابی در دوره دوم")
                    fig2 = px.bar(
                        seg2_dist,
                        x='rfm_segment',
                        y='count',
                        color='rfm_segment',
                        title="",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig2.update_layout(xaxis_title='سگمنت', yaxis_title='تعداد')
                    st.plotly_chart(fig2, use_container_width=True)

                #  Merge period1 and period2 data for selected customers for display
                data = pd.merge(
                    df2,
                    ids[ids['rfm_segment'] == segment1][['customer_id', 'rfm_segment']],
                    on="customer_id"
                )
                data = data.rename(columns={
                    'customer_id': 'شناسه مشتری',
                    'first_name': 'نام',
                    'last_name': 'نام خانوادگی',
                    'phone_number': 'شماره تماس',
                    'recency': 'تازگی خرید',
                    'frequency': 'تعداد خرید',
                    'monetary': 'ارزش خرید',
                    'total_nights': 'مجموع شب‌ها',
                    'last_reserve_date': 'تاریخ آخرین رزرو',
                    'last_checkin': 'تاریخ ورود آخر',
                    'last_checkout': 'تاریخ خروج آخر',
                    'favorite_product': 'محصول مورد علاقه',
                    'last_product': 'آخرین محصول',
                    'rfm_segment_x': 'سگمنت دوره دوم',
                    'rfm_segment_y': 'سگمنت دوره اول'
                })
                st.write(data)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="دانلود داده‌ها به صورت CSV",
                        data=convert_df(data),
                        file_name='rfm_segmentation.csv',
                        mime='text/csv',
                        key=f'download_{period1}_{segment1}_{period2}_{segment2}.csv'
                    )
                with col2:
                    st.download_button(
                        label="دانلود داده‌ها به صورت اکسل",
                        data=convert_df_to_excel(data),
                        file_name='rfm_segmentation.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key=f'download_{period1}_{segment1}_{period2}_{segment2}.xlsx'
                    )

        st.write('---')

        #  Join RFM segments with CHS scores for current month to show average scores per segment
        merged_df = exacute_query("""
            SELECT 
                rfm.customer_id, 
                rfm.rfm_segment, 
                chs.customer_nps, 
                chs.customer_amneties_score, 
                chs.customer_staff_score
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments` rfm
            INNER JOIN `customerhealth-crm-warehouse.CHS.CHS_components` chs
                ON rfm.customer_id = chs.Customer_ID
        """)

        #  Aggregate mean scores and count of surveys per segment
        agg_scores = merged_df.groupby('rfm_segment').agg(
            تعداد_نظرسنجی=('customer_nps', 'count'),
            میانگین_NPS=('customer_nps', 'mean'),
            میانگین_امکانات=('customer_amneties_score', 'mean'),
            میانگین_پرسنل=('customer_staff_score', 'mean')
        ).reset_index().rename(columns={'rfm_segment': 'سگمنت'})

        st.subheader("میانگین امتیازهای هپی کال هر سگمنت")
        st.dataframe(agg_scores)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="دانلود داده‌ها به صورت CSV",
                data=convert_df(agg_scores),
                file_name='rfm_segmentation_happy_calll.csv',
                mime='text/csv',
                key='rfm_segmentation_happy_calll.csv'
            )
        with col2:
            st.download_button(
                label="دانلود داده‌ها به صورت اکسل",
                data=convert_df_to_excel(agg_scores),
                file_name='rfm_segmentation_happy_calll.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key='rfm_segmentation_happy_calll.xlsx'
            )
    else:
        login()

if __name__ == "__main__":
    main()