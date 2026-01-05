#!/bin/bash

# Script: clean_inactive_customers.sh
# Description: Deletes customers with no orders in the past year and logs the count.

# Navigate to the Django project directory
cd "$(dirname "$0")/../.."  # Adjust if needed

# Run Django shell command to delete inactive customers
deleted_count=$(python3 manage.py shell <<EOF
from datetime import timedelta
from django.utils import timezone
from crm.models import Customer

one_year_ago = timezone.now() - timedelta(days=365)
inactive_customers = Customer.objects.filter(orders__isnull=True) | Customer.objects.exclude(orders__date__gte=one_year_ago)
count = inactive_customers.distinct().count()
inactive_customers.distinct().delete()
print(count)
EOF
)

# Log the result with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Deleted customers: $deleted_count" >> /tmp/customer_cleanup_log.txt
