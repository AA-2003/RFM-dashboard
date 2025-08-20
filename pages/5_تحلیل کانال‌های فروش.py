import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add parent directory to sys.path for utility imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def get_first_successful_deal_date(selected_channels):
    """
    Fetches the first successful deal date for each customer from BigQuery, filtered by date and channels.
    Returns a DataFrame with columns: Customer_id, first_successful_deal_date, DealChannel
    """
    query = """
        WITH first_deals AS (
            SELECT
                Customer_id,
                DealChannel,
                DealCreateDate,
                ROW_NUMBER() OVER (PARTITION BY Customer_id ORDER BY DealCreateDate ASC) as rn
            FROM `customerhealth-crm-warehouse.didar_data.deals`
            WHERE
                Status = 'Won'
        )
        SELECT
            Customer_id,
            DealChannel,
            DealCreateDate AS first_successful_deal_date
        FROM first_deals
        WHERE rn = 1
    """
    result = exacute_query(query)
    # Filter by selected channels if provided
    if selected_channels:
        result = result[result['DealChannel'].isin(selected_channels)]
    return result

def pct_diff(new_val, old_val):
    # Calculate percent difference, handle division by zero
    if old_val in [None, 0]:
        return None
    return f"{((new_val - old_val)/abs(old_val)*100):.2f}%"

@st.cache_data(ttl=600, show_spinner=False)
def channel_analysis(deals, prev_deals, df_first_deals, start_date_str,
                    end_date_str, horizontal=True) -> None:
    # Calculate main KPIs
    total_deals = len(deals)
    successful_deals = deals[deals['Status'] == 'Won']
    successful_deals_count = len(successful_deals)
    success_rate = (successful_deals_count / total_deals * 100) if total_deals > 0 else 0
    avg_deal_value = (deals['DealValue']/10).mean()  if not deals.empty else 0

    # Calculate new and returning customers
    if not deals.empty:
        new_customers = df_first_deals[
            (df_first_deals['first_successful_deal_date'] >= start_date_str) &
            (df_first_deals['first_successful_deal_date'] <= end_date_str)
        ]['Customer_id'].nunique()
        returning_customers = deals['Customer_id'].nunique() - new_customers
    else:
        new_customers = 0
        returning_customers = 0 

    # Calculate average nights and extension rate
    avg_nights = deals['Nights'].mean() if 'Nights' in deals.columns and not deals.empty else 0
    if 'DealType' in deals.columns and not deals.empty:
        extention_rate = deals[deals['DealType']=='Renewal'].shape[0] / deals.shape[0] * 100
    else:
        extention_rate = 0

    # Calculate previous period KPIs
    prev_total_deals = len(prev_deals)
    prev_successful_deals = prev_deals[prev_deals['Status'] == 'Won'] if not prev_deals.empty else []
    prev_successful_deals_count = len(prev_successful_deals)
    prev_success_rate = (prev_successful_deals_count / prev_total_deals * 100) if prev_total_deals > 0 else 0
    prev_avg_deal_value = (prev_deals['DealValue']/10).mean() if not prev_deals.empty else 0

    prev_avg_nights = prev_deals['Nights'].mean() if 'Nights' in prev_deals.columns and not prev_deals.empty else 0
    if 'DealType' in prev_deals.columns and not prev_deals.empty:
        prev_extention_rate = prev_deals[prev_deals['DealType']=='Renewal'].shape[0] / prev_deals.shape[0] * 100
    else:
        prev_extention_rate = 0

    # KPI Section: Show metrics horizontally or vertically
    if horizontal:
        st.subheader("شاخص‌های کلیدی عملکرد (KPI)")
        colKPI1, colKPI2, colKPI3, colKPI4 = st.columns(4)
        colKPI1.metric(
            "تعداد کل معاملات",
            f"{total_deals}",
            pct_diff(total_deals, prev_total_deals)
        )
        colKPI2.metric(
            "تعداد معاملات موفق",
            f"{successful_deals_count}",
            pct_diff(successful_deals_count, prev_successful_deals_count)
        )
        colKPI3.metric(
            "نرخ موفقیت (%)",
            f"{success_rate:.2f}%",
            pct_diff(success_rate, prev_success_rate)
        )
        colKPI4.metric(
            "میانگین ارزش معامله",
            f"{avg_deal_value:,.0f}",
            pct_diff(avg_deal_value, prev_avg_deal_value)
        )

        colKPI5, colKPI6, colKPI7, colKPI8 = st.columns(4)
        colKPI5.metric(
            "مشتریان جدید",
            f"{new_customers}",
        )
        colKPI6.metric(
            "مشتریان بازگشتی",
            f"{returning_customers}",
        )
        colKPI7.metric(
            "میانگین شب اقامت",
            f"{avg_nights:.2f}",
            pct_diff(avg_nights, prev_avg_nights)
        )
        colKPI8.metric(
            "نرخ تمدید",
            f"{extention_rate:.2f}%",
            pct_diff(extention_rate, prev_extention_rate)
        )
    else:
        # Show metrics vertically
        st.metric(
            "تعداد کل معاملات",
            f"{total_deals}",
            pct_diff(total_deals, prev_total_deals)
        )
        st.metric(
            "تعداد معاملات موفق",
            f"{successful_deals_count}",
            pct_diff(successful_deals_count, prev_successful_deals_count)
        )
        st.metric(
            "نرخ موفقیت (%)",
            f"{success_rate:.2f}%",
            pct_diff(success_rate, prev_success_rate)
        )
        st.metric(
            "میانگین ارزش معامله",
            f"{avg_deal_value:,.0f}",
            pct_diff(avg_deal_value, prev_avg_deal_value)
        )
        st.metric(
            "مشتریان جدید",
            f"{new_customers}",
        )
        st.metric(
            "مشتریان بازگشتی",
            f"{returning_customers}",
        )
        st.metric(
            "میانگین شب اقامت",
            f"{avg_nights:.2f}",
            pct_diff(avg_nights, prev_avg_nights)
        )
        st.metric(
            "نرخ تمدید",
            f"{extention_rate:.2f}%",
            pct_diff(extention_rate, prev_extention_rate)
        )
        st.write('---')

    # Customer clusters (RFM segmentation)
    customer_ids = deals['Customer_id'].values.tolist()
    if customer_ids:
        # Prepare customer IDs for SQL query
        customer_ids_list = ', '.join(str(int(id)) for id in customer_ids)
        cluster_query = f"""
            select * from `customerhealth-crm-warehouse.didar_data.RFM_segments`
            where customer_id in ({customer_ids_list})
            """
        cluster_df = exacute_query(cluster_query)
        if not cluster_df.empty and 'rfm_segment' in cluster_df.columns:
            # Count customers in each RFM segment
            segment_counts = cluster_df['rfm_segment'].value_counts().reset_index()
            segment_counts.columns = ['rfm_segment', 'count']

            # Plot bar chart for RFM segments
            cluster_chart = px.bar(
                segment_counts,
                x='rfm_segment',
                y='count',
                title='',
                labels={'rfm_segment': 'سگمنت', 'count': 'تعداد'},
                text='count',
                color='rfm_segment'
            )
            cluster_chart.update_traces(textposition='outside')
            cluster_chart.update_layout(xaxis_title='سگمنت', yaxis_title='تعداد')
            st.subheader('توزیع سگمنت مشتریان')
            st.plotly_chart(cluster_chart)
        else:
            st.info("داده‌ای برای سگمنت مشتریان یافت نشد.")

        # Show customer details
        st.subheader("جزئیات مشتریان")
        st.write(cluster_df)
        return cluster_df
    else:
        st.info("داده‌ای برای مشتریان یافت نشد.")
        return pd.DataFrame()

def main():
    st.set_page_config(page_title="تحلیل کانال فروش", page_icon="📊", layout="wide")
    apply_custom_css()
    st.header("تحلیل کانال فروش")
    
    # Check if user is authenticated
    if 'auth' in st.session_state and st.session_state.auth:    
        col1, _, col2, *_ = st.columns([5, 1, 5, 1, 1])

        ### Date filter UI
        with col1:
            st.subheader("انتخاب بازه زمانی تاریخ ایجاد معامله: ")
            config = Config(
                always_open=True,
                dark_mode=True,
                locale="fa",
                maximum_date=jdatetime.date.today() - jdatetime.timedelta(days=3),
                color_primary="#ff4b4b",
                color_primary_light="#ff9494",
                selection_mode="range",
                placement="bottom",
                disabled=False
            )
            res = datepicker_component(config=config)

            # If user selected a date, use it; otherwise, get min/max from DB
            if res and 'from' in res and res['from'] is not None:
                start_date = res['from'].togregorian()
            else:
                query = "select min(DealCreateDate) as min_deal_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                start_date = result['min_deal_date'].iloc[0].date()

            if res and 'to' in res and res['to'] is not None:
                end_date = res['to'].togregorian()
            else:
                query = "select max(DealCreateDate) as max_deal_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                end_date = result['max_deal_date'].iloc[0].date()

        ### Channel filter UI
        with col2:
            channels_query = """
                select DealChannel from `customerhealth-crm-warehouse.didar_data.deals`
                group by DealChannel
                """
            channels_options = exacute_query(channels_query)['DealChannel'].values.tolist()
            select_all = st.checkbox("انتخاب همه کانال‌های فروش‌", value=True, key='channels_select_all_checkbox')
            if select_all:
                selected_channels = channels_options
            else:
                selected_channels = st.multiselect(
                    "انتخاب  کانال فروش: ",
                    options=channels_options,
                    default=[],
                    key='channels_multiselect_box'
                )

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        if st.button("محاسبه و نمایش", key='calculate_button'):
            df_first_deals = get_first_successful_deal_date(selected_channels)
            channels_list = ','.join([f"'{channel}'" for channel in selected_channels])
            deals_query = f"""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE DealChannel IN ({channels_list})  
                AND DealCreateDate BETWEEN DATE('{start_date_str}') AND DATE('{end_date_str}')
                """
            deals = exacute_query(deals_query)
            if deals is None or deals.empty:
                st.info('هیچ داده در بازه زمانی انتخاب شده وجود ندارد!!!')
                return

            # Calculate previous period (same length, immediately before current period)
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            period_days = (end_dt - start_dt).days + 1

            prev_end_dt = start_dt - timedelta(days=1)
            prev_start_dt = prev_end_dt - timedelta(days=period_days - 1)
            prev_start_date_str = prev_start_dt.strftime("%Y-%m-%d")
            prev_end_date_str = prev_end_dt.strftime("%Y-%m-%d")

            prev_deals_query = f"""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE DealChannel IN ({channels_list})  
                AND DealCreateDate BETWEEN DATE('{prev_start_date_str}') AND DATE('{prev_end_date_str}')
                """
            prev_deals = exacute_query(prev_deals_query)

            if not selected_channels:
                st.warning('حداقل یک کانال فروش را انتخاب کنید!')
            match len(selected_channels):
                case 1:
                    # Single channel analysis
                    cluster_df = channel_analysis(
                        deals, prev_deals, df_first_deals, start_date_str, end_date_str
                    )
                    if not cluster_df.empty:
                        cols = st.columns(2)
                        with cols[0]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت CSV",
                                data=convert_df(cluster_df),
                                file_name='rfm_segmentation_with_churn.csv',
                                mime='text/csv',
                            )

                        with cols[1]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت اکسل",
                                data=convert_df_to_excel(cluster_df),
                                file_name='rfm_segmentation_with_churn.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            )

                case 2:
                    # Compare two channels side by side
                    col1, col2 = st.columns(2)
                    channel1, channel2 = selected_channels
                    with col1:                        
                        st.write(channel1)
                        cluster_df = channel_analysis(
                            deals[deals['DealChannel'] == channel1],
                            prev_deals[prev_deals['DealChannel'] == channel1],
                            df_first_deals, start_date_str, end_date_str, False
                        )
                        if not cluster_df.empty:
                            cols = st.columns(2)
                            with cols[0]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت CSV",
                                    data=convert_df(cluster_df),
                                    file_name='rfm_segmentation_with_churn.csv',
                                    mime='text/csv',
                                    key=f"download_csv_{channel1}"
                                )

                            with cols[1]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت اکسل",
                                    data=convert_df_to_excel(cluster_df),
                                    file_name='rfm_segmentation_with_churn.xlsx',
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    key=f"download_excel_{channel1}"
                                )
                    with col2:
                        st.write(channel2)
                        cluster_df = channel_analysis(
                            deals[deals['DealChannel'] == channel2],
                            prev_deals[prev_deals['DealChannel'] == channel2],
                            df_first_deals, start_date_str, end_date_str, False
                        )
                        if not cluster_df.empty:
                            cols = st.columns(2)
                            with cols[0]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت CSV",
                                    data=convert_df(cluster_df),
                                    file_name='rfm_segmentation_with_churn.csv',
                                    mime='text/csv',
                                    key=f"download_csv_{channel2}"
                                )

                            with cols[1]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت اکسل",
                                    data=convert_df_to_excel(cluster_df),
                                    file_name='rfm_segmentation_with_churn.xlsx',
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    key=f"download_excel_{channel2}"
                                )

                # Compare more than two channels
                case _:
                    metrics = []
                    # Collect all unique customer_ids for all selected channels
                    all_customer_ids = deals[deals['DealChannel'].isin(selected_channels)]['Customer_id'].unique().tolist()
                    if all_customer_ids:
                        all_customer_ids_list = ', '.join(str(int(id)) for id in all_customer_ids)
                        cluster_query = f"""
                            select * from `customerhealth-crm-warehouse.didar_data.RFM_segments`
                            where customer_id in ({all_customer_ids_list})
                        """
                        all_cluster_df = exacute_query(cluster_query)
                    else:
                        all_cluster_df = pd.DataFrame()

                    for channel in selected_channels:
                        channel_deals = deals[deals['DealChannel'] == channel]
                        channel_successful = channel_deals[channel_deals['Status'] == 'Won']
                        total_deals = len(channel_deals)
                        successful_deals = len(channel_successful)
                        # Calculate average value for successful deals, handle empty
                        avg_value = channel_deals[channel_deals['Status'] == 'Won']['DealValue'].mean() / 10 if not channel_deals.empty else 0
                        total_value = channel_deals['DealValue'].sum() / 10 if not channel_deals.empty else 0
                        success_rate = (successful_deals / total_deals * 100) if total_deals > 0 else 0
                        # Calculate renewal rate, handle division by zero
                        renewal_rate = len(channel_deals[channel_deals['DealType']=="Renewal"]) / successful_deals * 100 if successful_deals > 0 else 0
                        total_nights = channel_deals['Nights'].sum() if 'Nights' in channel_deals.columns and not channel_deals.empty else 0
                        # New customers for this channel
                        if (
                            df_first_deals is not None
                            and not channel_deals.empty
                            and 'first_successful_deal_date' in df_first_deals.columns
                        ):
                            # Filter first deals for this channel and date range
                            channel_first_deals = df_first_deals[
                                (df_first_deals['DealChannel'] == channel) &
                                (df_first_deals['first_successful_deal_date'] >= start_date_str) &
                                (df_first_deals['first_successful_deal_date'] <= end_date_str)
                            ]
                            new_customers = channel_first_deals['Customer_id'].nunique()
                        else:
                            new_customers = 0

                        # Get RFM segment for this channel
                        customer_ids = channel_deals['Customer_id'].unique().tolist()
                        if customer_ids and not all_cluster_df.empty and 'rfm_segment' in all_cluster_df.columns:
                            channel_cluster_df = all_cluster_df[all_cluster_df['customer_id'].isin(customer_ids)]
                            if not channel_cluster_df.empty:
                                seg_counts = channel_cluster_df['rfm_segment'].value_counts()
                                top_segment = seg_counts.idxmax()
                            else:
                                top_segment = "-"
                        else:
                            top_segment = "-"

                        metrics.append({
                            "کانال فروش": channel,
                            "تعداد کل معاملات": total_deals,
                            "تعداد معاملات موفق": successful_deals,
                            "نرخ موفقیت": f"{success_rate:.2f}",
                            "جمع تعداد شب": int(total_nights),
                            "ارزش کل معاملات": total_value,
                            "میانگین ارزش معاملات": avg_value,
                            "نرخ تمدید": renewal_rate,
                            "تعداد مشتریان جدید": new_customers,
                            "سگمنت غالب": top_segment
                        })
                    metrics_df = pd.DataFrame(metrics)
                    st.subheader("مقایسه کانال های فروش(جدول شاخص‌ها)")
                    st.dataframe(metrics_df.sort_values(by='تعداد معاملات موفق', ascending=False).reset_index(drop=True), use_container_width=True)

                    # Bar chart: تعداد معاملات موفق per channel 
                    st.subheader("تعداد معاملات موفق به تکفیک کانال")
                    fig1 = px.bar(
                        metrics_df,
                        x="کانال فروش",
                        y="تعداد معاملات موفق",
                        title='',
                        text="تعداد معاملات موفق",
                        color="کانال فروش"
                    )
                    fig1.update_layout(xaxis_title="کانال فروش", yaxis_title="تعداد معاملات موفق")
                    st.plotly_chart(fig1, use_container_width=True)

                    metrics_df["ارزش کل معاملات (میلیون تومان)"] = (metrics_df["ارزش کل معاملات"] / 1000).round(2)

                    # Bar chart: ارزش کل معاملات per channel 
                    st.subheader("ارزش کل معاملات به تکفیک کانال")
                    fig2 = px.bar(
                        metrics_df.sort_values(by="ارزش کل معاملات", ascending=False),
                        x="کانال فروش",
                        y="ارزش کل معاملات (میلیون تومان)",
                        title='',
                        text="ارزش کل معاملات (میلیون تومان)",
                        color="کانال فروش"
                    )
                    fig2.update_layout(xaxis_title="کانال فروش", yaxis_title="ارزش کل معاملات (میلیون تومان)")
                    st.plotly_chart(fig2, use_container_width=True)
    else:
        login()

if __name__ == "__main__":
    main()