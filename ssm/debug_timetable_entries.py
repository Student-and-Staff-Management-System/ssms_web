
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import Timetable

semester = 6
entries = Timetable.objects.filter(semester=semester).order_by('day', 'period', 'batch')

print(f"Timetable for Semester {semester}:")
for e in entries:
    print(f"{e.day} P{e.period} Batch:{e.batch} Subject:{e.subject.code if e.subject else 'None'} Staff:{e.staff.name if e.staff else 'None'}")
