#!/usr/bin/env python3
"""
Script: send_order_reminders.py
Description: Queries pending orders (within the last 7 days) via GraphQL 
and logs order details to /tmp/order_reminders_log.txt
"""

from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Define GraphQL endpoint
endpoint = "http://localhost:8000/graphql"

# Set up GraphQL client
transport = RequestsHTTPTransport(url=endpoint, verify=False)
client = Client(transport=transport, fetch_schema_from_transport=True)

# Calculate date range for the last 7 days
one_week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()

# Define GraphQL query
query = gql(
    """
    query GetRecentOrders($date: Date!) {
      orders(orderDate_Gte: $date, status: "PENDING") {
        id
        customer {
          email
        }
      }
    }
    """
)

# Execute the query
params = {"date": one_week_ago}
result = client.execute(query, variable_values=params)

# Log results
log_file = "/tmp/order_reminders_log.txt"
with open(log_file, "a") as f:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for order in result.get("orders", []):
        order_id = order["id"]
        email = order["customer"]["email"]
        f.write(f"{timestamp} - Order ID: {order_id}, Customer Email: {email}\n")

print("Order reminders processed!")
