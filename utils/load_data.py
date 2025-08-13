import re
from google.cloud import bigquery
import pandas as pd
import streamlit as st
from utils.logger import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time


# context manager

class BigQueryExecutor:
    def __init__(self):
        self.credentials = {
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


    @st.cache_data(ttl=3600, show_spinner=False)
    def exacute_query(_self, query: str) -> pd.DataFrame:
        """
        Execute a BigQuery query and return the results as a DataFrame.
        """
        start = time.time()
        try:
            query_preview = re.sub(r'\s+', ' ', str(query))
            if len(query_preview) > 200:
                query_preview = f"{query_preview[:100]} ... {query_preview[-100:]}"
            logger.info(f"Query: {query_preview}")
            
            client = bigquery.Client.from_service_account_info(_self.credentials)
            df = client.query(query).to_dataframe(create_bqstorage_client=False)
            client.close()
            
            end = time.time()
            logger.info(f"Query Executed: {query_preview} \n time:{end-start}s")
            print(f"Query Executed: {query_preview} \n time:{end-start}s")
            
            return df
        
        except Exception as e:
            logger.info(f"Error executing query: {str(e)}")
            print(f"Error executing query: {str(e)}")
            
            return None

    async def run_query_async(self, query: str, executor):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, self.exacute_query, query)
        return result

    async def run_queries_in_parallel(self, queries):
        executor = ThreadPoolExecutor(max_workers=5)
        tasks = [
            self.run_query_async(query, executor)
            for query in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def exacute_queries(self, queries: list[str]) -> None:
        try:
            results = asyncio.run(self.run_queries_in_parallel(queries))
            return results
        except Exception:
            return None

bq_executor = BigQueryExecutor()
exacute_queries = bq_executor.exacute_queries
exacute_query = bq_executor.exacute_query
if __name__ == "main":

    # For backward compatibility, you can instantiate and expose the main methods if needed:
    bq_executor = BigQueryExecutor()
    print(bq_executor.exacute_query("SELECT AVG(frequency) as avg_frequency FROM `customerhealth-crm-warehouse.didar_data.RFM_segments` WHERE phone_number IS NOT NULL"))
