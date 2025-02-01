import streamlit as st
import pandas as pd
import json

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
file_path = "Intervention_Database.xlsx"
xls = pd.ExcelFile(file_path)
df = xls.parse('Sheet1')

# --- Streamlit UI ---
st.title("Quantilytix-Epont ESD Programme")

# --- Sidebar Filters with Logos ---
col1, col2 = st.sidebar.columns([1, 1])
with col1:
    st.image("logo.png", width=100)  # Replace with your actual logo file
with col2:
    st.image("epnt.png", width=100)  # Replace with your actual logo file

st.sidebar.header("Filters")

# --- Sidebar Filters ---
companies = ["All"] + df["Company Name"].unique().tolist()
categories = ["All"] + df["Intervention_Category"].unique().tolist()
genders = ["All"] + df["Gender"].unique().tolist()
youth_options = ["All"] + df["Youth"].unique().tolist()

selected_company = st.sidebar.multiselect("Select Company", companies, default=["All"])
selected_category = st.sidebar.multiselect("Select Category", categories, default=["All"])
selected_gender = st.sidebar.multiselect("Select Gender", genders, default=["All"])
selected_youth = st.sidebar.radio("Show Youth", youth_options, index=0, horizontal=True)

# --- Logout Button ---
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- Apply Filters ---
filtered_df = df.copy()

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
    ["Bar Chart", "Pie Chart", "Line Chart", "Box Plot"]
)

# --- Chart Data Preparation ---
category_counts = filtered_df["Intervention_Category"].value_counts().reset_index()
category_counts.columns = ["Intervention_Category", "Count"]

# --- Bar Chart ---
if chart_option == "Bar Chart":
    st.write("### 📊 Interventions by Category")

    bar_chart_config = {
        "chart": {"type": "bar"},
        "title": {"text": "Intervention Categories"},
        "xAxis": {"categories": category_counts["Intervention_Category"].tolist()},
        "yAxis": {"title": {"text": "Number of Interventions"}},
        "series": [{
            "name": "Interventions",
            "data": category_counts["Count"].tolist()
        }]
    }

    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="bar_chart"></div>
        <script>
        Highcharts.chart('bar_chart', {json.dumps(bar_chart_config)});
        </script>
    """, height=400)

# --- Pie Chart ---
elif chart_option == "Pie Chart":
    st.write("### 📊 Intervention Category Distribution")

    pie_chart_config = {
        "chart": {"type": "pie"},
        "title": {"text": "Intervention Categories"},
        "series": [{
            "name": "Count",
            "colorByPoint": True,
            "data": [
                {"name": row["Intervention_Category"], "y": row["Count"]}
                for _, row in category_counts.iterrows()
            ]
        }]
    }

    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="pie_chart"></div>
        <script>
        Highcharts.chart('pie_chart', {json.dumps(pie_chart_config)});
        </script>
    """, height=400)

# --- Line Chart ---
elif chart_option == "Line Chart":
    st.write("### 📈 Interventions Over Time")

    time_series_data = filtered_df.groupby("Date").size().reset_index(name="Count")

    line_chart_config = {
        "chart": {"type": "line"},
        "title": {"text": "Intervention Trends"},
        "xAxis": {"categories": time_series_data["Date"].astype(str).tolist()},
        "yAxis": {"title": {"text": "Number of Interventions"}},
        "series": [{
            "name": "Interventions",
            "data": time_series_data["Count"].tolist()
        }]
    }

    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <div id="line_chart"></div>
        <script>
        Highcharts.chart('line_chart', {json.dumps(line_chart_config)});
        </script>
    """, height=400)

# --- Highcharts Box Plot ---
elif chart_option == "Box Plot":
    st.write("### 📦 Box Plot: Interventions Per Company")

    # Compute statistics for Box Plot
    company_interventions = filtered_df.groupby("Company Name")["Intervention"].count().reset_index()
    company_interventions.columns = ["Company", "Count"]

    box_plot_data = []
    for company in company_interventions["Company"].unique():
        company_data = company_interventions[company_interventions["Company"] == company]["Count"].tolist()
        if len(company_data) > 0:
            min_val = min(company_data)
            q1 = company_interventions["Count"].quantile(0.25)
            median = company_interventions["Count"].median()
            q3 = company_interventions["Count"].quantile(0.75)
            max_val = max(company_data)

            box_plot_data.append([min_val, q1, median, q3, max_val])

    box_plot_config = {
        "chart": {"type": "boxplot"},
        "title": {"text": "Intervention Count Distribution Per Company"},
        "xAxis": {"categories": company_interventions["Company"].tolist(), "title": {"text": "Companies"}},
        "yAxis": {"title": {"text": "Number of Interventions"}},
        "series": [{
            "name": "Interventions",
            "data": box_plot_data
        }]
    }

    st.components.v1.html(f"""
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <script src="https://code.highcharts.com/modules/boxplot.js"></script>
        <div id="box_plot"></div>
        <script>
        Highcharts.chart('box_plot', {json.dumps(box_plot_config)});
        </script>
    """, height=400)
