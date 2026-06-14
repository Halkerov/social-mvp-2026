from .models import Notification, Friendship

def user_theme(request):
    theme = 'light'
    if request.user.is_authenticated:
        theme = request.user.profile.theme if hasattr(request.user, 'profile') else 'light'
    
    unread_count = 0
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return {
        'user_theme': theme,
        'unread_count': unread_count,
    }


# ✅ ДОБАВЬ ЭТУ ФУНКЦИЮ В КОНЕЦ ФАЙЛА
def friend_requests_count(request):
    """Добавляет количество заявок в друзья в контекст"""
    if not request.user.is_authenticated:
        return {'pending_requests_count': 0, 'sent_requests_count': 0}
    
    pending_count = Friendship.objects.filter(
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    sent_count = Friendship.objects.filter(
        requester=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    return {
        'pending_requests_count': pending_count,
        'sent_requests_count': sent_count,
    }