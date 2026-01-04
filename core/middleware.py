"""
Custom middleware to replace django-login-required-middleware
which is incompatible with Django 5.0 (uses deprecated is_ajax() method)
"""
from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve


class LoginRequiredMiddleware:
    """
    Middleware that requires a user to be authenticated to view any page.
    URLs listed in LOGIN_REQUIRED_IGNORE_VIEW_NAMES setting are exempt.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.ignore_view_names = getattr(settings, 'LOGIN_REQUIRED_IGNORE_VIEW_NAMES', [])

    def __call__(self, request):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            # Try to resolve the current view name
            try:
                resolver_match = resolve(request.path_info)
                # Get the URL name from the resolved view
                view_name = resolver_match.url_name
                
                # Allow access if view name is in ignore list
                if view_name in self.ignore_view_names:
                    return self.get_response(request)
            except Exception:
                # If we can't resolve, continue to check (might be a 404 or other error)
                pass
            
            # Redirect to login page
            login_url = getattr(settings, 'LOGIN_URL', '/login/')
            return redirect(login_url)
        
        return self.get_response(request)

