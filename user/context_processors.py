from .models import user, communitymember, communityMessage, community, CommunityInvite, post, like, comment, follow, chat, UserSettings
from django.contrib import admin
from django.db.models import Max
from django.utils import timezone
from datetime import timedelta

def user_context(request):
    """
    Context processor to add the custom user object and joined community chats to all templates.
    """
    context = {
        'current_user': None,
        'joined_community_chats': [],
        'unread_chat_count': 0,
        'activity_count': 0,
        'invitation_count': 0,
        'admin_user_models': []
    }

    # Fetch 'user' app models for admin navbar
    try:
        app_list = admin.site.get_app_list(request)
        for app in app_list:
            if app.get('app_label') == 'user':
                context['admin_user_models'] = app.get('models', [])
                break
    except Exception:
        pass
    userid = request.session.get('userid')
    if userid:
        try:
            current_user = user.objects.get(pk=userid)
            context['current_user'] = current_user
            
            # Fetch user settings and add to context
            try:
                settings, created = UserSettings.objects.get_or_create(user=current_user)
                context['user_settings'] = settings
            except Exception:
                context['user_settings'] = None
            
            # 1. Invitations Count (Pending Community Invites since last checked)
            invites_query = CommunityInvite.objects.filter(receiverid=current_user, status=0)
            if current_user.last_checked_invites:
                invites_query = invites_query.filter(createddt__gt=current_user.last_checked_invites)
            context['invitation_count'] = invites_query.count()
            
            
            # 2. Activity Count (Likes, Comments, Follows since last checked)
            my_posts = post.objects.filter(userid=current_user).values_list('postid', flat=True)
            last_activity = current_user.last_checked_activity or (timezone.now() - timedelta(days=7))
            
            likes_count = like.objects.filter(postid__in=my_posts, createddt__gt=last_activity).count()
            comm_count = comment.objects.filter(postid__in=my_posts, createddt__gt=last_activity).count()
            follow_count = follow.objects.filter(userid=current_user, createddt__gt=last_activity).count()
            
            activity_total = 0
            if settings and settings.push_notifications:
                 activity_total = likes_count + comm_count + follow_count
                 
            context['activity_count'] = activity_total
            
            # 3. Chat Notifications (Community + Private)
            # Private Chats: Messages where current user is receiver and status is Unread (0)
            unread_private_count = chat.objects.filter(receiverid=current_user.userid, status=0).count()
            context['unread_chat_count'] = unread_private_count
            
            # Community Chats: Messages since last global check
            joined_comms = communitymember.objects.filter(userid=current_user, status=1).values_list('communityid', flat=True)
            created_comms = community.objects.filter(userid=current_user).values_list('communityid', flat=True)
            all_comms_ids = set(joined_comms) | set(created_comms)
            
            chat_list = []
            last_chat_check = current_user.last_checked_chats or (timezone.now() - timedelta(days=7))
            
            for cid in all_comms_ids:
                comm = community.objects.filter(pk=cid).first()
                if comm:
                    last_msg = communityMessage.objects.filter(communityid=comm).order_by('-senddt').first()
                    # Check for unread messages in this community
                    if settings and settings.community_updates:
                        if last_msg and last_msg.senddt > last_chat_check and last_msg.senderid != current_user.userid:
                            context['unread_chat_count'] += 1
                    
                    last_user_name = "System"
                    if last_msg:
                        sender = user.objects.filter(pk=last_msg.senderid).first()
                        if sender:
                            last_user_name = sender.username
                    
                    chat_list.append({
                        'community': comm,
                        'last_message': last_msg,
                        'last_user_name': last_user_name
                    })
            
            # Sort by latest message date if it exists, otherwise use community created date
            chat_list.sort(key=lambda x: x['last_message'].senddt if x['last_message'] else x['community'].createddt, reverse=True)
            context['joined_community_chats'] = chat_list[:5] # Show latest 5 chats
            
        except user.DoesNotExist:
            pass
    return context
