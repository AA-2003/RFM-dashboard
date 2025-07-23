import streamlit as st
import polars as pl
import pandas as pd
from utils.load_data import load_contacts, load_deals, load_products, insert_rfm
from utils.logger import logger
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.rfm_calculator import extract_vip_status, extract_blacklist_status, \
    calculate_rfm, normalize_rfm, rfm_segmentation
from utils.constants import DEALID, DEALSTATUS, CUSTOMERID, CUSTOMERNAME, CUSTOMERPHONE, DEALDONEDATE, DEALCREATEDDATE, NIGHTS, DEALVALUE, PRODUCTID, PRODUCTTITLE, COMPLEX
from utils.funcs import get_first_successful_deal_date_for_customers

# Constants
DATA_REFRESH_DAYS = 7   

@st.cache_data(ttl=600, show_spinner=False)
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

@st.cache_data(ttl=600, show_spinner=False)
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


@st.cache_data(ttl=600, show_spinner=False)
def map_complex(name):
    name = str(name) if name is not None else ''
    if not name or name.lower() == 'nan':
        return ''

    if 'میرداماد' in name:
        return 'میرداماد'
    elif 'ویلا' in name or 'نجات‌اللهی' in name:
        return 'ویلا'
    elif 'جردن' in name:
        return 'جردن'
    elif 'ترنج' in name:
        return 'ترنج'
    elif 'گاندی' in name:
        return 'گاندی'
    elif 'نوفل' in name:
        return 'نوفل'
    elif 'پاسداران' in name or 'پاسدذاران' in name:
        return 'پاسداران'
    elif 'مصلی' in name or 'نیلوفر' in name:
        return 'مصلی'
    elif 'کشاورز' in name or 'کشاور ز' in name:
        return 'کشاورز'
    elif 'اشرفی' in name:
        return 'اشرفی'
    elif 'پارک وی' in name or 'پارک‌وی' in name:
        return 'پارک وی'
    elif 'ولیعصر' in name:
        return 'ولیعصر'
    elif 'اوین' in name:
        return 'اوین'
    elif 'ونک' in name:
        return 'ونک'
    elif 'جمهوری' in name or 'جموری' in name:
        return 'جمهوری'
    elif 'ولنجک' in name:
        return 'ولنجک'
    elif 'بهشتی' in name:
        return 'بهشتی'
    elif 'مرزداران' in name or 'مرزرداران' in name:
        return 'مرزداران'
    elif 'کوروش' in name:
        return 'کوروش'
    elif 'دلچه' in name:
        return 'دلچه'
    elif 'شریعتی' in name:
        return 'شریعتی'
    else:
        return 'نامشخص'
    

@st.cache_data(ttl=600, show_spinner=False)
def preprocess_data(data: pd.DataFrame, products: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    
    # map products and customer names
    product_map = products.drop_duplicates(subset='ProductCode').set_index('ProductCode')['ProductName']
    customer_map = contacts.drop_duplicates(subset='Customer_ID').set_index('Customer_ID')['DisplayName']

    data[PRODUCTTITLE] = data[PRODUCTID].map(product_map)
    data[CUSTOMERNAME] = data[CUSTOMERID].map(customer_map)

    data = data[data[CUSTOMERNAME].notna()].copy()
    data[COMPLEX] = data[PRODUCTTITLE].map(map_complex)

    data.loc[:, 'BlackList Status'] = extract_blacklist_status(data.get(CUSTOMERNAME, ''))
    data.loc[:, 'VIP Status'] = extract_vip_status(data.get(CUSTOMERNAME, ''))
    data = data[~data[DEALDONEDATE].isna()].copy()
    data = data[
        (~data[PRODUCTTITLE]
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
    # st.write(deals)

    contacts = load_contacts()
    # st.write(contacts)

    products = load_products()
    # st.write(products)

    if 'auth' not in st.session_state or not st.session_state.auth:
        login()
    else:
        print("preprocess data and calculate RFM")
        # preprocess data and calculate RFM
        st.session_state.data = preprocess_data(deals, products, contacts)
        st.session_state.rfm_data, st.session_state.norm_rfm_data = rfm_calculation_cache(st.session_state.data)
        # save rfm
        insert_rfm(st.session_state.rfm_data)


        if deals is not None and not deals.empty:
            # Display data summary
            st.subheader("📊 خلاصه داده‌ها")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("تعداد کل رکوردها", f"{len(st.session_state.data):,}")
            with col2:
                last_deal_date = st.session_state.data[DEALCREATEDDATE].max()
                st.metric("تاریخ آخرین معامله", last_deal_date.strftime("%Y-%m-%d") if pd.notna(last_deal_date) else "نامشخص")


if __name__ == "__main__":
    main()