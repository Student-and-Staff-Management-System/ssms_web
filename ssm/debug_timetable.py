
import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import Subject, Timetable

def debug_timetable():
    print("Listing all Subjects and their Timetables...")
    subjects = Subject.objects.all()
    
    for sub in subjects:
        print(f"\nSubject: {sub.name} ({sub.code}) - Sem {sub.semester}")
        timetables = Timetable.objects.filter(subject=sub)
        if timetables.exists():
            for tt in timetables:
                print(f"  -> Scheduled: {tt.day} Period {tt.period} (TT Sem: {tt.semester})")
                
                # Check mismatch
                if tt.semester != sub.semester:
                    print(f"     [WARNING] SEMESTER MISMATCH! Subject Sem={sub.semester} vs Timetable Sem={tt.semester}")
        else:
            print("  -> No Timetable entries found.")

if __name__ == "__main__":
    debug_timetable()
