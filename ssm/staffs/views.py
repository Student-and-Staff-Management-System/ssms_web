from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Staff

def stafflogin(request):
    """Handles staff login."""
    if 'staff_id' in request.session:
        return redirect('staffs:staffdash')

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        try:
            staff = Staff.objects.get(staff_id=staff_id)
            if staff.check_password(password):
                request.session['staff_id'] = staff.staff_id
                # --- THIS IS THE FIX ---
                # Use the correct URL name 'staff_dashboard' with the namespace
                return redirect('staffs:staffdash')
            else:
                messages.error(request, 'Invalid Staff ID or Password.')
        except Staff.DoesNotExist:
            messages.error(request, 'Invalid Staff ID or Password.')
            
    return render(request, 'staff/stafflogin.html')


def staff_dashboard(request):
    """Displays the staff dashboard. Requires login."""
    if 'staff_id' not in request.session:
        return redirect('staffs:staff_login')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        if 'staff_id' in request.session:
            del request.session['staff_id']
        return redirect('staffs:stafflogin')

    return render(request, 'staff/staffdash.html', {'staff': staff})


def staff_logout(request):
    """Logs the staff member out."""
    try:
        del request.session['staff_id']
    except KeyError:
        pass
    messages.success(request, "You have been successfully logged out.")
    return redirect('staffs:stafflogin')

def staff_register(request):
    """Handles the creation of a new staff member."""
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        
        if Staff.objects.filter(staff_id=staff_id).exists():
            messages.error(request, f"A staff member with the ID '{staff_id}' already exists.")
            return render(request, 'staff/staff_register.html')
        
        new_staff = Staff(
            staff_id=staff_id,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            photo=request.FILES.get('photo'),
            salutation=request.POST.get('salutation'),
            designation=request.POST.get('designation'),
            department=request.POST.get('department'),
            qualification=request.POST.get('qualification'),
            specialization=request.POST.get('specialization'),
            date_of_birth=request.POST.get('date_of_birth') or None,
            date_of_joining=request.POST.get('date_of_joining') or None,
            address=request.POST.get('address'),
            academic_details=request.POST.get('academic_details'),
            experience=request.POST.get('experience'),
            publications=request.POST.get('publications'),
            awards_and_memberships=request.POST.get('awards_and_memberships'),
        )
        
        new_staff.set_password(request.POST.get('password'))
        new_staff.save()
        
        messages.success(request, f"Staff member {new_staff.name} has been registered successfully.")
        return redirect('staffs:staff_login')

    return render(request, 'staff/staff_register.html')
