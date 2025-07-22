import streamlit as st
import pandas as pd
import os
import sys
from io import BytesIO
from datetime import datetime
import plotly.express as px

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.logger import logger
from utils.constants import DEALSTATUS, DEALVALUE, \
    CUSTOMERID, COMPLEX, PRODUCTTITLE
from RFM.utils.funcs import convert_df, convert_df_to_excel

def main():
    st.set_page_config(page_title="تحلیل کمپین", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader("تحلیل سبد خرید مشتری بر اساس سگمنت‌ها و محصولات")    

    # Check data availability and login first
    if st.authentication_status:    
        if 'data' in st.session_state and 'rfm_data'in st.session_state:
            data = st.session_state.data
            rfm_data = st.session_state.rfm_data


            # Get unique clusters from RFM data
            cluster_options = rfm_data['RFM_segment_label'].unique().tolist()
            cluster_options.sort()
            select_all_clusters = st.checkbox("انتخاب تمام سگمنت‌ها", value=True, key='select_all_clusters_portfolio')

            if select_all_clusters:
                selected_clusters = cluster_options
            else:
                selected_clusters = st.multiselect(
                    "Select Clusters:",
                    options=cluster_options,
                    default=[],
                    key='clusters_multiselect_portfolio'
                )

            # Filter by Complex
            complex_options = data[COMPLEX].dropna().unique().tolist()
            complex_options.sort()
            select_all_complex = st.checkbox("انتخاب تمام مجتمع‌ها", value=True, key='select_all_complex')

            if select_all_complex:
                selected_complexes = complex_options
            else:
                selected_complexes = st.multiselect(
                    "Select Complexes:",
                    options=complex_options,
                    default=[],
                    key='complexes_multiselect'
                )

            data_filtered_by_complex = data[data[COMPLEX].isin(selected_complexes)]

            # Filter by Type
            type_options = data_filtered_by_complex[PRODUCTTITLE].dropna().unique().tolist()
            type_options.sort()
            select_all_types = st.checkbox("انتخاب تمام تیپ‌ها", value=True, key='select_all_types')

            if select_all_types:
                selected_types = type_options
            else:
                selected_types = st.multiselect(
                    "Select Types:",
                    options=type_options,
                    default=[],
                    key='types_multiselect'
                )

            data_filtered_by_type = data_filtered_by_complex[data_filtered_by_complex[PRODUCTTITLE].isin(selected_types)]

            # Filter by Blacklist Status
            blacklist_options = sorted(data['BlackList Status'].unique())
            select_all_blacklist = st.checkbox("هم بلک‌لیست و هم غیر بلک‌لیست", value=True, key='select_all_blacklist')

            if select_all_blacklist:
                selected_blacklist = blacklist_options
            else:
                selected_blacklist = st.multiselect(
                    "Select BlackList Status:",
                    options=blacklist_options,
                    default=[],
                    key='blacklist_multiselect'
                )

            data_filtered_by_blacklist = data_filtered_by_type[data_filtered_by_type['BlackList Status'].isin(selected_blacklist)]

            # VIP Filter
            vip_options_page = sorted(rfm_data['VIP Status'].unique())
            select_all_vips_page = st.checkbox("VIP انتخاب تمام دسته‌های ", value=True, key='select_all_vips_portfolio')

            if select_all_vips_page:
                selected_vips_portfolio = vip_options_page
            else:
                selected_vips_portfolio = st.multiselect(
                    "انتخاب کنید VIP سطح:",
                    options=vip_options_page,
                    default=[],
                    key='vips_multiselect_portfolio'
                )

            # Apply filters
            with st.form(key='portfolio_form'):
                apply_portfolio = st.form_submit_button(label='Apply')

            if apply_portfolio:
                if not selected_clusters:
                    st.warning("لااقل یک سگمنت را انتخاب کنید.")
                elif not selected_vips_portfolio:
                    st.warning(" انتخاب کنید VIP لااقل یک سطح")
                else:
                    # Get customers in selected clusters and VIP statuses
                    customers_in_clusters = rfm_data[(rfm_data['RFM_segment_label'].isin(selected_clusters)) &
                                                    (rfm_data['VIP Status'].isin(selected_vips_portfolio))]['Code'].unique()
                    # Filter deals data
                    deals_filtered = data_filtered_by_blacklist[data_filtered_by_blacklist[CUSTOMERID].isin(customers_in_clusters)]

                    if deals_filtered.empty:
                        st.warning("هیچ معامله‌ای با این شرایط پیدا نشد")
                    else:
                        # Frequency distribution
                        frequency_distribution = deals_filtered.groupby(PRODUCTTITLE).size().reset_index(name='Frequency')

                        # Monetary distribution
                        monetary_distribution = deals_filtered.groupby(PRODUCTTITLE)[DEALVALUE].sum().reset_index()

                        # Plot Frequency Distribution
                        st.subheader("توزیع فراوانی معاملات روی این محصولات")
                        fig_freq = px.bar(
                            frequency_distribution,
                            x=PRODUCTTITLE,
                            y='Frequency',
                            title='توزیع فراوانی',
                            labels={PRODUCTTITLE: 'Product', 'Frequency': 'Number of Purchases'},
                            text='Frequency'
                        )
                        fig_freq.update_traces(textposition='outside')
                        st.plotly_chart(fig_freq)

                        # Plot Monetary Distribution
                        st.subheader("توزیع ارزش مالی معاملات روی این محصولات")
                        fig_monetary = px.bar(
                            monetary_distribution,
                            x=PRODUCTTITLE,
                            y=DEALVALUE,
                            title='توزیع مالی',
                            labels={PRODUCTTITLE: 'Product', DEALVALUE: 'Total Monetary Value'},
                            text=DEALVALUE
                        )
                        fig_monetary.update_traces(textposition='outside')
                        st.plotly_chart(fig_monetary)

                        # Customer Details Table
                        st.subheader("Customer Details")
                        successful_deals = deals_filtered[deals_filtered[DEALSTATUS] == 'Won']

                        customer_nights = successful_deals.groupby([CUSTOMERID, PRODUCTTITLE])['nights'].sum().unstack(fill_value=0)

                        customer_details = rfm_data[rfm_data['Code'].isin(customers_in_clusters)][['Code', 'Name', 'VIP Status','average stay','Is staying', 'RFM_segment_label', 'Recency', 'Frequency', 'Monetary']]
                        customer_details = customer_details.merge(customer_nights, left_on='Code', right_index=True, how='inner').fillna(0)
                        
                        st.write(customer_details)
                        # Download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="Download data as CSV",
                                data=convert_df(customer_details),
                                file_name='portfolio_analysis.csv',
                                mime='text/csv',
                            )
                        with col2:
                            st.download_button(
                                label="Download data as Excel",
                                data=convert_df_to_excel(customer_details),
                                file_name='portfolio_analysis.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            )
        else:
            st.info('ابتدا داده را لود کنید')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')



if __name__ == "__main__":
    main()