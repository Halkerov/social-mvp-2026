from django.utils import timezone
from django.contrib.auth.models import User

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Обновляем last_seen при каждом запросе
            try:
                profile = request.user.profile
                profile.last_seen = timezone.now()
                profile.save(update_fields=['last_seen'])
            except:
                pass
        
        response = self.get_response(request)
        return response