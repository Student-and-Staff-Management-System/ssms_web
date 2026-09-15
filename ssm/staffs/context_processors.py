from .models import Staff, StaffHourSwapRequest, StaffNotification

def staff_context(request):
    """
    Context processor to provide the logged-in staff member globally across all templates,
    along with global notification counts, active role, all assigned roles, and recent notifications.
    """
    staff_id = request.session.get('staff_id')
    if staff_id:
        try:
            logged_in_staff = Staff.objects.get(staff_id=staff_id)
            all_assigned_roles = logged_in_staff.get_roles_list()
            active_role = request.session.get('active_role')
            if not active_role or active_role not in all_assigned_roles:
                active_role = logged_in_staff.role

            pending_hour_swaps_count = StaffHourSwapRequest.objects.filter(
                target_staff=logged_in_staff,
                status='Pending'
            ).count()

            unread_notifications_count = StaffNotification.objects.filter(
                staff=logged_in_staff,
                is_read=False
            ).count()

            staff_recent_notifications = StaffNotification.objects.filter(
                staff=logged_in_staff
            ).order_by('-created_at')[:25]

            assigned_consoles = logged_in_staff.get_assigned_consoles()

            return {
                'logged_in_staff': logged_in_staff,
                'active_role': active_role,
                'all_assigned_roles': all_assigned_roles,
                'assigned_consoles': assigned_consoles,
                'pending_hour_swaps_count': pending_hour_swaps_count,
                'unread_notifications_count': unread_notifications_count,
                'staff_recent_notifications': staff_recent_notifications,
            }
        except Staff.DoesNotExist:
            pass
    return {
        'logged_in_staff': None,
        'active_role': None,
        'all_assigned_roles': [],
        'assigned_consoles': [],
        'pending_hour_swaps_count': 0,
        'unread_notifications_count': 0,
        'staff_recent_notifications': [],
    }

