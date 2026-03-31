from django.utils import timezone
from .models import user

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'userid' in request.session:
            try:
                # Update last_seen for the logged-in user
                userid = request.session['userid']
                user.objects.filter(pk=userid).update(last_seen=timezone.now())
            except Exception:
                pass
        
        response = self.get_response(request)
        return response
