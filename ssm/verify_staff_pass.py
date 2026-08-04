import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import Staff

staff = Staff.objects.get(staff_id="STAFF03")
print("Staff Name:", staff.name)
print("Staff Email:", staff.email)
print("Password check 'STAFF03':", staff.check_password("STAFF03"))
