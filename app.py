from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
st.set_page_config(page_title="Lumio", layout="wide")

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.stApp { background-color:#0b0f17; color:white; }
section[data-testid="stSidebar"] { background-color:#172033; }
h1,h2,h3,h4,p,div,span,label { color:white; }
.metric-box {
    padding: 16px;
    border-radius: 14px;
    background: #111827;
    border: 1px solid #252f3f;
}
.metric-label { font-size:14px; color:#cbd5e1; }
.metric-value { font-size:36px; font-weight:600; color:white; }
.small-muted { color:#7b8494; font-size:13px; }
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Helpers
# -----------------------------



def get_search_console_keywords():
    credentials = google_credentials(
        ["https://www.googleapis.com/auth/webmasters.readonly"]
    )

    service = build("searchconsole", "v1", credentials=credentials)
    site_url = st.secrets["SEARCH_CONSOLE_SITE_URL"]

    request = {
        "startDate": "2026-05-01",
        "endDate": "2026-06-11",
        "dimensions": ["query"],
        "rowLimit": 20
    }

    response = service.searchanalytics().query(
        siteUrl=site_url,
        body=request
    ).execute()

    rows = response.get("rows", [])

    return pd.DataFrame([
        {
            "Query": row["keys"][0],
            "Clicks": row.get("clicks", 0),
            "Impressions": row.get("impressions", 0),
            "CTR": round(row.get("ctr", 0) * 100, 2),
            "Position": round(row.get("position", 0), 1),
        }
        for row in rows
    ])


def get_ga4_traffic():
    credentials = google_credentials(
        ["https://www.googleapis.com/auth/analytics.readonly"]
    )

    client = BetaAnalyticsDataClient(credentials=credentials)
    property_id = st.secrets["GA4_PROPERTY_ID"]

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")]
    )

    response = client.run_report(request)

    return pd.DataFrame([
        {
            "Channel": row.dimension_values[0].value,
            "Sessions": int(row.metric_values[0].value),
            "Users": int(row.metric_values[1].value),
        }
        for row in response.rows
    ])
def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Demo Data
# -----------------------------
def demo_clinical_data():
    return pd.DataFrame({
        "Practitioner": ["Emma Thornton", "Marcus Webb", "Anika Patel", "Daniel Forsythe", "Yuki Tanaka"],
        "Appointments": [241, 187, 163, 118, 54],
        "Revenue": [58400, 39600, 34200, 24800, 11200],
        "Cancel Rate": [22.8, 17.4, 11.8, 10.6, 7.1],
        "Rebooking": [91.2, 88.5, 95.7, 96.4, 98.1],
        "New Patients": [24, 17, 31, 11, 19],
        "DNA": [4, 6, 2, 3, 1],
    })


def demo_marketing_data():
    return pd.DataFrame({
        "Week": ["W01 Jan", "W02 Jan", "W03 Jan", "W04 Jan", "W05 Feb", "W06 Feb", "W07 Feb", "W08 Feb"],
        "Direct": [104, 43, 76, 68, 96, 67, 63, 64],
        "Organic": [30, 41, 34, 32, 38, 35, 33, 58],
        "Paid": [99, 112, 105, 69, 17, 23, 24, 12],
    })


def demo_search_console_data():
    return pd.DataFrame({
        "Query": [
            "northside physio brisbane",
            "mobile physio brisbane",
            "home physio brisbane northside",
            "physiotherapy near me",
            "ndis physiotherapy brisbane",
        ],
        "Clicks": [142, 38, 24, 19, 31],
        "Impressions": [298, 1240, 876, 2100, 540],
        "CTR": ["47.7%", "3.1%", "2.7%", "0.9%", "5.7%"],
    })


# -----------------------------
# Integrations
# -----------------------------
def splose_get(endpoint):
    token = secret("SPLOSE_API_TOKEN")
    base_url = secret("SPLOSE_BASE_URL", "https://api.splose.com")

    if not token:
        return None, "Missing SPLOSE_API_TOKEN"

    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def xero_get(endpoint):
    tenant_id = secret("XERO_TENANT_ID")
    access_token = secret("XERO_ACCESS_TOKEN")

    if not tenant_id or not access_token:
        return None, "Missing Xero tenant ID or access token"

    url = f"https://api.xero.com/api.xro/2.0/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept": "application/json",
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def google_status():
    ga4 = bool(secret("GA4_PROPERTY_ID"))
    gsc = bool(secret("SEARCH_CONSOLE_SITE_URL"))
    service_account = secret("GOOGLE_SERVICE_ACCOUNT_JSON", "{}").strip()
    has_sa = service_account not in ["", "{}"]
    return ga4, gsc, has_sa


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown("### ✦ Lumio Assistant")
st.sidebar.caption("Ask questions · Upload files")

uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
question = st.sidebar.text_input("Ask anything...")

st.sidebar.markdown("---")
st.sidebar.markdown("### Integrations")

splose_connected = bool(secret("SPLOSE_API_TOKEN"))
xero_connected = bool(secret("XERO_ACCESS_TOKEN"))
ga4_connected, gsc_connected, google_sa_connected = google_status()

st.sidebar.write("Splose:", "✅ Connected" if splose_connected else "⚠️ Not connected")
st.sidebar.write("Xero:", "✅ Connected" if xero_connected else "⚠️ Not connected")
st.sidebar.write("Google Analytics:", "✅ Ready" if ga4_connected and google_sa_connected else "⚠️ Not connected")
st.sidebar.write("Search Console:", "✅ Ready" if gsc_connected and google_sa_connected else "⚠️ Not connected")


# -----------------------------
# Header
# -----------------------------
st.markdown("## ✦ Lumio")
st.caption("Ergo Therapy Group · Intelligence Dashboard")

tabs = st.tabs([
    "📊 Overview",
    "🩺 Clinical - Team Leader",
    "📋 Clinical - Practice Manager",
    "📈 Marketing",
    "💰 Business Health",
    "🔌 Integrations",
])


clinical = demo_clinical_data()
marketing = demo_marketing_data()
search_console = demo_search_console_data()


# -----------------------------
# Overview
# -----------------------------
with tabs[0]:
    st.subheader("Overview")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Revenue", f"${clinical['Revenue'].sum():,.0f}")
    with c2:
        metric_card("Appointments", f"{clinical['Appointments'].sum():,.0f}")
    with c3:
        metric_card("Cancellation rate", f"{clinical['Cancel Rate'].mean():.1f}%")
    with c4:
        metric_card("Ad spend", "$8,080")
    with c5:
        metric_card("Cost per acquisition", "$192")

    st.markdown("### Revenue by practitioner")
    fig = px.bar(clinical, x="Practitioner", y="Revenue")
    st.plotly_chart(fig, use_container_width=True, key="overview_revenue_chart")


# -----------------------------
# Clinical Team Leader
# -----------------------------
with tabs[1]:
    st.subheader("Clinical - Team Leader")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Appointments attended", f"{clinical['Appointments'].sum():,.0f}")
    with c2:
        metric_card("Cancellations", "289")
    with c3:
        metric_card("Cancellation rate", f"{clinical['Cancel Rate'].mean():.1f}%")
    with c4:
        metric_card("DNA", f"{clinical['DNA'].sum():,.0f}")
    with c5:
        metric_card("Rebooking rate", f"{clinical['Rebooking'].mean():.1f}%")

    st.markdown("### Appointments by practitioner")
    fig = px.bar(clinical, x="Practitioner", y="Appointments")
    st.plotly_chart(fig, use_container_width=True, key="clinical_appointments_chart")

    st.markdown("### Performance summary")
    st.dataframe(clinical, use_container_width=True)


# -----------------------------
# Practice Manager
# -----------------------------
with tabs[2]:
    st.subheader("Clinical - Practice Manager")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("New patients", f"{clinical['New Patients'].sum():,.0f}")
    with c2:
        metric_card("DNA", f"{clinical['DNA'].sum():,.0f}")
    with c3:
        metric_card("Average rebooking", f"{clinical['Rebooking'].mean():.1f}%")
    with c4:
        metric_card("Revenue at risk", "$46,962")

    st.markdown("### Cancellation rate by practitioner")
    fig = px.bar(clinical, x="Practitioner", y="Cancel Rate")
    st.plotly_chart(fig, use_container_width=True, key="practice_cancel_chart")


# -----------------------------
# Marketing
# -----------------------------
with tabs[3]:
    st.subheader("Marketing")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Ad spend", "$8,080")
    with c2:
        metric_card("Clicks", "2,880")
    with c3:
        metric_card("Impressions", "53,340")
    with c4:
        metric_card("Conversions", "42")
    with c5:
        metric_card("Cost per conversion", "$192")

    st.markdown("### Website traffic")
    traffic_long = marketing.melt(id_vars="Week", value_vars=["Direct", "Organic", "Paid"],
                                  var_name="Channel", value_name="Sessions")
    fig = px.bar(traffic_long, x="Week", y="Sessions", color="Channel")
    st.plotly_chart(fig, use_container_width=True, key="marketing_traffic_chart")

    st.markdown("### Search Console - live keyword data")

if st.button("Refresh Search Console Data"):
    live_sc = get_search_console_keywords()

    if not live_sc.empty:
        st.success("Search Console connected successfully")
        st.dataframe(live_sc, use_container_width=True)
    else:
        st.warning("No live Search Console data returned. Showing demo data.")
        st.dataframe(search_console, use_container_width=True)
else:
    st.dataframe(search_console, use_container_width=True)


# -----------------------------
# Business Health
# -----------------------------
with tabs[4]:
    st.subheader("Business Health")

    total_revenue = clinical["Revenue"].sum()
    ad_spend = 8080
    cancellation_leakage = 46962

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Revenue", f"${total_revenue:,.0f}")
    with c2:
        metric_card("Appointments", f"{clinical['Appointments'].sum():,.0f}")
    with c3:
        metric_card("Ad spend", f"${ad_spend:,.0f}")
    with c4:
        metric_card("Cost per acquisition", "$192")
    with c5:
        metric_card("Cancellation leakage", f"${cancellation_leakage:,.0f}")

    st.markdown("### Revenue by practitioner")
    fig = px.bar(clinical, x="Practitioner", y="Revenue")
    st.plotly_chart(fig, use_container_width=True, key="business_health_revenue_chart")


# -----------------------------
# Integrations
# -----------------------------
with tabs[5]:
    st.subheader("Integrations")

    st.markdown("### Splose CRM")
    st.write("Status:", "✅ Connected" if splose_connected else "⚠️ Missing API token")

    if st.button("Test Splose connection"):
        data, err = splose_get("/cases")
        if err:
            st.error(err)
        else:
            st.success("Splose connected")
            st.json(data)

    st.markdown("---")
    st.markdown("### Xero")
    st.write("Status:", "✅ Connected" if xero_connected else "⚠️ Missing Xero access token")

    if st.button("Test Xero invoices"):
        data, err = xero_get("/Invoices")
        if err:
            st.error(err)
        else:
            st.success("Xero connected")
            st.json(data)

    st.markdown("---")
st.markdown("### Google Live Tests")

if st.button("Test Search Console", key="test_search_console"):
    try:
        df_sc = get_search_console_keywords()
        st.success("Search Console live data loaded")
        st.dataframe(df_sc, use_container_width=True)
    except Exception as e:
        st.error(e)

if st.button("Test Google Analytics", key="test_ga4"):
    try:
        df_ga = get_ga4_traffic()
        st.success("Google Analytics live data loaded")
        st.dataframe(df_ga, use_container_width=True)
    except Exception as e:
        st.error(e)
    st.write("GA4 Property ID:", "✅ Added" if ga4_connected else "⚠️ Missing")
    st.write("Search Console URL:", "✅ Added" if gsc_connected else "⚠️ Missing")
    st.write("Service Account JSON:", "✅ Added" if google_sa_connected else "⚠️ Missing")

    st.info("Google API pulling is scaffolded. Next step is adding the service account JSON and property/site permissions.")
