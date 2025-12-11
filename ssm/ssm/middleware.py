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



