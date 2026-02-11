import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Page Config ---
st.set_page_config(page_title="Malaysia CPI Dashboard", page_icon="🇲🇾", layout="wide")
st.title("🇲🇾 Malaysia CPI Dashboard")
st.markdown("Tracking Consumer Price Index trends across Malaysia's 16 states, powered by [OpenDOSM](https://open.dosm.gov.my).")

# --- Load Data ---
@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_data():
    df_cpi = pd.read_parquet("https://storage.dosm.gov.my/cpi/cpi_2d_state.parquet")
    df_cpi["date"] = pd.to_datetime(df_cpi["date"])
    
    df_inf = pd.read_parquet("https://storage.dosm.gov.my/cpi/cpi_2d_state_inflation.parquet")
    df_inf["date"] = pd.to_datetime(df_inf["date"])
    
    div_map = {
        "01": "Food & Beverages", "02": "Alcoholic Beverages & Tobacco",
        "03": "Clothing & Footwear", "04": "Housing, Water, Electricity, Gas & Other Fuels",
        "05": "Furnishings & Household Equipment", "06": "Health",
        "07": "Transport", "08": "Information & Communication",
        "09": "Recreation, Sport & Culture", "10": "Education",
        "11": "Restaurant & Accommodation Services", "12": "Insurance & Financial Services",
        "13": "Personal Care & Miscellaneous", "overall": "Overall"
    }
    df_cpi["category"] = df_cpi["division"].map(div_map)
    df_inf["category"] = df_inf["division"].map(div_map)
    
    return df_cpi, df_inf

df_cpi, df_inf = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

all_states = sorted(df_cpi["state"].unique())
selected_states = st.sidebar.multiselect("Select States", all_states, default=["Selangor", "W.P. Kuala Lumpur"])

categories = sorted([c for c in df_cpi["category"].unique() if c != "Overall"])
selected_category = st.sidebar.selectbox("Spending Category", ["Overall"] + categories)

min_date = df_cpi["date"].min().to_pydatetime()
max_date = df_cpi["date"].max().to_pydatetime()
date_range = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MMM YYYY")

# --- Filter Data ---
div_code = {v: k for k, v in df_cpi.set_index("division")["category"].drop_duplicates().items()}
selected_div = div_code.get(selected_category, "overall")

mask_cpi = (
    (df_cpi["state"].isin(selected_states)) &
    (df_cpi["division"] == selected_div) &
    (df_cpi["date"] >= date_range[0]) &
    (df_cpi["date"] <= date_range[1])
)
df_filtered = df_cpi[mask_cpi]

# --- Chart 1: CPI Trend ---
st.subheader(f"CPI Trend — {selected_category}")

fig1, ax1 = plt.subplots(figsize=(12, 5))
for state in selected_states:
    state_data = df_filtered[df_filtered["state"] == state]
    ax1.plot(state_data["date"], state_data["index"], label=state, linewidth=2)

# Add all-state average
avg_mask = (df_cpi["division"] == selected_div) & (df_cpi["date"] >= date_range[0]) & (df_cpi["date"] <= date_range[1])
avg = df_cpi[avg_mask].groupby("date")["index"].mean()
ax1.plot(avg.index, avg.values, label="All-State Average", color="grey", linewidth=1.5, linestyle="--")

ax1.set_ylabel("CPI Index (Base 2010 = 100)")
ax1.legend()
sns.despine()
st.pyplot(fig1)

# --- Chart 2: Latest CPI by Category ---
st.subheader("Latest CPI by Spending Category")

col1, col2 = st.columns(2)
compare_state = col1.selectbox("Compare state:", selected_states if selected_states else all_states)

df_latest_state = df_cpi[
    (df_cpi["state"] == compare_state) &
    (df_cpi["division"] != "overall")
].copy()
latest_date = df_latest_state["date"].max()
df_bar = df_latest_state[df_latest_state["date"] == latest_date].sort_values("index", ascending=True)

fig2, ax2 = plt.subplots(figsize=(10, 6))
colors = ["#2ecc71" if v < 100 else "#e74c3c" for v in df_bar["index"]]
ax2.barh(df_bar["category"], df_bar["index"], color=colors)
ax2.axvline(x=100, color="black", linestyle="--", alpha=0.5)
ax2.set_xlabel("CPI Index")
ax2.set_title(f"{compare_state} — {latest_date.strftime('%B %Y')}")
for i, (val, cat) in enumerate(zip(df_bar["index"], df_bar["category"])):
    ax2.text(val + 0.5, i, f"{val:.1f}", va="center", fontsize=9)
sns.despine()
st.pyplot(fig2)

# --- Chart 3: Year-on-Year Inflation Heatmap ---
st.subheader("Year-on-Year Inflation Heatmap")

heatmap_state = st.selectbox("Select state for heatmap:", all_states, index=all_states.index("Selangor"))
df_heat = df_inf[
    (df_inf["state"] == heatmap_state) &
    (df_inf["division"] != "overall") &
    (df_inf["inflation_yoy"].notna())
].copy()
df_heat["year"] = df_heat["date"].dt.year
heat_annual = df_heat.groupby(["category", "year"])["inflation_yoy"].mean().unstack()

fig3, ax3 = plt.subplots(figsize=(14, 7))
sns.heatmap(heat_annual, cmap="RdYlGn_r", center=0, annot=True, fmt=".1f", linewidths=0.5, ax=ax3)
ax3.set_title(f"Average YoY Inflation (%) — {heatmap_state}")
ax3.set_ylabel("")
ax3.set_xlabel("Year")
plt.tight_layout()
st.pyplot(fig3)

# --- Footer ---
st.markdown("---")
st.markdown("**Data Source:** [Department of Statistics Malaysia (DOSM)](https://open.dosm.gov.my) — CC BY 4.0")