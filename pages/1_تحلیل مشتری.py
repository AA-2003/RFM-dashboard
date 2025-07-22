import streamlit as st
import pandas as pd
import os
import sys
import plotly.express as px

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.constants import COLOR_MAP, DEALSTATUS, CUSTOMERID, COMPLEX, PRODUCTTITLE
from RFM.utils.funcs import convert_df, convert_df_to_excel

@st.cache_data
def filter_data(data, vip_values, black_list_values, complex_values, tip_values):
    """Filter RFM data based on user selections."""
    filtered_data = data[
        (data['VIP Status'].isin(vip_values)) &
        (data['BlackList Status'].isin(black_list_values)) &
        (data[COMPLEX].isin(complex_values)) &
        (data[PRODUCTTITLE].isin(tip_values))
    ]

    return filtered_data

@st.cache_data
def filter_rfm(rfm_data, data, segment_values, montly_values, monthly_limit, is_staying_values):
    """Filter RFM data based on user selections."""
    rfm_data = rfm_data[
        (rfm_data['Code'].isin(data[CUSTOMERID].unique().tolist()))
    ]
    
    filtered_data = rfm_data[
        (rfm_data['RFM_segment_label'].isin(segment_values)) 
    ]

    filtered_data['monthly'] = rfm_data['average stay'] > monthly_limit
    if montly_values == 'مهمانان ماهانه':
        filtered_data = filtered_data[
            (filtered_data['monthly'] == True)
        ]

    if is_staying_values == 'مقیم':
        filtered_data = filtered_data[
            (filtered_data['Is staying'] == True)
        ]

    return filtered_data

def customers_filters(data, rfm_data):
    # VIP filter
    vip_options = data['VIP Status'].dropna().unique().tolist()
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
    blacklist_options = data['BlackList Status'].dropna().unique().tolist()
    black_list_status = st.checkbox("انتخاب تمام وضعیت‌های Blacklist", value=True, key='blacklists_checkbox')
    if black_list_status:
        black_list_values = blacklist_options
    else:
        black_list_values = st.multiselect(
            "انتخاب وضعیت Blacklist:",
            options=blacklist_options,
            key='blacklist_multiselect_selectbox'
        )
    if black_list_values == []:
        black_list_values = blacklist_options

    # segmentation filter
    semention_options = rfm_data['RFM_segment_label'].dropna().unique().tolist()
    segment_status = st.checkbox("انتخاب تمام بخش‌ها", value=True, key='segments_checkbox')
    if segment_status:
        segment_values = semention_options
    else:
        segment_values = st.multiselect(
            "انتخاب بخش:",
            options=semention_options,
            default=[semention_options[0]],  # Default to first option
            key='segment_multiselect_selectbox'
        )
    if segment_values == []:
        segment_values = semention_options
    
    # complex filter
    complex_options = data[COMPLEX].dropna().unique().tolist()
    complex_status = st.checkbox(" انتخاب تمام مجتمع‌ها", value=True, key='complex_checkbox')
    if complex_status:
        complex_values = complex_options
    else:
        complex_values = st.multiselect(
            " انتخاب مجتمع :",
            options=complex_options,
            default=[],  # empty if user doesn’t pick
            key='complex_multiselect_selectbox'
        )
    if complex_values == []:
        complex_values = complex_options

    # tip filter             
    tip_options = data[data[DEALSTATUS]=='Won'][PRODUCTTITLE].dropna().unique().tolist()
    tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='tips_checkbox')
    if tip_status:
        tip_values = tip_options
    else:
        tip_values = st.multiselect(
            "Tip انتخاب وضعیت :",
            options=tip_options,
            default=[],  # empty if user doesn’t pick
            key='tip_multiselect_selectbox'
        )
    if tip_values == []:
        tip_values = tip_options

    # monthly filter
    montly_status = st.checkbox("ماهانه و غیرماهانه", value=True, key='monthly_checkbox')
    if montly_status:
        montly_values = ["مهمانان ماهانه","مهمانان غیر ماهانه"]
        monthly_limit = 15
    else:
        montly_values = st.selectbox(
            "انتخاب وضعیت :",
            options=["مهمانان ماهانه","مهمانان غیر ماهانه"],
            key='monthly_multiselect_selectbox'
        )
        monthly_limit  = st.number_input(
                "مینیمم میانگین اقامت برای اینکه مهمان ماهانه محسوب شود را وارد کنید:",
                min_value=0, value=15, step=1, key='min_nights_filter'
            )

    if montly_values == []:
        montly_values = ["مهمانان ماهانه","مهمانان غیر ماهانه"]
    
    # Is staying
    is_staying = st.checkbox('هم مقیم و هم غیرمقیم', value=True, key='is_staying_checkbox')
    if is_staying:
        is_staying_values = ["مقیم","غیرمقیم"]
    else:
        is_staying_values = st.selectbox(
            "انتخاب وضعیت اقامت:",
            options=["مقیم","غیرمقیم"],
            key='is_staying_selectbox'
        )
    if is_staying_values == []:
        is_staying_values = ["مقیم","غیرمقیم"]
    return vip_values, black_list_values, segment_values, complex_values, tip_values, montly_values, monthly_limit, is_staying_values

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="تحلیل مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل مشتری")
    
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:    
        if 'data' in st.session_state and 'rfm_data'in st.session_state:

            data = st.session_state.data
            rfm_data = st.session_state.rfm_data

            tab1, tab2, tab3, tab4  = st.tabs(["دیتای بخش‌بندی مشتریان", "نمودار دایره‌ای", "نمودار پراکندگی سه بعدی", "هیستوگرام‌ها"])

            # Customer Filters
            with tab1:
                vip_values, black_list_values, segment_values, complex_values, \
                tip_values, montly_values, monthly_limit, is_staying_values = customers_filters(
                    data,
                    rfm_data
                )    
                # Check if button was clicked previously
                if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
                    data = filter_data(
                        data,
                        vip_values,
                        black_list_values,
                        complex_values,
                        tip_values
                    )

                    filtered_rfm_data = filter_rfm(
                        rfm_data,
                        data,
                        segment_values,
                        montly_values,
                        monthly_limit,
                        is_staying_values
                    )

                    # check if there is any data after filter
                    if filtered_rfm_data.empty or filtered_rfm_data is None:
                        st.Info("با این فیلتر ها داده ای وجود ندارد")
                    # Display the results only if RFM was calculated
                    else:
                        st.session_state['filtered_rfm_data'] = filtered_rfm_data
                        
                        st.dataframe(filtered_rfm_data)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="Download data as CSV",
                                data=convert_df(filtered_rfm_data),
                                file_name='rfm_segmentation_with_churn.csv',
                                mime='text/csv',
                            )

                        with col2:
                            st.download_button(
                                label="Download data as Excel",
                                data=convert_df_to_excel(filtered_rfm_data),
                                file_name='rfm_segmentation_with_churn.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            )

            # نمودار دایره ای
            with tab2:
                st.subheader("توزیع بخش‌های مشتریان")
                if 'rfm_data' in st.session_state and st.session_state.rfm_data is not None:
                    segment_counts = st.session_state.rfm_data['RFM_segment_label'].value_counts()
                    fig = px.pie(
                        values=segment_counts.values,
                        names=segment_counts.index,
                        title='',
                        color=segment_counts.index,
                        color_discrete_map=COLOR_MAP
                    )
                    st.plotly_chart(fig)
                else:
                    st.info("داده‌ای برای نمایش وجود ندارد.")
                
            #نمودار سه بعدی
            with tab3:
                st.subheader("نمودار پراکندگی سه بعدی متریک‌های بخش‌بندی")
                if 'rfm_data' in st.session_state and st.session_state.rfm_data is not None:
                    rfm_data = st.session_state.rfm_data
                    # Ensure columns exist and are named correctly
                    required_cols = ['Recency', 'Frequency', 'Monetary', 'RFM_segment_label', 'Code']
                    if all(col in rfm_data.columns for col in required_cols):
                        fig_3d = px.scatter_3d(
                            rfm_data,
                            x='Frequency',
                            y='Recency',
                            z='Monetary',
                            color='RFM_segment_label',
                            color_discrete_map=COLOR_MAP,
                            title="نمودار سه‌بعدی RFM (Recency, Frequency, Monetary)",
                            opacity=0.8,
                            hover_data={'Code': True,
                                        'Name':True,
                                        'Phone Number':True,
                                    }
                        )
                        fig_3d.update_traces(marker=dict(size=6))
                        fig_3d.update_layout(
                            scene = dict(
                                xaxis_title='تعداد خرید (Frequency)',
                                yaxis_title='تازگی خرید (Recency)',
                                zaxis_title='ارزش خرید (Monetary)'
                            ),
                            legend_title_text='بخش‌بندی RFM'
                        )
                        st.plotly_chart(fig_3d, use_container_width=True)
                    else:
                        st.warning("ستون‌های مورد نیاز برای رسم نمودار سه‌بعدی وجود ندارند.")
                else:
                    st.info("داده‌ای برای نمایش وجود ندارد.")
                    
            #هیستوگرام ها
            with tab4:
                st.subheader("توزیع متریک‌های بخش‌بندی مشتریان")

                st.plotly_chart(px.histogram(
                    rfm_data, x='Recency', nbins=50,
                    title='Recency Distribution',
                    color='RFM_segment_label', color_discrete_map=COLOR_MAP
                ))
                st.plotly_chart(px.histogram(
                    rfm_data, x='Frequency', nbins=50,
                    title='Frequency Distribution',
                    color='RFM_segment_label', color_discrete_map=COLOR_MAP
                ))
                st.plotly_chart(px.histogram(
                    rfm_data, x='Monetary', nbins=50,
                    title='Monetary Value Distribution',
                    labels={'Monetary':'Monetary Value'},
                    color='RFM_segment_label', color_discrete_map=COLOR_MAP
                ))
        else:
            st.info('ابتدا داده را لود کنید')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')

if __name__ == "__main__":
    main()