import streamlit as st
import pandas as pd
import os
import sys
import plotly.express as px

# Add path and imports
sys.path.append(os.path.abspath(".."))

from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import load_rfms


def main():
    st.set_page_config(page_title="تحلیل زمانی", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader(" توزیع بخش‌بندی مشتریان در طول زمان")    


    if 'auth'in st.session_state and st.session_state.auth:    
        if 'rfms' not in st.session_state:
            load_rfms()
            st.rerun()
        else:
            #
            rfms = st.session_state['rfms']
            for i in range(5):
                if i == 0:
                    rfms[i]['quarter'] = "1-this month"
                else:
                    rfms[i]['quarter'] = f"{i+1}-{(i)*3} month ago"
                
                rfms[i] = rfms[i][~rfms[i]['rfm_segment'].str.contains('Lost|Risk')]

            df_all = pd.concat(rfms, ignore_index=True)

            # Count customers per segment per quarter
            segment_counts = df_all.groupby(['quarter', 'rfm_segment'])['customer_id'].count().reset_index()
            segment_counts.rename(columns={'customer_id': 'count'}, inplace=True)

            # Compute total customers per quarter
            total_per_quarter = segment_counts.groupby('quarter')['count'].sum().reset_index()
            total_per_quarter.rename(columns={'count': 'total'}, inplace=True)

            # Merge and compute normalized percentage
            segment_normalized = pd.merge(segment_counts, total_per_quarter, on='quarter')
            segment_normalized['percentage'] = segment_normalized['count'] / segment_normalized['total']
            segment_normalized = segment_normalized.sort_values(by='quarter', ascending=False)

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
            import plotly.express as px
            fig = px.line(
                segment_normalized,
                x='quarter',
                y=y_col,
                color='rfm_segment',
                markers=True,
                title='RFM Segment Changes Over Time',
                color_discrete_sequence=px.colors.qualitative.Set3 
            )
            fig.update_layout(
                xaxis_title='Quarter',
                yaxis_title=y_title,
                legend_title='RFM Segment'
            )
            st.plotly_chart(fig)
        
        st.write('---')
        # Create two filters for period and segment selection for comparison
        import plotly.express as px

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
            segment1 = st.multiselect("سگمنت اول را انتخاب کنید:", segments, key="segment1", default=segments)
        with cols[1]:
            period2 = st.selectbox("دوره دوم را انتخاب کنید:", months, key="period2")
            segment2 = st.multiselect("سگمنت دوم را انتخاب کنید:", segments, key="segment2", default=segments)

        if st.button("اجرا", key='calculate_rfm_button'):
            # Map period to rfms index
            period_map = {
                'این ماه': 0,
                'سه ماه پیش': 1,
                'شش ماه پیش': 2,
                'نه ماه پیش': 3,
                'دوازده ماه پیش': 4
            }
            df1 = rfms[period_map.get(period1, 0)]
            df2 = rfms[period_map.get(period2, 0)]

            # Filter customers in period 1 by selected segments
            ids = df1[df1['rfm_segment'].isin(segment1)]['customer_id'].unique().tolist()

            # Distribution of selected segments in period 1
            seg1_dist = df1[df1['rfm_segment'].isin(segment1)]['rfm_segment'].value_counts().reset_index()
            seg1_dist.columns = ['rfm_segment', 'count']

            # Distribution of those customers in period 2 by their segment
            df2_selected = df2[df2['customer_id'].isin(ids)]
            seg2_dist = df2_selected['rfm_segment'].value_counts().reset_index()
            seg2_dist.columns = ['rfm_segment', 'count']

            # Optionally filter seg2_dist by segment2 if user selected any
            if segment2:
                seg2_dist = seg2_dist[seg2_dist['rfm_segment'].isin(segment2)]

            # Plot bar chart for period 1
            st.subheader(f"توزیع سگمنت‌های انتخابی در {period1}")
            fig1 = px.bar(
                seg1_dist,
                x='rfm_segment',
                y='count',
                color='rfm_segment',
                title=f"توزیع سگمنت‌های انتخابی در {period1}",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig1.update_layout(xaxis_title='سگمنت', yaxis_title='تعداد')
            st.plotly_chart(fig1, use_container_width=True)

            # Plot bar chart for period 2
            st.subheader(f"توزیع سگمنت مشتریان انتخابی در {period2}")
            fig2 = px.bar(
                seg2_dist,
                x='rfm_segment',
                y='count',
                color='rfm_segment',
                title=f"توزیع سگمنت مشتریان انتخابی در {period2}",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig2.update_layout(xaxis_title='سگمنت', yaxis_title='تعداد')
            st.plotly_chart(fig2, use_container_width=True)

        
    else:
        login()
if __name__ == "__main__":
    main()