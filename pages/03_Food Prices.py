# 8. Percentage Contributions
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model  import Ridge
import time 

# --------------------------------------------------------------------------
# 8. Percentage Contributions with interactive year selection and stacked bar chart
# --------------------------------------------------------------------------
st.subheader("Percentage Contributions")

# Grab the forecast dataframe you computed earlier
if 'df_fc' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first.")
    st.stop()

df_fc = st.session_state['df_fc']

# Grab forecast_dates from session state
if 'forecast_dates' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first to generate the forecast.")
    st.stop()

forecast_dates = st.session_state['forecast_dates']

# Grab start_date from session state
if 'start_date' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first to generate the forecast.")
    st.stop()

start_date = st.session_state['start_date']

# Now you can safely use forecast_dates in your code

# 7. Forecast Results Table
# --------------------------------------------------------------------------
with st.expander("Show Forecast Data"):
    st.subheader("Forecast Results")
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']]
    st.table(table_df)
    st.download_button("Download CSV", table_df.to_csv().encode(),
                       file_name="inflation_forecasts.csv")

# --------------------------------------------------------------------------

# Load the full dataset for contributions
xlsx_path = "StackedBar - Copy.xlsx"
contrib_full_df = pd.read_excel(xlsx_path)

# --------------------------------------------------------------------------
# 9. Food Price Adjustment based on Forecast Inflation
# --------------------------------------------------------------------------
# 9. Food Price Adjustment based on Forecast Inflation
# --------------------------------------------------------------------------

# Load the FoodPricesTest dataset (containing food names and prices)
food_prices_df = pd.read_excel("FoodPricesTest.xlsx")

# Fetch the inflation rate for the forecasted months using the forecasted inflation values from df_fc
# Calculate the average inflation for the forecast period
inflation_rate = np.mean(df_fc['Inflation']) / 100  # Convert percentage to decimal

# Display the inflation rate to verify if the correct value is being used
st.markdown(f"**Inflation Rate Used for Adjustment**: {inflation_rate * 100:.2f}%")

# Adjust food prices based on the forecasted inflation
food_prices_df['Adjusted Price'] = food_prices_df['Price'] * (1 + inflation_rate)

# Calculate the total value (Adjusted Price * Quantity)
food_prices_df['Total Value'] = food_prices_df['Adjusted Price'] * food_prices_df['Quantity']
food_prices_df2= food_prices_df
# --------------------------------------------------------------------------
# Interactive Category Filter
# --------------------------------------------------------------------------

# Get the unique food categories
categories = food_prices_df['Category'].unique()

# Dropdown to select category
selected_category = st.selectbox(
    "Select Food Category",
    options=['All Categories'] + list(categories)
)

# Filter the dataframe based on the selected category
if selected_category != 'All Categories':
    food_prices_df = food_prices_df[food_prices_df['Category'] == selected_category]

# --------------------------------------------------------------------------
# Interactive Year Selection (if forecast > 12 months)
# --------------------------------------------------------------------------

# Calculate the number of full years and extra months in the forecast
num_months = len(forecast_dates)
full_years = num_months // 12  # Full years
extra_months = num_months % 12  # Extra months after full years

# Prepare a list of years for which to show food prices
years_to_show = []
if full_years > 0:
    years_to_show.append(f"Year 1: 2025 (Forecast for {full_years} year{'s' if full_years > 1 else ''})")

# If there are extra months, they will be in the next year (2026, for example)
if extra_months > 0:
    years_to_show.append(f"Year {full_years + 1}: {2025 + full_years} (Forecast for {extra_months} month{'s' if extra_months > 1 else ''})")


############################################
# Year selection dropdown
selected_year = st.selectbox(
    "Select Year for Food Price Breakdown",
    options=years_to_show
)

# --------------------------------------------------------------------------
# Filter food prices based on selected year
# --------------------------------------------------------------------------

# If user selects Year 1, filter only first set of months (this could be year or remaining months)
if selected_year.startswith("Year 1"):
    adjusted_prices_for_year = food_prices_df.copy()
    year_display = start_date.year  # Display the correct year
elif selected_year.startswith("Year 2"):
    adjusted_prices_for_year = food_prices_df.copy()
    year_display = start_date.year + 1  # Display the second year for remaining months

# Adjust the year displayed by subtracting 1 if forecast is under 12 months
if num_months <= 12:
    year_display = year_display  # Adjust the year to display correctly

# --------------------------------------------------------------------------
# Plot the bar chart for adjusted food prices for selected year
# --------------------------------------------------------------------------
st.subheader(f"Adjusted Food Prices for Year {year_display}")

# Create the horizontal bar chart for food prices (Total Value)
fig = go.Figure()

fig.add_trace(go.Bar(
    y=adjusted_prices_for_year['Food Name'],
    x=adjusted_prices_for_year['Total Value'],
    orientation='h',
    marker=dict(color='#FF8C00'),
    hovertemplate="<b>%{y}</b><br>Total Value:%{x:,.0f}<extra></extra>"
))

# Update layout
fig.update_layout(
    title=f"Import Bill adjusted for inflation by category: {year_display} -Forecasted",
    xaxis=dict(title=""),
    yaxis=dict(title=""),
    showlegend=False,
    template='plotly_white',
    height=500
)

st.plotly_chart(fig, use_container_width=True)


# 10. Summarize and Calculate NIR for 2025 (Total value based on all data)
# --------------------------------------------------------------------------
# 10. Summarize and Calculate NIR for 2025 (Total value based on all data)
# --------------------------------------------------------------------------

# Calculate the total price of all food items (using all the data, regardless of category)
total_value_all_food = food_prices_df2['Total Value'].sum()

# Subtract 16,046,071,327 from the total value
adjusted_value = total_value_all_food - 16046071327

# Divide by 1000 (to convert from billions to millions)
adjusted_value_in_millions = adjusted_value / 1000000

# Add 72,134 to the result
adjusted_value_plus_addition = adjusted_value_in_millions + 72134

# Divide by 12 (to get the monthly value)
monthly_value = adjusted_value_plus_addition / 12

# Finally, divide by 46,385 (to get the NIR)
nir_2025 = 46385 / monthly_value

# Format the values to make them stand out (in billions for simplicity)
total_value_all_food_formatted = f"${total_value_all_food / 1e9:.2f} Billion"
nir_2025_formatted = f"{nir_2025:.2f}"

# Display the values in a statement with enhanced focus and larger font
st.markdown(f"""
    <style>
        .result-box {{
            background-color: #f2f2f2;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }}
        .result-value {{
            font-size: 36px;
            color: #ff5733;
        }}
    </style>
    <div class="result-box">
        <p><strong>Total Food Import Bill:</strong></p>
        <p class="result-value">{total_value_all_food_formatted}</p>
        <p><strong>Months of Imports Covered by Reserves for 2025:</strong></p>
        <p class="result-value">{nir_2025_formatted}</p>
    </div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------