import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query

def main():
    """Main function """
    
    st.set_page_config(page_title="سرچ مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("ماژول استعلام و تحلیل مشتری")
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:    
        with st.form(key='customer_inquiry_form'):
            st.write("برای جستجوی مشتری، حداقل یکی از فیلدهای زیر را وارد کنید: ")

            col1, col2, col3 = st.columns(3)
            with col1:
                input_last_name = st.text_input("نام")
            with col2:
                input_phone_number = st.text_input("شماره تلفن")
            with col3:
                input_customer_id = st.text_input("کد دیدار مشتری")

            submit_inquiry = st.form_submit_button(label='جست‌وجو')

        if submit_inquiry:
            if not input_last_name and not input_phone_number and not input_customer_id:
                st.error("حداقل یکی از موارد را پر کنید.")
            else:
                # Build filters safely and correctly
                filters = []
                if input_last_name:
                    filters.append(f"Last_name LIKE '%{input_last_name}%'")
                if input_phone_number:
                    filters.append(f"phone_number LIKE '%{input_phone_number}%'")
                if input_customer_id:
                    try:
                        customer_id_int = int(input_customer_id)
                        filters.append(f"customer_id = {customer_id_int}")
                    except ValueError:
                        st.error("کد مشتری باید عدد باشد.")
                        filters.append("1=0")  # Prevent query if invalid

                # Always require last_name is not null or empty
                filters.insert(0, "Last_name IS NOT NULL AND Last_name != ''")
                where_clause = " AND ".join(filters)

                query = f"""
                    SELECT * FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                    WHERE {where_clause}
                    ORDER BY recency
                """
                rfm_data = exacute_query(query)

                if rfm_data is None or rfm_data.empty:
                    st.info('هیچ مشتری با این مشخصات وجود ندارد!!!')
                else:
                    ids = rfm_data['customer_id'].dropna().astype(int).unique().tolist()
                    if ids:
                        deals_query = f"""
                            SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                            WHERE Customer_id IN ({', '.join(str(id) for id in ids)})
                        """
                    else:
                        deals_query = None
                    deals = exacute_query(deals_query)
                    for _, customer in rfm_data.iterrows():
                        st.markdown("---")
                        # Display customer info in columns for better layout
                        info1, info2, info3 = st.columns([2, 2, 2])
                        with info1:
                            st.markdown(f"**کد دیدار مشتری:**<br>{customer['customer_id']}", unsafe_allow_html=True)
                            st.markdown(f"**نام:**<br>{customer['first_name'] if customer['first_name'] is not None else ''  } {customer['last_name']}", unsafe_allow_html=True)
                            st.markdown(f"**شماره همراه:**<br>{customer['phone_number']}", unsafe_allow_html=True)
                        with info2:
                            st.markdown(f"**تازگی (Recency):**<br>{customer['recency']} روز", unsafe_allow_html=True)
                            st.markdown(f"**تعداد خرید (Frequency):**<br>{customer['frequency']}", unsafe_allow_html=True)
                            st.markdown(f"**ارزش خرید (Monetary):**<br>{round(customer['monetary'], 2)}", unsafe_allow_html=True)
                        with info3:
                            st.markdown(f"**سگمنت RFM:**<br><span style='color:#2b9348;font-weight:bold'>{customer['rfm_segment']}</span>", unsafe_allow_html=True)

                        # Show deals history in an expandable section
                        customer_deals = deals[deals['Customer_id'] == customer['customer_id']]
                        with st.expander("مشاهده سوابق معامله", expanded=not customer_deals.empty):
                            if customer_deals.empty:
                                st.info("سابقه معامله‌ای وجود ندارد.")
                            else:
                                # Show only relevant columns and format
                                show_cols = [
                                    col for col in [
                                        "DealID", "DealCreateDate", "DealValue", "Status", "DealChannel", "DealType", "Nights", "DealExpert"
                                    ] if col in customer_deals.columns
                                ]
                                deals_to_show = customer_deals[show_cols].copy()
                                deals_to_show['DealValue'] = deals_to_show['DealValue'].round(2)
                                deals_to_show = deals_to_show.sort_values(by="DealCreateDate", ascending=False)
                                st.dataframe(
                                    deals_to_show,
                                    use_container_width=True,
                                    hide_index=True
                                )
    else:
        login()

if __name__ == "__main__":
    main()