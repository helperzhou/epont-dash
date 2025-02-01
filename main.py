import streamlit as st
import pandas as pd
import json
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar

st.set_page_config(
    page_title="Quantilytix-Epont ESD Programme",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- User Authentication ---
users = {"info@epont.co.za": {"password": "admin123"}, "user": {"password": "user123"}}

def authenticate(username, password):
    return users.get(username, {}).get("password") == password

# Session State for Login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Welcome! Login To Continue")
    username = st.text_input("Email", placeholder="Enter email")
    password = st.text_input("Password", placeholder="Enter password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# --- Load Dataset ---
file_path = "Intervention_Database-1.xlsx"
xls = pd.ExcelFile(file_path)

df_interventions = xls.parse('Interventions')
df_quant = xls.parse('Quant')

# --- Fix Numeric Columns ---
df_quant["Income"] = df_quant["Income"].astype(str).str.replace("R", "").str.replace(" ", "").astype(float)
df_quant["Expenses"] = df_quant["Expenses"].astype(str).str.replace("R", "").str.replace(" ", "").astype(float)

# --- Convert Month Names to Datetime (YYYY-MM) ---
month_mapping = {month: str(index).zfill(2) for index, month in enumerate(calendar.month_name) if month}
df_quant["Month"] = df_quant["Month"].map(month_mapping)

# Assign the latest year (Assuming 2024)
latest_year = 2024
df_quant["Month"] = df_quant["Month"].apply(lambda x: f"{latest_year}-{x}" if pd.notna(x) else None)

# Convert to datetime format
df_quant["Month"] = pd.to_datetime(df_quant["Month"], format="%Y-%m")

# --- Sidebar with Logos ---
col1, col2 = st.sidebar.columns([1, 1])
with col1:
    st.image("logo.png", width=100)  # Replace with your actual logo file
with col2:
    st.image("epnt.png", width=100)  # Replace with your actual logo file

st.sidebar.header("Filters")

companies = ["All"] + df_interventions["Company Name"].unique().tolist()
categories_list = ["All"] + df_interventions["Intervention_Category"].unique().tolist()
genders = ["All"] + df_interventions["Gender"].unique().tolist()
youth_options = ["All"] + df_interventions["Youth"].unique().tolist()

selected_company = st.sidebar.multiselect("Select Company", companies, default=["All"])
selected_category = st.sidebar.multiselect("Select Category", categories_list, default=["All"])
selected_gender = st.sidebar.multiselect("Select Gender", genders, default=["All"])
selected_youth = st.sidebar.radio("Show Youth", youth_options, index=0, horizontal=True)

# --- Logout Button ---
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- Apply Filters ---
filtered_df = df_interventions.copy()

if "All" not in selected_company:
    filtered_df = filtered_df[filtered_df["Company Name"].isin(selected_company)]

if "All" not in selected_category:
    filtered_df = filtered_df[filtered_df["Intervention_Category"].isin(selected_category)]

if "All" not in selected_gender:
    filtered_df = filtered_df[filtered_df["Gender"].isin(selected_gender)]

if selected_youth != "All":
    filtered_df = filtered_df[filtered_df["Youth"] == selected_youth]

# --- Collapsible Filtered Data Table ---
with st.expander("📊 View Filtered Data", expanded=False):
    st.dataframe(filtered_df)

# --- Chart Selection ---
st.write("### 📊 Select Chart to Display")
chart_option = st.selectbox(
    "Choose a Chart Type",
    [
        "Box Plot", "Monthly Interventions Trends", "Bar Chart", "Intervention Category Distribution",  "Correlation Matrix",
        "Employees", "Orders Received", "Transactions", "Income", "Expenses"
    ]
)
# --- Chart Data Preparation ---
category_counts = filtered_df["Intervention_Category"].value_counts().reset_index()
category_counts.columns = ["Intervention_Category", "Count"]

if chart_option == "Monthly Interventions Trends":
    st.write("### 📈 Monthly Intervention Trends")

    # Convert Date to Period (Monthly)
    df_interventions["Month"] = pd.to_datetime(df_interventions["Date"]).dt.to_period("M").astype(str)

    # Group by Company and Month
    company_monthly_data = df_interventions.groupby(["Company Name", "Month"]).size().reset_index(name="Count")

    # Prepare series for Highcharts
    series_data = []
    for company in company_monthly_data["Company Name"].unique():
        company_data = company_monthly_data[company_monthly_data["Company Name"] == company]
        series_data.append({
            "name": company,
            "data": company_data["Count"].tolist()
        })

    # Highcharts Configuration
    multi_company_chart_config = {
        "chart": {"type": "spline"},
        "title": {"text": "Monthly Interventions Trends (All Companies)"},
        "xAxis": {"categories": sorted(company_monthly_data["Month"].unique()), "title": {"text": "Month"}},
        "yAxis": {"title": {"text": "Number of Interventions"}},
        "legend": {"enabled": True},
        "series": series_data
    }

    # Render Highcharts in Streamlit
    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="multi_company_chart"></div>
        <script>
        Highcharts.chart('multi_company_chart', {json.dumps(multi_company_chart_config)});
        </script>
    """, height=500)


# --- Pie Chart ---
elif chart_option == "Intervention Category Distribution":
    st.write("### 📊 Intervention Category Distribution") 

    # Prepare Drilldown Data
    drilldown_data = {}
    category_data = []

    for category in df_interventions["Intervention_Category"].unique():
        companies = df_interventions[df_interventions["Intervention_Category"] == category]["Company Name"].value_counts()

        # Add category to main pie chart (Convert int64 to int)
        category_data.append({
            "name": category,
            "y": int(companies.sum()),  # Convert int64 to int
            "drilldown": category
        })

        # Add companies under each category for drill-down (Convert int64 to int)
        drilldown_data[category] = [{"name": company, "y": int(count)} for company, count in companies.items()]

    # Highcharts Configuration for Drilldown
    drilldown_pie_chart_config = {
        "chart": {"type": "pie"},
        # "plotOptions": {"series": {"dataLabels": {"enabled": True}}},
        "plotOptions": {
            "series": {"dataLabels": {"enabled": True}},
            "pie": {
                "dataLabels": {
                    "enabled": True,
                    "format": "{point.name}: {point.y}",  # Show Name and Count
                    "style": {"color": "#ffffff"}
                }
            }
        },
         "title": {"text": ""},
        "series": [{
            "name": "Categories",
            "colorByPoint": True,
            "data": category_data
        }],
        "drilldown": {
            "series": [
                {"name": category, "id": category, "data": drilldown_data[category]}
                for category in drilldown_data
            ]
        }
    }

    # Render Highcharts Drilldown Pie Chart in Streamlit
    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <script src="https://code.highcharts.com/modules/drilldown.js"></script>
        <div id="pie_chart"></div>
        <script>
        Highcharts.chart('pie_chart', {json.dumps(drilldown_pie_chart_config)});
        </script>
    """, height=500)

elif chart_option == "Bar Chart":
    st.write("### 📊 Intervention Categories (All Companies)")

    # Group by Company and Intervention Category
    company_category_counts = df_interventions.groupby(["Company Name", "Intervention_Category"]).size().reset_index(name="Count")

    # Pivot Data for Highcharts Format
    category_list = company_category_counts["Intervention_Category"].unique().tolist()
    company_list = company_category_counts["Company Name"].unique().tolist()

    # Prepare Data for Highcharts (Convert int64 to int)
    series_data = []
    for company in company_list:
        company_data = company_category_counts[company_category_counts["Company Name"] == company]
        series_data.append({
            "name": company,
            "data": [int(company_data[company_data["Intervention_Category"] == category]["Count"].sum()) 
                     if category in company_data["Intervention_Category"].values else 0
                     for category in category_list]  # Convert int64 to int
        })

    # Highcharts Configuration
    multi_company_bar_chart_config = {
        "chart": {"type": "bar"},
        "title": {"text": "Intervention Categories by Company"},
        "xAxis": {
            "categories": category_list,
            "title": {"text": "Intervention Categories"},
            "labels": {"style": {"color": "#ffffff"}}
        },
        "yAxis": {
            "title": {"text": "Number of Interventions"},
            "labels": {"style": {"color": "#ffffff"}}
        },
        "legend": {"enabled": True},
        "plotOptions": {
            "series": {"stacking": "normal"}  # Stacked Bar Chart
        },
        "series": series_data
    }

    # Render Highcharts Bar Chart in Streamlit
    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="multi_company_bar_chart"></div>
        <script>
        Highcharts.chart('multi_company_bar_chart', {json.dumps(multi_company_bar_chart_config)});
        </script>
    """, height=500)



# --- Box Plot for Intervention Count Per Company (Plotly) ---
elif chart_option == "Box Plot":
    st.write("### 📦 Intervention Count Distribution Per Company")

    company_category_counts = df_interventions.groupby(["Company Name", "Intervention_Category"]).size().reset_index(name="Count")

    if not company_category_counts.empty:
        fig = px.box(
            company_category_counts,
            x="Company Name",
            y="Count",
            title="Intervention Count Distribution Per Company",
            labels={"Count": "Number of Interventions Per Category"},
            color="Company Name",
            points=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data for a Box Plot. Try adjusting the filters.")

# --- Business Metrics Graphs (Highcharts) ---
elif chart_option in ["Employees", "Orders Received", "Transactions", "Income", "Expenses"]:
    quant_metrics = {
        "Employees": "Empoyees",
        "Orders Received": "Orders_Received",
        "Transactions": "Transactions_Recorded",
        "Income": "Income",
        "Expenses": "Expenses",
    }

    df_quant_grouped = df_quant.groupby("Name")[quant_metrics[chart_option]].sum().reset_index()

    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="{chart_option.lower().replace(' ', '_')}_chart"></div>
        <script>
        Highcharts.chart('{chart_option.lower().replace(' ', '_')}_chart', {json.dumps({"chart": {"type": "column"}, "title": {"text": f"{chart_option} Per Company"}, "xAxis": {"categories": df_quant_grouped["Name"].tolist()}, "yAxis": {"title": {"text": f"Total {chart_option}"}}, "series": [{"name": chart_option, "data": df_quant_grouped[quant_metrics[chart_option]].tolist(), "color": "#4CAF50"}]})});
        </script>
    """, height=400)

elif chart_option == "Correlation Matrix":
    st.write("### 🔬 Correlation: Interventions & Revenue (Filtered)")

    # Apply filters to df_interventions and df_quant
    filtered_correlation_df = df_interventions.copy()

    if "All" not in selected_company:
        filtered_correlation_df = filtered_correlation_df[filtered_correlation_df["Company Name"].isin(selected_company)]

    # Aggregate intervention count per company after filtering
    df_correlation = filtered_correlation_df.groupby("Company Name").size().reset_index(name="Intervention_Count")

    # Merge with revenue data
    df_correlation = df_correlation.merge(df_quant[["Name", "Income"]], left_on="Company Name", right_on="Name", how="inner")
    df_correlation.drop(columns=["Name"], inplace=True)  # Remove duplicate company column

    # Ensure enough data for correlation
    if df_correlation.shape[0] > 1:
        # Compute correlation matrix
        correlation_matrix = df_correlation.select_dtypes(include=["number"]).corr()

        # Convert to Plotly Heatmap format
        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale="RdBu",
                zmin=-1,
                zmax=1,
                text=correlation_matrix.values,
                hoverinfo="text",
            )
        )
        fig.update_layout(
            title="Correlation Matrix: Interventions & Revenue (Filtered)",
            xaxis_title="Metrics",
            yaxis_title="Metrics",
            width=700,
            height=500
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data to compute a correlation matrix. Try selecting more companies.")
