import streamlit as st
import os
import sys
import plotly.express as px
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime
import datetime
import math

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.load_data import exacute_query
from utils.auth import login

def to_sql_list(values):
    return ", ".join(f"'{v}'" for v in values)

def filter_tips(selected_complexes, all_tips):
    if len(selected_complexes) == 0:
        return all_tips
    else:
        return [
            tip for tip in all_tips
            if any(complex_name in tip for complex_name in selected_complexes)
        ]


def main():
    st.set_page_config(page_title="تحلیل خرید", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader("تحلیل سبد خرید مشتری ")    

    # Check data availability and login first
    if 'auth' in st.session_state and st.session_state.auth:  
        col1, _,col2, *_ = st.columns([5,1,5,1,1])

        ### date filter
        with col1:
            config = Config(
                always_open = True,
                dark_mode=True,
                locale="fa",
                maximum_date=jdatetime.date.today(),
                color_primary="#ff4b4b",
                color_primary_light="#ff9494",
                selection_mode="range",
                placement="bottom",
                disabled=True
            )
            res = datepicker_component(config=config)

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
                
        with col2: 
            vip_options = ['Non-VIP', 'Bronze VIP', 'Silver VIP', 'Gold VIP']
            vip_status = st.checkbox("انتخاب تمام وضعیت‌هایVIP", value=True, key='vips_checkbox')
            if vip_status:
                vip_values = vip_options
            else:
                vip_values = st.multiselect(
                "انتخاب وضعیت VIP:",
                    options=vip_options,
                    default=[],  
                    key='vips_multiselect_selectbox'
                )
            
            if vip_values == []:
                vip_values = vip_options

            # blacklist filter
            blacklist_options = ['non-blacklist', 'blacklist']
            black_list_status = st.checkbox("انتخاب تمام وضعیت‌های بلک لیست", value=True, key='blacklists_checkbox')
            if black_list_status:
                black_list_values = blacklist_options
            else:
                black_list_values = st.multiselect(
                    "انتخاب وضعیت بلک لیست:",
                    options=blacklist_options,
                    key='blacklist_multiselect_selectbox'
                )
            if black_list_values == []:
                black_list_values = blacklist_options

            # segmentation filter
            semention_options = ['At Risk ✨ Potential', 'At Risk ❤️ Loyal Customers', 'At Risk 👑 Champions',
                                'At Risk 💰 Big Spender', 'At Risk 🔒 Reliable Customers', 'At Risk �️️ Low Value',
                                'At Risk 🧐 Curious Customers', 'Lost ✨ Potential', 'Lost ❤️ Loyal Customers',
                                'Lost 👑 Champions', 'Lost 💰 Big Spender', 'Lost 🔒 Reliable Customers', 'Lost 🗑️ Low Value',
                                'Lost 🧐 Curious Customers', 'New 🧐 Curious Customers',  '✨ Potential', '❤️ Loyal Customers',
                                '👑 Champions', '💰 Big Spender', '🔒 Reliable Customers', '🗑️ Low Value', '🧐 Curious Customers']
            segment_status = st.checkbox("انتخاب تمام سگمنت ها", value=True, key='segments_checkbox')
            if segment_status:
                segment_values = semention_options
            else:
                segment_values = st.multiselect(
                    "انتخاب سگمنت:",
                    options=semention_options,
                    default=[semention_options[0]],  # Default to first option
                    key='segment_multiselect_selectbox'
                )
            if segment_values == []:
                segment_values = semention_options
        
            # tip filter  
            with open("data/tip_names.txt", "r", encoding="utf-8") as file:
                tip_options = [line.strip() for line in file if line.strip()]           
        
            complex_status = st.checkbox("انتخاب تمام مجتمع ها ", value=True, key='complex_checkbox')
            complex_options = [
                            "جمهوری", "اقدسیه", "جردن", "کوروش", "ترنج", 
                            "شریعتی (پاسداران)", "وزرا", "کشاورز", "مرزداران", "میرداماد",
                            "ونک", "ولنجک", "پارک وی", "بهشتی", "ولیعصر", "ویلا",
                        ]
            if complex_status:
                tip_values = tip_options
            else:
                complex_values = st.multiselect(
                        "انتخاب مجتمع:",
                        options=complex_options,
                        default=[],  # empty if user doesn’t pick
                        key='complex_multiselect_selectbox'
                    )
                cols = st.columns([1, 4])

                with cols[1]:
                    tip_options = filter_tips(complex_values, tip_options)
                    tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='tips_checkbox')
                    if tip_status:
                        tip_values = tip_options
                    else:
                        tip_values = st.multiselect(
                            "انتخاب تیپ:",
                            options=tip_options,
                            default=[],  # empty if user doesn’t pick
                            key='tip_multiselect_selectbox'
                        )
                    if tip_values == []:
                        tip_values = tip_options

            # monthly filter
            montly_status = st.checkbox("ماهانه و غیرماهانه", value=True, key='monthly_checkbox')
            if montly_status:
                montly_values = ["ماهانه", "غیر ماهانه"]
                monthly_limit = 15
            else:
                montly_values = st.selectbox(
                    "انتخاب وضعیت :",
                    options=["ماهانه", "غیر ماهانه"],
                    key='monthly_multiselect_selectbox'
                )
                monthly_limit  = st.number_input(
                        "مینیمم میانگین اقامت برای اینکه مهمان ماهانه محسوب شود را وارد کنید:",
                        min_value=0, value=15, step=1, key='min_nights_filter'
                    )

            if montly_values == []:
                montly_values = ["ماهانه", "غیر ماهانه"]
            elif len(montly_values) != 2:
                montly_values = list([montly_values])
            
            # Is staying
            is_staying = st.checkbox('هم مقیم و هم غیرمقیم', value=True, key='is_staying_checkbox')
            if is_staying:
                is_staying_values = ["مقیم","غیر مقیم"]
            else:
                is_staying_values = st.selectbox(
                    "انتخاب وضعیت اقامت:",
                    options=["مقیم","غیر مقیم"],
                    key='is_staying_selectbox'
                )
            if is_staying_values == []:
                is_staying_values = ["مقیم","غیر مقیم"]
            elif len(is_staying_values) != 2:
                is_staying_values = list([is_staying_values])

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

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
        """
        
        if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
            ids = exacute_query(query)
            customer_ids = ids['customer_id'].dropna().unique().tolist()
            id_list_sql = ', '.join(str(int(i)) for i in customer_ids)

            # Prepare mapping for complexes as a CASE statement for SQL
            complex_case = """
                CASE
                    WHEN p.ProductName LIKE '%جمهوری%' THEN 'جمهوری'
                    WHEN p.ProductName LIKE '%اقدسیه%' THEN 'اقدسیه'
                    WHEN p.ProductName LIKE '%جردن%' THEN 'جردن'
                    WHEN p.ProductName LIKE '%شریعتی%' THEN 'شریعتی (پاسداران)'
                    WHEN p.ProductName LIKE '%پاسداران%' THEN 'شریعتی (پاسداران)'
                    WHEN p.ProductName LIKE '%وزرا%' THEN 'وزرا'
                    WHEN p.ProductName LIKE '%کشاورز%' THEN 'کشاورز'
                    WHEN p.ProductName LIKE '%مرزداران%' THEN 'مرزداران'
                    WHEN p.ProductName LIKE '%میرداماد%' THEN 'میرداماد'
                    WHEN p.ProductName LIKE '%ونک%' THEN 'ونک'
                    WHEN p.ProductName LIKE '%ولنجک%' THEN 'ولنجک'
                    WHEN p.ProductName LIKE '%پارک وی%' THEN 'پارک وی'
                    WHEN p.ProductName LIKE '%بهشتی%' THEN 'بهشتی'
                    WHEN p.ProductName LIKE '%ولیعصر%' THEN 'ولیعصر'
                    WHEN p.ProductName LIKE '%ویلا%' THEN 'ویلا'
                    WHEN p.ProductName LIKE '%کوروش%' THEN 'کوروش'
                    WHEN p.ProductName LIKE '%ترنج%' THEN 'ترنج'
                    ELSE NULL
                END AS complex
            """

            # Mapping ProductCode to Region as a CASE statement for SQL
            region_case = """
                CASE
                    WHEN p.ProductCode IN ('GA3','EV1','EV2','EV3','GA1','GA2','GA4','GA5','GA6','JD1','JD2','JD3','JD4','PV1','PV2','PV3','PV4') THEN 'شمال'
                    WHEN p.ProductCode IN ('AF1','AF2','AF3','KS1','KS2','TRN1','TRN2','TRN3','TRN4','TRN5') THEN 'غرب'
                    WHEN p.ProductCode IN ('KE1','KE2','KE3','NM1','NM2','NM3','NM4','NM5','NS1','NS2','NS3','NS4','NS5','VA1','VA2','VLA1','VLA2','VLA3','VLA4','VLA5','VLA6','VLA7','VLA8') THEN 'مرکز'
                    WHEN p.ProductCode IN ('MD1','MD2','MD3','MD4','MD5','MD6','MD7','MD8','MD9','MD10','MD11','MD12','PA1','PA2','ZZ3') THEN 'شرق'
                    ELSE 'نامشخص'
                END AS region
            """

            # Mapping quality_rank to Persian label
            quality_case = """
                CASE
                    WHEN p.quality_rank = 1 THEN 'اکونومی'
                    WHEN p.quality_rank = 2 THEN 'استاندارد'
                    WHEN p.quality_rank = 3 THEN 'ویژه'
                    WHEN p.quality_rank = 4 THEN 'VIP'
                    ELSE 'نامشخص'
                END AS quality_rank_label
            """

            # Only include selected tip_values in the query
            tip_values_sql = ', '.join([f"'{v}'" for v in tip_values])

            # Query: join deals and products, filter by customer and tip, map complex, region, and quality, aggregate in SQL
            agg_query = f"""
                SELECT 
                    {complex_case},
                    {region_case},
                    {quality_case},
                    COUNT(*) AS Frequency,
                    SUM(d.DealValue) AS DealValue
                FROM `customerhealth-crm-warehouse.didar_data.deals` d
                JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                    ON d.Product_code = p.ProductCode
                WHERE d.Customer_id IN ({id_list_sql})
                  AND p.ProductName IN ({tip_values_sql})
                  AND d.DealCreateDate BETWEEN DATE('{start_date_str}') AND DATE('{end_date_str}')
                GROUP BY complex, region, quality_rank_label
                HAVING complex IS NOT NULL
            """

            agg_df = exacute_query(agg_query)

            if agg_df.empty:
                st.warning("هیچ معامله‌ای با این شرایط پیدا نشد")
            else:
                # Format numbers with thousands separator
                agg_df['Frequency_fmt'] = agg_df['Frequency'].apply(lambda x: f"{x:,}")
                agg_df['DealValue_fmt'] = agg_df['DealValue'].apply(lambda x: f"{round(x/10_000_000):,} میلیون")

                # Plot Frequency Distribution by Complex
                st.subheader("توزیع فراوانی معاملات")
                plot_df = agg_df.copy()
                plot_df = plot_df[plot_df['complex'].notnull()]
                plot_df['complex'] = plot_df['complex'].astype(str)
                plot_df = plot_df.groupby('complex', as_index=False).agg({'Frequency': 'sum'})
                # plot_df = plot_df.sort_values('Frequency', ascending=False)

                fig_freq = px.bar(
                    plot_df,
                    x='complex',
                    y='Frequency',
                    title='توزیع فراوانی',
                    labels={'complex': 'مجتمع', 'Frequency': 'تعداد خرید'},
                    text='Frequency'
                )
                fig_freq.update_xaxes(type='category')
                st.plotly_chart(fig_freq)

                # Plot Monetary Distribution by Complex
                st.subheader("توزیع ارزش مالی معاملات")
                plot_monetary_df = agg_df.groupby('complex', as_index=False).agg({'DealValue': 'sum'})
                plot_monetary_df['DealValue_fmt'] = plot_monetary_df['DealValue'].apply(lambda x: f"{math.ceil(x/1_000_000_000):,} میلیارد ریال")
                fig_monetary = px.bar(
                    plot_monetary_df,
                    x='complex',
                    y='DealValue',
                    title='توزیع مالی',
                    labels={'complex': 'مجتمع', 'DealValue': 'ارزش کل معاملات'},
                    text='DealValue_fmt'
                )
                fig_monetary.update_traces(textposition='outside')
                max_val = plot_monetary_df['DealValue'].max()
                fig_monetary.update_yaxes(range=[0, max_val * 1.1 if max_val > 0 else 1])
                st.plotly_chart(fig_monetary)

                # Plot Monetary Distribution by Quality Rank
                st.subheader("توزیع ارزش مالی به تفکیک نوع محصول")
                quality_df = agg_df.groupby('quality_rank_label', as_index=False).agg({'DealValue': 'sum'})
                # Remove 'نامشخص' if you want only 1-4
                quality_df = quality_df[quality_df['quality_rank_label'] != 'نامشخص']
                quality_df['DealValue_fmt'] = quality_df['DealValue'].apply(lambda x: f"{round(x/1_000_000_000):,} میلیارد ریال")
                fig_quality = px.bar(
                    quality_df,
                    x='quality_rank_label',
                    y='DealValue',
                    title='ارزش فروش به تفکیک کیفیت',
                    labels={'quality_rank_label': 'کیفیت', 'DealValue': 'ارزش کل معاملات'},
                    text='DealValue_fmt'
                )
                fig_quality.update_traces(textposition='outside')
                max_val = quality_df['DealValue'].max()
                fig_quality.update_yaxes(range=[0, max_val * 1.1 if max_val > 0 else 1])
                st.plotly_chart(fig_quality)

                cols = st.columns(2)
                with cols[0]:
                    # Plot Sale by Region (Monetary) as Pie Chart
                    st.subheader("ارزش فروش در هر منطقه")
                    region_agg = agg_df.groupby('region', as_index=False).agg({'DealValue': 'sum'})
                    region_agg = region_agg[region_agg['region'] != 'نامشخص']
                    region_agg['DealValue_billion'] = region_agg['DealValue'] / 10_000_000_000
                    region_agg['DealValue_billion_fmt'] = region_agg['DealValue_billion'].apply(lambda x: f"{x:,.1f} میلیارد تومن")
                    
                    fig_region_pie = px.pie(
                        region_agg,
                        names='region',
                        values='DealValue',
                        title='سهم ارزش فروش به تفکیک منطقه',
                        hole=0.3,
                        labels={'region': 'منطقه', 'DealValue': 'ارزش کل فروش'},
                    )
                    fig_region_pie.update_traces(
                        textinfo='label+text',
                        texttemplate='%{label}\n%{customdata}',
                        customdata=region_agg[['DealValue_billion_fmt']],
                        hovertemplate='<b>%{label}</b><br>ارزش فروش: %{value:,} ریال<br>ارزش فروش: %{customdata[0]}'
                    )
                    st.plotly_chart(fig_region_pie)
                with cols[1]:
                    # Plot Sale Frequency by Region as Pie Chart
                    st.subheader("تعداد معاملات در هر منطقه")
                    region_freq = agg_df.groupby('region', as_index=False).agg({'Frequency': 'sum'})
                    region_freq = region_freq[region_freq['region'] != 'نامشخص']
                    region_freq['Frequency_fmt'] = region_freq['Frequency'].apply(lambda x: f"{x:,}")
                    fig_region_freq_pie = px.pie(
                        region_freq,
                        names='region',
                        values='Frequency',
                        title='سهم تعداد معاملات به تفکیک منطقه',
                        hole=0.3,
                        labels={'region': 'منطقه', 'Frequency': 'تعداد معاملات'},
                    )
                    fig_region_freq_pie.update_traces(
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>تعداد معاملات: %{value:,}'
                    )
                    st.plotly_chart(fig_region_freq_pie)
    else:
        login()

if __name__ == "__main__":
    main()