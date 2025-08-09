import logging
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse

logger = logging.getLogger('core.admin')

class AdminAccessControlMiddleware(MiddlewareMixin):
    """
    Middleware to redirect non-admin users from /admin/ to settings page
    Admin yetkisi olmayan kullanıcıları /admin/'den ayarlara yönlendirir
    """
    
    def process_request(self, request):
        # Check if user is trying to access admin area
        if request.path.startswith('/admin/'):
            user = getattr(request, 'user', None)
            
            # If user is not authenticated, allow Django to handle (will redirect to login)
            if not user or not user.is_authenticated:
                return None
            
            # If user is authenticated but not staff, redirect to settings
            if not user.is_staff:
                logger.warning(
                    f"Non-staff user {user.username} attempted to access admin at {request.path}. "
                    f"Redirected to settings. IP: {self.get_client_ip(request)}"
                )
                # Redirect to settings page instead of showing 403
                return redirect('settings_page')
            
            # If user is staff, log successful access
            logger.info(
                f"Staff user {user.username} accessed admin at {request.path}. "
                f"IP: {self.get_client_ip(request)}"
            )
        
        return None
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to log and monitor admin access attempts
    """
    
    def process_request(self, request):
        # Log superuser admin access attempts
        if request.path.startswith('/superuser-admin/'):
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                if not user.is_superuser:
                    logger.warning(
                        f"Unauthorized superuser admin access attempt by {user.username} "
                        f"({user.email}) from IP {self.get_client_ip(request)} "
                        f"to {request.path}"
                    )
                else:
                    logger.info(
                        f"Superuser admin access granted to {user.username} "
                        f"from IP {self.get_client_ip(request)} to {request.path}"
                    )
        
        return None
    
    def process_exception(self, request, exception):
        """Handle PermissionDenied exceptions for admin areas"""
        if isinstance(exception, PermissionDenied):
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                logger.error(
                    f"Permission denied for user {user.username} "
                    f"from IP {self.get_client_ip(request)} "
                    f"accessing {request.path}: {str(exception)}"
                )
            
            # Return custom 403 page for superuser admin areas
            if request.path.startswith('/superuser-admin/') or request.path.startswith('/admin-dashboard/'):
                return render(request, '403.html', status=403)
        
        return None
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminDashboardSecurityMiddleware(MiddlewareMixin):
    """
    Specific middleware for admin dashboard security
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check for admin-dashboard access
        if request.path == '/admin-dashboard/':
            user = getattr(request, 'user', None)
            
            # Log access attempt
            if user and user.is_authenticated:
                if user.is_superuser:
                    logger.info(
                        f"Admin dashboard access granted to superuser {user.username} "
                        f"from IP {self.get_client_ip(request)}"
                    )
                else:
                    logger.warning(
                        f"Admin dashboard access denied to non-superuser {user.username} "
                        f"({user.email}) from IP {self.get_client_ip(request)}"
                    )
            else:
                logger.warning(
                    f"Unauthenticated admin dashboard access attempt "
                    f"from IP {self.get_client_ip(request)}"
                )
        
        return None
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 