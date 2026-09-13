"""
Custom middleware to ensure static files are served with correct headers
"""
from django.utils.deprecation import MiddlewareMixin


class StaticFilesHeadersMiddleware(MiddlewareMixin):
    """
    Ensure static files (CSS, JS) are served with correct Content-Type headers
    """
    def process_response(self, request, response):
        # Only process static file requests
        if request.path.startswith('/static/'):
            # Set correct Content-Type for CSS files
            if request.path.endswith('.css'):
                response['Content-Type'] = 'text/css; charset=utf-8'
            # Set correct Content-Type for JS files
            elif request.path.endswith('.js'):
                response['Content-Type'] = 'application/javascript; charset=utf-8'
            # Ensure CORS headers don't block static files
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET'
            response['Access-Control-Allow-Headers'] = '*'
        return response

class StaffAdminAutoLoginMiddleware(MiddlewareMixin):
    """
    Middleware to automatically authenticate HOD or assigned Admin staff members
    into Django Native Admin (/admin/) without requiring a separate login prompt.
    """
    def process_request(self, request):
        if request.path.startswith('/admin/'):
            staff_id = request.session.get('staff_id')
            if staff_id:
                try:
                    from staffs.models import Staff
                    staff = Staff.objects.filter(staff_id=staff_id).first()
                    if staff and staff.is_staff_admin:
                        username = staff.staff_id.replace(" ", "").upper()
                        if not request.user.is_authenticated or request.user.username != username:
                            from django.contrib.auth.models import User
                            from django.contrib.auth import login

                            user = User.objects.filter(username=username).first()
                            if not user and staff.email:
                                user = User.objects.filter(email=staff.email).first()

                            if not user:
                                user = User.objects.create_user(
                                    username=username,
                                    email=staff.email or f"{username.lower()}@ssms.edu",
                                    password=staff.password
                                )
                                user.first_name = staff.name

                            if not user.is_staff or not user.is_superuser:
                                user.is_staff = True
                                user.is_superuser = True
                                user.save()

                            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                except Exception:
                    pass








