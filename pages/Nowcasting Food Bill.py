# pages/Nowcasting Food Bill.py

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model  import Ridge
import time 

# ------------------------------------------------------------------------------
# Button styling: colored backgrounds, shading, no-wrap
# ------------------------------------------------------------------------------
st.markdown("""
<style>
/* All selector buttons */
.stButton button {
    white-space: nowrap !important;
    background-color: #ffccbc !important;    /* light cyan */
    border-radius: 5px !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
    color: #000 !important;               /* dark teal text */
}
/* Highlight active button */
.stButton button:focus, .stButton button:hover {
    background-color: #ffab91 !important;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Country check (must be Egypt)
# --------------------------------------------------------------------------
if 'country' not in st.session_state or st.session_state['country'] != "Egypt":
    st.info("Forecasting is only available for Egypt.")
    st.stop()

# --------------------------------------------------------------------------
# 1. Load & train the model
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_and_train():
    df = pd.read_excel('Python Data New - Interface.xlsx')
    df['Year'] = pd.to_datetime(df['Year'], dayfirst=True)
    df = df.sort_values('Year').dropna(subset=[
        'Exchange Rate Growth','Global Inflation',
        'Egypt Inflation Lag1','Egypt Inflation Lag2',
        'Global Inflation Lag1','Global Inflation Lag2',
        'Egypt Inflation'
    ])
    features = [
        'Exchange Rate Growth','Global Inflation',
        'Egypt Inflation Lag1','Egypt Inflation Lag2',
        'Global Inflation Lag1'
    ]
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge(alpha=0.001, random_state=42))
    ])
    model.fit(df[features], df['Egypt Inflation'])
    return model, df

model, df_hist = load_and_train()

# --------------------------------------------------------------------------
# 2. Page title
# --------------------------------------------------------------------------
st.title("Nowcasting Food Bill — Egypt")

# --------------------------------------------------------------------------
# 3. Sidebar: configuration & inputs
# --------------------------------------------------------------------------
st.sidebar.header("Forecast Configuration")
n_periods = st.sidebar.number_input(
    "Months to forecast", min_value=1, max_value=60, value=1, step=1
)

last = df_hist.iloc[-1]
start_date = last['Year'] + pd.DateOffset(months=1)
forecast_dates = [start_date + pd.DateOffset(months=i) for i in range(n_periods)]

st.sidebar.subheader("Exchange Rate Growth")
exrg_future = [
    st.sidebar.number_input(
        f"Exchange Rate for {dt:%b %Y}", value=0.0,
        key=f"er_{dt.month}_{dt.year}"
    ) for dt in forecast_dates
]

st.sidebar.subheader("Global Inflation")
gi_future = [
    st.sidebar.number_input(
        f"Global Inflation for {dt:%b %Y}", value=0.0,
        key=f"gi_{dt.month}_{dt.year}"
    ) for dt in forecast_dates
]

if 'run_forecast' not in st.session_state:
    st.session_state['run_forecast'] = False
if st.sidebar.button("Run Forecast"):
    st.session_state['run_forecast'] = True
if not st.session_state['run_forecast']:
    st.info("Fill inputs on the left and click **Run Forecast**.")
    st.stop()

# --------------------------------------------------------------------------
# 4. Perform forecasting loop
# --------------------------------------------------------------------------
ei_lag1 = last['Egypt Inflation']
ei_lag2 = last['Egypt Inflation Lag1']
gi_lag1 = last['Global Inflation']


forecasts = []
for i, dt in enumerate(forecast_dates):
    feat = {
        'Exchange Rate Growth': exrg_future[i],
        'Global Inflation':     gi_future[i],
        'Egypt Inflation Lag1': ei_lag1,
        'Egypt Inflation Lag2': ei_lag2,
        'Global Inflation Lag1': gi_lag1
    }
    pred = model.predict(pd.DataFrame([feat]))[0]
    forecasts.append({'Year': dt, 'Inflation': pred})
    ei_lag2, ei_lag1 = ei_lag1, pred
    gi_lag1 = gi_future[i]

df_fc = pd.DataFrame(forecasts)

# --------------------------------------------------------------------------
# 5. View selector: two buttons in columns [1,3,8]
# --------------------------------------------------------------------------
if 'view_choice' not in st.session_state:
    st.session_state['view_choice'] = 'Yearly average'

col1, col2, _ = st.columns([1, 1, 8])
with col1:
    if st.button("Yearly average", key="btn_yearly"):
        st.session_state['view_choice'] = 'Yearly average'
with col2:
    if st.button("Monthly detail", key="btn_monthly"):
        st.session_state['view_choice'] = 'Monthly detail'

view = st.session_state['view_choice']

# --------------------------------------------------------------------------
# 6. Charts based on selection
# --------------------------------------------------------------------------
if view == 'Yearly average':
    st.subheader("Yearly Average Inflation: Historical vs Forecast")
    hist_avg = (
        df_hist.assign(Year=df_hist['Year'].dt.year)
               .groupby('Year', as_index=False)['Egypt Inflation']
               .mean()
               .rename(columns={'Egypt Inflation':'Inflation'})
    )
    hist_avg['Type'] = 'Historical'
    fc_avg = (
        df_fc.assign(Year=df_fc['Year'].dt.year)
             .groupby('Year', as_index=False)['Inflation']
             .mean()
    )
    fc_avg['Type'] = 'Forecast'
    plot_df = pd.concat([hist_avg, fc_avg], ignore_index=True)

    yearly = alt.Chart(plot_df).mark_line(interpolate='linear', strokeWidth=3).encode(
        x=alt.X('Year:O', axis=alt.Axis(title='Year', labelAngle=0)),
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Avg Inflation (%)')),
        color=alt.Color('Type:N',
                        scale=alt.Scale(domain=['Historical','Forecast'],
                                        range=['steelblue','orange']),
                        legend=alt.Legend(title=None, orient='top-right')),  
        strokeDash=alt.StrokeDash('Type:N',
                                  scale=alt.Scale(domain=['Historical','Forecast'],
                                                  range=[[],[4,4]]),
                                  legend=None)
    )
    pts = alt.Chart(plot_df[plot_df['Type']=='Forecast']).mark_point(size=100).encode(
        x='Year:O',
        y='Inflation:Q',
        color=alt.value('orange')
    )
    st.altair_chart((yearly + pts).properties(width=700, height=400),
                    use_container_width=True)

else:
    st.subheader("Monthly Inflation: Last Historical Year & Forecast")
    last_year = df_hist['Year'].dt.year.max()
    hist_monthly = (
        df_hist[df_hist['Year'].dt.year == last_year]
               [['Year','Egypt Inflation']]
               .rename(columns={'Egypt Inflation':'Inflation'})
    )
    hist_monthly['Type'] = 'Historical'
    fc_monthly = df_fc.copy()
    fc_monthly['Type'] = 'Forecast'
    monthly_df = pd.concat([hist_monthly, fc_monthly], ignore_index=True)

    base = alt.Chart(monthly_df).encode(
        x=alt.X('yearmonth(Year):T',
                axis=alt.Axis(title='', format='%b %Y', labelAngle=0)),
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Inflation Rate (%)')),
        color=alt.Color('Type:N',
                        scale=alt.Scale(domain=['Historical','Forecast'],
                                        range=['steelblue','orange']),
                        legend=alt.Legend(title=None, orient='top-right'))
    )
    line = base.mark_line(strokeWidth=3)
    pts = base.mark_point(size=60).transform_filter(alt.datum.Type=='Forecast')
    st.altair_chart((line + pts).properties(width=700, height=350), use_container_width=True)

# --------------------------------------------------------------------------
# 7. Forecast Results Table
# --------------------------------------------------------------------------
with st.expander("Show Forecast Data"):
    st.subheader("Forecast Results")
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']]
    st.table(table_df)
    st.download_button("Download CSV", table_df.to_csv().encode(),
                       file_name="inflation_forecasts.csv")

# --------------------------------------------------------------------------
# 8. Percentage Contributions
import plotly.graph_objects as go

# --------------------------------------------------------------------------
# 8. Percentage Contributions with interactive year selection and stacked bar chart
# --------------------------------------------------------------------------
st.subheader("Percentage Contributions")

# Load the full dataset for contributions
xlsx_path = "StackedBar - Copy.xlsx"
contrib_full_df = pd.read_excel(xlsx_path)

# Year selection dropdown
selected_year = st.selectbox(
    "Select Year for Contribution Breakdown",
    options=contrib_full_df['Year'].astype(str).tolist()
)

# Filter dataset for selected year
row = contrib_full_df[contrib_full_df['Year'].astype(str) == selected_year].iloc[0]
year_label = str(int(row["Year"]))

# Define desired legend order
desired_order = [
    "World Food Price (increase)",
    "World Food Price (decrease)",
    "Exchange Rate (depreciation)",
    "Exchange Rate (appreciation)",
    "Other Factors",
    "Unexplained (residuals)"
]

# Extract values in that order
cats = []
vals = []
for cat in desired_order:
    if cat in row.index:
        cats.append(cat)
        vals.append(float(row[cat]))

# Split into negative and positive preserving order
neg_data = []
pos_data = []
for cat, val in zip(cats, vals):
    if val < 0:
        neg_data.append((cat, val))
    else:
        pos_data.append((cat, val))

# Define colors
color_map = {
    "World Food Price (increase)": "#1F3B73",
    "World Food Price (decrease)": "#8B0000",
    "Exchange Rate (depreciation)": "#89CFF0",
    "Exchange Rate (appreciation)": "#F08080",
    "Other Factors": "#FFB347",
    "Unexplained (residuals)": "#FF8C00"
}

# Build Plotly figure
fig = go.Figure()

neg_base = 0.0
for cat, val in neg_data:
    fig.add_trace(go.Bar(
        y=[year_label],
        x=[val],
        name=cat,
        orientation='h',
        marker=dict(color=color_map[cat]),
        base=[neg_base],
        customdata=[val],
        hovertemplate=f"<b>{cat}</b><br>Value: %{{customdata}}<extra></extra>"
    ))
    neg_base += val

pos_base = 0.0
for cat, val in pos_data:
    fig.add_trace(go.Bar(
        y=[year_label],
        x=[val],
        name=cat,
        orientation='h',
        marker=dict(color=color_map[cat]),
        base=[pos_base],
        customdata=[val],
        hovertemplate=f"<b>{cat}</b><br>Value: %{{customdata}}<extra></extra>"
    ))
    pos_base += val

fig.update_layout(
    title=dict(
        text="Decomposition of Domestic Food Price Change in Egypt",
        x=0.5, xanchor="center",
        font=dict(size=16)
    ),
    barmode='relative',
    template='plotly_white',
    height=350,
    margin=dict(l=40, r=40, t=60, b=80),
    xaxis=dict(
        title="",
        showline=True,
        linecolor="black",
        linewidth=1,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="black",
        showgrid=False,
        tickmode='array',
        tickvals=[-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100, 120, 140, 160],
        ticks="outside",
        tickfont=dict(size=12)
    ),
    yaxis=dict(
        title="",
        tickmode='array',
        tickvals=[year_label],
        ticktext=[year_label],
        ticks="",
        showgrid=False,
        showline=False
    ),
    legend=dict(
        orientation="h",
        y=-0.25,
        x=0.5,
        xanchor="center",
        yanchor="top",
        font=dict(size=12),
        bgcolor="rgba(0,0,0,0)"
    ),
    showlegend=True
)

st.plotly_chart(fig, use_container_width=True)

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
# 11. Subsidy Calculation Based on Inflation Average
# --------------------------------------------------------------------------

# Calculate the average inflation from the forecasted values
avg_inflation = np.mean(df_fc['Inflation'])

# Apply the multiplier to adjust the value based on inflation
adjusted_value = 117.675118055328 * (1 + avg_inflation / 100)

# Calculate the subsidy
subsidy = (adjusted_value * 133278000000) / 117.675118055328

# Display the subsidy in a formatted way
st.subheader("Subsidy Calculation")

# Display the subsidy in a more noticeable format
subsidy_formatted = f"${subsidy / 1e9:.2f} Billion"  # Display in billions

st.markdown(f"**Subsidy Value:** {subsidy_formatted}")

# --------------------------------------------------------------------------
# 11. Visualization - Bar Graph to Show Subsidy Value
# --------------------------------------------------------------------------

# Prepare data for the bar graph
subsidy_data = pd.DataFrame({
    "Category": ["Subsidy Value"],
    "Amount": [subsidy]
})

# Create a bar chart to visualize the subsidy value
import plotly.express as px

fig = px.bar(subsidy_data, x="Category", y="Amount", 
             title="Subsidy Calculation Visualization", 
             labels={"Amount": "Subsidy Value (in billions)"}, 
             color="Category")

fig.update_layout(
    xaxis_title="",
    yaxis_title="Subsidy Amount (in billions)",
    template='plotly_white',
    height=400
)

# Show the bar chart
st.plotly_chart(fig, use_container_width=True)
