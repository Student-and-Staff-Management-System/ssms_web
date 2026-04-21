import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

from staffs.models import (
    ConferenceParticipation, JournalPublication, 
    BookPublication, StaffSeminar, StaffAwardHonour
)

models_to_migrate = [
    ConferenceParticipation, JournalPublication, 
    BookPublication, StaffSeminar, StaffAwardHonour
]

for model in models_to_migrate:
    print(f"Migrating {model.__name__}...")
    for item in model.objects.all():
        if item.staff:
            item.associated_staffs.add(item.staff)
    print(f"Done with {model.__name__}")

print("Data migration complete!")
