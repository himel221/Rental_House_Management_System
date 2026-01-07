from .models import Notifications

def notifications_context(request):
    """
    Context processor to add unread notification count to all templates.
    """
    context = {
        'unread_notifications_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            context['unread_notifications_count'] = Notifications.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        except Exception:
            pass
    
    return context
