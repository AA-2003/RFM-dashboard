import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from utils.logger import logger
from utils.constants import DEALID, DEALSTATUS, DEALDONEDATE, DEALVALUE, \
    CUSTOMERID, CUSTOMERNAME, CUSTOMERPHONE, CHECKINDATE, CHECKOUTDATE, COMPLEX, PRODUCTTITLE, NIGHTS

@st.cache_data(ttl=0, show_spinner=False)
def calculate_rfm(data: pd.DataFrame, today=None):
    """
    Calculate RFM (Recency, Frequency, Monetary) metrics for customer segmentation.
    """
    try:
        # Convert deal values from Rial to Toman
        data[DEALVALUE] = pd.to_numeric(data[DEALVALUE], errors='coerce').fillna(0).astype(int) / 10

        # Set reference date
        today = pd.to_datetime(today) if today is not None else pd.Timestamp.now().replace(tzinfo=None)

        # Filter successful deals
        successful_deals = data[data[DEALSTATUS] == "Won"].copy()
        # Calculate core RFM metrics
        rfm_data = successful_deals.groupby(CUSTOMERID).agg({
            CUSTOMERNAME: 'first',
            CUSTOMERPHONE: 'first',
            DEALDONEDATE: lambda x: (
                today - pd.to_datetime(x, format="%m/%d/%Y %H:%M").max().replace(tzinfo=None)
            ).days,
            DEALID: 'count',
            DEALVALUE: 'sum',
            NIGHTS: 'sum',
            'VIP Status': 'first'
        }).reset_index()


        # Standardize column names
        column_mapping = {
            CUSTOMERID: 'Code',
            CUSTOMERNAME: 'Name',
            CUSTOMERPHONE: 'Phone Number',
            DEALDONEDATE: 'Recency',
            DEALID: 'Frequency',
            DEALVALUE: 'Monetary',
            NIGHTS: 'Total Nights'
        }
        rfm_data.rename(columns=column_mapping, inplace=True)

        # Calculate derived metrics
        rfm_data['average stay'] = rfm_data['Total Nights'] / rfm_data['Frequency']

        # Get customer's latest transaction details
        last_deals = (successful_deals
                     .sort_values(DEALDONEDATE)
                     .groupby(CUSTOMERID)
                     .last()
                     .reset_index())

        # Add check-in/out dates
        stay_columns = [CHECKINDATE, CHECKOUTDATE]
        rfm_data = rfm_data.merge(
            last_deals[[CUSTOMERID] + stay_columns],
            left_on='Code',
            right_on=CUSTOMERID,
            how='left'
        )

        # Calculate current stay status
        checkin_dates = pd.to_datetime(rfm_data[CHECKINDATE], errors='coerce').dt.tz_localize(None)
        checkout_dates = pd.to_datetime(rfm_data[CHECKOUTDATE], errors='coerce').dt.tz_localize(None)
        today_naive = today.tz_localize(None) if today.tzinfo else today
        rfm_data['Is staying'] = (
            (checkin_dates.notna()) & (checkout_dates.notna()) &
            (today_naive >= checkin_dates) & (today_naive <= checkout_dates)
        )
        
        rfm_data['Is Monthly'] = rfm_data['average stay'] > 15

        # Add favorite and last complex/type info
        for metric in [(COMPLEX, 'مجتمع'), (PRODUCTTITLE, 'تیپ')]:
            field, label = metric
            
            # Calculate favorite
            favorite = (successful_deals[successful_deals[field].notna()]
                      .groupby([CUSTOMERID, field])
                      .size()
                      .reset_index(name='count')
                      .sort_values([CUSTOMERID,'count'], ascending=[True, True])
                      .groupby(CUSTOMERID)
                      .last()
                      .reset_index()
                      .rename(columns={field: f'{label} محبوب'}))
            
            # Get last used
            last = (last_deals[[CUSTOMERID, field]]
                   .rename(columns={field: f'آخرین {label}'}))

            # Merge both
            for df in [favorite, last]:
                rfm_data = rfm_data.merge(
                    df, 
                    left_on='Code',
                    right_on=CUSTOMERID,
                    how='left'
                )
            rfm_data.drop(columns=[CUSTOMERID+'_x', CUSTOMERID+'_y'], inplace=True)

        # Rename date columns
        rfm_data.rename(columns={
            CHECKINDATE: 'تاریخ ورود آخرین رزرو',
            CHECKOUTDATE: 'تاریخ خروج آخرین رزرو',
        }, inplace=True)


        rfm_data = rfm_data[(rfm_data['تاریخ ورود آخرین رزرو'] != str(0)) & 
                            (rfm_data['تاریخ خروج آخرین رزرو'] != str(0))]


        rfm_data.drop(columns=[CUSTOMERID, 'count_y', 'count_x'], inplace=True)

        return rfm_data

    except Exception as e:
        logger.error(f"Error calculating RFM metrics: {str(e)}")
        st.error(f"Error calculating RFM metrics: {str(e)}")
        raise

def normalize_rfm(data):
    """
    Normalize RFM metrics using MinMaxScaler.
    """
    try:
        df = data.copy()
        scaler = MinMaxScaler()
        metrics = ['Recency', 'Frequency', 'Monetary', 'Total Nights']
        normalized_cols = [f'{col}_norm' for col in metrics]
        
        df[normalized_cols] = scaler.fit_transform(df[metrics])
        df['Recency_norm'] = 1 - df['Recency_norm']  # Invert recency
        return df
    except Exception as e:
        logger.error(f"Error normalizing RFM metrics: {str(e)}")
        raise

def rfm_segmentation(data):
    """
    Segment customers based on RFM metrics and behavioral patterns.
    """
    try:
        df = data.copy()
        
        # Filter valid data
        df = df[(df['Monetary'] > 0) & 
                (df['Frequency'] > 0) 
                # df['Name'].notnull()].copy()
                ].copy()

        # Calculate derived metrics
        df['average_stay'] = df['Total Nights'] / df['Frequency']
        today = pd.to_datetime(datetime.now()).normalize()
        exits = pd.to_datetime(df['تاریخ خروج آخرین رزرو'], errors='coerce').dt.tz_localize(None)
        exit_days = (today - exits).dt.days.clip(lower=0)

        # Define segments constants
        SEGMENTS = {
            'NEW_DAYS': 90,
            'AT_RISK_DAYS': 180,
            'CHURN_DAYS': 365
        }

        EMOJI_MAP = {
            'Champions': '👑',
            'Big Spender': '💰',
            'Loyal Customers': '❤️',
            'Curious Customers': '🧐',
            'Potential': '✨',
            'Low Value': '🗑️',
            'Reliable Customers': '🔒'
        }

        # Calculate percentiles excluding outliers
        def get_percentiles(df, columns):
            outliers = {col: df[col].quantile(0.99) for col in columns}
            non_outliers = df[
                df[columns].apply(
                    lambda x: x <= outliers[x.name]
                ).all(axis=1)
            ]
            
            percentiles = {}
            for col in columns:
                for p in [0.20, 0.33, 0.50, 0.80, 0.95]:
                    percentiles[f'{col}_{int(p*100)}'] = non_outliers[col].quantile(p)
            return percentiles

        p = get_percentiles(df, ['Frequency', 'Monetary', 'average_stay'])

        def get_customer_segment(row, exit_d):
            """Determine customer segment based on RFM metrics."""
            R, F, M, A = row['Recency'], row['Frequency'], row['Monetary'], row['average_stay']
            
            # Base segment
            if F >= p['Frequency_80'] and M >= p['Monetary_95']:
                base = 'Champions'
            elif (A >= p['average_stay_95'] or F <= p['Frequency_20']) and M >= p['Monetary_95']:
                base = 'Big Spender'
            elif F >= 5 and M >= p['Monetary_50']:
                base = 'Loyal Customers'
            elif F <= p['Frequency_50'] and (A >= p['average_stay_50'] or M >= p['Monetary_50']):
                base = 'Curious Customers'
            elif F >= p['Frequency_80']:
                base = 'Reliable Customers'
            elif F > p['Frequency_50'] or M > p['Monetary_50'] or A > p['average_stay_50']:
                base = 'Potential'
            else:
                base = 'Low Value'

            # Recency prefix
            if R <= SEGMENTS['NEW_DAYS'] and F == 1:
                prefix = 'New '
            elif R > SEGMENTS['CHURN_DAYS'] and exit_d > 0:
                prefix = 'Lost '
            elif R > SEGMENTS['AT_RISK_DAYS'] and R <= SEGMENTS['CHURN_DAYS'] and exit_d > SEGMENTS['NEW_DAYS']:
                prefix = 'At Risk '
            else:
                prefix = ''

            return f"{prefix}{EMOJI_MAP[base]} {base}".strip()

        df['RFM_segment_label'] = df.apply(
            lambda row: get_customer_segment(row, exit_days[row.name]), axis=1)
        
        return df.drop(columns=['average_stay'], errors='ignore')
    
    except Exception as e:
        logger.error(f"Error in RFM segmentation: {str(e)}")
        raise