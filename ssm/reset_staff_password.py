import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import Staff

def reset_password(staff_id="STAFF03", new_password="STAFF03"):
    try:
        staff = Staff.objects.get(staff_id=staff_id)
        staff.set_password(new_password)
        staff.save(update_fields=['password'])
        print(f"SUCCESS: Password for staff ID '{staff.staff_id}' ({staff.name}) has been reset to '{new_password}'.")
    except Staff.DoesNotExist:
        print(f"ERROR: Staff with ID '{staff_id}' does not exist.")

if __name__ == "__main__":
    target_id = sys.argv[1] if len(sys.argv) > 1 else "STAFF03"
    target_pass = sys.argv[2] if len(sys.argv) > 2 else "STAFF03"
    reset_password(target_id, target_pass)
