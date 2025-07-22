from google.cloud import bigquery
import pandas as pd
import streamlit as st
from utils.logger import logger

credentials = {
            "type": st.secrets["GOOGLE_TYPE"],
            "project_id": st.secrets["GOOGLE_PROJECT_ID"],
            "private_key_id": st.secrets["GOOGLE_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GOOGLE_PRIVATE_KEY"],
            "client_email": st.secrets["GOOGLE_CLIENT_EMAIL"],
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "auth_uri": st.secrets["GOOGLE_AUTH_URI"],
            "token_uri": st.secrets["GOOGLE_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GOOGLE_AUTH_PROVIDER_X509_CERT_URL"],
            "client_x509_cert_url": st.secrets["GOOGLE_CLIENT_X509_CERT_URL"],
            "universe_domain": st.secrets["GOOGLE_UNIVERSE_DOMAIN"],
        }


@st.cache_data(ttl=3600, show_spinner=False)
def load_deals() -> pd.DataFrame:
    query = "SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`"
    logger.info(f"Executing BigQuery query: {query}")
    try:
        # Initialize BigQuery client
        client = bigquery.Client.from_service_account_info(credentials)
        
        # Execute query and return results as DataFrame using REST API only
        df = client.query(query).to_dataframe(create_bqstorage_client=False)
        return df
        
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

@st.cache_data(ttl=3600, show_spinner=False) 
def load_products() -> pd.DataFrame:
    query = "SELECT * FROM `customerhealth-crm-warehouse.didar_data.Products`"
    logger.info(f"Executing BigQuery query: {query}")
    try:
        client = bigquery.Client.from_service_account_info(credentials)
        df = client.query(query).to_dataframe(create_bqstorage_client=False)
        return df
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None
    
@st.cache_data(ttl=3600 , show_spinner=False)
def load_contacts() -> pd.DataFrame:
    query = "SELECT * FROM `customerhealth-crm-warehouse.didar_data.Contacts`"
    logger.info(f"Executing BigQuery query: {query}")
    try:
        client = bigquery.Client.from_service_account_info(credentials)
        df = client.query(query).to_dataframe(create_bqstorage_client=False)
        return df
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None
    

def insert_rfm(data: pd.DataFrame):
    pass