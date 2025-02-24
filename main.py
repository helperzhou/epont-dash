import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import os
from pandasai.llm import GoogleGemini
import google.generativeai as genai
from pandasai import SmartDataframe
from pandasai.responses.response_parser import ResponseParser
import calendar
import json


class StreamLitResponse(ResponseParser):
    def __init__(self, context) -> None:
        super().__init__(context)

    def format_dataframe(self, result):
        st.dataframe(result['value'])
        return

    def format_plot(self, result):
        st.image(result['value'])
        return

    def format_other(self, result):
        st.write(result['value'])
        return


st.set_page_config(
    page_title='Quantilytix ESD AI Platform'
    , page_icon='📈'
    , layout='wide'
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

st.title(':red[Quantilytix ESD AI] Platform')

options = option_menu(
    menu_title=None
    , options=['Dashboard', 'Quick Helper', 'Reports', 'Settings']
    , icons=['clipboard', 'line', 'activity', 'gear']
    , menu_icon='cast'
    , default_index=0
    , orientation='horizontal'
)

gemini_api_key = os.environ['API_KEY']

genai.configure(
    api_key=os.environ['API_KEY']
)

generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "max_output_tokens": 5000,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-thinking-exp",
    generation_config=generation_config,
)


def calculate_kpis(df):
    total_interventions = len(df) if hasattr(df, '__len__') else 0  # Check if df is a dataframe
    try:
        interventions_by_category = df[
            'Intervention_Category'].value_counts().to_dict() if 'Intervention_Category' in df.columns else {}
    except AttributeError:
        interventions_by_category = {}
    try:
        interventions_by_type = df['Intervention'].value_counts().to_dict() if 'Intervention' in df.columns else {}
    except AttributeError:
        interventions_by_type = {}
    try:
        male_participants = len(df[df['Gender'] == 'Male']) if 'Gender' in df.columns else 0
    except TypeError:
        male_participants = 0
    try:
        female_participants = len(df[df['Gender'] == 'Female']) if 'Gender' in df.columns else 0
    except TypeError:
        female_participants = 0
    try:
        youth_participants = len(df[df['Youth'] == 'Yes']) if 'Youth' in df.columns else 0
    except TypeError:
        youth_participants = 0
    try:
        non_youth_participants = len(df[df['Youth'] == 'No']) if 'Youth' in df.columns else 0
    except TypeError:
        non_youth_participants = 0

    kpis = {
        "total_interventions": total_interventions,
        "interventions_by_category": interventions_by_category,
        "interventions_by_type": interventions_by_type,
        "male_participants": male_participants,
        "female_participants": female_participants,
        "youth_participants": youth_participants,
        "non_youth_participants": non_youth_participants,
    }
    return kpis


def get_pandas_profile(df_interventions):
    profile = ProfileReport(df_interventions, title="Profiling Report")
    json_profile = profile.to_json()
    dict_p = json.loads(json_profile)
    keys_to_keep = ['analysis', 'table', 'correlations', 'alerts', 'sample']

    # Assuming your dictionary is named 'my_dict'
    filtered_dict = {key: dict_p[key] for key in keys_to_keep}
    return filtered_dict


def generateResponse(dataFrame, prompt):
    llm = GoogleGemini(api_key=gemini_api_key)
    pandas_agent = SmartDataframe(dataFrame, config={"llm": llm,
                                                     "custom_instructions": "Plot using plotly chart which should be well spaced and the axes labels correctly orientated .",
                                                     "response_parser": StreamLitResponse})
    answer = pandas_agent.chat(prompt)
    return answer


# --- Load Dataset ---
file_path = "Intervention_Database-1.xlsx"
xls = pd.ExcelFile(file_path)

df_interventions = xls.parse('Interventions')
df_quant = xls.parse('Quant')

if options == 'Dashboard':
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

    # # --- Sidebar with Logos ---
    # col1, col2 = st.sidebar.columns([1, 1])
    # with col1:
    #     st.image("logo.png", width=100)  # Replace with your actual logo file
    # with col2:
    #     st.image("epnt.png", width=100)  # Replace with your actual logo file

    # st.sidebar.header("Quantilytix-Epont Platform")



    # --- Chart Selection ---
    st.write("### 📊 Select Chart to Display")
    chart_option = st.selectbox(
        "Choose a Chart Type",
        [
            "Box Plot", "Monthly Interventions Trends", "Intervention Categories", "Intervention Category Distribution",
            "Employees", "Orders Received", "Transactions", "Income", "Expenses"
        ]
    )
    # --- Chart Data Preparation ---
    category_counts = df_interventions["Intervention_Category"].value_counts().reset_index()
    category_counts.columns = ["Intervention_Category", "Count"]

    if chart_option == "Monthly Interventions Trends":


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
            "title": {"text": "Monthly Interventions Trends"},
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


        # Prepare Drilldown Data
        drilldown_data = {}
        category_data = []

        for category in df_interventions["Intervention_Category"].unique():
            companies = df_interventions[df_interventions["Intervention_Category"] == category][
                "Company Name"].value_counts()

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
            "title": {"text": "Intervention Category Distribution"},
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

    elif chart_option == "Intervention Categories":


        # Group by Company and Intervention Category
        company_category_counts = df_interventions.groupby(
            ["Company Name", "Intervention_Category"]).size().reset_index(
            name="Count")

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
                "labels": {"style": {"color": "#000"}}
            },
            "yAxis": {
                "title": {"text": "Number of Interventions"},
                "labels": {"style": {"color": "#000"}}
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


        company_category_counts = df_interventions.groupby(
            ["Company Name", "Intervention_Category"]).size().reset_index(
            name="Count")

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


    elif chart_option in ["Employees", "Orders Received", "Transactions", "Income", "Expenses"]:


        # Correct dictionary with actual column names
        quant_metrics = {
            "Employees": "Empoyees",
            "Orders Received": "Orders_Received",
            "Transactions": "Transactions_Recorded",
            "Income": "Income",
            "Expenses": "Expenses",
        }

        # Ensure datetime format
        df_quant["Month"] = pd.to_datetime(df_quant["Month"])

        # **Group by BOTH "Month" and "Name"**
        df_quant_time_series = df_quant.groupby(["Month", "Name"])[quant_metrics[chart_option]].sum().reset_index()

        # Convert column values to JSON serializable types
        df_quant_time_series[quant_metrics[chart_option]] = df_quant_time_series[quant_metrics[chart_option]].astype(
            float)

        # Generate a series for each company
        series_data = []
        for company in df_quant_time_series["Name"].unique():
            company_data = df_quant_time_series[df_quant_time_series["Name"] == company]
            series_data.append({
                "name": company,
                "data": company_data[quant_metrics[chart_option]].tolist()
            })

        # Highcharts Configuration
        line_chart_config = {
            "chart": {"type": "spline"},
            "title": {"text": f"{chart_option} Trends Over Time", "style": {"color": "#00"}},
            "xAxis": {
                "categories": df_quant_time_series["Month"].dt.strftime("%Y-%m").unique().tolist(),
                "title": {"text": "Month"},
                "labels": {"style": {"color": "#000"}}
            },
            "yAxis": {
                "title": {"text": f"Total {chart_option}"},
                "labels": {"style": {"color": "#000"}}
            },
            "legend": {"enabled": True},  # Show legend for multiple companies
            "series": series_data  # Use the dynamically generated company series
        }

        # Render Highcharts Line Graph in Streamlit
        st.components.v1.html(f"""
            <script src="https://code.highcharts.com/highcharts.js"></script>
            <div id="{chart_option.lower().replace(' ', '_')}_chart"></div>
            <script>
            Highcharts.chart('{chart_option.lower().replace(' ', '_')}_chart', {json.dumps(line_chart_config)});
            </script>
        """, height=500)

    # --- Navigation Buttons ---
    # pg = st.navigation([st.Page(dashboard), st.Page(chat), st.Page(reports)])
    # pg.run()

elif options == 'Quick Helper':
    st.subheader("Chat with AI")
    st.write("Get visualizations and analysis from our Gemini powered agent")

    with st.expander("Preview"):
        st.write(df_interventions.head())

    user_input = st.text_input("Type your message here", placeholder="Ask me about your data")
    if user_input:
        answer = generateResponse(dataFrame=df_interventions, prompt=user_input)
        st.write(answer)
elif options == 'Reports':

    st.subheader("Reports")
    st.write("Filter by Company Name, Gender, Youth, Intervention Category or Intervention to generate report")

    # Filtering Interface
    st.write("Filtering Options")
    company_names = df_interventions['Company Name'].unique().tolist()
    gender_options = df_interventions['Gender'].unique().tolist()
    youth_options = df_interventions['Youth'].unique().tolist()
    intervention_categories = df_interventions['Intervention_Category'].unique().tolist()
    intervention_types = df_interventions['Intervention'].unique().tolist()

    selected_companies = st.multiselect('Select Company(ies)', company_names, default=company_names)
    selected_genders = st.multiselect('Select Gender(s)', gender_options, default=gender_options)
    selected_youth = st.multiselect('Select Youth Status(es)', youth_options, default=youth_options)
    selected_categories = st.multiselect('Select Intervention Category(ies)', intervention_categories,
                                         default=intervention_categories)
    selected_interventions = st.multiselect('Select Intervention(s)', intervention_types, default=intervention_types)

    if st.button('Apply Filters and Generate report'):
        filtered_df = df_interventions.copy()

        if selected_companies:
            filtered_df = filtered_df[filtered_df['Company Name'].isin(selected_companies)]
        if selected_genders:
            filtered_df = filtered_df[filtered_df['Gender'].isin(selected_genders)]
        if selected_youth:
            filtered_df = filtered_df[filtered_df['Youth'].isin(selected_youth)]
        if selected_categories:
            filtered_df = filtered_df[filtered_df['Intervention_Category'].isin(selected_categories)]
        if selected_interventions:
            filtered_df = filtered_df[filtered_df['Intervention'].isin(selected_interventions)]

        if not filtered_df.empty:
            if len(filtered_df) > 1:
                st.write("Filtered DataFrame")
                with st.expander("Preview"):
                    st.write(filtered_df.head())

                with st.spinner("Generating Report, Please Wait...."):
                    try:

                        prompt = f"""
                        You are an expert business analyst. Analyze the following data and generate a comprehensive and insightful business report, 
                        including appropriate key performance indicators and recommendations.
                        Data: dataset:{str(filtered_df.to_json(orient='records'))}, kpis: {str(calculate_kpis(filtered_df))}
                        """
                        response = model.generate_content(prompt)
                        report = response.text
                        st.markdown(report)
                        st.success("Report Generation Complete")
                    except Exception as e:
                        st.write(f"Error generating report: {e}")

            else:
                st.write("Not enough data after filtering for full visualizations and report generation.")
                if not filtered_df.empty:
                    st.write("Filtered DataFrame:")
                    st.write(filtered_df)
        else:
            st.write("No data after filtering.")

    else:
        st.write("Click 'Apply Filters' to see the filtered data.")
elif options == 'Settings':
    # st.button()
    # --- Logout Button ---
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
