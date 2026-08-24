from .models import Staff

def staff_context(request):
    """
    Context processor to provide the logged-in staff member globally across all templates.
    Prevents context variable collisions when viewing other staff profiles or records.
    """
    staff_id = request.session.get('staff_id')
    if staff_id:
        try:
            logged_in_staff = Staff.objects.get(staff_id=staff_id)
            return {
                'logged_in_staff': logged_in_staff,
            }
        except Staff.DoesNotExist:
            pass
    return {
        'logged_in_staff': None,
    }
