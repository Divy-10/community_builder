from .models import user

def user_context(request):
    """
    Context processor to add the custom user object to all templates
    if the user is logged in (userid is in session).
    """
    context = {'current_user': None}
    userid = request.session.get('userid')
    if userid:
        try:
            current_user = user.objects.get(pk=userid)
            context['current_user'] = current_user
        except user.DoesNotExist:
            pass
    return context
