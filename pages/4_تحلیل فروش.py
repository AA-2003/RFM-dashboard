import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
from datetime import  timedelta
import plotly.express as px
import plotly.graph_objects as go

# Add parent directory to sys.path for utility imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.constants import DEALDONEDATE, DEALOWNER, DEALSTATUS, DEALCREATEDDATE



@st.cache_data(ttl=600, show_spinner=False)
def analysis_seller(data: pd.DataFrame, rfm_data: pd.DataFrame, selected_sellers: list, start_date: str, end_date: str, selected_vips: list):
    mask = (
        (data[DEALCREATEDDATE] >= pd.to_datetime(start_date))
        & (data[DEALCREATEDDATE] <= pd.to_datetime(end_date))
        & (data[DEALOWNER].isin(selected_sellers))
        & (data["VIP Status"].isin(selected_vips))
    )
    
    filtered_data_all = data.loc[mask]
    filtered_data_success = filtered_data_all[filtered_data_all[DEALSTATUS] == "Won"]

    if filtered_data_all.empty:
        st.warning("No deals found for the selected sellers in the specified date range.")
    match len(selected_sellers):
        case 1:
            st.warning("one seller")
        case 2:
            # two tab
            st.warning("Multiple sellers selected.")
        case _:
            # page
            st.warning("More than two sellers selected.")


def main():
    st.set_page_config(page_title="تحلیل فروش", page_icon="📊", layout="wide")
    apply_custom_css()
    st.header("تحلیل فروش ")

    
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:    
        if 'data' in st.session_state and 'rfm_data'in st.session_state:
            data = st.session_state.data
            rfm_data = st.session_state.rfm_data

            sellers_options = data[DEALOWNER].unique().tolist()

            vip_options = sorted(rfm_data["VIP Status"].unique().tolist())
            select_all_vips = st.checkbox("انتخاب تمام وضعیت‌هایVIP", value=True, key="select_all_vips_seller_unified")
            selected_vips = (
                vip_options if select_all_vips else st.multiselect(
                "Select VIP Status:",
                options=vip_options,
                default=[],
                key="vips_multiselect_seller_unified",
                )
            )

            tab1, tab2 = st.tabs(["Seller Analysis", "RFM Analysis"])

            with tab1:
                with st.form(key="unified_seller_form", clear_on_submit=False):
                    selected_sellers = st.multiselect(
                    "Select Seller(s):",
                    options=sellers_options,
                    default=[],
                    key="unified_seller_multiselect",
                    )
                    min_date = data[DEALCREATEDDATE].min()
                    max_date = data[DEALCREATEDDATE].max()
                    if pd.isna(min_date) or pd.isna(max_date):
                        st.warning("Date range is invalid. Please check your data.")
                        st.stop()
                    min_date, max_date = min_date.date(), max_date.date()

                    start_date = st.date_input(
                    "Start Date", value=min_date, min_value=min_date, max_value=max_date, key="unified_seller_start_date"
                    )

                    end_date = st.date_input(
                    "End Date", value=max_date, min_value=min_date, max_value=max_date, key="unified_seller_end_date"
                    )
                    apply_unified_filters = st.form_submit_button(label="Apply Filters")

                if apply_unified_filters:
                    if not selected_vips:
                        st.warning("Please select at least one VIP status.")
                    else:
                        if not selected_sellers:
                            selected_sellers = sellers_options
                        
                        analysis_seller(
                            data,
                            rfm_data,
                            selected_sellers,
                            start_date,
                            end_date,
                            selected_vips
                        )
            with tab2:
                st.info("RFM Analysis will be implemented in future versions.")
        else:
            st.info('ابتدا داده را لود کنید')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')

if __name__ == "__main__":
    main()