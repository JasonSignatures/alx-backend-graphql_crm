🧭 CRM Celery + GraphQL Automation Setup

This project integrates Django, GraphQL, Celery, and Celery Beat to automate CRM tasks like generating weekly reports, updating low-stock products, and monitoring app health.
If you just need to get everything running fast, follow these 5 steps 👇
# 1️⃣ Install Redis and dependencies
sudo apt update && sudo apt install redis-server -y
sudo systemctl enable redis-server --now
redis-cli ping  # should return PONG
pip install -r requirements.txt
sudo apt install redis-server

# 2️⃣ Run Django migrations
python manage.py migrate

# 3️⃣ Start the Celery worker
celery -A crm worker -l info

# 4️⃣ Start Celery Beat scheduler
celery -A crm beat -l info

# 5️⃣ Verify logs are generated
cat /tmp/crm_report_log.txt


✅ Example log output:

2025-10-28 06:00:00 - Report: 152 customers, 348 orders, ₦2,560,000 revenue

📦 Project Overview

This CRM system uses:

GraphQL for querying customers, orders, and products.

Celery + Redis for asynchronous and scheduled tasks.

Celery Beat for periodic automation (like weekly reporting).

Django ORM for database management.

🧰 Installation & Setup (Detailed)
1. Clone the Repository
git clone https://github.com/yourusername/alx_backend_graphql_crm.git
cd alx_backend_graphql_crm

2. Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

3. Install Dependencies

Make sure your requirements.txt includes:

django
graphene-django
django-filter
django-celery-beat
celery
redis
django-crontab


Then install:

pip install -r requirements.txt

⚙️ 4. Configure Django & Celery
crm/settings.py

Ensure:

INSTALLED_APPS = [
    ...,
    'django_celery_beat',
    'django_crontab',
    'crm',
]

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'generate-crm-report': {
        'task': 'crm.tasks.generate_crm_report',
        'schedule': crontab(day_of_week='mon', hour=6, minute=0),
    },
}

crm/celery.py
from __future__ import absolute_import
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

app = Celery('crm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

crm/init.py
from .celery import app as celery_app
__all__ = ['celery_app']

📊 5. Celery Task: generate_crm_report

crm/tasks.py

from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime

@shared_task
def generate_crm_report():
    transport = RequestsHTTPTransport(url='http://localhost:8000/graphql')
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql("""
    query {
        customers { id }
        orders { id totalAmount }
    }
    """)

    data = client.execute(query)
    total_customers = len(data['customers'])
    total_orders = len(data['orders'])
    total_revenue = sum(o['totalAmount'] for o in data['orders'])

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("/tmp/crm_report_log.txt", "a") as log:
        log.write(f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, ₦{total_revenue} revenue\n")

💾 6. Redis Setup
sudo apt update && sudo apt install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping  # expect "PONG"

🚀 7. Running the System
Run Migrations
python manage.py migrate

Start Celery Worker
celery -A crm worker -l info

Start Celery Beat Scheduler
celery -A crm beat -l info

📋 8. Verify Logs

Check that weekly reports are logged to:

cat /tmp/crm_report_log.txt


Example output:

2025-10-28 06:00:00 - Report: 152 customers, 348 orders, ₦2,560,000 revenue

🧪 9. Optional Commands

Stop all Celery tasks:

pkill -f 'celery'


Check Redis service:

sudo systemctl status redis-server

🧠 10. Summary of Automation Jobs
Task	Frequency	Tool	File
Clean inactive customers	Weekly (Sunday 2 AM)	cron	clean_inactive_customers.sh
Send order reminders	Daily (8 AM)	cron	send_order_reminders.py
CRM heartbeat	Every 5 mins	django-crontab	crm/cron.py
Update low stock	Every 12 hrs	django-crontab	crm/cron.py
Generate weekly report	Weekly (Monday 6 AM)	Celery Beat	crm/tasks.py

Create crm/README.md with steps to:

InstallRedis and dependencies.
Run migrations (python manage.py migrate).
Start Celery worker (celery -A crm worker -l info).
Start Celery Beat (celery -A crm beat -l info).
Verify logs in /tmp/crm_report_log.txt.
