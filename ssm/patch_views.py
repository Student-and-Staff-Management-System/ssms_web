import re

file_path = r'c:\Users\sachi\OneDrive\Desktop\nojinx\ssm\students\scholars_views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update scholar_portfolio_add logic for staff_ids
# Replace the staff selection block
old_selection = r"""        staff_id = request\.POST\.get\('staff_id'\)
        staff = get_object_or_404\(Staff, staff_id=staff_id\) if staff_id else None
        
        if not staff:
            messages\.error\(request, "Please select a Staff member\."\)
            return redirect\(request\.path\)"""

new_selection = """        staff_ids = request.POST.getlist('staff_ids')
        if not staff_ids:
            messages.error(request, "Please select at least one Faculty member.")
            return redirect(request.path)"""

content = re.sub(old_selection, new_selection, content)

# 2. Remove staff=staff from constructors and add item.staff.set(staff_ids)
# Specifically for ConferenceParticipation, JournalPublication, BookPublication, StaffSeminar, StaffAwardHonour
# They were like: item = Model(student=student, staff=staff)
content = re.sub(r"item = ConferenceParticipation\(student=student, staff=staff\)", "item = ConferenceParticipation(student=student)", content)
content = re.sub(r"item = JournalPublication\(student=student, staff=staff\)", "item = JournalPublication(student=student)", content)
content = re.sub(r"item = BookPublication\(student=student, staff=staff\)", "item = BookPublication(student=student)", content)
content = re.sub(r"item = StaffSeminar\(student=student, staff=staff\)", "item = StaffSeminar(student=student)", content)
content = re.sub(r"item = StaffAwardHonour\(student=student, staff=staff\)", "item = StaffAwardHonour(student=student)", content)

# Add item.staff.set(staff_ids) after item.save()
content = re.sub(r"item\.save\(\)\n(\s*)messages\.success\(request, \"Conference added\.\"\)", r"item.save()\n\1item.staff.set(staff_ids)\n\1messages.success(request, \"Conference added.\")", content)
content = re.sub(r"item\.save\(\)\n(\s*)messages\.success\(request, \"Journal added\.\"\)", r"item.save()\n\1item.staff.set(staff_ids)\n\1messages.success(request, \"Journal added.\")", content)
content = re.sub(r"item\.save\(\)\n(\s*)messages\.success\(request, \"Book added\.\"\)", r"item.save()\n\1item.staff.set(staff_ids)\n\1messages.success(request, \"Book added.\")", content)
content = re.sub(r"item\.save\(\)\n(\s*)messages\.success\(request, \"Seminar added\.\"\)", r"item.save()\n\1item.staff.set(staff_ids)\n\1messages.success(request, \"Seminar added.\")", content)
content = re.sub(r"item\.save\(\)\n(\s*)messages\.success\(request, \"Award added\.\"\)", r"item.save()\n\1item.staff.set(staff_ids)\n\1messages.success(request, \"Award added.\")", content)

# 3. Update scholar_portfolio_edit logic
# It had staff_id = ... block too
old_edit_selection = r"""        staff_id = request\.POST\.get\('staff_id'\)
        staff = get_object_or_404\(Staff, staff_id=staff_id\) if staff_id else None
        
        if staff:
            item\.staff = staff"""

new_edit_selection = """        staff_ids = request.POST.getlist('staff_ids')
        if staff_ids:
            item.staff.set(staff_ids)"""

content = re.sub(old_edit_selection, new_edit_selection, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated views.py")
