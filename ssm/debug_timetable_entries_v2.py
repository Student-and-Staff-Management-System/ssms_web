
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import Timetable

semester = 6
entries = Timetable.objects.filter(semester=semester).order_by('day', 'period', 'batch')

with open('debug_timetable_entries_v2.txt', 'w', encoding='utf-8') as f:
    f.write(f"Timetable for Semester {semester}:\n")
    for e in entries:
        f.write(f"{e.day} P{e.period} Batch:{e.batch} Subject:{e.subject.code if e.subject else 'None'} Staff:{e.staff.name if e.staff else 'None'}\n")
