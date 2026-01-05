import os
from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

def log_crm_heartbeat():
    """
    Logs a heartbeat message every 5 minutes.
    Optionally checks GraphQL hello field for responsiveness.
    """

    log_file = "/tmp/crm_heartbeat_log.txt"
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    # Optional: check GraphQL health
    try:
        endpoint = "http://localhost:8000/graphql"
        transport = RequestsHTTPTransport(url=endpoint, verify=False)
        client = Client(transport=transport, fetch_schema_from_transport=True)

        query = gql("{ hello }")
        result = client.execute(query)
        response_message = result.get("hello", "No response")
        status = f"{timestamp} CRM is alive - GraphQL says: {response_message}\n"
    except Exception as e:
        status = f"{timestamp} CRM is alive - GraphQL check failed: {e}\n"

    # Log to file
    with open(log_file, "a") as f:
        f.write(status)

def update_low_stock():
    """
    Runs every 12 hours.
    Executes a GraphQL mutation to restock low-stock products
    and logs results to /tmp/low_stock_updates_log.txt.
    """
    log_file = "/tmp/low_stock_updates_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Connect to GraphQL endpoint
        endpoint = "http://localhost:8000/graphql"
        transport = RequestsHTTPTransport(url=endpoint, verify=False)
        client = Client(transport=transport, fetch_schema_from_transport=True)

        # Define and run mutation
        mutation = gql(
            """
            mutation {
              updateLowStockProducts {
                success
                message
                updatedProducts {
                  name
                  stock
                }
              }
            }
            """
        )

        result = client.execute(mutation)
        data = result.get("updateLowStockProducts", {})

        message = data.get("message", "No response message")
        updated_products = data.get("updatedProducts", [])

        # Log results
        with open(log_file, "a") as f:
            f.write(f"{timestamp} - {message}\n")
            for p in updated_products:
                f.write(f"    {p['name']} → Stock: {p['stock']}\n")

    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"{timestamp} - ERROR: {e}\n")
