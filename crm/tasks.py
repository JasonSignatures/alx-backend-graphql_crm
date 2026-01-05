from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime
import logging
import requests

@shared_task
def generate_crm_report():
    # GraphQL setup
    transport = RequestsHTTPTransport(
        url='http://localhost:8000/graphql',
        verify=False,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # GraphQL query
    query = gql("""
    query {
        allCustomers {
            totalCount
        }
        allOrders {
            totalCount
        }
        orders {
            totalAmount
        }
    }
    """)

    try:
        result = client.execute(query)

        total_customers = result.get('allCustomers', {}).get('totalCount', 0)
        total_orders = result.get('allOrders', {}).get('totalCount', 0)

        # Calculate total revenue
        orders = result.get('orders', [])
        total_revenue = sum([o.get('totalAmount', 0) for o in orders])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, ₦{total_revenue} revenue\n"

        # Log to file
        with open("/tmp/crm_report_log.txt", "a") as log_file:
            log_file.write(log_message)

        print("✅ Weekly CRM report generated successfully!")

    except Exception as e:
        logging.error(f"CRM Report generation failed: {str(e)}")
