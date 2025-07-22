import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="سرچ مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("ماژول استعلام و تحلیل مشتری")
    # Check data availability and login first
    if st.authentication_status:    
        if 'data' in st.session_state and st.session_state.data is not None and not st.session_state.data.empty:

            data = st.session_state.data
            rfm_data = st.session_state.rfm_data

            with st.form(key='customer_inquiry_form'):
                st.write("Enter at least one of the following fields to search for a customer:")

                col1, col2, col3 = st.columns(3)
                with col1:
                    input_last_name = st.text_input("Last Name")
                with col2:
                    input_phone_number = st.text_input("Phone Number")
                with col3:
                    input_customer_id = st.text_input("Customer ID")

                submit_inquiry = st.form_submit_button(label='Search')

            if submit_inquiry:
                if not input_last_name and not input_phone_number and not input_customer_id:
                    st.error("Please enter at least one of Last Name, Phone Number, or Customer ID.")
                else:
                    # Filter rfm_data based on inputs
                    inquiry_results = rfm_data.copy()

                    if input_last_name:
                        inquiry_results = inquiry_results[inquiry_results['Name'].str.contains(input_last_name, na=False)]
                    if input_phone_number:
                        inquiry_results = inquiry_results[inquiry_results['Phone Number'].astype(str).str.contains(input_phone_number)]
                    if input_customer_id:
                        inquiry_results = inquiry_results[inquiry_results['Code'].astype(str).str.contains(input_customer_id)]

                    if inquiry_results.empty:
                        st.warning("No customers found matching the given criteria.")
                    else:
                        st.success(f"Found {len(inquiry_results)} customer(s) matching the criteria.")

                        # Display customer information
                        for index, customer in inquiry_results.sort_values(by='Recency', ascending=True).iterrows():
                            st.markdown("---")
                            st.subheader(f"Customer ID: {customer['Code']}")
                            st.write(f"**Name:** {customer['Name']}")
                            st.write(f"**Phone Number:** {customer['Phone Number']}")
                            st.write(f"**VIP Status:** {customer['VIP Status']}")
                            st.write(f"**Recency:** {customer['Recency']} days")
                            st.write(f"**Frequency:** {customer['Frequency']}")
                            st.write(f"**Monetary:** {round(customer['Monetary'], 2)}")
                            st.write(f"**Segment:** {customer['RFM_segment_label']}")

                            # Fetch deal history
                            customer_deals = data[data['person_code'] == customer['Code']]
                            if customer_deals.empty:
                                st.write("No deal history available.")
                            else:
                                st.write("**Deal History:**")
                                deal_history = customer_deals[['deal_done_date', 'product_title', 'deal_value', 'deal_status']].copy()
                                # Adjust monetary values for display
                                deal_history['deal_value'] = deal_history['deal_value'].round(2)
                                st.dataframe(deal_history)

            # New Feature: Upload Excel or CSV File and Select Column Type
            st.subheader("Bulk Customer Inquiry")

            uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=['xlsx', 'csv'])
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        file_data = pd.read_csv(uploaded_file)
                    else:
                        file_data = pd.read_excel(uploaded_file)

                    st.write("File uploaded successfully!")
                    st.write("Columns in the file:", list(file_data.columns))

                    selected_column = st.selectbox("Select the column to search by", file_data.columns)

                    column_type = st.radio("What does the selected column contain?", ["Numbers", "Names", "IDs"])

                    if st.button("Search from File"):
                        if column_type == "Numbers":
                            matching_results = rfm_data[rfm_data['Phone Number'].astype(str).isin(file_data[selected_column].astype(str))]
                        elif column_type == "Names":
                            matching_results = rfm_data[rfm_data['Last Name'].isin(file_data[selected_column])]
                        elif column_type == "IDs":
                            matching_results = rfm_data[rfm_data['Code'].astype(str).isin(file_data[selected_column].astype(str))]
                        else:
                            matching_results = pd.DataFrame()

                        # Separate results into existing and new users
                        file_data['Exists_in_Dataset'] = file_data[selected_column].astype(str).isin(rfm_data['Code'].astype(str)) | \
                                                        file_data[selected_column].astype(str).isin(rfm_data['Phone Number'].astype(str)) | \
                                                        file_data[selected_column].isin(rfm_data['Last Name'])

                        existing_users = file_data[file_data['Exists_in_Dataset']]
                        new_users = file_data[~file_data['Exists_in_Dataset']]

                        # Display existing users
                        if not existing_users.empty:
                            st.success(f"Found {len(existing_users)} existing customer(s) from the uploaded file.")
                            st.dataframe(matching_results)

                        # Display new users (Acquisition users)
                        if not new_users.empty:
                            st.warning(f"Identified {len(new_users)} new user(s) not present in the dataset.")
                            st.subheader("Acquisition Users")
                            st.dataframe(new_users)

                except Exception as e:
                    st.error(f"Error processing file: {e}")
            
        else:
            st.warning('ابتدا از صفحه اصلی داده را بارگذاری کنید!')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')

if __name__ == "__main__":
    main()