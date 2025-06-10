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


# 11. Subsidy Calculation Based on Inflation Average
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
st.subheader("Subsidy Responsiveness")

# Display the subsidy in a more noticeable format
subsidy_formatted = f"{subsidy / 1e9:.2f} Billion Egyptian Pounds"  # Display in billions

st.markdown(f"**Subsidy Value:** {subsidy_formatted}")

# --------------------------------------------------------------------------
# 11. Visualization - Bar Graph to Show Subsidy Value and Reference Value
# --------------------------------------------------------------------------

# Prepare data for the bar graph (Subsidy value and Reference value of 140B)
subsidy_data = pd.DataFrame({
    "Category": ["Subsidy Value", "Reference Value (140B)"],
    "Amount": [subsidy / 1e9, 140]  # Divide subsidy by 1e9 to convert to billions
})

# Create a horizontal bar chart to visualize the subsidy value alongside the reference value
import plotly.express as px

fig = px.bar(subsidy_data, x="Amount", y="Category", 
             title="Subsidy Calculation Visualization", 
             labels={"Amount": "Amount (in billions EGP)"}, 
             orientation='h',  # Set orientation to horizontal
             color="Category",  # Color by category
             color_discrete_map={"Subsidy Value": "#FF8C00",  # Orange for Subsidy
                                 "Reference Value (140B)": "#D3D3D3"})  # Light grey for Reference

# Update the layout
fig.update_layout(
    xaxis_title="Amount (in billions EGP)",
    yaxis_title="",
    template='plotly_white',
    height=400,
    showlegend=False,  # Hide the legend
    hoverlabel=dict(namelength=0)  # Removes the category name from the hover text
)

# Update hovertemplate to customize the hover text (convert to billions and display as B)
fig.update_traces(
    hovertemplate="Amount: %{x:,.2f}B EGP"  # Shows the amount in billions with "B" suffix and two decimal places
)

# Show the bar chart
st.plotly_chart(fig, use_container_width=True)