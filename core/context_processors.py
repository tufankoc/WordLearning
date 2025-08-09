from .models import UserProfile


def user_profile(request):
    """
    Context processor to add user profile and Pro status to all templates.
    """
    context = {
        'user_is_pro': False,
        'user_profile': None,
    }
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            context['user_profile'] = profile
            context['user_is_pro'] = profile.is_pro_active()
        except UserProfile.DoesNotExist:
            # Profile doesn't exist yet, create it
            profile = UserProfile.objects.create(user=request.user)
            context['user_profile'] = profile
            context['user_is_pro'] = False
    
    return context 