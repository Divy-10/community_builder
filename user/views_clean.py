from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json
from .models import *
# Create your views here.
def home(request):
    userid = request.session.get('userid')
    if not userid:
        communities = community.objects.all().order_by('-createddt')
        data = {
            'posts': None,
            'user_likes': [],
            'communities': communities,
            'pending_ids': set(),
        }
        return render(request, 'home.html', data)

    u = user.objects.get(pk=userid)
    
    # --- Stories Section ---
    # Get stories from last 24 hours from following users + self
    last_24h = timezone.now() - timedelta(hours=24)
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    
    # Get everyone's stories (following + self)
    story_user_ids = list(following_ids) + [userid]
    recent_stories = story.objects.filter(
        userid_id__in=story_user_ids, 
        createddt__gte=last_24h
    ).order_by('createddt').select_related('userid')
    
    # Group stories by user and check if they are "seen"
    stories_by_user = {}
    for s in recent_stories:
        if s.userid_id not in stories_by_user:
            # Check if this user's story has been seen by the current user
            is_seen = StorySeen.objects.filter(storyid=s, userid_id=userid).exists()
            stories_by_user[s.userid_id] = {
                'stories': [],
                'all_seen': True # Assume all seen until we find an unseen one
            }
        
        # Check if THIS specific story is seen
        story_is_seen = StorySeen.objects.filter(storyid=s, userid_id=userid).exists()
        if not story_is_seen:
            stories_by_user[s.userid_id]['all_seen'] = False

        # Get view details (for owner to see the list)
        view_records = StorySeen.objects.filter(storyid=s).select_related('userid')
        viewers = []
        for vr in view_records:
            viewers.append({
                'username': vr.userid.username,
                'profile': vr.userid.profile.url if vr.userid.profile else '/static/assets/images/user/1.jpg'
            })

        stories_by_user[s.userid_id]['stories'].append({
            'id': s.storyid,
            'url': s.image.url,
            'seen': story_is_seen,
            'views': view_records.count(),
            'viewers': viewers,
            'created_at': s.createddt.isoformat()
        })

    # Separate 'Mine' from 'Others'
    my_data = stories_by_user.get(userid, {'stories': [], 'all_seen': True})
    my_stories_json = json.dumps(my_data['stories'])
    my_all_seen = my_data['all_seen']
    
    other_users_stories = []
    for uid, data in stories_by_user.items():
        if uid != userid:
            usr = user.objects.get(pk=uid)
            other_users_stories.append({
                'user': usr,
                'stories_json': json.dumps(data['stories']),
                'all_seen': data['all_seen']
            })

    user_communities = communitymember.objects.filter(userid=u, status=1).values_list('communityid', flat=True)
    creator_communities = community.objects.filter(userid=u).values_list('communityid', flat=True)
    
    all_my_communities = set(user_communities) | set(creator_communities)

    # --- Sidebar Data ---
    # Active Users (Random users for demo, excluding self)
    active_users = user.objects.exclude(userid=userid).order_by('?')[:4]
    
    # Suggestions For You (Users not followed yet)
    suggested_users = user.objects.exclude(
        userid__in=list(following_ids) + [userid]
    ).order_by('?')[:3]

    # --- Latest Activities (Likes, Comments, Follows on current user) ---
    my_posts = post.objects.filter(userid=userid).values_list('postid', flat=True)
    
    recent_comments = comment.objects.filter(postid__in=my_posts).select_related('userid').order_by('-createddt')[:5]
    recent_likes = like.objects.filter(postid__in=my_posts).select_related('userid', 'postid').order_by('-likeid')[:5] # Assuming likeid order for recency
    recent_follows = follow.objects.filter(userid=userid).order_by('-followid')[:5] # Users who followed me

    latest_activities = []
    for c in recent_comments:
        latest_activities.append({
            'user': c.userid,
            'text': 'commented on your post.',
            'time': c.createddt
        })
    for l in recent_likes:
        latest_activities.append({
            'user': l.userid,
            'text': 'liked your post.',
            'time': timezone.now() # Simulated time as Like model lacks createddt
        })
    for f in recent_follows:
        try:
            follower = user.objects.get(pk=f.followerid)
            latest_activities.append({
                'user': follower,
                'text': 'followed you.',
                'time': timezone.now()
            })
        except user.DoesNotExist:
            continue

    # Sort combined activities by time (most recent first)
    latest_activities.sort(key=lambda x: x['time'], reverse=True)
    latest_activities = latest_activities[:4] # Limit to 4 for sidebar

    if all_my_communities:
        posts = post.objects.filter(communityid__in=all_my_communities).order_by('-createddt')
        user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)
        data = {
            'posts': posts,
            'user_likes': user_likes,
            'communities': None,
            'pending_ids': set(),
            'current_user': u,
            'my_stories': my_stories_json,
            'my_all_seen': my_all_seen,
            'other_users_stories': other_users_stories,
            'active_users': active_users,
            'suggested_users': suggested_users,
            'latest_activities': latest_activities,
        }
    else:
        communities = community.objects.all().order_by('-createddt')
        pending_ids = set(
            communitymember.objects.filter(userid=u, status=0).values_list('communityid_id', flat=True)
        )
        data = {
            'posts': None,
            'user_likes': [],
            'communities': communities,
            'pending_ids': pending_ids,
            'current_user': u,
            'my_stories': my_stories_json,
            'my_all_seen': my_all_seen,
            'other_users_stories': other_users_stories,
            'active_users': active_users,
            'suggested_users': suggested_users,
            'latest_activities': latest_activities,
        }

    return render(request, 'home.html', data)

def add_story(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    if request.method == 'POST':
        image = request.FILES.get('story_image')
        if image:
            u = user.objects.get(pk=userid)
            s = story.objects.create(userid=u, image=image)
            s.save()
    
    return redirect('home')

def mark_story_seen(request):
    userid = request.session.get('userid')
    if not userid:
        return JsonResponse({'success': False, 'error': 'Not logged in'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            story_id = data.get('story_id')
            if story_id:
                u = user.objects.get(pk=userid)
                s = story.objects.get(pk=story_id)
                # Mark as seen if not already
                StorySeen.objects.get_or_create(storyid=s, userid=u)
                return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def blog_list(request):
    blogs = blog.objects.all().order_by('-createddt')
    return render(request, 'blog_list.html', {'blogs': blogs})

def blog_detail(request, blog_id):
    blog_obj = get_object_or_404(blog, pk=blog_id)
    return render(request, 'blog_detail.html', {'blog': blog_obj})

def buzz(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    u = user.objects.get(pk=userid)
    
    # Get IDs of users current user is following
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    
    if following_ids:
        # Get posts only from followed users, approved posts only if your logic requires it (assuming all are shown here based on home logic, but we can filter by isapproved=True if needed. The home page doesn't filter by isapproved, it filters by community. Let's filter by userid__in=following_ids)
        # Assuming we want to show posts from any community they posted in.
        posts = post.objects.filter(userid__in=following_ids).order_by('-createddt')
        user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)
        data = {
            'posts': posts,
            'user_likes': user_likes,
            'has_following': True,
        }
    else:
        data = {
            'posts': None,
            'user_likes': [],
            'has_following': False,
        }

    return render(request, 'buzz.html', data)

def signup(request):
    import re
    data={
        "states":state.objects.all()
    }
    if request.POST.get('sign-up-btn'):
        username=request.POST.get('name')
        email=request.POST.get('email','').strip()
        password=request.POST.get('password','')
        profile=request.FILES.get('fup')
        bio=request.POST.get('bio')
        gender=request.POST.get('gender')
        dob=request.POST.get('dob')
        cityid=request.POST.get('city')

        # ── Email Validation ──
        email_regex = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not email:
            data['error_msg'] = 'Email is required.'
            return render(request, 'sign-up.html', data)
        if ' ' in email:
            data['error_msg'] = 'Email must not contain spaces.'
            return render(request, 'sign-up.html', data)
        if not re.match(email_regex, email):
            data['error_msg'] = 'Please enter a valid email address.'
            return render(request, 'sign-up.html', data)
        if user.objects.filter(email=email).exists():
            data['error_msg'] = 'This email is already registered. Please use a different email.'
            return render(request, 'sign-up.html', data)

        # ── Password Validation ──
        if len(password) < 8:
            data['error_msg'] = 'Password must be at least 8 characters long.'
            return render(request, 'sign-up.html', data)
        if not re.search(r'[A-Z]', password):
            data['error_msg'] = 'Password must contain at least one uppercase letter.'
            return render(request, 'sign-up.html', data)
        if not re.search(r'[a-z]', password):
            data['error_msg'] = 'Password must contain at least one lowercase letter.'
            return render(request, 'sign-up.html', data)
        if not re.search(r'[0-9]', password):
            data['error_msg'] = 'Password must contain at least one number.'
            return render(request, 'sign-up.html', data)
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            data['error_msg'] = 'Password must contain at least one special character.'
            return render(request, 'sign-up.html', data)
        if ' ' in password:
            data['error_msg'] = 'Password must not contain spaces.'
            return render(request, 'sign-up.html', data)

        u=user.objects.create(userid=None,username=username,email=email,password=password,profile=profile,bio=bio,gender=gender,dob=dob,cityid=city.objects.get(pk=cityid))
        u.save()
        return redirect('signin')
    return render(request,'sign-up.html',data)

def get_cities_by_state(request, state_id):
    cities = city.objects.filter(stateid_id=state_id).values('cityid', 'cityname')
    return JsonResponse(list(cities), safe=False)

def signin(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.POST.get('sign-in-btn') or is_ajax:
        email=request.POST.get('email')
        password=request.POST.get('password')
        u=user.objects.filter(email=email,password=password).first()
        if u==None:
            if is_ajax:
                return JsonResponse({"success": False, "msg": "invalid email or password"})
            data={"simsg":"invalid email or password"}
            return render(request,'sign-in.html',data)
        else:
            request.session['userid']=u.userid
            request.session['username']=u.username
            if is_ajax:
                return JsonResponse({"success": True, "redirect_url": "/", "username": u.username}) # Assuming home URL is '/' or we can resolve it
            return redirect('home')

    return render(request,'sign-in.html')

def logout_view(request):
    request.session.flush()
    return redirect('signup')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        
        u = user.objects.filter(email=email).first()
        if u:
            u.password = new_password
            u.save()
            data = {"simsg": "Password reset successfully. You can now login.", "alert_type": "success"}
            return render(request, 'sign-in.html', data)
        else:
            data = {"simsg": "Email not found.", "alert_type": "danger"}
            return render(request, 'sign-in.html', data)
            
    return redirect('signin')

def group(request):
    communities = community.objects.annotate(num_members=Count('communitymember')).order_by('-createddt')

    search_name = request.GET.get('search_name', '')
    search_category = request.GET.get('search_category', '')
    search_city = request.GET.get('search_city', '')
    search_members = request.GET.get('search_members', '')

    if search_name:
        communities = communities.filter(communitytitle__icontains=search_name)
    if search_category:
        communities = communities.filter(categoryid_id=search_category)
    if search_city:
        communities = communities.filter(userid__cityid_id=search_city)
    if search_members and search_members.isdigit():
        communities = communities.filter(num_members__gte=int(search_members))

    userid = request.session.get('userid')
    joined_ids = set()
    pending_ids = set()
    admin_ids = set()
    if userid:
        joined_ids = set(
            communitymember.objects.filter(userid__userid=userid, status=1).values_list('communityid_id', flat=True)
        )
        pending_ids = set(
            communitymember.objects.filter(userid__userid=userid, status=0).values_list('communityid_id', flat=True)
        )
        admin_ids = set(
            communitymember.objects.filter(userid__userid=userid, role='admin', status=1).values_list('communityid_id', flat=True)
        )
    
    data = {
        'communities': communities,
        'joined_ids': joined_ids,
        'pending_ids': pending_ids,
        'admin_ids': admin_ids,
        'categories': category.objects.all(),
        'cities': city.objects.all(),
        'search_name': search_name,
        'search_category': search_category,
        'search_city': search_city,
        'search_members': search_members,
    }
    return render(request, 'group.html', data)

def join_group(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    if request.method == 'POST':
        c = community.objects.get(pk=community_id)
        u = user.objects.get(pk=userid)
        if not communitymember.objects.filter(communityid=c, userid=u).exists():
            communitymember.objects.create(communityid=c, userid=u, status=0, role='member')
    return redirect('group')

def create_group(request):
    allowed_categories = ['Event', 'Music', 'Programming', 'Sports', 'Gaming', 'Technology', 'Art', 'Education']
    
    # Let's ensure these categories exist, and only pass them to the template
    for cat_name in allowed_categories:
        category.objects.get_or_create(categoryname=cat_name)
        
    data = {
        "categories": category.objects.filter(categoryname__in=allowed_categories),
    }
    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('description')
        thumb = request.FILES.get('thumbnail')
        bg_image = request.FILES.get('background_image')
        cat_id = request.POST.get('category')
        
        userid = request.session.get('userid')
        if not userid:
            return redirect('signin')

        u = user.objects.get(pk=userid)
        cat = category.objects.get(pk=cat_id)

        is_paid = request.POST.get('is_paid') == 'on'
        price = request.POST.get('price')
        if not is_paid or not price:
            price = 0

        c = community.objects.create(
            communitytitle=title, 
            discription=desc, 
            thumbnail=thumb, 
            background_image=bg_image,
            categoryid=cat, 
            userid=u,
            is_paid=is_paid,
            price=price
        )
        c.save()

        ca = communityAdmins.objects.create(
            communityid=c,
            adminid=u,
            addedbyuserid=u.userid
        )
        ca.save()

        cm = communitymember.objects.create(
            communityid=c,
            userid=u,
            status=1,
            role='admin'
        )
        cm.save()
        
        return redirect('group')
        
    return render(request, 'create-group.html', data)

def edit_community(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    
    # Ensure only admins can edit
    if not _is_community_admin(userid, c):
        return redirect('community_detail', community_id=community_id)

    allowed_categories = ['Event', 'Music', 'Programming', 'Sports', 'Gaming', 'Technology', 'Art', 'Education']
    data = {
        "community": c,
        "categories": category.objects.filter(categoryname__in=allowed_categories),
    }

    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('description')
        thumb = request.FILES.get('thumbnail')
        bg_image = request.FILES.get('background_image')
        cat_id = request.POST.get('category')
        
        c.communitytitle = title
        c.discription = desc
        
        if thumb:
            c.thumbnail = thumb
        if bg_image:
            c.background_image = bg_image
            
        if cat_id:
            c.categoryid = category.objects.get(pk=cat_id)
            
        is_paid = request.POST.get('is_paid') == 'on'
        price = request.POST.get('price')
        
        c.is_paid = is_paid
        c.price = price if (is_paid and price) else 0

        c.save()
        return redirect('group_members', community_id=community_id)
        
    return render(request, 'edit-group.html', data)


def users_list(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    current_user = user.objects.get(pk=userid)
    all_users = user.objects.exclude(pk=userid)

    search_name = request.GET.get('search_name', '')
    search_city = request.GET.get('search_city', '')

    if search_name:
        all_users = all_users.filter(username__icontains=search_name)
    if search_city:
        all_users = all_users.filter(cityid_id=search_city)
    
    # Get IDs of users current user is following
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    
    # Get communities where current user is admin or member (can invite others to these)
    my_communities = communitymember.objects.filter(userid=current_user, status=1).values_list('communityid', flat=True)
    comms_to_invite = community.objects.filter(pk__in=my_communities)
    
    data = {
        'users': all_users,
        'following_ids': following_ids,
        'comms_to_invite': comms_to_invite,
        'cities': city.objects.all(),
        'search_name': search_name,
        'search_city': search_city,
    }
    return render(request, 'users_list.html', data)

def toggle_follow(request, target_userid):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    target_user = user.objects.get(pk=target_userid)
    
    # Check if already following
    existing_follow = follow.objects.filter(followerid=userid, userid=target_user).first()
    
    if existing_follow:
        # Unfollow
        existing_follow.delete()
    else:
        # Follow
        f = follow.objects.create(followerid=userid, userid=target_user)
        f.save()
        
    return redirect('users_list')

def invite_user(request, target_userid):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    if request.method == "POST":
        community_id = request.POST.get('community_id')
        if community_id:
            target_user = user.objects.get(pk=target_userid)
            c = community.objects.get(pk=community_id)
            
            # Check if user is already a member
            is_member = communitymember.objects.filter(communityid=c, userid=target_user).exists()
            
            if not is_member:
                # Create invite if one doesn't already exist and is pending
                existing_invite = CommunityInvite.objects.filter(communityid=c, senderid=userid, receiverid=target_user, status=0).exists()
                if not existing_invite:
                    inv = CommunityInvite.objects.create(
                        communityid=c, 
                        senderid=userid, 
                        receiverid=target_user,
                        status=0
                    )
                    inv.save()
            
    return redirect('users_list')

def invitations_list(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    current_user = user.objects.get(pk=userid)
    invites = CommunityInvite.objects.filter(receiverid=current_user, status=0).order_by('-createddt')
    
    for inv in invites:
        sender = user.objects.filter(pk=inv.senderid).first()
        inv.sender_name = sender.username if sender else "Unknown User"
        
    data = {"invites": invites}
    return render(request, 'invitations_list.html', data)

def respond_invite(request, inviteid, action):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    current_user = user.objects.get(pk=userid)
    inv = CommunityInvite.objects.filter(pk=inviteid, receiverid=current_user, status=0).first()
    
    if inv:
        if action == 'accept':
            inv.status = 1
            inv.save()
            # Add to community
            cm = communitymember.objects.create(
                communityid=inv.communityid,
                userid=current_user,
                status=1
            )
            cm.save()
        elif action == 'decline':
            inv.status = 2
            inv.save()
            
    return redirect('invitations_list')

def user_profile(request, target_userid=None):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    if target_userid is None:
        target_userid = userid
        
    user_profile = user.objects.get(pk=target_userid)
    
    # Check if current user is following this user
    is_following = False
    if userid != target_userid:
        is_following = follow.objects.filter(followerid=userid, userid=user_profile).exists()
        
    is_own_profile = (userid == target_userid)
    
    # Calculate relationships
    followers_count = follow.objects.filter(userid=user_profile).count()
    following_count = follow.objects.filter(followerid=target_userid).count()
    
    # Fetch user's posts
    user_posts = post.objects.filter(userid=user_profile).order_by('-createddt')
    
    # Pre-calculate active likes for the session user across these posts
    user_likes = []
    if userid:
        user_likes = like.objects.filter(userid=userid, postid__in=user_posts).values_list('postid_id', flat=True)
    
    # Fetch user's communities
    created_communities = list(community.objects.filter(userid=user_profile))
    joined_community_ids = communitymember.objects.filter(userid=user_profile, status=1).values_list('communityid', flat=True)
    joined_communities = list(community.objects.filter(pk__in=joined_community_ids))
    
    # Merge and deduplicate just in case
    user_communities = list({c.communityid: c for c in (created_communities + joined_communities)}.values())
        
    data = {
        'user_profile': user_profile,
        'is_following': is_following,
        'is_own_profile': is_own_profile,
        'followers_count': followers_count,
        'following_count': following_count,
        'user_posts': user_posts,
        'user_likes': user_likes,
        'user_communities': user_communities
    }
    return render(request, 'user_profile.html', data)

def edit_profile(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    u = user.objects.get(pk=userid)
    data = {
        "states": state.objects.all(),
        "cities": city.objects.all(),
        "user_profile": u,
        "user_state_id": u.cityid.stateid.stateid if u.cityid else None,
    }
    
    if request.method == "POST":
        u.username = request.POST.get('name')
        u.email = request.POST.get('email')
        
        profile_img = request.FILES.get('fup')
        if profile_img:
            u.profile = profile_img
            
        u.bio = request.POST.get('bio')
        u.gender = request.POST.get('gender')
        
        dob = request.POST.get('dob')
        if dob:
            u.dob = dob
            
        cityid = request.POST.get('city')
        if cityid:
            u.cityid = city.objects.get(pk=cityid)
            
        u.save()
        
        request.session['username'] = u.username
        return redirect('my_profile')
        
    return render(request, 'edit-profile.html', data)

def delete_profile(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    if request.method == "POST":
        u = user.objects.get(pk=userid)
        u.delete()
        request.session.flush()
        return redirect('signin')
        
    return redirect('my_profile')


# ─── Group Member Management ───────────────────────────────────────

def _is_community_admin(user_id, community_obj):
    """Return True if the user is an admin of the community (by role or creator)."""
    if community_obj.userid.userid == user_id:
        return True
    return communitymember.objects.filter(
        communityid=community_obj, userid__userid=user_id, role='admin'
    ).exists()


def group_members(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    members = communitymember.objects.filter(communityid=c, status=1).select_related('userid')
    pending = communitymember.objects.filter(communityid=c, status=0).select_related('userid')
    is_admin = _is_community_admin(userid, c)

    # Fetch pending post permission requests for admins
    pending_posting_requests = None
    if is_admin:
        pending_posting_requests = communitymember.objects.filter(communityid=c, post_request_status=1).select_related('userid')

    data = {
        'community': c,
        'members': members,
        'pending': pending,
        'pending_posting_requests': pending_posting_requests,
        'is_admin': is_admin,
    }
    return render(request, 'group_members.html', data)


def accept_join_request(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    c = community.objects.get(pk=community_id)
    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)
    if request.method == 'POST':
        mem = communitymember.objects.filter(pk=member_id, communityid=c, status=0).first()
        if mem:
            mem.status = 1
            mem.save()
    return redirect('group_members', community_id=community_id)


def reject_join_request(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    c = community.objects.get(pk=community_id)
    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)
    if request.method == 'POST':
        mem = communitymember.objects.filter(pk=member_id, communityid=c, status=0).first()
        if mem:
            mem.delete()
    return redirect('group_members', community_id=community_id)


def add_member(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)

    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)

    error_msg = None
    success_msg = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'member')

        target = user.objects.filter(email=email).first()
        if not target:
            error_msg = 'No user found with that email address.'
        elif communitymember.objects.filter(communityid=c, userid=target).exists():
            error_msg = 'This user is already a member of the group.'
        else:
            communitymember.objects.create(
                communityid=c, userid=target, status=1, role=role
            )
            if role == 'admin':
                # Also add to communityAdmins for backward compat
                communityAdmins.objects.get_or_create(
                    communityid=c, adminid=target,
                    defaults={'addedbyuserid': userid}
                )
            success_msg = f'{target.username} has been added as {role}.'

    data = {
        'community': c,
        'error_msg': error_msg,
        'success_msg': success_msg,
    }
    return render(request, 'add_member.html', data)


def promote_member(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)

    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)

    if request.method == 'POST':
        mem = communitymember.objects.filter(pk=member_id, communityid=c).first()
        if mem:
            mem.role = 'admin'
            mem.save()
            # Also sync communityAdmins table
            communityAdmins.objects.get_or_create(
                communityid=c, adminid=mem.userid,
                defaults={'addedbyuserid': userid}
            )

    return redirect('group_members', community_id=community_id)


def delete_member(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)

    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)

    if request.method == 'POST':
        mem = communitymember.objects.filter(pk=member_id, communityid=c).first()
        if mem:
            # Also remove from communityAdmins if present
            communityAdmins.objects.filter(communityid=c, adminid=mem.userid).delete()
            mem.delete()

    return redirect('group_members', community_id=community_id)

# ─── Group Posts & Interactions ────────────────────────────────────

def community_detail(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    posts = post.objects.filter(communityid=c).order_by('-createddt')
    is_admin = _is_community_admin(userid, c)

    u = user.objects.get(pk=userid)
    member_obj = communitymember.objects.filter(communityid=c, userid=u, status=1).first()
    is_member = member_obj is not None
    
    can_post = False
    post_request_status = 0
    if is_member:
        can_post = member_obj.can_post
        post_request_status = member_obj.post_request_status

    # Admins or permitted users can see all posts (now all posts are assumed approved since they must be permitted to post)
    posts = post.objects.filter(communityid=c).order_by('-createddt')

    user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)

    data = {
        'community': c,
        'posts': posts,
        'is_admin': is_admin,
        'is_member': is_member,
        'can_post': can_post,
        'post_request_status': post_request_status,
        'user_likes': user_likes,
    }
    return render(request, 'community_detail.html', data)

def add_post(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    u = user.objects.get(pk=userid)
    is_admin = _is_community_admin(userid, c)
    is_member = communitymember.objects.filter(communityid=c, userid=u, status=1).exists()

    if not is_member:
        return redirect('community_detail', community_id=community_id)

    if request.method == 'POST':
        if is_member or is_admin:
            # Check permissions first
            can_post = communitymember.objects.filter(communityid=c, userid=u, status=1, can_post=True).exists()
            if not (is_admin or can_post):
                return redirect('community_detail', community_id=community_id)

            post_title = request.POST.get('title')
            description = request.POST.get('description')
            thumbnail = request.FILES.get('thumbnail')
            
            p = post(
                posttitle=post_title,
                description=description,
                thumbnail=thumbnail,
                communityid=c,
                userid=u,
                isapproved=True # Everything is auto-approved from here on out because they needed permission first
            )
            p.save()
            return redirect('community_detail', community_id=community_id)

def delete_post(request, community_id, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    p = post.objects.get(pk=post_id, communityid=c)
    
    is_admin = _is_community_admin(userid, c)
    
    # Only allow the post creator or an admin to delete it
    if p.userid.userid == int(userid) or is_admin:
        p.delete()
        
    # Redirect logic: if called from pending posts management (group members page), redirect there
    referer = request.META.get('HTTP_REFERER', '')
    if 'members' in referer:
        return redirect('group_members', community_id=community_id)
    return redirect('community_detail', community_id=community_id)

def request_post_permission(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    c = get_object_or_404(community, pk=community_id)
    u = get_object_or_404(user, pk=userid)
    
    # Get the member record
    member_record = communitymember.objects.filter(communityid=c, userid=u, status=1).first()
    if member_record and not member_record.can_post:
        # Mark as pending request
        member_record.post_request_status = 1
        member_record.save()
        
    return redirect('community_detail', community_id=community_id)

def approve_post_permission(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    c = get_object_or_404(community, pk=community_id)
    is_admin = _is_community_admin(userid, c)
    
    if is_admin:
        m = get_object_or_404(communitymember, pk=member_id)
        # Approve the request and grant permission
        m.post_request_status = 2
        m.can_post = True
        m.save()
        
    return redirect('group_members', community_id=community_id)

def reject_post_permission(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    c = get_object_or_404(community, pk=community_id)
    is_admin = _is_community_admin(userid, c)
    
    if is_admin:
        m = get_object_or_404(communitymember, pk=member_id)
        # Reject the request
        m.post_request_status = 0
        m.can_post = False
        m.save()
        
    return redirect('group_members', community_id=community_id)


def add_comment(request, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    if request.method == 'POST':
        p = post.objects.get(pk=post_id)
        u = user.objects.get(pk=userid)
        c_text = request.POST.get('comment')
        
        c = comment.objects.create(
            comment=c_text,
            postid=p,
            userid=u
        )
        c.save()
        return redirect('community_detail', community_id=p.communityid.communityid)
        
    return redirect('group')

def toggle_like(request, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    p = post.objects.get(pk=post_id)
    u = user.objects.get(pk=userid)
    
    existing_like = like.objects.filter(postid=p, userid=u).first()
    
    if existing_like:
        existing_like.delete()
    else:
        l = like.objects.create(postid=p, userid=u)
        l.save()
        
    return redirect('community_detail', community_id=p.communityid.communityid)

# ─── Group Chat ────────────────────────────────────────────────────

def community_chat(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    u = user.objects.get(pk=userid)
    
    is_admin = _is_community_admin(userid, c)
    is_member = communitymember.objects.filter(communityid=c, userid=u, status=1).exists()

    if not (is_admin or is_member):
        return redirect('community_detail', community_id=community_id)

    messages = communityMessage.objects.filter(communityid=c).order_by('senddt')
    
    # Enrich messages with sender info
    valid_messages = []
    for msg in messages:
        sender = user.objects.filter(pk=msg.senderid).first()
        if sender:
            msg.sender = sender
            valid_messages.append(msg)

    data = {
        'community': c,
        'messages': valid_messages,
        'current_user': u,
        'is_admin': is_admin,
    }
    return render(request, 'community_chat.html', data)

def send_community_message(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    u = user.objects.get(pk=userid)

    is_admin = _is_community_admin(userid, c)
    is_member = communitymember.objects.filter(communityid=c, userid=u, status=1).exists()

    if not (is_admin or is_member):
        return redirect('community_detail', community_id=community_id)

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if msg_text:
            cm = communityMessage.objects.create(
                senderid=userid,
                message=msg_text,
                communityid=c
            )
            cm.save()

    return redirect('community_chat', community_id=community_id)

# ─── Chats List Page ────────────────────────────────────────────────
def chats_list(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    u = user.objects.get(pk=userid)
    
    # Fetch communities where user is a member or creator
    joined_comms = communitymember.objects.filter(userid=u, status=1).values_list('communityid', flat=True)
    created_comms = community.objects.filter(userid=u).values_list('communityid', flat=True)
    all_comms_ids = set(joined_comms) | set(created_comms)
    
    chat_list = []
    for cid in all_comms_ids:
        comm = community.objects.filter(pk=cid).first()
        if comm:
            last_msg = communityMessage.objects.filter(communityid=comm).order_by('-senddt').first()
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
    
    data = {
        'joined_community_chats': chat_list,
        'current_user': u
    }
    
    return render(request, 'chats_list.html', data)

# ─── Activity Page ────────────────────────────────────────────────────

def activity(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    u = user.objects.get(pk=userid)
    
    # Get all posts created by the user
    user_posts = post.objects.filter(userid=u)
    
    # 1. Get likes on the user's posts (excluding their own likes)
    likes = like.objects.filter(postid__in=user_posts).exclude(userid=u)
    
    # 2. Get comments on the user's posts (excluding their own comments)
    comments = comment.objects.filter(postid__in=user_posts).exclude(userid=u)
    
    # 3. Get follows where the user was followed
    # In follow model: followerid is the person who clicked follow, userid is the person being followed
    follows = follow.objects.filter(userid=u)
    
    # Create a unified activity list
    activities = []
    
    for l in likes:
        activities.append({
            'type': 'like',
            'user': l.userid,
            'post': l.postid,
            # like model doesn't have a date, we will use the post date as a fallback, or we can just sort by likeid as a proxy for time
            # Since like model lacks addeddt, we'll assign a mock date or None
            'date': getattr(l, 'addeddt', None), 
            'id': l.likeid
        })
        
    for c in comments:
        activities.append({
            'type': 'comment',
            'user': c.userid,
            'post': c.postid,
            'comment': c.comment,
            'date': c.createddt,
            'id': c.commentid
        })
        
    for f in follows:
        # We need to get the actual user object for the follower
        follower = user.objects.filter(pk=f.followerid).first()
        activities.append({
            'type': 'follow',
            'user': follower,
            # No date on follow model natively, use fallback or None
            'date': getattr(f, 'addeddt', None),
            'id': f.followid
        })

    # Sort activities. We will try to sort by date if available, otherwise by ID to estimate chronologically
    # For models lacking dates, we'll push them to the end or sort by ID descending.
    # A safe fallback is sorting descending by ID (largest ID = most recent)
    activities.sort(key=lambda x: (x['date'] is not None, x['date'], x['id']), reverse=True)

    data = {
        'current_user': u,
        'activities': activities
    }
    
    return render(request, 'activity.html', data)

@csrf_exempt
def delete_story(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            story_id = data.get('story_id')
            userid = request.session.get('userid')
            
            print(f"Attempting to delete story {story_id} for user {userid}")
            
            # Using specific field name storyid just in case
            s = get_object_or_404(story, storyid=story_id, userid_id=userid)
            s.delete()
            print(f"Successfully deleted story {story_id}")
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error deleting story: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

 d e f   b l o g _ l i s t ( r e q u e s t ) : 
         b l o g s   =   b l o g . o b j e c t s . a l l ( ) . o r d e r _ b y ( ' - c r e a t e d d t ' ) 
         r e t u r n   r e n d e r ( r e q u e s t ,   ' b l o g _ l i s t . h t m l ' ,   { ' b l o g s ' :   b l o g s } ) 
 
 d e f   b l o g _ d e t a i l ( r e q u e s t ,   b l o g _ i d ) : 
         b l o g _ o b j   =   g e t _ o b j e c t _ o r _ 4 0 4 ( b l o g ,   p k = b l o g _ i d ) 
         r e t u r n   r e n d e r ( r e q u e s t ,   ' b l o g _ d e t a i l . h t m l ' ,   { ' b l o g ' :   b l o g _ o b j } ) 
 
 
 
