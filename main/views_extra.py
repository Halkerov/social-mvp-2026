# Additional Views for Friends, Notifications
# These are already implemented in main/views.py
# This file is kept for reference only

# Notifications
@login_required
def notifications_list(request):
    notifications = request.user.notifications.all()[:50]
    for notif in notifications:
        notif.is_read = True
        notif.save()
    return render(request, 'main/notifications.html', {'notifications': notifications})

@login_required
def notifications_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    return redirect('notifications_list')
