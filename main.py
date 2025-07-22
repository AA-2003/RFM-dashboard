import streamlit as st
import polars as pl
import pandas as pd
from utils.load_data import load_contacts, load_deals, load_products, insert_rfm
from utils.logger import logger
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.rfm_calculator import extract_vip_status, extract_blacklist_status, \
    calculate_rfm, normalize_rfm, rfm_segmentation
from utils.constants import DEALID, DEALSTATUS, CUSTOMERID, CUSTOMERNAME, DEALDONEDATE, DEALCREATEDDATE, NIGHTS, DEALVALUE, PRODUCTID
from utils.funcs import get_first_successful_deal_date_for_customers

# Constants
DATA_REFRESH_DAYS = 7   
def update_data():
    """Background function to update data. Only one update at a time."""
    try:
        logger.info("Starting background data update")
        st.session_state.deals = load_deals()
        st.session_state.products = load_products()
        st.session_state.deals = load_contacts()

        logger.info(f"Successfully updated data")
    except Exception as e:
        logger.error(f"Error during background data update: {str(e)}")

def convert_to_nights(val):
    """Convert Persian text or numeric to integer nights."""
    if pd.isna(val):
        return None
    val = str(val).strip().replace("شب", "").replace(" ", "")
    mapping = {
        "یک": 1,
        "دو": 2,
        "سه": 3,
        "چهار": 4,
        "پنج": 5,
        "شش": 6,
        "هفت": 7,
        "هشت": 8,
        "نه": 9,
        "ده": 10,
    }
    return mapping.get(val, pd.to_numeric(val, errors="coerce"))


@st.cache_data(ttl=10, show_spinner=False)
def preprocess_data(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    data['BlackList Status'] = extract_blacklist_status(data.get(CUSTOMERNAME, ''))
    data['VIP Status'] = extract_vip_status(data.get(CUSTOMERNAME, ''))
    data = data[~data[DEALDONEDATE].isna()]
    data = data[
        (~data['product_title']
        .str.contains(r'خودرو|صبحانه|نفر اضافه', regex=True, na=False))
    ]
    data["nights"] = data[NIGHTS].apply(convert_to_nights).astype(float)
    data[DEALDONEDATE] = pd.to_datetime(data[DEALDONEDATE])
    data[DEALVALUE] = data[DEALVALUE] / 10
    st.session_state.first_deal_date_by_customer = get_first_successful_deal_date_for_customers(data)
    return data


@st.cache_data(ttl=10, show_spinner=False)
def rfm_calculation_cache(data):
    """Calculate RFM metrics."""
    try:
        rfm_data = rfm_segmentation(calculate_rfm(data))
        norm = normalize_rfm(rfm_data)
        if rfm_data is not None:
            return rfm_data, norm
        else:
            st.error("خطا در محاسبه RFM")
            return None
    except Exception as e:
        st.error(f"خطا در محاسبه RFM : {e}")
        logger.error("Error in calcualting RFM:", e)
        return None

def main():
    """
    Main function that creates a Streamlit dashboard for Tehran Mobel sales analysis.
    """
    st.set_page_config(
        page_title="داشبورد تحلیل فروش و مشتری تهران مبله", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    apply_custom_css()
    st.title("داشبورد تحلیل فروش و مشتری تهران مبله")

    deals = load_deals()
    contacts = load_contacts()
    products = load_products()
    if 'auth' not in st.session_state or not st.session_state.auth:
        login()
    else:
        st.write(deals)
        # deals['Customer_name'] = deals[CUSTOMERID].map(contacts['Customer Id'])
        product_map = products.set_index('ProductCode')['ProductName']
        deals['Product_title'] = deals[PRODUCTID].map(product_map)
        
        if deals is not None and not deals.empty:
            # Display data summary
            st.subheader("📊 خلاصه داده‌ها")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("تعداد کل رکوردها", f"{len(deals):,}")
            with col2:
                last_deal_date = deals[DEALCREATEDDATE].max()
                st.metric("تاریخ آخرین معامله", last_deal_date.strftime("%Y-%m-%d") if pd.notna(last_deal_date) else "نامشخص")
        
        
        # preprocess data and calculate RFM
        # st.session_state.data = preprocess_data(deals)
        st.session_state.data = deals
        st.session_state.rfm_data, st.session_state.norm_rfm_data = rfm_calculation_cache(deals)

        # save rfm
        insert_rfm(st.session_state.rfm_data)


if __name__ == "__main__":
    main()