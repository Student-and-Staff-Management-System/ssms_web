from .models import Staff, StaffHourSwapRequest, StaffNotification

def staff_context(request):
    """
    Context processor to provide the logged-in staff member globally across all templates,
    along with global notification counts and recent notifications list.
    """
    staff_id = request.session.get('staff_id')
    if staff_id:
        try:
            logged_in_staff = Staff.objects.get(staff_id=staff_id)
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
            ).order_by('-created_at')[:10]

            return {
                'logged_in_staff': logged_in_staff,
                'pending_hour_swaps_count': pending_hour_swaps_count,
                'unread_notifications_count': unread_notifications_count,
                'staff_recent_notifications': staff_recent_notifications,
            }
        except Staff.DoesNotExist:
            pass
    return {
        'logged_in_staff': None,
        'pending_hour_swaps_count': 0,
        'unread_notifications_count': 0,
        'staff_recent_notifications': [],
    }

