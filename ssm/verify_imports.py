import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\sachi\OneDrive\Desktop\nojinx\ssm')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssm.settings')
django.setup()

try:
    from staffs import views
    from staffs import urls
    print("Imports successful.")
    
    # Check if new views exist
    assert hasattr(views, 'portfolio_add_conference')
    assert hasattr(views, 'portfolio_add_journal')
    assert hasattr(views, 'portfolio_add_book')
    print("New views verified.")
    
except Exception as e:
    print(f"Error: {e}")
