import streamlit as st
import pandas as pd
import os
import sys
from io import BytesIO
from datetime import time, timedelta
# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.logger import logger
from utils.constants import COLOR_MAP
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

@st.cache_data
def convert_df(df):
    # Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="تحلیل چک‌این", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل وضعیت چک‌این مجتمع‌ها")
    # Check data availability and login first
    if st.authentication_status:    
        if 'data' in st.session_state and st.session_state.data is not None and not st.session_state.data.empty:

            data = st.session_state.data
            # Ensure 'checkin_date' is a proper datetime column
            data['checkin_date'] = pd.to_datetime(data['checkin_date'], errors='coerce')
            # Drop rows with no arrival date
            df_arrivals = data.dropna(subset=['checkin_date']).copy()

            if df_arrivals.empty:
                st.warning("No valid arrival dates found in the dataset.")
                st.stop()

            # Get the min/max arrival dates from the data
            min_date_dt = df_arrivals['checkin_date'].min()
            max_date_dt = df_arrivals['checkin_date'].max()

            if pd.isna(min_date_dt) or pd.isna(max_date_dt):
                st.warning("Date range is invalid. Please check your data.")
                st.stop()

            min_date = min_date_dt.date()
            max_date = max_date_dt.date()

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start of arrival date range",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )
            with col2:
                end_date = st.date_input(
                    "End of arrival date range",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )

            if start_date > end_date:
                st.error("Start date cannot be after end date.")
                st.stop()

            # 2) --- FILTERS ON COMPLEXES AND HOUSE TYPES (DEPENDENT) ---

            # Complex filter
            complex_options = sorted(df_arrivals['complex_name'].dropna().unique().tolist())
            select_all_complexes = st.checkbox("Select all complexes", value=True)
            if select_all_complexes:
                selected_complexes = complex_options
            else:
                selected_complexes = st.multiselect(
                    "Select complexes:",
                    options=complex_options,
                    default=[]
                )
            if not selected_complexes:
                st.warning("No complexes selected. Showing all by default.")
                selected_complexes = complex_options

            # Narrow down product options only to what's in the chosen complexes:
            temp_for_complex = df_arrivals[df_arrivals['complex_name'].isin(selected_complexes)]
            product_options = sorted(temp_for_complex['product_title'].dropna().unique().tolist())

            # House type (product) filter
            select_all_products = st.checkbox("Select all house types", value=True)
            if select_all_products:
                selected_products = product_options
            else:
                selected_products = st.multiselect(
                    "Select house types:",
                    options=product_options,
                    default=[]
                )
            if not selected_products:
                st.warning("No house types selected. Showing all by default.")
                selected_products = product_options

            # 3) --- APPLY ALL FILTERS ---
            mask = (
                (df_arrivals['checkin_date'].dt.date >= start_date) &
                (df_arrivals['checkin_date'].dt.date <= end_date) &
                (df_arrivals['complex_name'].isin(selected_complexes)) &
                (df_arrivals['product_title'].isin(selected_products))
            )
            filtered_df = df_arrivals[mask].copy()

            if filtered_df.empty:
                st.warning("No arrivals found for the selected date range and filters.")
                st.stop()

            # 4) --- COMPUTE THE METRICS FOR SCOREBOARD ---

            # 4.1) Total Arrivals
            total_arrivals = len(filtered_df)

            # 4.2) Average Weekly Arrivals
            date_range_days = (end_date - start_date).days + 1
            weeks_in_range = date_range_days / 7.0  # approximate
            if weeks_in_range > 0:
                avg_weekly = total_arrivals / weeks_in_range
            else:
                avg_weekly = 0

            # 4.3) Average Monthly Arrivals (approx by ~30.44 days/month)
            months_in_range = date_range_days / 30.44
            if months_in_range > 0:
                avg_monthly = total_arrivals / months_in_range
            else:
                avg_monthly = 0

            # 4.4) Average Length of Stay
            if 'nights' in filtered_df.columns:
                avg_stay = filtered_df['nights'].mean()
            else:
                avg_stay = 0

            # 4.5) Extensions count => "purchase_type" == "تمدید"
            filtered_df['IsExtension'] = filtered_df['purchase_type'].eq('تمدید')
            total_extensions = filtered_df['IsExtension'].sum()

            # 4.6) New arrivals = non-extensions
            total_new_arrivals = len(filtered_df[~filtered_df['IsExtension']])

            # 5) --- SCOREBOARD DISPLAY ---
            colA1, colA2, colA3 = st.columns(3)
            colA1.metric("Total Arrivals", f"{total_arrivals}")
            colA2.metric("Avg Weekly Arrivals", f"{avg_weekly:.2f}")
            colA3.metric("Avg Monthly Arrivals", f"{avg_monthly:.2f}")

            colB1, colB2, colB3 = st.columns(3)
            colB1.metric("Average Stay (Nights)", f"{avg_stay:.2f}")
            colB2.metric("Total Extensions", f"{total_extensions}")
            colB3.metric("Total New Arrivals", f"{total_new_arrivals}")

            st.write("---")

            # 6) --- TABLE BREAKDOWN BY HOUSE TYPE (product_title) ---
            st.subheader("Arrival Breakdown by House Type")

            grouped = filtered_df.groupby('product_title', dropna=False)

            house_type_data = []
            for house_type, subdf in grouped:
                arrivals_count = len(subdf)
                avg_stay_ht = subdf['nights'].mean() if 'nights' in subdf.columns else 0
                ext_count = subdf['IsExtension'].sum()
                new_count = len(subdf[~subdf['IsExtension']])

                house_type_data.append({
                    'House Type': house_type,
                    'Arrivals': arrivals_count,
                    'Avg Stay': round(avg_stay_ht, 2),
                    'Extensions': ext_count,
                    'New Arrivals': new_count,
                })

            df_house_type = pd.DataFrame(house_type_data)
            st.dataframe(df_house_type)

            csv_house_type = convert_df(df_house_type)
            excel_house_type = convert_df_to_excel(df_house_type)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="Download CSV",
                    data=csv_house_type,
                    file_name="arrival_by_house_type.csv",
                    mime="text/csv"
                )
            with c2:
                st.download_button(
                    label="Download Excel",
                    data=excel_house_type,
                    file_name="arrival_by_house_type.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # 7) --- MONTHLY COLUMN CHARTS FOR EACH COMPLEX ---
            # Each chart is a stacked bar of extension vs new arrivals, one bar per month.
            # Show the sub-segment counts *and* a total label on top of each stacked bar.

            st.write("---")
            st.subheader("Monthly Arrivals by Complex (Extensions vs. New)")

            # Create a 'Month' column (e.g. '2023-07') for grouping
            filtered_df['Month'] = filtered_df['checkin_date'].dt.to_period('M').astype(str)

            # We'll loop over each chosen complex and show a stacked column chart
            for cx in selected_complexes:
                sub_df = filtered_df[filtered_df['complex_name'] == cx]
                if sub_df.empty:
                    continue  # skip if no data for this complex

                # Group by Month + IsExtension to get counts
                monthly_counts = sub_df.groupby(['Month', 'IsExtension']).size().reset_index(name='ArrivalsCount')
                # Also get monthly totals (regardless of extension)
                monthly_totals = sub_df.groupby('Month').size().reset_index(name='TotalCount')

                # Plot a stacked bar chart using Plotly Express
                fig = px.bar(
                    monthly_counts,
                    x='Month',
                    y='ArrivalsCount',
                    color='IsExtension',  # True/False
                    barmode='stack',
                    title=f"Monthly Arrivals - {cx}",
                    text='ArrivalsCount'
                )

                # Position the sub-segment labels inside or outside
                fig.update_traces(textposition='inside')
                fig.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Number of Arrivals",
                    # Some spacing so top labels don't get cut off
                    margin=dict(t=80)
                )

                # Add an annotation with the total on top of each stacked column
                for _, row in monthly_totals.iterrows():
                    fig.add_annotation(
                        x=row['Month'],
                        y=row['TotalCount'],
                        text=str(row['TotalCount']),
                        showarrow=False,
                        font=dict(color='black', size=12),
                        xanchor='center',
                        yanchor='bottom'
                    )

                st.plotly_chart(fig, use_container_width=True)

            st.success("Arrival analysis completed.")
        else:
            st.warning('ابتدا از صفحه اصلی داده را بارگذاری کنید!')
    else:
        st.warning('ابتدا وارد اکانت خود شوید!')

if __name__ == "__main__":
    main()