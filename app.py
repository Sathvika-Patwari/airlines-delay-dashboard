import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page config ---
st.set_page_config(page_title="US Airline Delays", layout="wide")

# --- Title ---
st.title("✈️ US Airline Delays Dashboard")

# --- Load & cache data ---
@st.cache_data
def load_data():
    df = pd.read_csv("merged_airline_airport_data.csv")
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

unique_years = sorted(df['year'].unique())
selected_years = st.sidebar.multiselect("Select Year(s)", unique_years, default=unique_years)

# Month filter clean (Jan - Dec)
month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
selected_months = st.sidebar.multiselect("Select Month(s)", month_order, default=month_order)

delay_type_options = {
    'Carrier Delay': 'carrier_delay',
    'Weather Delay': 'weather_delay',
    'NAS Delay': 'nas_delay',
    'Security Delay': 'security_delay',
    'Late Aircraft Delay': 'late_aircraft_delay',
    'Total Delay': 'Total_Delay'
}
selected_delay_types = st.sidebar.multiselect("Select Delay Type(s)", list(delay_type_options.keys()), default=["Total Delay"])

if "Total Delay" in selected_delay_types and len(selected_delay_types) > 1:
    st.sidebar.warning("Total Delay selected. Other delay types will be ignored.")
    selected_delay_types = ["Total Delay"]

selected_delay_columns = [delay_type_options[dt] for dt in selected_delay_types]

all_airlines = df['carrier_name'].unique().tolist()
selected_airlines = st.sidebar.multiselect("Select Airlines", all_airlines, default=all_airlines)

all_airports = df['airport_name'].unique().tolist()
selected_airports = st.sidebar.multiselect("Select Airports", all_airports, default=all_airports)

# --- Apply Filters ---
filtered_df = df[
    (df['year'].isin(selected_years)) &
    (df['month'].map(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b')).isin(selected_months)) &
    (df['carrier_name'].isin(selected_airlines)) &
    (df['airport_name'].isin(selected_airports))
]

filtered_df['Selected_Delay'] = filtered_df[selected_delay_columns].sum(axis=1)

# --- KPI Cards ---
st.subheader("📊 Key Metrics (Based on Filters)")
col1, col2, col3, col4, col5 = st.columns(5)

total_flights = filtered_df['arr_flights'].sum()
total_delays = filtered_df['arr_del15'].sum()
delay_percentage = (total_delays / total_flights) * 100 if total_flights > 0 else 0

col1.metric("Total Flights", int(total_flights))
col2.metric("Total Delayed Flights", int(total_delays))
col3.metric("Delay %", f"{delay_percentage:.2f}%")
col4.metric("Total Delay Time (minutes)", int(filtered_df['Selected_Delay'].sum()))
col5.metric("Total Cancellations", int(filtered_df['arr_cancelled'].sum()))

# --- Delay Breakdown Visualizations ---
st.subheader("🔎 Delay Cause Breakdown")
col5, col6 = st.columns(2)

with col5:
    delay_reasons = ['carrier_ct', 'weather_ct', 'nas_ct', 'security_ct', 'late_aircraft_ct']
    reason_totals = filtered_df[delay_reasons].sum().reset_index()
    reason_totals.columns = ['Reason', 'Count']
    reason_totals = reason_totals.sort_values(by='Count', ascending=False)
    fig_pie = px.pie(reason_totals, values='Count', names='Reason', title='Delay Causes Distribution')
    st.plotly_chart(fig_pie, use_container_width=True)

with col6:
    delay_duration_reasons = ['carrier_delay', 'weather_delay', 'nas_delay', 'security_delay', 'late_aircraft_delay']
    delay_duration = filtered_df[delay_duration_reasons].sum().reset_index()
    delay_duration.columns = ['Reason', 'Total Delay (min)']
    delay_duration = delay_duration.sort_values(by='Total Delay (min)', ascending=False)
    fig_bar = px.bar(delay_duration, x='Reason', y='Total Delay (min)', color='Reason', title='Delay Duration by Cause')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- Monthly Trend Line Chart ---
if not filtered_df.empty:
    st.subheader(f"📈 Monthly Delay Trend (Selected Years) {', '.join(selected_delay_types)}" )

    trend_df = filtered_df.groupby(['year', 'month']).agg({'Selected_Delay': 'sum'}).reset_index()
    trend_df['month_name'] = pd.to_datetime(trend_df['month'], format='%m').dt.strftime('%b')

    # Enforce fixed Jan-Dec order
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    trend_df['month_name'] = pd.Categorical(trend_df['month_name'], categories=month_order, ordered=True)

    # Fix missing months problem: reindex month_name properly
    fig_line = px.line(
        trend_df,
        x='month_name',
        y='Selected_Delay',
        color='year',
        markers=True,
        title="Monthly Delay Trend for Selected Years"
    )

    fig_line.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=month_order
        ),
        xaxis_title="Month",
        yaxis_title="Total Delay (minutes)",
        legend_title="Year",
        hovermode="x unified"
    )

    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("No data available for selected filters.")
# --- Airport-Wise Stats + Delay Rate ---
st.subheader(f"🏢 Airport-wise Delay Metrics {', '.join(selected_delay_types)}")
col7, col8 = st.columns(2)

with col7:
    airport_df = filtered_df.groupby('airport_name', as_index=False)[['arr_del15', 'arr_cancelled', 'arr_diverted', 'Selected_Delay']].sum()
    airport_df = airport_df.sort_values(by='Selected_Delay', ascending=False)
    fig_airport = px.bar(airport_df.head(10),
                         x='airport_name', y='Selected_Delay', color='Selected_Delay',
                         title='Top 10 Airports by Selected Delay')
    st.plotly_chart(fig_airport, use_container_width=True)

with col8:
    filtered_df['delay_rate'] = filtered_df['arr_del15'] / filtered_df['arr_flights']
    delay_rate_df = filtered_df.groupby('airport_name', as_index=False)['delay_rate'].mean()
    delay_rate_df = delay_rate_df.sort_values(by='delay_rate', ascending=False)
    fig_rate = px.bar(delay_rate_df.head(10),
                      x='airport_name', y='delay_rate',
                      title='Top 10 Airports by Delay Rate', color='delay_rate')
    st.plotly_chart(fig_rate, use_container_width=True)

# --- Geospatial Delay Map ---
st.subheader(f"🗺️ Airport Delay Intensity by {', '.join(selected_delay_types)}")

geo_df = filtered_df.dropna(subset=selected_delay_columns)
geo_df = geo_df[geo_df['Selected_Delay'] > 0]

if not geo_df.empty:
    if "Total Delay" in selected_delay_types:
        hover_data = {
            'airport_name': True,
            'carrier_name': True,
            'carrier_delay': True,
            'weather_delay': True,
            'nas_delay': True,
            'security_delay': True,
            'late_aircraft_delay': True,
            'LATITUDE': False,
            'LONGITUDE': False
        }
    else:
        hover_data = {'airport_name': True, 'carrier_name': True, 'LATITUDE': False, 'LONGITUDE': False}
        for selected_type in selected_delay_types:
            hover_data[delay_type_options[selected_type]] = True

    fig_map = px.scatter_geo(
        geo_df,
        lat='LATITUDE',
        lon='LONGITUDE',
        color='Selected_Delay',
        size='Selected_Delay',
        size_max=40,
        opacity=0.7,
        hover_name='airport_name',
        hover_data=hover_data,
        scope='usa',
        title=f"Airport Delay Intensity (Selected Airlines: {len(selected_airlines)} | Selected Airports: {len(selected_airports)})"
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("No data available for the selected filters and delay type.")

# --- Raw Data Table ---
with st.expander("📃 View Filtered Raw Data"):
    st.dataframe(filtered_df.head(100), use_container_width=True)
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Filtered Data", csv, "filtered_airline_delay_data.csv", "text/csv")
