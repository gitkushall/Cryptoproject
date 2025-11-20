# CS 196 FINAL project
import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
import plotly.express as px

# Set page config
st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

# Initialize session state variables
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = {}

# Get supported coins
@st.cache_data(ttl=3600)
def get_coin_list():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/coins/list")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching coin list: {e}")
        return []

# Get current prices
def get_current_prices(coin_ids):
    if not coin_ids:
        return {}
    try:
        ids_param = ",".join(coin_ids)
        response = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd&include_market_cap=true")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return {}

# Get historical price data
def get_historical_data(coin_id, days=7):
    try:
        response = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return {"prices": []}

# Save portfolio to file
def save_portfolio():
    try:
        with open("crypto_portfolio.json", "w") as f:
            json.dump(st.session_state.portfolio, f)
        st.success("Portfolio saved successfully!")
    except Exception as e:
        st.error(f"Error saving portfolio: {e}")

# Load portfolio from file
def load_portfolio():
    try:
        if os.path.exists("crypto_portfolio.json"):
            with open("crypto_portfolio.json", "r") as f:
                st.session_state.portfolio = json.load(f)
            st.success("Portfolio loaded successfully!")
        else:
            st.info("No saved portfolio found.")
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")

# App Title
st.title("Crypto Portfolio Tracker")

# Navigation Tabs
tabs = ["Portfolio Dashboard", "Add Coin", "Price History", "Settings"]
selected_tab = st.sidebar.radio("Navigation", tabs)

# Portfolio Dashboard
if selected_tab == "Portfolio Dashboard":
    st.header("Your Portfolio")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Portfolio"):
            save_portfolio()
    with col2:
        if st.button("Load Portfolio"):
            load_portfolio()
            st.rerun()

    if not st.session_state.portfolio:
        st.info("Your portfolio is empty. Add coins from the 'Add Coin' tab or load a saved portfolio.")
    else:
        coin_ids = list(st.session_state.portfolio.keys())
        prices_data = get_current_prices(coin_ids)

        portfolio_data = []
        total_value = 0

        for coin_id, quantity in st.session_state.portfolio.items():
            if coin_id in prices_data:
                price = prices_data[coin_id]["usd"]
                market_cap = prices_data[coin_id].get("usd_market_cap", 0)
                value = price * quantity
                total_value += value

                portfolio_data.append({
                    "Coin ID": coin_id,
                    "Quantity": quantity,
                    "Current Price (USD)": f"${price:,.2f}",
                    "Value (USD)": f"${value:,.2f}",
                    "Market Cap (USD)": f"${market_cap:,.0f}" if market_cap else "N/A"
                })

        if portfolio_data:
            df = pd.DataFrame(portfolio_data)
            st.dataframe(df, use_container_width=True)

            st.subheader(f"Total Portfolio Value: ${total_value:,.2f}")

            col1, col2 = st.columns([3, 1])
            with col1:
                coin_to_remove = st.selectbox("Select coin to remove:", list(st.session_state.portfolio.keys()))
            with col2:
                if st.button("Remove Coin"):
                    if coin_to_remove in st.session_state.portfolio:
                        del st.session_state.portfolio[coin_to_remove]
                        st.success(f"Removed {coin_to_remove} from portfolio.")
                        st.rerun()

# Add Coin
elif selected_tab == "Add Coin":
    st.header("Add Coin to Portfolio")

    coin_list = get_coin_list()
    coin_names = [coin["name"] + " (" + coin["symbol"] + ")" for coin in coin_list]
    coin_ids = [coin["id"] for coin in coin_list]
    coin_dict = dict(zip(coin_names, coin_ids))

    with st.form("add_coin_form"):
        coin_selection = st.selectbox("Select Coin:", coin_names)
        quantity = st.number_input("Quantity:", min_value=0.0, value=1.0, step=0.01)
        submit_button = st.form_submit_button("Add to Portfolio")

        if submit_button:
            if quantity > 0:
                selected_coin_id = coin_dict[coin_selection]
                st.session_state.portfolio[selected_coin_id] = st.session_state.portfolio.get(selected_coin_id, 0) + quantity
                st.success(f"Added {quantity} of {coin_selection.split(' (')[0]} to your portfolio!")
            else:
                st.error("Quantity must be greater than 0.")

# Price History
elif selected_tab == "Price History":
    st.header("Price History Graph")

    if not st.session_state.portfolio:
        st.info("Your portfolio is empty. Add coins from the 'Add Coin' tab.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            coin_to_graph = st.selectbox("Select coin:", list(st.session_state.portfolio.keys()))
        with col2:
            time_period = st.selectbox("Select time period:", ["7 days", "30 days", "90 days", "1 year"])

        days_mapping = {
            "7 days": 7,
            "30 days": 30,
            "90 days": 90,
            "1 year": 365
        }

        historical_data = get_historical_data(coin_to_graph, days=days_mapping[time_period])

        if historical_data and historical_data["prices"]:
            prices_df = pd.DataFrame(historical_data["prices"], columns=["timestamp", "price"])
            prices_df["date"] = pd.to_datetime(prices_df["timestamp"], unit="ms")

            fig = px.line(
                prices_df,
                x="date",
                y="price",
                title=f"{coin_to_graph.capitalize()} Price (USD) - Last {time_period}"
            )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)

            current_price = prices_df["price"].iloc[-1]
            start_price = prices_df["price"].iloc[0]
            change_pct = ((current_price - start_price) / start_price) * 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${current_price:.2f}")
            col2.metric("Starting Price", f"${start_price:.2f}")
            col3.metric("Change", f"{change_pct:.2f}%", delta=f"{change_pct:.2f}%")

# Settings
elif selected_tab == "Settings":
    st.header("Settings")
    st.subheader("Price Alerts")

    if not st.session_state.portfolio:
        st.info("Your portfolio is empty. Add coins first to set price alerts.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            alert_coin = st.selectbox("Select coin for alert:", list(st.session_state.portfolio.keys()))
        with col2:
            alert_type = st.selectbox("Alert type:", ["Above", "Below"])
        with col3:
            current_prices = get_current_prices([alert_coin])
            current_price = current_prices.get(alert_coin, {}).get("usd", 0)
            alert_price = st.number_input(
                "Price threshold (USD):",
                min_value=0.0,
                value=float(current_price) if isinstance(current_price, (int, float)) else 0.0,
                step=0.01
            )

        if st.button("Set Alert"):
            alert_key = f"{alert_coin}_{alert_type}_{alert_price}"
            st.session_state.price_alerts[alert_key] = {
                "coin": alert_coin,
                "type": alert_type,
                "price": alert_price,
                "active": True
            }
            st.success(f"Alert set: {alert_coin} {alert_type.lower()} ${alert_price}")

    if st.session_state.price_alerts:
        st.subheader("Active Alerts")
        alerts_data = []

        for key, alert in st.session_state.price_alerts.items():
            alerts_data.append({
                "Coin": alert["coin"],
                "Type": alert["type"],
                "Price Threshold": f"${alert['price']:.2f}",
                "Status": "Active" if alert.get("active", True) else "Inactive"
            })

        alerts_df = pd.DataFrame(alerts_data)
        st.dataframe(alerts_df, use_container_width=True)

        if st.button("Clear All Alerts"):
            st.session_state.price_alerts = {}
            st.success("All alerts cleared")
            st.rerun()

    st.subheader("Notification Settings")
    notify_price_alerts = st.toggle("Notify on price alerts", value=True)
    notify_portfolio_changes = st.toggle("Notify on portfolio value changes", value=True)

    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

# Notification Checker
if st.session_state.price_alerts:
    current_prices = get_current_prices(list(st.session_state.portfolio.keys()))

    for key, alert in list(st.session_state.price_alerts.items()):
        if not alert.get("active", True):
            continue

        coin = alert["coin"]
        if coin in current_prices:
            current_price = current_prices[coin]["usd"]
            if (alert["type"] == "Above" and current_price > alert["price"]) or \
               (alert["type"] == "Below" and current_price < alert["price"]):
                notification = f"ALERT: {coin} is now ${current_price:.2f}, which is {alert['type'].lower()} your threshold of ${alert['price']:.2f}"
                st.session_state.notifications.append({
                    "message": notification,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "read": False
                })
                st.session_state.price_alerts[key]["active"] = False

# Sidebar Notifications
with st.sidebar:
    st.subheader("Notifications")

    if not st.session_state.notifications:
        st.sidebar.info("No notifications")
    else:
        for i, notif in enumerate(st.session_state.notifications):
            with st.sidebar.container():
                st.text(f"{notif['time']} - {notif['message']}")
                st.divider()

        if st.sidebar.button("Clear All Notifications"):
            st.session_state.notifications = []
            st.sidebar.success("Notifications cleared")
            st.rerun()
