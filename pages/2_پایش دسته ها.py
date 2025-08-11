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
    st.subheader(" توزیع بخش‌بندی مشتریان در طول زمان")    

    if 'auth'in st.session_state and st.session_state.auth:    
        # Instead of loading all data, fetch only the aggregated data needed for the plot directly from the database.
        if 'rfms_segment_normalized' not in st.session_state:
            # Compose a single query to get counts per segment per period, excluding 'Lost' and 'Risk'
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

            # Compute total customers per quarter
            total_per_quarter = segment_counts.groupby('quarter')['count'].sum().reset_index()
            total_per_quarter.rename(columns={'count': 'total'}, inplace=True)

            # Merge and compute normalized percentage
            segment_normalized = pd.merge(segment_counts, total_per_quarter, on='quarter')
            segment_normalized['percentage'] = segment_normalized['count'] / segment_normalized['total']
            segment_normalized = segment_normalized.sort_values(by='quarter', ascending=False)

            st.session_state['rfms_segment_normalized'] = segment_normalized
        else:
            segment_normalized = st.session_state['rfms_segment_normalized'].copy()


        if segment_normalized is None or segment_normalized.empty:
            st.info("مشکلی در بارگذاری داده ها پیش امده است!!")
        else:
            # Select box for user to choose between real number or normalized
            y_axis_option = st.selectbox(
                "نمایش بر اساس:",
                options=["تعداد", "نرمال شده"],
                index=1
            )

            if y_axis_option == "تعداد":
                y_col = 'count'
                y_title = 'تعداد مشتریان'
            else:
                y_col = 'percentage'
                y_title = 'درصد مشتریان'

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
        # Create two filters for period and segment selection for comparison
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

        # Map period to rfms index and to a numeric order for comparison
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
            print(period_map.get(period1, 0), period_map.get(period2, 0))
            if period_number_map.get(period1, -1) <= period_number_map.get(period2, -1):
                st.warning("دوره اول باید قبل از دوره دوم باشد")
            else:
                if segment2 == 'All':
                    segment2 = segments
                
                rfm_id_1 = period_map.get(period1)
                rfm_id_2 = period_map.get(period2)

                ids_query = f"""
                            SELECT customer_id, rfm_segment FROM `{rfm_id_1}`
                            WHERE rfm_segment = '{segment1}'
                            """
                ids = exacute_query(ids_query)
                if ids is None or ids.empty:
                    st.info("مشکلی در بارگذاری داده ها پیش آمده است!!!")
                    return

                # Distribution of those customers in period 2 by their segment
                id_list_sql = ', '.join(str(i) for i in ids['customer_id'].values.tolist())
                if isinstance(segment2, str):
                    df2_query = f"""
                            SELECT * FROM `{rfm_id_2}`
                            WHERE rfm_segment = '{segment2}'
                            AND customer_id IN ({id_list_sql})
                            """
                else:
                    segments2 = ', '.join(f"'{i}'" for i in segment2)
                    df2_query = f"""
                            SELECT * FROM `{rfm_id_2}`
                            WHERE rfm_segment IN ({segments2})
                            AND customer_id IN ({id_list_sql})
                    """
                df2 = exacute_query(df2_query)

                if df2 is None or df2.empty:
                    st.info("مشکلی در بارگذاری داده ها پیش آمده است!!!")
                    return
                seg2_dist = df2['rfm_segment'].value_counts().reset_index()

                seg2_dist.columns = ['rfm_segment', 'count']

                # Plot bar chart for period 2
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
                data = pd.merge(df2, ids[ids['rfm_segment'] == segment1][['customer_id', 'rfm_segment']], on="customer_id")

                # change columns names
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

        st.write('---')

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
                file_name='rfm_segmentation_with_churn.csv',
                mime='text/csv',
            )

        with col2:
            st.download_button(
                label="دانلود داده‌ها به صورت اکسل",
                data=convert_df_to_excel(agg_scores),
                file_name='rfm_segmentation_with_churn.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
    else:
        login()
if __name__ == "__main__":
    main()