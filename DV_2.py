import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import random
import json
from fpdf import FPDF

import sys
import subprocess

# Ensure plotly is installed
try:
    import plotly.express as px
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px


# Define menu and inventory data
coffee_menu = {
    "Americano": 5.00,
    "Cappuccino": 6.50,
    "Latte": 6.00,
    "Caramel Macchiato": 7.00
}

# Load inventory from a JSON file at startup
if "inventory" not in st.session_state:
    try:
        with open("inventory.json", "r") as f:
            st.session_state["inventory"] = json.load(f)
    except FileNotFoundError:
        st.session_state["inventory"] = {"coffee beans": 1000, "milk": 500, "sugar": 300, "cups": 200}

# Load sales data from a JSON file at startup
if "sales_data" not in st.session_state:
    try:
        with open("sales_data.json", "r") as f:
            st.session_state["sales_data"] = json.load(f)
    except FileNotFoundError:
        st.session_state["sales_data"] = []

# Initialize session states for additional data
if "order_summary" not in st.session_state:
    st.session_state["order_summary"] = {}
if "orders" not in st.session_state:
    st.session_state["orders"] = []  # Customer order history
if "feedbacks" not in st.session_state:
    st.session_state["feedbacks"] = []  # Feedback storage
if "discount_codes" not in st.session_state:
    st.session_state["discount_codes"] = {"DISCOUNT10": 10}  # Sample discount codes

# Save inventory to a JSON file
def save_inventory():
    with open("inventory.json", "w") as f:
        json.dump(st.session_state["inventory"], f)

# Save sales data to a JSON file
def save_sales_data():
    with open("sales_data.json", "w") as f:
        json.dump(st.session_state["sales_data"], f)

# Save discount codes to a JSON file
def save_discount_codes():
    with open("discount_codes.json", "w") as f:
        json.dump(st.session_state["discount_codes"], f)

# Admin Functions
def admin_dashboard():
    st.title("Admin Dashboard - Real-Time Sales Monitoring")

    # Sales Report - Coffee Type Sales Count Chart
    st.subheader("Daily Sales Count by Coffee Type")
    if st.session_state["sales_data"]:
        sales_df = pd.DataFrame(st.session_state["sales_data"])
        sales_df['date'] = pd.to_datetime(sales_df['time']).dt.date  # Convert time to date only for daily aggregation
        sales_df['weekday'] = sales_df['date'].apply(lambda x: x.strftime('%A'))  # Convert dates to weekdays

        # Group by weekday and coffee type to get the count of each coffee sold
        daily_sales_count = sales_df.groupby(['weekday', 'coffee']).size().reset_index(name='count')
        weekday_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        daily_sales_count['weekday'] = pd.Categorical(daily_sales_count['weekday'], categories=weekday_order, ordered=True)
        daily_sales_count = daily_sales_count.sort_values('weekday')

        # Plot the daily sales count for each coffee type
        fig_daily_sales = px.line(daily_sales_count, x='weekday', y='count', color='coffee', title='Daily Sales Count by Coffee Type')
        fig_daily_sales.update_layout(xaxis_title="Day of the Week", yaxis_title="Count of Sales")
        st.plotly_chart(fig_daily_sales)

    else:
        st.write("No sales data available. Add some sales to view the report.")

    # Coffee Sales Breakdown
    st.subheader("Coffee Sales Breakdown")
    if st.session_state["sales_data"]:
        coffee_sales = sales_df['coffee'].value_counts().reset_index()
        coffee_sales.columns = ['coffee', 'count']
        fig_bar = px.bar(coffee_sales, x='coffee', y='count', title='Coffee Sales Breakdown')
        st.plotly_chart(fig_bar)

        st.write("Best Seller:", coffee_sales.iloc[0]['coffee'] if not coffee_sales.empty else "N/A")
        st.write("Least Popular:", coffee_sales.iloc[-1]['coffee'] if not coffee_sales.empty else "N/A")
    else:
        st.write("No sales data available.")

def inventory_management():
    st.title("Inventory Management")
    st.subheader("Current Inventory Levels")
    for item, qty in st.session_state["inventory"].items():
        st.write(f"{item.capitalize()}: {qty}")

    restock_item = st.selectbox("Select Item to Restock", list(st.session_state["inventory"].keys()))
    restock_qty = st.number_input("Restock Quantity", min_value=1, step=1)
    if st.button("Restock"):
        st.session_state["inventory"][restock_item] += restock_qty
        save_inventory()
        st.success(f"Restocked {restock_qty} units of {restock_item.capitalize()}")

def promotions_discounts():
    st.title("Promotions & Discounts")
    discount_code = st.text_input("Enter New Coupon Code")
    discount_percentage = st.slider("Discount Percentage", 0, 50, 10)
    if st.button("Create Discount Code"):
        st.session_state["discount_codes"][discount_code] = discount_percentage
        save_discount_codes()
        st.success(f"Discount Code '{discount_code}' with {discount_percentage}% discount created!")

    # Display all available discount codes
    st.subheader("Available Discount Codes")
    if st.session_state["discount_codes"]:
        for code, discount in st.session_state["discount_codes"].items():
            st.write(f"Code: {code}, Discount: {discount}%")
    else:
        st.write("No discount codes available.")

# Deduction logic for inventory based on order
def deduct_inventory(coffee_choice, add_ons):
    requirements = {
        "Americano": {"coffee beans": 1, "cups": 1},
        "Cappuccino": {"coffee beans": 1, "milk": 1, "sugar": 1, "cups": 1},
        "Latte": {"coffee beans": 1, "milk": 1, "cups": 1},
        "Caramel Macchiato": {"coffee beans": 1, "milk": 1, "sugar": 2, "cups": 1}
    }

    for item, qty in requirements.get(coffee_choice, {}).items():
        if st.session_state["inventory"][item] >= qty:
            st.session_state["inventory"][item] -= qty
        else:
            st.warning(f"Not enough {item} for {coffee_choice}. Adjust inventory!")

    if "Extra Sugar" in add_ons and st.session_state["inventory"]["sugar"] > 0:
        st.session_state["inventory"]["sugar"] -= 1
    if "Milk" in add_ons and st.session_state["inventory"]["milk"] > 0:
        st.session_state["inventory"]["milk"] -= 1

    save_inventory()

# Customer Functions
def customer_order():
    st.title("Order Coffee")
    st.write("Menu:")
    for coffee, price in coffee_menu.items():
        st.write(f"{coffee} - RM{price:.2f}")

    coffee_choice = st.selectbox("Select Coffee", list(coffee_menu.keys()))
    size = st.selectbox("Select Size", ["Small", "Medium", "Large"])
    add_ons = st.multiselect("Add-ons", ["Extra Sugar", "Milk"])

    # Apply size adjustment
    size_price_adjustment = 0
    if size == "Medium":
        size_price_adjustment = 1
    elif size == "Large":
        size_price_adjustment = 2

    # Apply add-on adjustment
    add_ons_price_adjustment = 0
    if "Extra Sugar" in add_ons:
        add_ons_price_adjustment += 1
    if "Milk" in add_ons:
        add_ons_price_adjustment += 2

    discount_code = st.text_input("Enter Discount Code (if any)")
    discount_applied = 0
    if discount_code:
        # Check if the discount code is valid and apply it
        discount_applied = st.session_state["discount_codes"].get(discount_code, 0)
        if discount_applied > 0:
            st.success(f"{discount_applied}% discount applied!")
        else:
            st.warning("Invalid discount code")

    # Calculate the price with the size and add-on adjustments and the applied discount
    base_price = coffee_menu[coffee_choice] + size_price_adjustment + add_ons_price_adjustment
    final_price = base_price * (1 - discount_applied / 100)  # Apply the discount to the adjusted base price
    st.write(f"Total Price after Discount, Size Adjustment, and Add-ons: RM{final_price:.2f}")

    if st.button("Place Order"):
        order_id = random.randint(1000, 9999)
        est_time = datetime.now() + timedelta(minutes=5)
        order_summary = {
            "order_id": order_id,
            "coffee": coffee_choice,
            "size": size,
            "add_ons": add_ons,
            "price": final_price,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "est_pickup_time": est_time.strftime('%H:%M:%S')
        }
        st.session_state["orders"].append(order_summary)
        st.session_state["sales_data"].append(order_summary)
        save_sales_data()
        st.success(f"Order placed! Order ID: {order_id}, Estimated Pickup Time: {est_time.strftime('%H:%M:%S')}")
        
        deduct_inventory(coffee_choice, add_ons)
        st.info("Inventory updated based on your order.")

def payment_integration():
    st.title("Payment")
    if st.session_state["orders"]:
        order_summary = st.session_state["orders"][-1]
        st.write("Order Summary:")
        st.write(f"Coffee: {order_summary['coffee']}")
        st.write(f"Size: {order_summary['size']}")
        st.write(f"Add-ons: {', '.join(order_summary['add_ons']) if order_summary['add_ons'] else 'None'}")
        st.write(f"Total Price: RM{order_summary['price']:.2f}")
        payment_method = st.selectbox("Payment Method", ["Credit Card", "Debit Card", "PayPal"])

        if st.button("Pay Now"):
            st.success("Payment successful!")
            order_summary["payment_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["orders"][-1] = order_summary
            generate_invoice(order_summary)

def generate_invoice(order_summary):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Coffee Shop Invoice", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Order ID: {order_summary['order_id']}", ln=True)
    pdf.cell(200, 10, f"Coffee: {order_summary['coffee']}", ln=True)
    pdf.cell(200, 10, f"Size: {order_summary['size']}", ln=True)
    pdf.cell(200, 10, f"Add-ons: {', '.join(order_summary['add_ons']) if order_summary['add_ons'] else 'None'}", ln=True)
    pdf.cell(200, 10, f"Total Price: RM{order_summary['price']:.2f}", ln=True)
    pdf.cell(200, 10, f"Pickup Time: {order_summary['est_pickup_time']}", ln=True)
    pdf_path = "invoice.pdf"
    pdf.output(pdf_path)
    with open(pdf_path, "rb") as pdf_file:
        st.download_button("Download Invoice", pdf_file, file_name="invoice.pdf")

def feedback():
    st.title("Feedback")
    rating = st.slider("Rate your experience", 1, 5)
    feedback_text = st.text_area("Leave a comment")
    if st.button("Submit Feedback"):
        if feedback_text.strip():
            feedback_entry = {
                "rating": rating,
                "comment": feedback_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state["feedbacks"].append(feedback_entry)
            st.success("Thank you for your feedback!")
        else:
            st.warning("Please enter a comment before submitting.")

    if st.session_state["feedbacks"]:
        st.subheader("Customer Feedbacks")
        for feedback in reversed(st.session_state["feedbacks"]):
            st.write(f"Rating: {feedback['rating']} - Comment: {feedback['comment']}")
            st.write(f"Submitted on: {feedback['timestamp']}")
            st.write("---")

def order_history():
    st.title("Order History")
    if st.session_state["orders"]:
        for order in st.session_state["orders"]:
            st.write(f"Order ID: {order['order_id']}")
            st.write(f"Coffee: {order['coffee']}")
            st.write(f"Size: {order['size']}")
            st.write(f"Add-ons: {', '.join(order['add_ons']) if order['add_ons'] else 'None'}")
            st.write(f"Total Price: RM{order['price']:.2f}")
            st.write(f"Pickup Time: {order['est_pickup_time']}")
            st.write(f"Payment Time: {order.get('payment_time', 'Not paid')}")
            st.write("---")
    else:
        st.write("No orders yet.")

def main():
    st.sidebar.title("Coffee Shop App")
    user_role = st.sidebar.radio("Choose Role", ["Customer", "Admin"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    # Admin functionalities
    if user_role == "Admin" and username == "admin" and password == "admin123":
        st.sidebar.success("Logged in as Admin")
        admin_option = st.sidebar.selectbox("Admin Menu", ["Dashboard", "Inventory Management", "Promotions & Discounts"])
        if admin_option == "Dashboard":
            admin_dashboard()
        elif admin_option == "Inventory Management":
            inventory_management()
        elif admin_option == "Promotions & Discounts":
            promotions_discounts()

    # Customer functionalities
    elif user_role == "Customer" and username and password:
        st.sidebar.success("Logged in as Customer")
        customer_option = st.sidebar.selectbox("Customer Menu", ["Order Coffee", "Order History", "Give Feedback"])
        if customer_option == "Order Coffee":
            customer_order()
            if st.session_state["orders"]:
                payment_integration()
        elif customer_option == "Order History":
            order_history()
        elif customer_option == "Give Feedback":
            feedback()

if __name__ == "__main__":
    main()
