import streamlit as st
import pandas as pd
import os
import sys

from datetime import datetime
import plotly.express as px

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.logger import logger
from utils.rfm_calculator import calculate_rfm, normalize_rfm, rfm_segmentation
from utils.constants import COLOR_MAP, DEALDONEDATE
from RFM.utils.funcs import convert_df, convert_df_to_excel

@st.cache_data(ttl=60)
def rfm_calculation_cache(data, date=None):
    """Calculate RFM metrics."""
    try:
        rfm_data = rfm_segmentation(calculate_rfm(data, date))
        norm = normalize_rfm(rfm_data)

        return rfm_data, norm
    except Exception as e:
        st.error(f"خطا در محاسبه RFM")
        logger.error("Error in calcualting RFM:", e)
        return None

def main():
    st.set_page_config(page_title="تحلیل کمپین", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader("سنجش عملکرد کمپین از طریق بخش‌بندی مشتریان ")    


    if st.authentication_status:    
        if 'data' in st.session_state and 'rfm_data'in st.session_state:
                        
            data = st.session_state.data
            rfm_data = st.session_state.rfm_data
            # VIP filter
            vip_options = sorted([v for v in data['VIP Status'].dropna().unique() if v != ''])
            vip_status_all = st.checkbox("انتخاب تمام وضعیت‌هایVIP", value=True, key='vips_checkbox')
            if vip_status_all or not vip_options:
                vip_values = vip_options
            else:
                vip_values = st.multiselect(
                    "انتخاب وضعیت VIP:",
                    options=vip_options,
                    default=[],
                    key='vips_multiselect_selectbox'
                )
                if not vip_values:
                    vip_values = vip_options
        
            # --- UI for comparison ---
            with st.form(key='comparison_form'):
                comparison_date = st.date_input("یک تاریخ را برای مقایسه انتخاب کنید", value=datetime.today())
                # Get list of unique segments
                segment_options = ['All'] + sorted(rfm_data['RFM_segment_label'].dropna().unique())
                col1, col2 = st.columns(2)
                with col1:
                    from_segment = st.selectbox("بررسی تغییرات از سگمنت...", options=segment_options)
                with col2:
                    to_segment = st.selectbox("به سگمنت...", options=segment_options)
                submit_button = st.form_submit_button(label='مشاهده نتایج')

            if submit_button:
                # Handle the cases
                if from_segment == 'All' and to_segment == 'All':
                    st.error("لااقل یک سگمنت مشخص برای مقصد یا مبدا انتخاب کنید")
                    return

                # Filter data before the selected date
                data_before_date = data[data[DEALDONEDATE] <= pd.to_datetime(comparison_date)]

                if data_before_date.empty:
                    st.warning("هیچ دیتایی در بازه تاریخی انتخاب شده موجود نیست")
                    return

                # Calculate RFM1 (RFM before the selected date)
                rfm_data1, norm_rfm_data1 = rfm_calculation_cache(data_before_date, date=comparison_date)

                if rfm_data1 is None or rfm_data1.empty:
                    st.warning("داده RFM قبل از تاریخ انتخابی محاسبه نشد یا خالی است.")
                    return

                # Filter RFM data based on selected VIP statuses
                rfm_data1 = rfm_data1[rfm_data1['VIP Status'].isin(vip_values)]
                rfm_data_filtered = rfm_data[rfm_data['VIP Status'].isin(vip_values)]

                # Merge RFM1 and RFM2 on 'Customer ID'
                merge_cols = ['Code', 'Name', 'Phone Number', 'VIP Status', 'RFM_segment_label']
                extra_cols = ['average stay','Is Monthly','Is staying'] if all(col in rfm_data_filtered.columns for col in ['average stay','Is Monthly','Is staying']) else []
                right_cols = ['Code'] + extra_cols + ['RFM_segment_label']
                comparison_df = rfm_data1[merge_cols].merge(
                    rfm_data_filtered[right_cols],
                    on='Code',
                    how='inner',
                    suffixes=('_RFM1', '_RFM2')
                )

                if from_segment != 'All':
                    comparison_df = comparison_df[comparison_df['RFM_segment_label_RFM1'] == from_segment]
                if to_segment != 'All':
                    comparison_df = comparison_df[comparison_df['RFM_segment_label_RFM2'] == to_segment]

                if comparison_df.empty:
                    st.warning("هیچ مشتری‌ای این انتقال سگمنتی را نداشته است")
                    return

                # Display count and bar chart
                if from_segment != 'All':
                    counts = comparison_df['RFM_segment_label_RFM2'].value_counts().reset_index()
                    counts.columns = ['RFM_segment_label_RFM2', 'Count']
                    fig = px.bar(
                        counts,
                        x='RFM_segment_label_RFM2',
                        y='Count',
                        color='RFM_segment_label_RFM2',
                        color_discrete_map=COLOR_MAP,
                        text='Count',
                        labels={'RFM_segment_label_RFM2': 'سگمنت‌ها بعد از تاریخ انتخابی', 'Count': 'تعداد مشتریان'}
                    )
                elif to_segment != 'All':
                    counts = comparison_df['RFM_segment_label_RFM1'].value_counts().reset_index()
                    counts.columns = ['RFM_segment_label_RFM1', 'Count']
                    fig = px.bar(
                        counts,
                        x='RFM_segment_label_RFM1',
                        y='Count',
                        color='RFM_segment_label_RFM1',
                        color_discrete_map=COLOR_MAP,
                        text='Count',
                        labels={'RFM_segment_label_RFM1': 'سگمنت‌ها قبل از تاریخ انتخابی', 'Count': 'تعداد مشتریان'}
                    )
                else:
                    fig = None

                st.write(f"تعداد مشتریانی که در این انتقال بوده‌اند: **{len(comparison_df)}**")
                if from_segment!='All':
                    fig = px.bar(
                        counts,
                        x='RFM_segment_label_RFM2',
                        y='Count',
                        color='RFM_segment_label_RFM2',
                        color_discrete_map=COLOR_MAP,
                        text='Count',
                        labels={'RFM_segment_label_RFM2': 'سگمنت‌ها بعد از تاریخ انتخابی', 'Count': 'تعداد مشتریان'}
                    )
                elif to_segment!='All':
                    fig = px.bar(
                        counts,
                        x='RFM_segment_label_RFM1',
                        y='Count',
                        color='RFM_segment_label_RFM1',
                        color_discrete_map=COLOR_MAP,
                        text='Count',
                        labels={'RFM_segment_label_RFM1': 'سگمنت‌ها قبل از تاریخ انتخابی', 'Count': 'تعداد مشتریان'}
                    )
                
                if to_segment=='All' or from_segment=='All':
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig)

                # Show customer table
                st.subheader("Customer Details")
                customer_table = comparison_df[['Code', 'Name', 'Phone Number', 'VIP Status', 'RFM_segment_label_RFM1', 'RFM_segment_label_RFM2']]
                customer_table.rename(columns={
                    'RFM_segment_label_RFM1': 'Before Segment',
                    'RFM_segment_label_RFM2': 'After Segment'
                }, inplace=True)
                st.write(customer_table)

                # Download buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="Download data as CSV",
                        data=convert_df(customer_table),
                        file_name='rfm_segment_comparison.csv',
                        mime='text/csv',
                    )
                with col2:
                    st.download_button(
                        label="Download data as Excel",
                        data=convert_df_to_excel(customer_table),
                        file_name='rfm_segment_comparison.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
        else:
            st.info('ابتدا داده را لود کنید')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')
if __name__ == "__main__":
    main()