import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.constants import DEALSOURCE, DEALOWNER, DEALDONEDATE, DEALCREATEDDATE, DEALSTATUS, DEALVALUE, PURCHASETYPE, CUSTOMERID
from utils.funcs import convert_df, convert_df_to_excel, get_first_successful_deal_date_for_customers

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="تحلیل کانال های فروش", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("‌تحلیل عملکرد کانال‌های فروش")

    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:    
        if 'data' in st.session_state and 'rfm_data'in st.session_state:
            data = st.session_state.data
            rfm_data = st.session_state.rfm_data
            
            if 'first_deal_date_by_customer' not in st.session_state:
                global_first_deal_date_series_channels = get_first_successful_deal_date_for_customers(data)
            else:
                global_first_deal_date_series_channels = st.session_state.first_deal_date_by_customer
            tabs = st.tabs([
                    "Single Channel Analysis",
                    "Compare Two Channels",
                    "Compare All Channels",
                    "RFM Sales Analysis",
                    "Channel Transitions"  

                ])
            sale_channels_options = data[DEALSOURCE].unique().tolist()

            ###########################################################################
            #  SINGLE CHANNEL ANALYSIS
            ###########################################################################
            with tabs[0]:
                st.markdown("### Single Channel Analysis")

                # VIP Filter
                vip_options_page = sorted(rfm_data['VIP Status'].unique())
                select_all_vips_page = st.checkbox("Select all VIP statuses", value=True, key='select_all_vips_channel_single')
                if select_all_vips_page:
                    selected_vips_channel = vip_options_page
                else:
                    selected_vips_channel = st.multiselect(
                        "Select VIP Status:",
                        options=vip_options_page,
                        default=[],
                        key='vips_multiselect_channel_single'
                    )

                with st.form(key='channel_filters_form', clear_on_submit=False):
                    selected_channel = st.selectbox("Select a Sale Channel:", options=sale_channels_options)
                    min_date = data[DEALCREATEDDATE].min()
                    max_date = data[DEALCREATEDDATE].max()
                    if pd.isna(min_date) or pd.isna(max_date):
                        st.warning("Date range is invalid. Please check your data.")
                        st.stop()

                    min_date = min_date.date()
                    max_date = max_date.date()

                    start_date = st.date_input(
                        "Start Date", 
                        value=min_date,
                        min_value=min_date, 
                        max_value=max_date, 
                        key='channel_start_date_single'
                    )
                    end_date = st.date_input(
                        "End Date", 
                        value=max_date,
                        min_value=min_date, 
                        max_value=max_date, 
                        key='channel_end_date_single'
                    )

                    apply_channel_filters = st.form_submit_button(label='Apply Filters')

                if "single_channel_data" not in st.session_state:
                    st.session_state.single_channel_data = None
                    st.session_state.single_channel_filtered_all = None
                    st.session_state.single_channel_kpi_df = None
                    st.session_state.single_channel_daily_df = None

                if apply_channel_filters:
                    if selected_channel:
                        if selected_vips_channel:
                            # Filter data
                            date_filtered_data_all = data[
                                (data[DEALCREATEDDATE] >= pd.to_datetime(start_date)) &
                                (data[DEALCREATEDDATE] <= pd.to_datetime(end_date)) &
                                (data[DEALSOURCE] == selected_channel)
                            ]
                            date_filtered_data_all = date_filtered_data_all[date_filtered_data_all['VIP Status'].isin(selected_vips_channel)]
                            channel_data_success = date_filtered_data_all[date_filtered_data_all[DEALSTATUS] == 'Won']

                            if date_filtered_data_all.empty:
                                st.warning("No deals found for this channel in the specified date range.")
                                st.session_state.single_channel_data = None
                                st.session_state.single_channel_filtered_all = None
                                st.session_state.single_channel_kpi_df = None
                                st.session_state.single_channel_daily_df = None
                            else:
                                st.session_state.single_channel_filtered_all = date_filtered_data_all.copy()
                                st.session_state.single_channel_data = channel_data_success.copy()

                                # KPIs
                                total_deals = len(date_filtered_data_all)
                                successful_deals_count = len(channel_data_success)
                                success_rate = (successful_deals_count / total_deals)*100 if total_deals>0 else 0

                                new_customers = 0
                                returning_customers = 0
                                if not channel_data_success.empty:
                                    unique_customers = channel_data_success[CUSTOMERID].unique()
                                    for cid in unique_customers:
                                        first_deal_date =  global_first_deal_date_series_channels.get(cid, pd.NaT)
                                        if pd.isna(first_deal_date):
                                            continue
                                        if start_date <= first_deal_date.date() <= end_date:
                                            new_customers += 1
                                        elif first_deal_date.date() < start_date:
                                            returning_customers += 1

                                avg_deal_value = channel_data_success[DEALVALUE].mean() if not channel_data_success.empty else 0
                                avg_nights = channel_data_success['nights'].mean() if not channel_data_success.empty else 0

                                # Extension analysis
                                ext = channel_data_success[channel_data_success[PURCHASETYPE] == 'تمدید']
                                ext_cnt = len(ext)
                                ext_rate = (ext_cnt/successful_deals_count*100) if successful_deals_count>0 else 0

                                # Compare with previous period
                                prev_period_length = (end_date - start_date).days + 1
                                prev_end_date = start_date - timedelta(days=1)
                                prev_start_date = prev_end_date - timedelta(days=prev_period_length - 1)
                                prev_period_data_all = data[
                                    (data[DEALDONEDATE] >= pd.to_datetime(prev_start_date)) &
                                    (data[DEALDONEDATE] <= pd.to_datetime(prev_end_date)) &
                                    (data[DEALSOURCE] == selected_channel)
                                ]
                                prev_period_data_all = prev_period_data_all[prev_period_data_all['VIP Status'].isin(selected_vips_channel)]
                                prev_channel_success = prev_period_data_all[prev_period_data_all[DEALSTATUS] == 'Won']

                                if not prev_period_data_all.empty:
                                    prev_total_deals = len(prev_period_data_all)
                                    prev_successful_deals_count = len(prev_channel_success)
                                    prev_success_rate = (prev_successful_deals_count / prev_total_deals)*100 if prev_total_deals>0 else 0
                                    prev_avg_deal_value = prev_channel_success[DEALVALUE].mean() if not prev_channel_success.empty else 0
                                    prev_avg_nights = prev_channel_success['nights'].mean() if not prev_channel_success.empty else 0
                                    prev_ext_ = prev_channel_success[prev_channel_success[PURCHASETYPE] == 'تمدید']
                                    prev_ext_cnt_ = len(prev_ext_)
                                    prev_ext_rate = (prev_ext_cnt_/prev_successful_deals_count*100) if prev_successful_deals_count>0 else 0

                                    prev_new_customers = 0
                                    prev_returning_customers = 0
                                    if not prev_channel_success.empty:
                                        unique_customers_prev = prev_channel_success[CUSTOMERID].unique()
                                        for cid in unique_customers_prev:
                                            first_deal_date = global_first_deal_date_series_channels.get(cid, pd.NaT)
                                            if pd.isna(first_deal_date):
                                                continue
                                            if prev_start_date <= first_deal_date.date() <= prev_end_date:
                                                prev_new_customers += 1
                                            elif first_deal_date.date() < prev_start_date:
                                                prev_returning_customers += 1
                                else:
                                    prev_total_deals = 0
                                    prev_successful_deals_count = 0
                                    prev_success_rate = 0
                                    prev_avg_deal_value = 0
                                    prev_avg_nights = 0
                                    prev_ext_rate = 0
                                    prev_new_customers = 0
                                    prev_returning_customers = 0

                                st.session_state.single_channel_kpi_df = {
                                    'total_deals': total_deals,
                                    'successful_deals_count': successful_deals_count,
                                    'success_rate': success_rate,
                                    'avg_deal_value': avg_deal_value,
                                    'avg_nights': avg_nights,
                                    'extention_rate': ext_rate,
                                    'new_customers': new_customers,
                                    'returning_customers': returning_customers,
                                    'prev_total_deals': prev_total_deals,
                                    'prev_successful_deals_count': prev_successful_deals_count,
                                    'prev_success_rate': prev_success_rate,
                                    'prev_avg_deal_value': prev_avg_deal_value,
                                    'prev_avg_nights': prev_avg_nights,
                                    'prev_extention_rate': prev_ext_rate,
                                    'prev_new_customers': prev_new_customers,
                                    'prev_returning_customers': prev_returning_customers
                                }

                                # Build daily metrics
                                daily_metrics = []
                                days_range = pd.date_range(start=start_date, end=end_date, freq='D')
                                earliest_global = global_first_deal_date_series_channels.to_dict()
                                for single_day in days_range:
                                    day_data_all = date_filtered_data_all[date_filtered_data_all[DEALDONEDATE].dt.date == single_day.date()]
                                    day_data_success = day_data_all[day_data_all[DEALSTATUS] == 'Won']
                                    td = len(day_data_all)
                                    sd = len(day_data_success)
                                    dv = day_data_success[DEALVALUE].mean() if not day_data_success.empty else 0
                                    nights_v = day_data_success['nights'].mean() if not day_data_success.empty else 0

                                    new_cus = 0
                                    ret_cus = 0
                                    if not day_data_success.empty:
                                        for ccid in day_data_success[CUSTOMERID].unique():
                                            fdate = earliest_global.get(ccid, pd.NaT)
                                            if not pd.isna(fdate):
                                                if single_day.date() == fdate.date():
                                                    new_cus += 1
                                                elif fdate.date() < single_day.date():
                                                    ret_cus += 1

                                    daily_metrics.append({
                                        'Date': single_day,
                                        'Total Deals': td,
                                        'Successful Deals': sd,
                                        'New Customers': new_cus,
                                        'Returning Customers': ret_cus,
                                        'Average Deal Value': dv,
                                        'Average Nights': nights_v
                                    })
                                daily_df = pd.DataFrame(daily_metrics)
                                st.session_state.single_channel_daily_df = daily_df.copy()
                        else:
                            st.warning("Please select at least one VIP status.")
                    else:
                        st.warning("Please select a sale channel.")

                # Display results
                if (
                    st.session_state.single_channel_data is not None and
                    st.session_state.single_channel_filtered_all is not None and
                    st.session_state.single_channel_kpi_df is not None
                ):
                    channel_data_success = st.session_state.single_channel_data
                    data_filtered_all = st.session_state.single_channel_filtered_all
                    kpi_data = st.session_state.single_channel_kpi_df

                    def pct_diff(new_val, old_val):
                        if old_val == 0:
                            return None
                        return f"{((new_val - old_val)/abs(old_val)*100):.2f}%"

                    total_deals = kpi_data['total_deals']
                    successful_deals_count = kpi_data['successful_deals_count']
                    success_rate = kpi_data['success_rate']
                    avg_deal_value = kpi_data['avg_deal_value']
                    avg_nights = kpi_data['avg_nights']
                    extention_rate = kpi_data['extention_rate']
                    new_customers = kpi_data['new_customers']
                    returning_customers = kpi_data['returning_customers']

                    prev_total_deals = kpi_data['prev_total_deals']
                    prev_successful_deals_count = kpi_data['prev_successful_deals_count']
                    prev_success_rate = kpi_data['prev_success_rate']
                    prev_avg_deal_value = kpi_data['prev_avg_deal_value']
                    prev_avg_nights = kpi_data['prev_avg_nights']
                    prev_extention_rate = kpi_data['prev_extention_rate']
                    prev_new_customers = kpi_data['prev_new_customers']
                    prev_returning_customers = kpi_data['prev_returning_customers']

                    st.markdown("### Key Performance Indicators (KPIs)")
                    colKPI1, colKPI2, colKPI3, colKPI4 = st.columns(4)
                    colKPI1.metric(
                        "Total Deals",
                        f"{total_deals}",
                        pct_diff(total_deals, prev_total_deals)
                    )
                    colKPI2.metric(
                        "Successful Deals",
                        f"{successful_deals_count}",
                        pct_diff(successful_deals_count, prev_successful_deals_count)
                    )
                    colKPI3.metric(
                        "Success Rate (%)",
                        f"{success_rate:.2f}%",
                        pct_diff(success_rate, prev_success_rate)
                    )
                    colKPI4.metric(
                        "Avg. Deal Value",
                        f"{avg_deal_value:,.0f}",
                        pct_diff(avg_deal_value, prev_avg_deal_value)
                    )

                    colKPI5, colKPI6, colKPI7, colKPI8 = st.columns(4)
                    colKPI5.metric(
                        "New Customers",
                        f"{new_customers}",
                        pct_diff(new_customers, prev_new_customers)
                    )
                    colKPI6.metric(
                        "Returning Customers",
                        f"{returning_customers}",
                        pct_diff(returning_customers, prev_returning_customers)
                    )
                    colKPI7.metric(
                        "Avg. Nights",
                        f"{avg_nights:.2f}",
                        pct_diff(avg_nights, prev_avg_nights)
                    )
                    colKPI8.metric(
                        "Extention Rate",
                        f"{extention_rate:.2f}%",
                        pct_diff(extention_rate, prev_extention_rate)
                    )

                    st.write("---")

                    # Outlier Detection
                    st.markdown("**Outlier Detection in Deal Values**")
                    deals_df = channel_data_success[[DEALVALUE,DEALDONEDATE,CUSTOMERID,'nights',PURCHASETYPE,'VIP Status']].copy()
                    deals_df.dropna(subset=[DEALVALUE], inplace=True)
                    if len(deals_df) > 5:
                        q1, q3 = np.percentile(deals_df[DEALVALUE], [25,75])
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        outliers = deals_df[(deals_df[DEALVALUE] < lower_bound) | (deals_df[DEALVALUE] > upper_bound)]
                        if not outliers.empty:
                            st.write(f"Detected {len(outliers)} outlier deal(s). Below is the table of those outlier deals:")
                            st.write(outliers)
                        else:
                            st.write("No outliers detected in deal values.")
                    else:
                        st.info("Not enough data to detect outliers reliably.")

                    if channel_data_success.empty:
                        st.warning("No successful deals found for the selected channel and date range.")
                    else:
                        # RFM distribution
                        channel_customer_ids = channel_data_success[CUSTOMERID].unique()
                        channel_rfm_data = rfm_data[rfm_data['Code'].isin(channel_customer_ids)]
                        if channel_rfm_data.empty:
                            st.warning("No RFM data available for the selected channel and VIP statuses.")
                        else:
                            # Cluster distribution (frequency)
                            cluster_counts = channel_rfm_data['RFM_segment_label'].value_counts().reset_index()
                            cluster_counts.columns = ['RFM_segment_label', 'Count']
                            fig_channel_freq = px.bar(
                                cluster_counts,
                                x='RFM_segment_label',
                                y='Count',
                                title="Cluster Distribution (Frequency)",
                                labels={'RFM_segment_label': 'RFM Segment','Count': 'Number of Customers'},
                                text='Count',
                                color='RFM_segment_label',
                                color_discrete_sequence=px.colors.qualitative.Set1
                            )
                            fig_channel_freq.update_traces(textposition='outside')
                            st.plotly_chart(fig_channel_freq)

                            # Cluster distribution (monetary)
                            channel_monetary = channel_rfm_data.groupby('RFM_segment_label')['Monetary'].sum().reset_index()
                            fig_channel_monetary = px.bar(
                                channel_monetary,
                                x='RFM_segment_label',
                                y='Monetary',
                                title="Cluster Distribution (Monetary)",
                                labels={'RFM_segment_label': 'RFM Segment','Monetary': 'Total Monetary Value'},
                                text='Monetary',
                                color='RFM_segment_label',
                                color_discrete_sequence=px.colors.qualitative.Set1
                            )
                            fig_channel_monetary.update_traces(textposition='outside')
                            st.plotly_chart(fig_channel_monetary)

                        st.subheader("Customer Details")
                        channel_nights = channel_data_success.groupby(CUSTOMERID)['nights'].sum().reset_index()
                        channel_nights.rename(columns={CUSTOMERID: 'Code','nights': 'Total Nights'}, inplace=True)
                        if 'Code' in rfm_data.columns:
                            customer_details = rfm_data[['Code','Name','Phone Number','VIP Status','Recency','Frequency','Monetary','average stay','Is staying']].copy()
                            if 'RFM_segment_label' in rfm_data.columns:
                                customer_details['RFM_segment_label'] = rfm_data['RFM_segment_label']
                        else:
                            customer_details = pd.DataFrame()

                        if not customer_details.empty:
                            customer_details = customer_details.merge(channel_nights, on='Code', how='right').fillna(0)
                        else:
                            customer_details = channel_nights

                        st.write(customer_details)
                        csv_data = convert_df(customer_details)
                        excel_data = convert_df_to_excel(customer_details)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(label="Download data as CSV", data=csv_data, file_name='channel_analysis.csv', mime='text/csv')
                        with col2:
                            st.download_button(label="Download data as Excel", data=excel_data, file_name='channel_analysis.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                        # Time Series
                        st.subheader("Time Series Analysis of Sales")
                        daily_df = st.session_state.single_channel_daily_df
                        if daily_df is None or daily_df.empty:
                            st.info("No time-series data available for this channel.")
                        else:
                            days_in_range = (end_date - start_date).days + 1
                            kpi_options = ['Total Deals','Successful Deals','New Customers','Returning Customers','Average Deal Value','Average Nights']
                            selected_kpis_to_plot = st.multiselect(
                                "Select KPI(s) to Plot:", 
                                kpi_options, 
                                default=['Total Deals','Successful Deals'], 
                                key='single_channel_ts_kpis'
                            )
                            if selected_kpis_to_plot:
                                for c in selected_kpis_to_plot:
                                    df_p = daily_df[['Date', c]].copy()
                                    df_p.sort_values('Date', inplace=True)
                                    if days_in_range < 60:
                                        df_p[c+'_7d_MA'] = df_p[c].rolling(7).mean()
                                        fig_ts = px.line(
                                            df_p,
                                            x='Date',
                                            y=[c, c+'_7d_MA'],
                                            title=f"Time Series of {c} (with 7 day MA)",
                                            labels={'value': f"{c}"},
                                            color_discrete_sequence=px.colors.qualitative.Set1
                                        )
                                    else:
                                        df_p[c+'_30d_MA'] = df_p[c].rolling(30).mean()
                                        fig_ts = px.line(
                                            df_p,
                                            x='Date',
                                            y=[c, c+'_30d_MA'],
                                            title=f"Time Series of {c} (with 30 day MA)",
                                            labels={'value': f"{c}"},
                                            color_discrete_sequence=px.colors.qualitative.Set1
                                        )
                                    st.plotly_chart(fig_ts)

            ###########################################################################
            #  COMPARE TWO CHANNELS
            ###########################################################################
            with tabs[1]:
                st.markdown("### Compare Two Channels")

                vip_options_compare_two = sorted(rfm_data['VIP Status'].unique())
                select_all_vips_compare_two = st.checkbox("Select all VIP statuses", value=True, key='select_all_vips_channel_compare_two')
                if select_all_vips_compare_two:
                    selected_vips_channel_compare_two = vip_options_compare_two
                else:
                    selected_vips_channel_compare_two = st.multiselect(
                        "Select VIP Status:",
                        options=vip_options_compare_two,
                        default=[],
                        key='vips_multiselect_channel_compare_two'
                    )

                with st.form(key='compare_two_channels_form', clear_on_submit=False):
                    two_channels = st.multiselect("Select Two Channels:", options=sale_channels_options, max_selections=2, key='two_channels_select')
                    min_date_compare = data[DEALCREATEDDATE].min()
                    max_date_compare = data[DEALCREATEDDATE].max()
                    if pd.isna(min_date_compare) or pd.isna(max_date_compare):
                        st.warning("Date range is invalid. Please check your data.")
                        st.stop()

                    min_date_compare = min_date_compare.date()
                    max_date_compare = max_date_compare.date()

                    start_date_compare = st.date_input("Start Date", value=min_date_compare, min_value=min_date_compare, max_value=max_date_compare, key='compare_two_channel_start_date')
                    end_date_compare = st.date_input("End Date", value=max_date_compare, min_value=min_date_compare, max_value=max_date_compare, key='compare_two_channel_end_date')

                    compare_kpi_options = [
                        'Total Deals','Successful Deals','Average Deal Value','Average Nights',
                        'Extension Rate','New Customers','Returning Customers'
                    ]
                    selected_compare_kpis = st.multiselect(
                        "Select KPI(s) to Plot",
                        compare_kpi_options,
                        default=['Average Deal Value','Extension Rate'],
                        key='compare_two_channels_kpis'
                    )
                    apply_compare_two = st.form_submit_button(label='Compare')

                if "two_channels_results" not in st.session_state:
                    st.session_state.two_channels_results = None
                    st.session_state.two_channels_tsdata = None

                if apply_compare_two:
                    if len(two_channels) == 2:
                        if selected_vips_channel_compare_two:
                            ch1 = two_channels[0]
                            ch2 = two_channels[1]

                            df_ch1 = data[
                                (data[DEALSOURCE] == ch1) &
                                (data[DEALCREATEDDATE] >= pd.to_datetime(start_date_compare)) &
                                (data[DEALCREATEDDATE] <= pd.to_datetime(end_date_compare)) &
                                (data['VIP Status'].isin(selected_vips_channel_compare_two))
                            ]
                            df_ch2 = data[
                                (data[DEALSOURCE] == ch2) &
                                (data[DEALCREATEDDATE] >= pd.to_datetime(start_date_compare)) &
                                (data[DEALCREATEDDATE] <= pd.to_datetime(end_date_compare)) &
                                (data['VIP Status'].isin(selected_vips_channel_compare_two))
                            ]
                            df_ch1_success = df_ch1[df_ch1[DEALSTATUS] == 'Won']
                            df_ch2_success = df_ch2[df_ch2[DEALSTATUS] == 'Won']

                            def kpi_calc(df_all, df_succ):
                                td = len(df_all)
                                sd = len(df_succ)
                                avgv = df_succ[DEALVALUE].mean() if not df_succ.empty else 0
                                nights_ = df_succ['nights'].mean() if not df_succ.empty else 0
                                ext = df_succ[df_succ[PURCHASETYPE] == 'تمدید']
                                ext_count = len(ext)
                                ex_rate = (ext_count/sd*100) if sd>0 else 0
                                nw = 0
                                rt = 0
                                if not df_succ.empty:
                                    earliest_global = global_first_deal_date_series_channels.to_dict()
                                    for cid_ in df_succ[CUSTOMERID].unique():
                                        fd_ = earliest_global.get(cid_, pd.NaT)
                                        if not pd.isna(fd_):
                                            if start_date_compare <= fd_.date() <= end_date_compare:
                                                nw += 1
                                            elif fd_.date() < start_date_compare:
                                                rt += 1
                                return {
                                    'Channel': (df_all[DEALSOURCE].iloc[0] if not df_all.empty else ""),
                                    'Total Deals': td,
                                    'Successful Deals': sd,
                                    'Average Deal Value': avgv,
                                    'Average Nights': nights_,
                                    'Extension Rate': ex_rate,
                                    'New Customers': nw,
                                    'Returning Customers': rt
                                }

                            ch1_stats = kpi_calc(df_ch1, df_ch1_success)
                            ch2_stats = kpi_calc(df_ch2, df_ch2_success)

                            st.session_state.two_channels_results = (ch1_stats, ch2_stats)

                            if not df_ch1_success.empty:
                                df_ch1_success = df_ch1_success.copy()
                                df_ch1_success['Channel'] = ch1
                            if not df_ch2_success.empty:
                                df_ch2_success = df_ch2_success.copy()
                                df_ch2_success['Channel'] = ch2
                            combined_success = pd.concat([df_ch1_success, df_ch2_success], ignore_index=True)
                            st.session_state.two_channels_tsdata = combined_success
                        else:
                            st.warning("Please select at least one VIP status.")
                    else:
                        st.warning("Please select exactly two channels.")

                if st.session_state.two_channels_results is not None:
                    ch1_res, ch2_res = st.session_state.two_channels_results
                    if ch1_res['Channel'] and ch2_res['Channel']:
                        st.markdown("### Comparison KPIs")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**{ch1_res['Channel']}**")
                            st.metric("Total Deals", f"{ch1_res['Total Deals']}")
                            st.metric("Successful Deals", f"{ch1_res['Successful Deals']}")
                            st.metric("Average Deal Value", f"{ch1_res['Average Deal Value']:.0f}")
                            st.metric("Average Nights", f"{ch1_res['Average Nights']:.2f}")
                            st.metric("Extension Rate (%)", f"{ch1_res['Extension Rate']:.2f}%")
                            st.metric("New Customers", f"{ch1_res['New Customers']}")
                            st.metric("Returning Customers", f"{ch1_res['Returning Customers']}")
                        with c2:
                            st.markdown(f"**{ch2_res['Channel']}**")
                            st.metric("Total Deals", f"{ch2_res['Total Deals']}")
                            st.metric("Successful Deals", f"{ch2_res['Successful Deals']}")
                            st.metric("Average Deal Value", f"{ch2_res['Average Deal Value']:.0f}")
                            st.metric("Average Nights", f"{ch2_res['Average Nights']:.2f}")
                            st.metric("Extension Rate (%)", f"{ch2_res['Extension Rate']:.2f}%")
                            st.metric("New Customers", f"{ch2_res['New Customers']}")
                            st.metric("Returning Customers", f"{ch2_res['Returning Customers']}")

                        st.write("---")
                        st.markdown("**Direct Comparison of Each KPI**")

                        # We'll normalize each KPI for side-by-side
                        comp_data = [
                            {'KPI':'Total Deals','Channel':ch1_res['Channel'],'Value': ch1_res['Total Deals']},
                            {'KPI':'Total Deals','Channel':ch2_res['Channel'],'Value': ch2_res['Total Deals']},
                            {'KPI':'Successful Deals','Channel':ch1_res['Channel'],'Value': ch1_res['Successful Deals']},
                            {'KPI':'Successful Deals','Channel':ch2_res['Channel'],'Value': ch2_res['Successful Deals']},
                            {'KPI':'Average Deal Value','Channel':ch1_res['Channel'],'Value': ch1_res['Average Deal Value']},
                            {'KPI':'Average Deal Value','Channel':ch2_res['Channel'],'Value': ch2_res['Average Deal Value']},
                            {'KPI':'Average Nights','Channel':ch1_res['Channel'],'Value': ch1_res['Average Nights']},
                            {'KPI':'Average Nights','Channel':ch2_res['Channel'],'Value': ch2_res['Average Nights']},
                            {'KPI':'Extension Rate','Channel':ch1_res['Channel'],'Value': ch1_res['Extension Rate']},
                            {'KPI':'Extension Rate','Channel':ch2_res['Channel'],'Value': ch2_res['Extension Rate']},
                            {'KPI':'New Customers','Channel':ch1_res['Channel'],'Value': ch1_res['New Customers']},
                            {'KPI':'New Customers','Channel':ch2_res['Channel'],'Value': ch2_res['New Customers']},
                            {'KPI':'Returning Customers','Channel':ch1_res['Channel'],'Value': ch1_res['Returning Customers']},
                            {'KPI':'Returning Customers','Channel':ch2_res['Channel'],'Value': ch2_res['Returning Customers']},
                        ]
                        comp_df_side = pd.DataFrame(comp_data)

                        # For each KPI, normalize
                        comp_df_list = []
                        for kpi_name in comp_df_side['KPI'].unique():
                            sub = comp_df_side[comp_df_side['KPI'] == kpi_name].copy()
                            max_val = sub['Value'].max()
                            if max_val == 0:
                                sub['Normalized Value'] = 0
                            else:
                                sub['Normalized Value'] = sub['Value']/max_val
                            comp_df_list.append(sub)
                        comp_df_side_final = pd.concat(comp_df_list, ignore_index=True)

                        fig_kpi_compare = px.bar(
                            comp_df_side_final,
                            x='KPI',
                            y='Normalized Value',
                            color='Channel',
                            barmode='group',
                            color_discrete_sequence=px.colors.qualitative.Set1,
                            title="Side-by-Side KPI Comparison (Normalized)"
                        )
                        fig_kpi_compare.update_traces(
                            hovertemplate='<b>KPI</b>: %{x}<br><b>Channel</b>: %{color}<br>Value: %{customdata[0]}<extra></extra>',
                            customdata=np.expand_dims(comp_df_side_final['Value'], axis=1)
                        )
                        st.plotly_chart(fig_kpi_compare)

                # Time-Series
                if (
                    'two_channels_tsdata' in st.session_state and
                    st.session_state.two_channels_tsdata is not None and
                    not st.session_state.two_channels_tsdata.empty and
                    selected_compare_kpis
                ):
                    ts_df = st.session_state.two_channels_tsdata.copy()
                    ts_df['Date'] = pd.to_datetime(ts_df[DEALDONEDATE], errors='coerce')
                    ts_df.dropna(subset=['Date'], inplace=True)

                    st.markdown("### Time Series Comparison (Each KPI in its own plot)")
                    days_in_range_compare = (end_date_compare - start_date_compare).days + 1

                    existing_channels_in_ts = ts_df['Channel'].unique()

                    # color pairs
                    # fallback if channels not found in mapping
                    def get_channel_colors(chname):
                        color_pairs = {
                            ch1_res['Channel'] if ch1_res else 'ChannelA': ('#d62728','#ffa09e'),  # bold red, pastel red
                            ch2_res['Channel'] if ch2_res else 'ChannelB': ('#1f77b4','#aec7e8'),  # bold blue, pastel
                        }
                        return color_pairs.get(chname, ('#2ca02c','#98df8a'))

                    for k in selected_compare_kpis:
                        day_list = pd.date_range(start=start_date_compare, end=end_date_compare, freq='D')
                        daily_list = []
                        earliest_global = global_first_deal_date_series_channels.to_dict()
                        sub_columns = ts_df[['Date','Channel',CUSTOMERID,DEALVALUE,PURCHASETYPE,'nights']].copy()

                        for dday in day_list:
                            day_sub = sub_columns[sub_columns['Date'].dt.date == dday.date()]
                            for ch_ in day_sub['Channel'].unique():
                                sub2 = day_sub[day_sub['Channel'] == ch_]
                                val = 0
                                if k == 'Average Deal Value':
                                    val = sub2[DEALVALUE].sum()/len(sub2) if len(sub2)>0 else 0
                                elif k == 'Extension Rate':
                                    ex_cnt = len(sub2[sub2[PURCHASETYPE]=='تمدید'])
                                    tot_cnt = len(sub2)
                                    val = (ex_cnt/tot_cnt*100) if tot_cnt>0 else 0
                                elif k == 'Average Nights':
                                    val = sub2['nights'].mean() if len(sub2)>0 else 0
                                elif k == 'Total Deals':
                                    val = len(sub2)
                                elif k == 'Successful Deals':
                                    val = len(sub2)
                                elif k == 'New Customers':
                                    newC = 0
                                    for cid_ in sub2[CUSTOMERID].unique():
                                        fdate = earliest_global.get(cid_, pd.NaT)
                                        if not pd.isna(fdate) and fdate.date() == dday.date():
                                            newC += 1
                                    val = newC
                                elif k == 'Returning Customers':
                                    retC = 0
                                    for cid_ in sub2[CUSTOMERID].unique():
                                        fdate = earliest_global.get(cid_, pd.NaT)
                                        if not pd.isna(fdate) and fdate.date() < dday.date():
                                            retC += 1
                                    val = retC

                                daily_list.append({
                                    'Date': dday,
                                    'Channel': ch_,
                                    'Value': val
                                })
                            # fill missing channel with 0
                            for ch_ in existing_channels_in_ts:
                                if ch_ not in day_sub['Channel'].unique():
                                    daily_list.append({'Date': dday, 'Channel': ch_, 'Value': 0})

                        daily_k_df = pd.DataFrame(daily_list)
                        daily_k_df.sort_values(['Channel','Date'], inplace=True)

                        if days_in_range_compare < 60:
                            daily_k_df['MA'] = daily_k_df.groupby('Channel')['Value'].transform(lambda x: x.rolling(7).mean())
                            nameMA = '7d MA'
                        else:
                            daily_k_df['MA'] = daily_k_df.groupby('Channel')['Value'].transform(lambda x: x.rolling(30).mean())
                            nameMA = '30d MA'

                        fig_ts = go.Figure()
                        fig_ts.update_layout(
                            title=f"{k} Over Time",
                            xaxis_title="Date",
                            yaxis_title=f"{k}"
                        )

                        for ch_ in daily_k_df['Channel'].unique():
                            sub_ch = daily_k_df[daily_k_df['Channel'] == ch_]
                            raw_color, pastel_color = get_channel_colors(ch_)

                            fig_ts.add_trace(go.Scatter(
                                x=sub_ch['Date'],
                                y=sub_ch['Value'],
                                mode='lines+markers',
                                name=f"{ch_} - raw {k}",
                                line=dict(color=raw_color, width=2),
                                marker=dict(color=raw_color, size=5)
                            ))
                            fig_ts.add_trace(go.Scatter(
                                x=sub_ch['Date'],
                                y=sub_ch['MA'],
                                mode='lines',
                                name=f"{ch_} - {nameMA}",
                                line=dict(color=pastel_color, width=3, dash='dot')
                            ))

                        st.plotly_chart(fig_ts)

            ###########################################################################
            #  COMPARE ALL CHANNELS
            ###########################################################################
            with tabs[2]:
                st.markdown("### Compare All Channels")

                vip_options_compare_all = sorted(rfm_data['VIP Status'].unique())
                select_all_vips_compare_all = st.checkbox("Select all VIP statuses", value=True, key='select_all_vips_channel_compare_all')
                if select_all_vips_compare_all:
                    selected_vips_channel_compare_all = vip_options_compare_all
                else:
                    selected_vips_channel_compare_all = st.multiselect(
                        "Select VIP Status:",
                        options=vip_options_compare_all,
                        default=[],
                        key='vips_multiselect_channel_compare_all'
                    )

                with st.form(key='compare_all_channels_form', clear_on_submit=False):
                    min_date_all = data[DEALCREATEDDATE].min()
                    max_date_all = data[DEALCREATEDDATE].max()
                    if pd.isna(min_date_all) or pd.isna(max_date_all):
                        st.warning("Date range is invalid. Please check your data.")
                        st.stop()

                    min_date_all = min_date_all.date()
                    max_date_all = max_date_all.date()

                    start_date_all = st.date_input("Start Date", value=min_date_all, min_value=min_date_all, max_value=max_date_all, key='compare_all_channel_start_date')
                    end_date_all = st.date_input("End Date", value=max_date_all, min_value=min_date_all, max_value=max_date_all, key='compare_all_channel_end_date')
                    apply_compare_all = st.form_submit_button(label='Compare All Channels')

                if "compare_all_channels_results" not in st.session_state:
                    st.session_state.compare_all_channels_results = None

                if apply_compare_all:
                    if selected_vips_channel_compare_all:
                        all_channels_data = data[
                            (data[DEALCREATEDDATE] >= pd.to_datetime(start_date_all)) &
                            (data[DEALCREATEDDATE] <= pd.to_datetime(end_date_all)) &
                            (data['VIP Status'].isin(selected_vips_channel_compare_all))
                        ]
                        if all_channels_data.empty:
                            st.warning("No deals found for the selected VIP statuses in the specified date range.")
                        else:
                            channels_list = all_channels_data[DEALSOURCE].dropna().unique().tolist()
                            final_rows = []
                            for ch_ in channels_list:
                                sel_df = all_channels_data[all_channels_data[DEALSOURCE] == ch_]
                                sel_suc = sel_df[sel_df[DEALSTATUS] == 'Won']
                                td_ = len(sel_df)
                                sd_ = len(sel_suc)
                                sr_ = (sd_/td_)*100 if td_>0 else 0
                                av_ = sel_suc[DEALVALUE].mean() if not sel_suc.empty else 0
                                ni_ = sel_suc['nights'].mean() if not sel_suc.empty else 0
                                ex_ = sel_suc[sel_suc[PURCHASETYPE] == 'تمدید']
                                ex_cnt_ = len(ex_)
                                ex_rate_ = (ex_cnt_/sd_*100) if sd_>0 else 0
                                n_c = 0
                                r_c = 0
                                if not sel_suc.empty:
                                    for cc in sel_suc[CUSTOMERID].unique():
                                        fd = global_first_deal_date_series_channels.get(cc, pd.NaT)
                                        if not pd.isna(fd):
                                            if start_date_all <= fd.date() <= end_date_all:
                                                n_c += 1
                                            elif fd.date() < start_date_all:
                                                r_c += 1
                                final_rows.append({
                                    'Sale Channel': ch_,
                                    'Total Deals': td_,
                                    'Successful Deals': sd_,
                                    'Success Rate': sr_,
                                    'Avg Deal Value': av_,
                                    'Avg Nights': ni_,
                                    'Extension Rate': ex_rate_,
                                    'New Customers': n_c,
                                    'Returning Customers': r_c
                                })
                            comp_df = pd.DataFrame(final_rows)
                            st.session_state.compare_all_channels_results = comp_df
                    else:
                        st.warning("Please select at least one VIP status.")

                if st.session_state.compare_all_channels_results is not None and not st.session_state.compare_all_channels_results.empty:
                    comp_df = st.session_state.compare_all_channels_results
                    st.write("### All Channels Comparison")
                    st.write(comp_df)

                    c_csv = convert_df(comp_df)
                    c_excel = convert_df_to_excel(comp_df)
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.download_button(label="Download as CSV", data=c_csv, file_name='all_channels_comparison.csv', mime='text/csv')
                    with cc2:
                        st.download_button(label="Download as Excel", data=c_excel, file_name='all_channels_comparison.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                    if not comp_df.empty:
                        fig_all_channels_sd = px.bar(
                            comp_df,
                            x='Sale Channel',
                            y='Successful Deals',
                            title="Successful Deals by Channel",
                            text='Successful Deals',
                            color='Sale Channel',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_all_channels_sd.update_traces(textposition='outside')
                        st.plotly_chart(fig_all_channels_sd)

                        fig_all_channels_val = px.bar(
                            comp_df,
                            x='Sale Channel',
                            y='Avg Deal Value',
                            title="Average Deal Value by Channel",
                            text='Avg Deal Value',
                            color='Sale Channel',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_all_channels_val.update_traces(textposition='outside')
                        st.plotly_chart(fig_all_channels_val)

                        fig_all_channels_sr = px.bar(
                            comp_df,
                            x='Sale Channel',
                            y='Success Rate',
                            title="Success Rate (%) by Channel",
                            text='Success Rate',
                            color='Sale Channel',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_all_channels_sr.update_traces(textposition='outside')
                        st.plotly_chart(fig_all_channels_sr)

                        fig_all_ext = px.bar(
                            comp_df,
                            x='Sale Channel',
                            y='Extension Rate',
                            title="Extension Rate (%) by Channel",
                            text='Extension Rate',
                            color='Sale Channel',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_all_ext.update_traces(textposition='outside')
                        st.plotly_chart(fig_all_ext)

                        # Show separate box plots for each metric
                        st.markdown("#### Separate Box Plots for Key Metrics")
                        for metric in ['Avg Deal Value','Avg Nights','Success Rate','Extension Rate']:
                            bx_df = comp_df[['Sale Channel', metric]].copy()
                            fig_box = px.box(
                                bx_df,
                                x='Sale Channel',
                                y=metric,
                                color='Sale Channel',
                                color_discrete_sequence=px.colors.qualitative.Set1,
                                title=f"Box Plot of {metric} by Channel"
                            )
                            st.plotly_chart(fig_box)

            ###########################################################################
            #  RFM SALES ANALYSIS (for Channels)
            ###########################################################################
            with tabs[3]:
                st.markdown("### RFM Sales Analysis by Channel")

                select_all_clusters_channel = st.checkbox("Select all clusters", value=True, key='select_all_clusters_channel_analysis')
                if 'RFM_segment_label' in rfm_data.columns:
                    channel_cluster_options = sorted(rfm_data['RFM_segment_label'].unique().tolist())
                else:
                    channel_cluster_options = []

                if select_all_clusters_channel:
                    selected_clusters_channel = channel_cluster_options
                else:
                    selected_clusters_channel = st.multiselect(
                        "Select Clusters:",
                        options=channel_cluster_options,
                        default=[],
                        key='clusters_multiselect_channel_analysis'
                    )

                vip_options_page_cluster = sorted(rfm_data['VIP Status'].unique())
                select_all_vips_page_cluster = st.checkbox("Select all VIP statuses", value=True, key='select_all_vips_channel_cluster_analysis')
                if select_all_vips_page_cluster:
                    selected_vips_channel_cluster = vip_options_page_cluster
                else:
                    selected_vips_channel_cluster = st.multiselect(
                        "Select VIP Status:",
                        options=vip_options_page_cluster,
                        default=[],
                        key='vips_multiselect_channel_cluster_analysis'
                    )

                with st.form(key='channel_cluster_form', clear_on_submit=False):
                    min_date = data[DEALCREATEDDATE].min()
                    max_date = data[DEALCREATEDDATE].max()
                    if pd.isna(min_date) or pd.isna(max_date):
                        st.warning("Date range is invalid. Please check your data.")
                        st.stop()

                    min_date = min_date.date()
                    max_date = max_date.date()

                    start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date, key='channel_cluster_start_date')
                    end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date, key='channel_cluster_end_date')

                    apply_cluster_filters = st.form_submit_button(label='Apply Filters')

                if "channel_rfm_sales_data" not in st.session_state:
                    st.session_state.channel_rfm_sales_data = None
                    st.session_state.channel_rfm_sales_kpis = None

                if apply_cluster_filters:
                    if len(selected_clusters_channel) == 0:
                        st.warning("Please select at least one cluster (or ensure RFM_segment_label is present).")
                        st.session_state.channel_rfm_sales_data = None
                        st.session_state.channel_rfm_sales_kpis = None
                    else:
                        if selected_vips_channel_cluster:
                            date_filtered_data_all = data[
                                (data[DEALCREATEDDATE] >= pd.to_datetime(start_date)) &
                                (data[DEALCREATEDDATE] <= pd.to_datetime(end_date))
                            ]
                            if 'RFM_segment_label' not in rfm_data.columns:
                                st.error("RFM_segment_label column not found in rfm_data. Cannot filter by cluster.")
                                st.session_state.channel_rfm_sales_data = None
                                st.session_state.channel_rfm_sales_kpis = None
                            else:
                                cluster_customers = rfm_data[rfm_data['RFM_segment_label'].isin(selected_clusters_channel)]['Code'].unique()
                                cluster_deals_all = date_filtered_data_all[
                                    date_filtered_data_all[CUSTOMERID].isin(cluster_customers) &
                                    date_filtered_data_all['VIP Status'].isin(selected_vips_channel_cluster)
                                ]
                                if cluster_deals_all.empty:
                                    st.warning("No deals found for the selected clusters and VIP statuses in the specified date range.")
                                    st.session_state.channel_rfm_sales_data = None
                                    st.session_state.channel_rfm_sales_kpis = None
                                else:
                                    channel_deals = cluster_deals_all[cluster_deals_all[DEALSTATUS] == 'Won']
                                    total_deals = len(cluster_deals_all)
                                    successful_deals_count = len(channel_deals)
                                    success_rate = (successful_deals_count / total_deals)*100 if total_deals>0 else 0
                                    new_customers = 0
                                    returning_customers = 0
                                    if not channel_deals.empty:
                                        unique_customers = channel_deals[CUSTOMERID].unique()
                                        for cid in unique_customers:
                                            first_deal_date = global_first_deal_date_series_channels.get(cid, pd.NaT)
                                            if pd.isna(first_deal_date):
                                                continue
                                            if start_date <= first_deal_date.date() <= end_date:
                                                new_customers += 1
                                            elif first_deal_date.date() < start_date:
                                                returning_customers += 1

                                    avg_deal_value = channel_deals[DEALVALUE].mean() if not channel_deals.empty else 0
                                    avg_nights = channel_deals['nights'].mean() if not channel_deals.empty else 0
                                    channel_extentions = channel_deals[channel_deals[PURCHASETYPE] == 'تمدید']
                                    channel_extentions_count = len(channel_extentions)
                                    channel_extention_rate = (channel_extentions_count / successful_deals_count*100) if successful_deals_count>0 else 0

                                    prev_length = (end_date - start_date).days + 1
                                    prev_end = start_date - timedelta(days=1)
                                    prev_start = prev_end - timedelta(days=prev_length - 1)
                                    prev_data_all = data[
                                        (data[DEALDONEDATE] >= pd.to_datetime(prev_start)) &
                                        (data[DEALDONEDATE] <= pd.to_datetime(prev_end))
                                    ]
                                    prev_data_all = prev_data_all[
                                        prev_data_all[CUSTOMERID].isin(cluster_customers) &
                                        prev_data_all['VIP Status'].isin(selected_vips_channel_cluster)
                                    ]
                                    prev_deals = prev_data_all[prev_data_all[DEALSTATUS] == 'Won']
                                    if not prev_data_all.empty:
                                        ptd = len(prev_data_all)
                                        psd = len(prev_deals)
                                        psr = (psd / ptd)*100 if ptd>0 else 0
                                        pav = prev_deals[DEALVALUE].mean() if not prev_deals.empty else 0
                                        pni = prev_deals['nights'].mean() if not prev_deals.empty else 0
                                        pext = prev_deals[prev_deals[PURCHASETYPE] == 'تمدید']
                                        pext_cnt = len(pext)
                                        pext_rate = (pext_cnt/psd*100) if psd>0 else 0
                                        pnew_c = 0
                                        pret_c = 0
                                        if not prev_deals.empty:
                                            for p_cid in prev_deals[CUSTOMERID].unique():
                                                fd = global_first_deal_date_series_channels.get(p_cid, pd.NaT)
                                                if not pd.isna(fd):
                                                    if prev_start <= fd.date() <= prev_end:
                                                        pnew_c += 1
                                                    elif fd.date() < prev_start:
                                                        pret_c += 1
                                    else:
                                        ptd = 0
                                        psd = 0
                                        psr = 0
                                        pav = 0
                                        pni = 0
                                        pext_rate = 0
                                        pnew_c = 0
                                        pret_c = 0

                                    st.session_state.channel_rfm_sales_data = channel_deals.copy()
                                    st.session_state.channel_rfm_sales_kpis = {
                                        'total_deals': total_deals,
                                        'successful_deals_count': successful_deals_count,
                                        'success_rate': success_rate,
                                        'avg_deal_value': avg_deal_value,
                                        'avg_nights': avg_nights,
                                        'channel_extention_rate': channel_extention_rate,
                                        'new_customers': new_customers,
                                        'returning_customers': returning_customers,
                                        'ptd': ptd,
                                        'psd': psd,
                                        'psr': psr,
                                        'pav': pav,
                                        'pni': pni,
                                        'pext_rate': pext_rate,
                                        'pnew_c': pnew_c,
                                        'pret_c': pret_c
                                    }
                        else:
                            st.warning("Please select at least one VIP status.")

                if st.session_state.channel_rfm_sales_data is not None and st.session_state.channel_rfm_sales_kpis is not None:
                    channel_deals = st.session_state.channel_rfm_sales_data
                    kpis = st.session_state.channel_rfm_sales_kpis

                    def pdiff(x, y):
                        if y == 0:
                            return None
                        return f"{((x-y)/abs(y)*100):.2f}%"

                    total_deals = kpis['total_deals']
                    successful_deals_count = kpis['successful_deals_count']
                    success_rate = kpis['success_rate']
                    avg_deal_value = kpis['avg_deal_value']
                    avg_nights = kpis['avg_nights']
                    channel_extention_rate = kpis['channel_extention_rate']
                    new_customers = kpis['new_customers']
                    returning_customers = kpis['returning_customers']
                    ptd = kpis['ptd']
                    psd = kpis['psd']
                    psr = kpis['psr']
                    pav = kpis['pav']
                    pni = kpis['pni']
                    pext_rate = kpis['pext_rate']
                    pnew_c = kpis['pnew_c']
                    pret_c = kpis['pret_c']

                    colKPI1, colKPI2, colKPI3, colKPI4 = st.columns(4)
                    colKPI1.metric(
                        "Total Deals", 
                        f"{total_deals}", 
                        pdiff(total_deals, ptd)
                    )
                    colKPI2.metric(
                        "Successful Deals", 
                        f"{successful_deals_count}",
                        pdiff(successful_deals_count, psd)
                    )
                    colKPI3.metric(
                        "Success Rate (%)",
                        f"{success_rate:.2f}%",
                        pdiff(success_rate, psr)
                    )
                    colKPI4.metric(
                        "Avg. Deal Value",
                        f"{avg_deal_value:,.0f}",
                        pdiff(avg_deal_value, pav)
                    )

                    colKPI5, colKPI6, colKPI7, colKPI8 = st.columns(4)
                    colKPI5.metric(
                        "New Customers",
                        f"{new_customers}",
                        pdiff(new_customers, pnew_c)
                    )
                    colKPI6.metric(
                        "Returning Customers",
                        f"{returning_customers}",
                        pdiff(returning_customers, pret_c)
                    )
                    colKPI7.metric(
                        "Avg. Nights",
                        f"{avg_nights:.2f}",
                        pdiff(avg_nights, pni)
                    )
                    colKPI8.metric(
                        "Extention Rate",
                        f"{channel_extention_rate:.2f}%",
                        pdiff(channel_extention_rate, pext_rate)
                    )

                    st.write("---")
                    if channel_deals.empty:
                        st.warning("No successful deals found for these clusters in the specified date range.")
                    else:
                        seller_counts = channel_deals[DEALOWNER].value_counts().reset_index()
                        seller_counts.columns = ['Seller','Count']
                        fig_seller_channel_freq = px.bar(
                            seller_counts,
                            x='Seller',
                            y='Count',
                            title="Seller Distribution (Frequency)",
                            labels={'Seller': 'Seller','Count': 'Number of Deals'},
                            text='Count',
                            color='Seller',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_seller_channel_freq.update_traces(textposition='outside')
                        st.plotly_chart(fig_seller_channel_freq)

                        seller_monetary = channel_deals.groupby(DEALOWNER)[DEALVALUE].sum().reset_index()
                        seller_monetary.columns = ['Seller','Monetary']
                        fig_seller_channel_monetary = px.bar(
                            seller_monetary,
                            x='Seller',
                            y='Monetary',
                            title="Seller Distribution (Monetary)",
                            labels={'Seller': 'Seller','Monetary': 'Total Monetary Value'},
                            text='Monetary',
                            color='Seller',
                            color_discrete_sequence=px.colors.qualitative.Set1
                        )
                        fig_seller_channel_monetary.update_traces(textposition='outside')
                        st.plotly_chart(fig_seller_channel_monetary)

                        st.subheader("Successful Deals")
                        if 'RFM_segment_label' in rfm_data.columns:
                            channel_deals = channel_deals.merge(
                                rfm_data[['Code','RFM_segment_label']],
                                left_on=CUSTOMERID,
                                right_on='Code',
                                how='left'
                            )
                        if 'RFM_segment_label' in channel_deals.columns:
                            deals_table = channel_deals[[
                                'Code', 'person_name',
                                'person_mobile','VIP Status','RFM_segment_label',
                                DEALOWNER,'nights',DEALVALUE,DEALDONEDATE
                            ]]
                        else:
                            deals_table = channel_deals

                        st.write(deals_table)
                        csv_data = convert_df(deals_table)
                        excel_data = convert_df_to_excel(deals_table)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(label="Download data as CSV", data=csv_data, file_name='channel_cluster_deals.csv', mime='text/csv')
                        with col2:
                            st.download_button(label="Download data as Excel", data=excel_data, file_name='channel_cluster_deals.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                        st.subheader("Time Series Analysis of Sales")
                        channel_deals_time_df = channel_deals[[DEALDONEDATE,DEALVALUE]].copy()
                        channel_deals_time_df[DEALDONEDATE] = pd.to_datetime(channel_deals_time_df[DEALDONEDATE], errors='coerce')
                        channel_deals_time_df.dropna(subset=[DEALDONEDATE], inplace=True)
                        if channel_deals_time_df.empty:
                            st.info("No time-series data available for these clusters.")
                        else:
                            channel_deals_time_df = channel_deals_time_df.groupby(channel_deals_time_df[DEALDONEDATE].dt.date)[DEALVALUE].sum().reset_index()
                            channel_deals_time_df.rename(columns={DEALDONEDATE: 'Date',DEALVALUE: 'Sales'}, inplace=True)
                            channel_deals_time_df['Date'] = pd.to_datetime(channel_deals_time_df['Date'])
                            channel_deals_time_df.sort_values('Date', inplace=True)

                            days_in_rfm = (end_date - start_date).days + 1
                            if days_in_rfm < 60:
                                channel_deals_time_df['7d_MA'] = channel_deals_time_df['Sales'].rolling(7).mean()
                                lines_to_use = ['Sales','7d_MA']
                                chart_title = "Daily Sales Over Time (with 7-day MA)"
                            else:
                                channel_deals_time_df['30d_MA'] = channel_deals_time_df['Sales'].rolling(30).mean()
                                lines_to_use = ['Sales','30d_MA']
                                chart_title = "Daily Sales Over Time (with 30-day MA)"

                            fig_channel_time = px.line(
                                channel_deals_time_df,
                                x='Date',
                                y=lines_to_use,
                                labels={'value': 'Sales Amount'},
                                title=chart_title,
                                color_discrete_sequence=px.colors.qualitative.Set1
                            )
                            st.plotly_chart(fig_channel_time)

                            monthly_df = channel_deals_time_df[['Date','Sales']].copy()
                            monthly_df['Month'] = monthly_df['Date'].dt.to_period('M')
                            monthly_avg = monthly_df.groupby('Month')['Sales'].mean().reset_index()
                            monthly_avg['Month'] = monthly_avg['Month'].astype(str)
                            fig_channel_monthly = px.bar(
                                monthly_avg,
                                x='Month',
                                y='Sales',
                                labels={'Sales': 'Average Sales'},
                                title="Monthly Average Sales"
                            )
                            st.plotly_chart(fig_channel_monthly)

                            total_sales_time = channel_deals_time_df['Sales'].sum()
                            avg_sales_time = channel_deals_time_df['Sales'].mean()
                            colA, colB = st.columns(2)
                            with colA:
                                st.metric("Total Sales (Selected Period)", f"{total_sales_time:,.0f}")
                            with colB:
                                st.metric("Avg Daily Sales (Selected Period)", f"{avg_sales_time:,.2f}")

                ######################
                # New Channel Transitions Tab
                ######################
                with tabs[4]:
                    st.markdown("### Channel Transitions")

                    # 1) UI for selecting the initial channel and RFM clusters
                    chosen_channel = st.selectbox(
                        "Select a Sale Channel (First Reservation Channel)",
                        options=sale_channels_options
                    )

                    rfm_cluster_options = sorted(rfm_data['RFM_segment_label'].dropna().unique())
                    chosen_clusters = st.multiselect(
                        "Select RFM Clusters",
                        options=rfm_cluster_options,
                        default=rfm_cluster_options
                    )

                    if chosen_channel and chosen_clusters:
                        # Prepare the data of successful deals
                        df_success = data[data[DEALSTATUS] == 'Won'].copy()
                        df_success = df_success.sort_values(DEALDONEDATE)

                        # Find each customer's earliest successful deal
                        first_deals = (
                            df_success.groupby(CUSTOMERID)
                            .head(1)
                            .reset_index(drop=True)
                        )

                        # 1) Filter to customers whose FIRST reservation was on the chosen channel
                        #    and also whose RFM cluster is in the chosen set
                        first_channel_customers = first_deals[
                            first_deals[DEALSOURCE] == chosen_channel
                        ][CUSTOMERID].unique()

                        # Filter by chosen RFM clusters
                        # We look up the cluster in rfm_data where rfm_data["Code"] == person's code
                        cluster_matched_customers = rfm_data[
                            (rfm_data["Code"].isin(first_channel_customers))
                            & (rfm_data["RFM_segment_label"].isin(chosen_clusters))
                        ]["Code"].unique()

                        if len(cluster_matched_customers) == 0:
                            st.warning("No customers found matching both the selected channel and these RFM clusters.")
                        else:
                            # ----------  Part 1: Next reservations and their channels  ----------
                            # We want subsequent deals (beyond the first) for these customers
                            subsequent_deals = df_success[df_success[CUSTOMERID].isin(cluster_matched_customers)].copy()

                            # Attach earliest deal date so we can filter out the first deal
                            earliest_dates = (
                                df_success.groupby(CUSTOMERID)[DEALDONEDATE]
                                .min()
                                .rename("EarliestDealDate")
                            )
                            subsequent_deals = subsequent_deals.merge(
                                earliest_dates,
                                left_on=CUSTOMERID,
                                right_index=True
                            )

                            # Keep only deals strictly AFTER the first deal date
                            subsequent_deals = subsequent_deals[
                                subsequent_deals[DEALDONEDATE] > subsequent_deals["EarliestDealDate"]
                            ]

                            if subsequent_deals.empty:
                                st.info("No subsequent reservations found for those customers.")
                            else:
                                # Count how many next reservations happened on each channel
                                channel_counts = subsequent_deals[DEALSOURCE].value_counts().reset_index()
                                channel_counts.columns = ["Sale Channel", "Count"]

                                st.subheader("1) Next Reservations: Which channels were used?")
                                fig_next_reservations = px.bar(
                                    channel_counts,
                                    x="Sale Channel",
                                    y="Count",
                                    title="Subsequent Reservations by Channel",
                                    text="Count",
                                    labels={"Count": "Number of Non-First Reservations"}
                                )
                                fig_next_reservations.update_traces(textposition='outside')
                                st.plotly_chart(fig_next_reservations)

                            # ----------  Part 2: Customers’ Favorite Reservation Channel  ----------
                            # For the same group of cluster-matched customers, figure out
                            # which channel each one used the most across ALL successful deals
                            # (including the first and subsequent).

                            all_deals_for_these_customers = df_success[
                                df_success[CUSTOMERID].isin(cluster_matched_customers)
                            ].copy()

                            # Group (customer, channel) => count
                            cust_channel_counts = (
                                all_deals_for_these_customers
                                .groupby([CUSTOMERID, DEALSOURCE])
                                .size()
                                .reset_index(name="NumReservations")
                            )
                            # Sort so highest count is first, then drop duplicates
                            cust_channel_counts.sort_values(
                                [CUSTOMERID, "NumReservations"],
                                ascending=[True, False],
                                inplace=True
                            )
                            favorite_channels = cust_channel_counts.drop_duplicates(
                                subset=[CUSTOMERID], keep="first"
                            )
                            favorite_channels.rename(columns={DEALSOURCE: "FavoriteSaleChannel"}, inplace=True)

                            # Summarize how many times each channel is "favorite"
                            fav_counts = favorite_channels["FavoriteSaleChannel"].value_counts().reset_index()
                            fav_counts.columns = ["Sale Channel", "Count"]

                            st.subheader("2) Favorite Reservation Channel")
                            colA, colB = st.columns([1,1.3])

                            with colA:
                                st.markdown("#### Column Chart")
                                fig_fav_channels = px.bar(
                                    fav_counts,
                                    x="Sale Channel",
                                    y="Count",
                                    text="Count",
                                    title="Customers' Favorite Channel (Count)"
                                )
                                fig_fav_channels.update_traces(textposition='outside')
                                st.plotly_chart(fig_fav_channels)

                            with colB:
                                st.markdown("#### Detailed Table")

                                # Merge back to RFM data to get user info
                                detailed_fav = favorite_channels.merge(
                                    rfm_data,
                                    left_on=CUSTOMERID,
                                    right_on="Code",
                                    how="left"
                                )

                                # Pick relevant columns
                                columns_to_show = [
                                    "Code",
                                    "Name",
                                    "Phone Number",
                                    "VIP Status",
                                    "RFM_segment_label",
                                    "Recency",
                                    "Frequency",
                                    "Monetary",
                                    "Total Nights",
                                    "FavoriteSaleChannel"
                                ]

                                # Check if 'Total Nights' is in rfm_data (depends on your code)
                                # If not, handle gracefully:
                                if "Total Nights" not in detailed_fav.columns:
                                    # you might have "Total Nights" under a different name
                                    # or you can calculate it from deals if you want
                                    # For now, we add a placeholder if missing:
                                    detailed_fav["Total Nights"] = None

                                final_table = detailed_fav[columns_to_show].copy()

                                st.dataframe(final_table)

                                # Download buttons
                                csv_data = convert_df(final_table)
                                excel_data = convert_df_to_excel(final_table)

                                c1, c2 = st.columns(2)
                                with c1:
                                    st.download_button(
                                        label="Download (CSV)",
                                        data=csv_data,
                                        file_name="favorite_channels.csv",
                                        mime="text/csv"
                                    )
                                with c2:
                                    st.download_button(
                                        label="Download (Excel)",
                                        data=excel_data,
                                        file_name="favorite_channels.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )

                            # ----------  Part 3: Additional Interesting Data / Charts  ----------
                            # ----------  Part 3: Additional Channel Transition Insights  ----------
                            st.subheader("3) Additional Channel Transition Insights")

                            # We'll create data about how many times the chosen channel is the "from" side vs. the "to" side 
                            # of a reservation transition (in consecutive deals) among cluster_matched_customers.

                            df_cluster_success = df_success[df_success[CUSTOMERID].isin(cluster_matched_customers)].copy()
                            df_cluster_success = df_cluster_success.sort_values([CUSTOMERID, DEALDONEDATE])

                            # We will gather all consecutive (channel_i -> channel_(i+1)) transitions
                            # for these cluster-matched customers.
                            transitions = []
                            for cust_id, group_df in df_cluster_success.groupby(CUSTOMERID):
                                group_df = group_df.reset_index(drop=True)
                                for i in range(len(group_df) - 1):
                                    from_channel = group_df.loc[i, DEALSOURCE]
                                    to_channel   = group_df.loc[i+1, DEALSOURCE]
                                    if pd.notna(from_channel) and pd.notna(to_channel) and from_channel != "" and to_channel != "":
                                        transitions.append((from_channel, to_channel))

                            if not transitions:
                                st.info("No consecutive channel-to-channel transitions found among these customers.")
                            else:                                
                                # Count the total transitions for each (from -> to) pair
                                transition_counts = Counter(transitions)

                                # 1) Incoming transitions to the chosen channel
                                #    i.e., (X -> chosen_channel)
                                incoming_counts = defaultdict(int)
                                # 2) Outgoing transitions from the chosen channel
                                #    i.e., (chosen_channel -> X)
                                outgoing_counts = defaultdict(int)

                                for (from_c, to_c), cnt in transition_counts.items():
                                    if to_c == chosen_channel:
                                        incoming_counts[from_c] += cnt
                                    if from_c == chosen_channel:
                                        outgoing_counts[to_c] += cnt

                                # -------------
                                #   INCOMING
                                # -------------
                                if len(incoming_counts) > 0:
                                    st.markdown(f"#### Incoming Transitions into {chosen_channel}")
                                    incoming_df = pd.DataFrame(
                                        {"From Channel": list(incoming_counts.keys()),
                                        "Count": list(incoming_counts.values())}
                                    ).sort_values("Count", ascending=False)
                                    fig_incoming = px.bar(
                                        incoming_df,
                                        x="From Channel",
                                        y="Count",
                                        text="Count",
                                        labels={"Count": "Number of Transitions"},
                                        title=f"Incoming Transitions to {chosen_channel}"
                                    )
                                    fig_incoming.update_traces(textposition='outside')
                                    st.plotly_chart(fig_incoming)
                                    st.dataframe(incoming_df)
                                else:
                                    st.info(f"No incoming transitions from other channels to {chosen_channel} among these customers.")

                                # -------------
                                #   OUTGOING
                                # -------------
                                if len(outgoing_counts) > 0:
                                    st.markdown(f"#### Outgoing Transitions from {chosen_channel}")
                                    outgoing_df = pd.DataFrame(
                                        {"To Channel": list(outgoing_counts.keys()),
                                        "Count": list(outgoing_counts.values())}
                                    ).sort_values("Count", ascending=False)
                                    fig_outgoing = px.bar(
                                        outgoing_df,
                                        x="To Channel",
                                        y="Count",
                                        text="Count",
                                        labels={"Count": "Number of Transitions"},
                                        title=f"Outgoing Transitions from {chosen_channel}"
                                    )
                                    fig_outgoing.update_traces(textposition='outside')
                                    st.plotly_chart(fig_outgoing)
                                    st.dataframe(outgoing_df)
                                else:
                                    st.info(f"No outgoing transitions from {chosen_channel} to other channels among these customers.")

                                # -------------
                                # Net Flow by Other Channels
                                # (i.e., transitions_in - transitions_out with respect to the chosen channel)
                                # For each "other channel" X:
                                #     in_from_X = X -> chosen_channel
                                #     out_to_X  = chosen_channel -> X
                                #     net_flow  = in_from_X - out_to_X
                                # A positive net_flow means more transitions from X into chosen_channel 
                                #      than from chosen_channel to X. 
                                # A negative net_flow means the opposite.
                                # -------------

                                # Gather all unique channels that appear in either incoming_counts or outgoing_counts
                                all_involved_channels = set(incoming_counts.keys()) | set(outgoing_counts.keys())

                                net_rows = []
                                for ch in sorted(all_involved_channels):
                                    in_val = incoming_counts[ch]
                                    out_val = outgoing_counts[ch]
                                    net_flow = in_val - out_val
                                    net_rows.append({
                                        "Channel": ch,
                                        f"{ch} -> {chosen_channel}": in_val,
                                        f"{chosen_channel} -> {ch}": out_val,
                                        "Net Flow (In - Out)": net_flow
                                    })

                                if net_rows:
                                    st.markdown(f"#### Net Transitions (In - Out) relative to {chosen_channel}")
                                    net_df = pd.DataFrame(net_rows)
                                    st.dataframe(net_df)

                                    fig_net_flow = px.bar(
                                        net_df,
                                        x="Channel",
                                        y="Net Flow (In - Out)",
                                        text="Net Flow (In - Out)",
                                        labels={"Net Flow (In - Out)": "In - Out"},
                                        title=f"Net Flow (In - Out) with respect to {chosen_channel}"
                                    )
                                    fig_net_flow.update_traces(textposition='outside')
                                    st.plotly_chart(fig_net_flow)
                                else:
                                    st.info(f"No transitions found when calculating Net Flow for {chosen_channel}.")


        else:
            st.warning('ابتدا از صفحه اصلی داده را بارگذاری کنید!')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')

if __name__ == "__main__":
    main()