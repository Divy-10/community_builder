from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta
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

    # Active Users (Users active in the last 5 minutes)
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    active_users = user.objects.filter(last_seen__gte=five_minutes_ago).exclude(userid=userid).order_by('?')[:4]
    
    # Check if AI Recommendations are disabled
    has_ai_recs = True
    if hasattr(u, 'usersettings') and not u.usersettings.ai_recommendations:
        has_ai_recs = False

    # Suggestions For You (Users not followed yet)
    if has_ai_recs:
        suggested_users = user.objects.exclude(
            userid__in=list(following_ids) + [userid]
        ).order_by('?')[:3]
    else:
        suggested_users = []

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
            'time': l.createddt or timezone.now()
        })
    for f in recent_follows:
        try:
            follower = user.objects.get(pk=f.followerid)
            latest_activities.append({
                'user': follower,
                'text': 'followed you.',
                'time': f.createddt or timezone.now()
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
    following_ids = list(follow.objects.filter(followerid=userid).values_list('userid_id', flat=True))
    
    # Add logged user to the list to see their own posts
    feed_user_ids = following_ids + [userid]
    
    if feed_user_ids:
        # Get posts from followed users and self, but ONLY personal posts (no community)
        posts = post.objects.filter(userid__in=feed_user_ids, communityid__isnull=True).order_by('-createddt')
        user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)
        data = {
            'posts': posts,
            'user_likes': user_likes,
            'current_user': u,
            'has_following': bool(following_ids),
        }
    else:
        # User follows none and has no posts
        posts = post.objects.filter(userid=userid, communityid__isnull=True).order_by('-createddt')
        user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)
        data = {
            'posts': posts,
            'user_likes': user_likes,
            'current_user': u,
            'has_following': False,
        }

    return render(request, 'buzz.html', data)

def add_buzz_post(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('description')
        thumb = request.FILES.get('thumbnail')

        u = user.objects.get(pk=userid)
        
        # Create a post without a community
        p = post.objects.create(
            posttitle=title,
            description=desc,
            thumbnail=thumb,
            userid=u,
            isapproved=True # Auto-approve personal posts
        )
        p.save()
        
    return redirect('buzz')

def edit_buzz_post(request, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    p = post.objects.get(pk=post_id)
    if p.userid.userid != int(userid):
        return redirect('buzz')

    if request.method == "POST":
        p.posttitle = request.POST.get('title')
        p.description = request.POST.get('description')
        p.save()

    referer = request.META.get('HTTP_REFERER', '')
    if 'profile' in referer:
        return redirect('my_profile')
    return redirect('buzz')

def delete_buzz_post(request, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    p = post.objects.get(pk=post_id)
    if p.userid.userid == int(userid):
        p.delete()

    referer = request.META.get('HTTP_REFERER', '')
    if 'profile' in referer:
        return redirect('my_profile')
    return redirect('buzz')

def signup(request):
    import re
    data={
        "states":state.objects.all().order_by('statename')
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
    cities = city.objects.filter(stateid_id=state_id).order_by('cityname').values('cityid', 'cityname')
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
            try:
                # Check Two-Factor Authentication
                if hasattr(u, 'usersettings') and u.usersettings.two_factor_auth:
                    request.session['pending_2fa_userid'] = u.userid
                    request.session['pending_2fa_username'] = u.username
                    
                    import random
                    otp = str(random.randint(100000, 999999))
                    request.session['2fa_otp'] = otp
                    
                    # Print OTP to console for development simulation
                    print(f"\n{'='*40}\n[SECURITY] 2FA OTP for {u.email}: {otp}\n{'='*40}\n")
                    
                    if is_ajax:
                        from django.urls import reverse
                        return JsonResponse({"success": True, "redirect_url": reverse('verify_2fa'), "username": u.username, "is_2fa": True})
                    return redirect('verify_2fa')
            except Exception as e:
                print("2FA Check Error:", e)
                pass

            request.session['userid']=u.userid
            request.session['username']=u.username
            if is_ajax:
                return JsonResponse({"success": True, "redirect_url": "/", "username": u.username}) # Assuming home URL is '/' or we can resolve it
            return redirect('home')

    return render(request,'sign-in.html')

def verify_2fa(request):
    pending_userid = request.session.get('pending_2fa_userid')
    pending_username = request.session.get('pending_2fa_username')
    expected_otp = request.session.get('2fa_otp')

    if not pending_userid or not expected_otp:
        return redirect('signin')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == expected_otp:
            # OTP Verified successfully
            request.session['userid'] = pending_userid
            request.session['username'] = pending_username
            
            # Clean up session
            del request.session['pending_2fa_userid']
            del request.session['pending_2fa_username']
            del request.session['2fa_otp']
            
            return redirect('home')
        else:
            return render(request, 'verify_2fa.html', {'error': 'Invalid 6-digit code. Please check your developer console.'})

    return render(request, 'verify_2fa.html')

def logout_view(request):
    userid = request.session.get('userid')
    if userid:
        try:
            # Set last_seen to None to immediately remove from active users
            user.objects.filter(pk=userid).update(last_seen=None)
        except Exception:
            pass
    request.session.flush()
    return redirect('signin')

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

# ── Google OAuth 2.0 ──────────────────────────────────────────────────────────
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
import os as _os

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid',
]

def _build_google_flow(state=None):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state
    )
    return flow

def google_login(request):
    """Redirect the user to Google's OAuth 2.0 consent screen."""
    _os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local dev
    flow = _build_google_flow()
    auth_url, state = flow.authorization_url(prompt='select_account')
    request.session['google_oauth_state'] = state
    # Save the code_verifier for PKCE (Proof Key for Code Exchange)
    request.session['google_code_verifier'] = flow.code_verifier
    return redirect(auth_url)

def google_callback(request):
    """Handle Google OAuth callback, log in or create the user."""
    _os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local dev

    state = request.session.get('google_oauth_state')
    code_verifier = request.session.get('google_code_verifier')
    
    if not state:
        print("GOOGLE AUTH ERROR: No state in session")
        return redirect('signin')
    
    if request.GET.get('state') != state:
        print(f"GOOGLE AUTH ERROR: State mismatch. Session: {state}, GET: {request.GET.get('state')}")
        return redirect('signin')

    flow = _build_google_flow(state=state)
    # Restore the code_verifier to the flow object
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as e:
        print(f"GOOGLE AUTH ERROR during fetch_token: {str(e)}")
        return redirect('signin')

    credentials = flow.credentials
    try:
        import time
        time.sleep(2) # Small delay to avoid 'Token used too early' if local clock is slightly behind
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except Exception as e:
        print(f"GOOGLE AUTH ERROR during verify_token: {str(e)}")
        return redirect('signin')

    google_user_id = id_info.get('sub')
    google_email   = id_info.get('email', '')
    google_name    = id_info.get('name', 'User')

    # 1. Find by google_id
    existing_user = user.objects.filter(google_id=google_user_id).first()

    # 2. Find by email and link accounts
    if not existing_user and google_email:
        existing_user = user.objects.filter(email=google_email).first()
        if existing_user:
            existing_user.google_id = google_user_id
            existing_user.save()

    # 3. Create new user with defaults
    if not existing_user:
        default_city = city.objects.first()
        if not default_city:
            return redirect('signin')
        existing_user = user.objects.create(
            username=google_name,
            email=google_email,
            password='',
            profile='',
            bio='',
            gender='Other',
            dob='2000-01-01',
            cityid=default_city,
            google_id=google_user_id,
        )
        existing_user.save()

    request.session['userid'] = existing_user.userid
    request.session['username'] = existing_user.username
    return redirect('home')

# ─────────────────────────────────────────────────────────────────────────────

from django.db.models import Count, Q, Case, When, Value, IntegerField

def group(request):
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

    # Initial queryset with member count
    communities = community.objects.annotate(num_members=Count('communitymember'))

    # Prioritize: 1. Created by user, 2. Joined by user, 3. Others
    if userid:
        communities = communities.annotate(
            priority=Case(
                When(userid__userid=userid, then=Value(1)),
                When(communityid__in=joined_ids, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('priority', '-createddt')
    else:
        communities = communities.order_by('-createddt')

    search_name = request.GET.get('search_name', '')
    search_category = request.GET.get('search_category', '')
    search_city = request.GET.get('search_city', '')
    search_members = request.GET.get('search_members', '')

    if search_name:
        communities = communities.filter(communitytitle__istartswith=search_name)
    if search_category:
        communities = communities.filter(categoryid_id=search_category)
    if search_city:
        communities = communities.filter(userid__cityid_id=search_city)
    if search_members and search_members.isdigit():
        communities = communities.filter(num_members__gte=int(search_members))
    
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
            # If community is paid, redirect to payment page
            if c.is_paid and c.price > 0:
                return redirect('community_payment', community_id=community_id)
            else:
                communitymember.objects.create(communityid=c, userid=u, status=0, role='member')
    return redirect('group')

def community_payment(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    c = community.objects.get(pk=community_id)
    u = user.objects.get(pk=userid)
    
    # Already a member? redirect away
    if communitymember.objects.filter(communityid=c, userid=u).exists():
        return redirect('community_detail', community_id=community_id)
    
    # Not a paid community? just join
    if not c.is_paid or c.price <= 0:
        communitymember.objects.create(communityid=c, userid=u, status=0, role='member')
        return redirect('community_detail', community_id=community_id)
    
    import razorpay
    from django.conf import settings
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Amount in paise (₹1 = 100 paise)
    amount_paise = c.price * 100
    
    order_data = {
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': 1,
    }
    
    try:
        razorpay_order = client.order.create(data=order_data)
    except Exception as e:
        # If Razorpay API fails (e.g. bad test keys), show error
        return render(request, 'payment.html', {
            'community': c,
            'current_user': u,
            'error': f'Payment gateway error: {str(e)}. Please check Razorpay API keys in settings.',
        })
    
    # Save the payment record
    payment = Payment.objects.create(
        userid=u,
        communityid=c,
        razorpay_order_id=razorpay_order['id'],
        amount=c.price,
        status='pending'
    )
    
    data = {
        'community': c,
        'current_user': u,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': amount_paise,
        'amount_display': c.price,
        'payment': payment,
    }
    return render(request, 'payment.html', data)

@csrf_exempt
def verify_payment(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=403)
    
    if request.method == 'POST':
        import razorpay
        from django.conf import settings
        
        data = json.loads(request.body)
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            # Payment verified! Update payment record
            payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if payment:
                payment.razorpay_payment_id = razorpay_payment_id
                payment.razorpay_signature = razorpay_signature
                payment.status = 'success'
                payment.save()
            
            # Add user to community
            c = community.objects.get(pk=community_id)
            u = user.objects.get(pk=userid)
            if not communitymember.objects.filter(communityid=c, userid=u).exists():
                communitymember.objects.create(communityid=c, userid=u, status=1, role='member')
            
            return JsonResponse({'success': True})
        
        except razorpay.errors.SignatureVerificationError:
            # Payment failed
            payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if payment:
                payment.status = 'failed'
                payment.save()
            return JsonResponse({'success': False, 'error': 'Payment verification failed'}, status=400)
    
    return JsonResponse({'success': False}, status=400)

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
        is_paid = request.POST.get('is_paid') == 'on'
        
        price = 0
        if is_paid:
            try:
                price = int(request.POST.get('price', 0))
            except ValueError:
                price = 0
        
        userid = request.session.get('userid')
        if not userid:
            return redirect('signin')

        u = user.objects.get(pk=userid)
        cat = category.objects.get(pk=cat_id)

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
    search_state = request.GET.get('search_state', '')
    search_city = request.GET.get('search_city', '')

    if search_name:
        all_users = all_users.filter(username__icontains=search_name)
    if search_state:
        all_users = all_users.filter(cityid__stateid=search_state)
    if search_city:
        all_users = all_users.filter(cityid_id=search_city)
    
    # Get IDs of users current user is following
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    
    # Filtering cities logic for the dropdown (if state is selected, only show state cities)
    cities_list = city.objects.all().order_by('cityname')
    if search_state:
        cities_list = cities_list.filter(stateid_id=search_state)

    # Get communities where current user is admin or member (can invite others to these)
    my_communities = communitymember.objects.filter(userid=current_user, status=1).values_list('communityid', flat=True)
    comms_to_invite = community.objects.filter(pk__in=my_communities)
    
    data = {
        'users': all_users,
        'following_ids': following_ids,
        'comms_to_invite': comms_to_invite,
        'states': state.objects.all().order_by('statename'),
        'cities': cities_list,
        'search_name': search_name,
        'search_state': search_state,
        'search_city': search_city,
    }
    return render(request, 'users_list.html', data)

def toggle_follow(request, target_userid):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    target_user = user.objects.get(pk=target_userid)
    
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    existing_follow = follow.objects.filter(followerid=userid, userid=target_user).first()
    
    if existing_follow:
        # Unfollow
        existing_follow.delete()
        if is_ajax:
            return JsonResponse({'success': True, 'following': False, 'message': f'Unfollowed {target_user.username}.'})
    else:
        # Follow
        f = follow.objects.create(followerid=userid, userid=target_user)
        f.save()
        if is_ajax:
            return JsonResponse({'success': True, 'following': True, 'message': f'Following {target_user.username}!'})
        
    return redirect(request.META.get('HTTP_REFERER', 'users_list'))

def invite_user(request, target_userid):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if request.method == "POST":
        community_id = request.POST.get('community_id')
        if community_id:
            target_user = user.objects.get(pk=target_userid)
            c = community.objects.get(pk=community_id)
            
            # Check if user is already a member
            is_member = communitymember.objects.filter(communityid=c, userid=target_user, status=1).exists()
            
            if is_member:
                msg = f"{target_user.username} is already a member of {c.communitytitle}."
                if is_ajax: return JsonResponse({'success': False, 'message': msg})
                messages.info(request, msg)
            else:
                # Check if invite is already pending
                existing_invite = CommunityInvite.objects.filter(communityid=c, senderid=userid, receiverid=target_user, status=0).exists()
                if not existing_invite:
                    inv = CommunityInvite.objects.create(
                        communityid=c, 
                        senderid=userid, 
                        receiverid=target_user,
                        status=0
                    )
                    inv.save()
                    msg = f"Invitation sent to {target_user.username} for {c.communitytitle}!"
                    if is_ajax: return JsonResponse({'success': True, 'message': msg})
                    messages.success(request, msg)
                else:
                    msg = f"An invitation is already pending for {target_user.username} in {c.communitytitle}."
                    if is_ajax: return JsonResponse({'success': False, 'message': msg})
                    messages.warning(request, msg)
        else:
            msg = "Please select a community to invite this user."
            if is_ajax: return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            
    return redirect(request.META.get('HTTP_REFERER', 'users_list'))

def invitations_list(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    current_user = user.objects.get(pk=userid)
    current_user.last_checked_invites = timezone.now()
    current_user.save()
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
    
    # Fetch actual user objects for the lists
    follower_ids = follow.objects.filter(userid=user_profile).values_list('followerid', flat=True)
    follower_users = user.objects.filter(userid__in=follower_ids)
    followers_count = follower_users.count()
    
    following_user_ids = follow.objects.filter(followerid=target_userid).values_list('userid', flat=True)
    following_users = user.objects.filter(userid__in=following_user_ids)
    following_count = following_users.count()
    
    # Fetch user's posts
    user_posts = post.objects.filter(userid=user_profile).order_by('-createddt')
    
    # Separate Buzz posts and Community posts
    buzz_posts = user_posts.filter(communityid__isnull=True)
    community_posts = user_posts.filter(communityid__isnull=False)
    
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
        'follower_users': follower_users,
        'following_users': following_users,
        'user_posts': user_posts,
        'buzz_posts': buzz_posts,
        'community_posts': community_posts,
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
        "states": state.objects.all().order_by('statename'),
        "cities": city.objects.all().order_by('cityname'),
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


def demote_member(request, community_id, member_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)

    if not _is_community_admin(userid, c):
        return redirect('group_members', community_id=community_id)

    if request.method == 'POST':
        mem = communitymember.objects.filter(pk=member_id, communityid=c).first()
        if mem:
            # SAFETY CHECK: Don't allow demoting the community creator
            if mem.userid.userid == c.userid.userid:
                return redirect('group_members', community_id=community_id)

            mem.role = 'member'
            mem.save()
            # Also remove from communityAdmins table
            communityAdmins.objects.filter(communityid=c, adminid=mem.userid).delete()

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

    # Admins or permitted users can see all posts
    posts = post.objects.filter(communityid=c).order_by('-createddt')

    user_likes = like.objects.filter(userid=u).values_list('postid_id', flat=True)

    # Fetch all approved members for the members modal
    community_members = communitymember.objects.filter(communityid=c, status=1).select_related('userid')
    
    # Fetch specifically admins for the sidebar list
    admins = community_members.filter(role='admin')

    # Purge expired meetups
    delete_expired_meetups()

    # Fetch upcoming meetups for this community
    upcoming_meetups = meetup.objects.filter(communityid=c, meeting_date__gte=timezone.now()).order_by('meeting_date')

    data = {
        'community': c,
        'posts': posts,
        'is_admin': is_admin,
        'is_member': is_member,
        'can_post': can_post,
        'post_request_status': post_request_status,
        'user_likes': user_likes,
        'community_members': community_members,
        'admins': admins,
        'upcoming_meetups': upcoming_meetups,
        'meetup_count': upcoming_meetups.count(),
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
        
    # Redirect logic:
    referer = request.META.get('HTTP_REFERER', '')
    if 'profile' in referer:
        return redirect('my_profile')
    if 'members' in referer:
        return redirect('group_members', community_id=community_id)
    return redirect('community_detail', community_id=community_id)

def edit_post(request, community_id, post_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    p = post.objects.get(pk=post_id, communityid=c)
    
    # Only allow the post creator to edit it
    if p.userid.userid != int(userid):
        return redirect('community_detail', community_id=community_id)

    if request.method == "POST":
        p.posttitle = request.POST.get('title')
        p.description = request.POST.get('description')
        p.save()

    referer = request.META.get('HTTP_REFERER', '')
    if 'profile' in referer:
        return redirect('my_profile')
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
        referer = request.META.get('HTTP_REFERER', 'home')
        return redirect(f"{referer}#post-{post_id}")
        
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
        liked = False
    else:
        l = like.objects.create(postid=p, userid=u)
        l.save()
        liked = True
        
    like_count = p.like_set.count()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'like_count': like_count
        })
        
    referer = request.META.get('HTTP_REFERER', 'home')
    return redirect(f"{referer}#post-{post_id}")

def get_share_targets(request):
    userid = request.session.get('userid')
    if not userid:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=403)
        
    u = user.objects.get(pk=userid)
    
    # People I follow
    following = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    # People following me
    followers = follow.objects.filter(userid=u).values_list('followerid', flat=True)
    
    network_ids = set(list(following) + list(followers))
    network_users = user.objects.filter(pk__in=network_ids).exclude(pk=userid)
    
    targets = []
    for target in network_users:
        targets.append({
            'id': target.userid,
            'username': target.username,
            'profile_url': target.profile.url if target.profile else '/static/assets/images/user/1.jpg'
        })
        
    return JsonResponse({'success': True, 'targets': targets})

@csrf_exempt
def share_post_to_user(request, post_id):
    userid = request.session.get('userid')
    if not userid:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=403)
        
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiverId')
            
            p = post.objects.get(pk=post_id)
            u = user.objects.get(pk=userid)
            
            # Create a chat message
            # Clean post name for message
            msg_content = f"Hey! Check out this post: {p.posttitle}\n\nView post here: http://{request.get_host()}/buzz/#post-{post_id}"
            
            c = chat.objects.create(
                senderid=int(userid),
                receiverid=int(receiver_id),
                message=msg_content,
                status=0, # Unread
                shared_post=p
            )
            c.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False}, status=400)

# ─── Group Chat ────────────────────────────────────────────────────

def community_chat(request, community_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    u = user.objects.get(pk=userid)
    
    # Clear chat notifications for this user
    u.last_checked_chats = timezone.now()
    u.save()
    
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
        msg_image = request.FILES.get('image')
        
        if msg_text or msg_image:
            cm = communityMessage.objects.create(
                senderid=userid,
                message=msg_text,
                image=msg_image,
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
    
    # Target user to chat with
    target_userid = request.GET.get('u')
    
    # Clear notification count for private chat ONLY when viewing that specific user's chat
    if target_userid:
        chat.objects.filter(
            senderid=int(target_userid),
            receiverid=userid,
            status=0
        ).update(status=1)
    else:
        # If just staying on the general chats page (the sidebar), we could optionally
        # update last_checked_chats to clear any global/community badges, 
        # but let's keep it minimal for now to satisfy the "granular" request.
        u.last_checked_chats = timezone.now()
        u.save()
    
    from django.db.models import Q
    from datetime import datetime, timezone as dt_timezone
    
    # Handle sending a new message from the chat interface
    if request.method == 'POST' and target_userid:
        msg_text = request.POST.get('message', '').strip()
        msg_image = request.FILES.get('image')
        if msg_text or msg_image:
            chat.objects.create(
                senderid=int(userid),
                receiverid=int(target_userid),
                message=msg_text,
                image=msg_image,
                status=0 # Unread
            )
        return redirect(f"{request.path}?u={target_userid}")

    # 1. Fetch unique users the current user HAS ALREADY chatted with
    all_user_chats = chat.objects.filter(Q(senderid=userid) | Q(receiverid=userid))
    chatted_user_ids = set()
    for c in all_user_chats:
        if c.senderid != int(userid):
            chatted_user_ids.add(c.senderid)
        if c.receiverid != int(userid):
            chatted_user_ids.add(c.receiverid)

    # 2. Fetch users the current user FOLLOWS or is FOLLOWED BY (their social network)
    # This allows discovering users to start a new chat with.
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    follower_ids = follow.objects.filter(userid=u).values_list('followerid', flat=True)
    
    # Combined set of ALL potential chat users (chatted or in network)
    all_potential_ids = chatted_user_ids | set(following_ids) | set(follower_ids)

    # 3. BUILD CONTACT LIST
    search_query = request.GET.get('search', '').strip()
    chatted_users_list = []
    
    if search_query:
        # Search ALL users in the system (limiting to 20 for performance)
        # Exclude self and prioritize those in social network or existing chats if needed
        search_results = user.objects.filter(
            username__icontains=search_query
        ).exclude(pk=userid)[:20]
        target_ids_to_process = [u.userid for u in search_results]
    else:
        # Normal view: only those with existing chats
        target_ids_to_process = chatted_user_ids

    for uid in target_ids_to_process:
        c_user = user.objects.filter(pk=uid).first()
        if c_user:

            # Fetch last message with this user
            last_msg = chat.objects.filter(
                (Q(senderid=userid) & Q(receiverid=uid)) |
                (Q(senderid=uid) & Q(receiverid=userid))
            ).order_by('-senddt').first()
            
            # Count unread messages from this specific user
            unread_count = chat.objects.filter(senderid=uid, receiverid=userid, status=0).count()
            
            chatted_users_list.append({
                'user': c_user,
                'last_msg': last_msg,
                'unread_count': unread_count,
                'sort_date': last_msg.senddt if last_msg else timezone.make_aware(datetime(1970, 1, 1))
            })
    
    # Sort contacts: Most recent messages first, others at the end
    chatted_users_list.sort(key=lambda x: x['sort_date'], reverse=True)



    messages = []
    target_user = None
    if target_userid:
        target_user = user.objects.filter(pk=target_userid).first()
        if target_user:
            # Fetch with select_related for optimization
            messages = chat.objects.filter(
                (Q(senderid=userid) & Q(receiverid=target_userid)) |
                (Q(senderid=target_userid) & Q(receiverid=userid))
            ).select_related('shared_post').order_by('senddt')

    # Mark as read and detect emoji-only messages
    import re
    from datetime import timedelta
    now_dt = timezone.now()
    yesterday_dt = now_dt - timedelta(days=1)
    
    # Simplified emoji detection regex
    emoji_pattern = re.compile(r'^(\s*)[\U0001f300-\U0001faff\U00002600-\U000027ff\U00002b50-\U00002b55\U0000231a-\U000023f3\U0001f000-\U0001fbff]+(\s*)$')

    for msg in messages:
        if msg.receiverid == userid and msg.status == 0:
            msg.status = 1
            msg.save()
            
        stripped_msg = msg.message.strip()
        if emoji_pattern.match(stripped_msg) and len(stripped_msg) <= 12:
            msg.is_emoji_only = True
        else:
            msg.is_emoji_only = False

    data = {
        'current_user': u,
        'chatted_users_list': chatted_users_list,
        'chat_messages': messages,
        'target_user': target_user,
        'search_query': search_query,
        'now': now_dt,
        'yesterday': yesterday_dt,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'chats_sidebar_items.html', data)

    return render(request, 'chats_list.html', data)
    
def delete_chat(request, chat_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    msg = chat.objects.filter(pk=chat_id, senderid=userid).first()
    target_u = None
    if msg:
        target_u = msg.receiverid
        msg.delete()
        
    if target_u:
        return redirect(f"/chats/?u={target_u}")
    return redirect('chats')

def edit_chat(request, chat_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if msg_text:
            msg = chat.objects.filter(pk=chat_id, senderid=userid).first()
            if msg:
                msg.message = msg_text
                msg.save()
                target_u = msg.receiverid
                return redirect(f"/chats/?u={target_u}")
                
    return redirect('chats')


# ─── Activity Page ────────────────────────────────────────────────────

def activity(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    u = user.objects.get(pk=userid)
    u.last_checked_activity = timezone.now()
    u.save()
    
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
            'date': getattr(l, 'createddt', None), 
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
            'date': getattr(f, 'createddt', None),
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

def blog_list(request):
    blogs = blog.objects.all().order_by('-createddt')
    return render(request, 'blog_list.html', {'blogs': blogs})

def blog_detail(request, blog_id):
    blog_obj = get_object_or_404(blog, pk=blog_id)
    return render(request, 'blog_detail.html', {'blog': blog_obj})

def add_blog(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')

        u = user.objects.get(pk=userid)
        c = category.objects.get(pk=category_id)

        b = blog.objects.create(
            title=title,
            description=description,
            image=image,
            author=u,
            categoryid=c
        )
        b.save()
        return redirect('blog_list')

    categories = category.objects.all()
    return render(request, 'add_blog.html', {'categories': categories})

def edit_blog(request, blog_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    blog_obj = get_object_or_404(blog, pk=blog_id)
    
    # Ensure only author can edit
    if blog_obj.author.userid != int(userid):
        return redirect('blog_detail', blog_id=blog_id)
        
    if request.method == 'POST':
        blog_obj.title = request.POST.get('title')
        blog_obj.description = request.POST.get('description')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')
        
        if category_id:
            blog_obj.categoryid = category.objects.get(pk=category_id)
        if image:
            blog_obj.image = image
            
        blog_obj.save()
        return redirect('blog_detail', blog_id=blog_id)
        
    categories = category.objects.all()
    return render(request, 'edit_blog.html', {'blog': blog_obj, 'categories': categories})

def delete_blog(request, blog_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    blog_obj = get_object_or_404(blog, pk=blog_id)
    
    # Ensure only author can delete
    if blog_obj.author.userid == int(userid):
        blog_obj.delete()
        
    return redirect('blog_list')


def contact_us(request):
    userid = request.session.get('userid')
    u = None
    if userid:
        u = user.objects.get(pk=userid)
    
    return render(request, 'contact_us.html', {'current_user': u})

def settings_view(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    u = user.objects.get(pk=userid)
    settings, created = UserSettings.objects.get_or_create(user=u)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle AJAX Requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                action = data.get('action')
                
                if action == 'update_appearance':
                    settings.dark_mode = data.get('dark_mode', settings.dark_mode)
                    settings.theme_color = data.get('theme_color', settings.theme_color)
                    settings.font_size = data.get('font_size', settings.font_size)
                    settings.save()
                    return JsonResponse({'success': True, 'msg': 'Appearance settings saved.'})
                
                elif action == 'update_notifications':
                    settings.email_notifications = data.get('email_notifications', settings.email_notifications)
                    settings.push_notifications = data.get('push_notifications', settings.push_notifications)
                    settings.meetup_reminders = data.get('meetup_reminders', settings.meetup_reminders)
                    settings.community_updates = data.get('community_updates', settings.community_updates)
                    settings.notification_frequency = data.get('notification_frequency', settings.notification_frequency)
                    settings.save()
                    return JsonResponse({'success': True, 'msg': 'Notification preferences saved.'})
                
                elif action == 'update_privacy':
                    settings.profile_visibility = data.get('profile_visibility', settings.profile_visibility)
                    settings.data_usage_consent = data.get('data_usage_consent', settings.data_usage_consent)
                    settings.save()
                    return JsonResponse({'success': True, 'msg': 'Privacy settings updated.'})
                
                elif action == 'update_advanced':
                    settings.ai_recommendations = data.get('ai_recommendations', settings.ai_recommendations)
                    settings.two_factor_auth = data.get('two_factor_auth', settings.two_factor_auth)
                    settings.save()
                    return JsonResponse({'success': True, 'msg': 'Advanced settings saved.'})
                    
                elif action == 'update_regional':
                    settings.language = data.get('language', settings.language)
                    settings.currency_format = data.get('currency_format', settings.currency_format)
                    settings.date_time_format = data.get('date_time_format', settings.date_time_format)
                    settings.save()
                    return JsonResponse({'success': True, 'msg': 'Regional settings updated.'})

            except Exception as e:
                return JsonResponse({'success': False, 'msg': str(e)})

        # Non-AJAX forms (like Profile Update or Password Change)
        if action == 'update_profile':
            u.username = request.POST.get('name', u.username)
            u.email = request.POST.get('email', u.email)
            
            phone = request.POST.get('phone', u.phone)
            if phone and len(phone) != 10:
                messages.error(request, "Phone number must be exactly 10 digits.")
                return redirect('settings')
            u.phone = phone
            
            u.bio = request.POST.get('bio', u.bio)
            u.gender = request.POST.get('gender', u.gender)
            u.dob = request.POST.get('dob', u.dob)
            
            city_id = request.POST.get('city')
            if city_id:
                try:
                    u.cityid = city.objects.get(pk=city_id)
                except city.DoesNotExist:
                    pass
            
            if 'profile_pic' in request.FILES:
                u.profile = request.FILES['profile_pic']
                
            u.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('settings')
            
        elif action == 'change_password':
            current_pass = request.POST.get('current_password')
            new_pass = request.POST.get('new_password')
            
            if u.password == current_pass:
                u.password = new_pass
                u.save()
                messages.success(request, "Password changed successfully.")
            else:
                messages.error(request, "Current password is incorrect.")
            return redirect('settings')

    states_list = state.objects.all().order_by('statename')
    user_state_id = u.cityid.stateid.stateid if u.cityid else None
    
    return render(request, 'settings.html', {
        'current_user': u, 
        'settings': settings,
        'states': states_list,
        'user_state_id': user_state_id
    })

# ─── Meetups ───────────────────────────────────────────────────────

def meetup_list(request):
    """Public page — all users (even non-logged-in) can see upcoming meetups."""
    from django.utils import timezone as tz
    
    delete_expired_meetups()

    upcoming = meetup.objects.filter(meeting_date__gte=tz.now()).order_by('meeting_date')

    # Filters
    filter_type = request.GET.get('type', '')
    filter_category = request.GET.get('category', '')
    search_q = request.GET.get('q', '')

    if filter_type in ('online', 'offline'):
        upcoming = upcoming.filter(meetup_type=filter_type)
    if filter_category:
        upcoming = upcoming.filter(communityid__categoryid_id=filter_category)
    if search_q:
        upcoming = upcoming.filter(title__icontains=search_q)

    # For each meetup, annotate member count for the community
    userid = request.session.get('userid')
    joined_ids = set()
    pending_ids = set()
    if userid:
        joined_ids = set(
            communitymember.objects.filter(userid__userid=userid, status=1).values_list('communityid_id', flat=True)
        )
        pending_ids = set(
            communitymember.objects.filter(userid__userid=userid, status=0).values_list('communityid_id', flat=True)
        )

    data = {
        'meetups': upcoming,
        'categories': category.objects.all(),
        'filter_type': filter_type,
        'filter_category': filter_category,
        'search_q': search_q,
        'joined_ids': joined_ids,
        'pending_ids': pending_ids,
    }
    return render(request, 'meetup_list.html', data)


def create_meetup(request, community_id):
    """Only community admins can create meetups."""
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')

    c = community.objects.get(pk=community_id)
    if not _is_community_admin(userid, c):
        return redirect('community_detail', community_id=community_id)

    u = user.objects.get(pk=userid)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        meetup_type = request.POST.get('meetup_type', 'offline')
        meeting_link = request.POST.get('meeting_link', '').strip() or None
        location = request.POST.get('location', '').strip() or None
        meetup_date = request.POST.get('meetup_date')

        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        thumbnail = request.FILES.get('thumbnail')

        # Server-side validation
        from django.utils.dateparse import parse_datetime
        meeting_date = parse_datetime(f"{meetup_date}T{start_time}")
        meeting_end_date = parse_datetime(f"{meetup_date}T{end_time}")
        
        if meeting_date:
            if timezone.is_naive(meeting_date):
                meeting_date = timezone.make_aware(meeting_date)
            
            if meeting_date < timezone.now():
                data = {
                    'community': c,
                    'error_msg': 'Meeting date and time cannot be in the past.',
                    'prev_data': request.POST
                }
                return render(request, 'create_meetup.html', data)

        if meeting_end_date:
            if timezone.is_naive(meeting_end_date):
                meeting_end_date = timezone.make_aware(meeting_end_date)
            
            if meeting_end_date <= meeting_date:
                data = {
                    'community': c,
                    'error_msg': 'Meeting end time must be after start time.',
                    'prev_data': request.POST
                }
                return render(request, 'create_meetup.html', data)


        m = meetup.objects.create(
            title=title,
            description=description,
            meetup_type=meetup_type,
            meeting_link=meeting_link,
            location=location,
            meeting_date=meeting_date,
            meeting_end_date=meeting_end_date,
            thumbnail=thumbnail,
            communityid=c,
            created_by=u,
        )

        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(meeting_date)
            formatted_date = dt.strftime("%B %d, %Y at %I:%M %p") if dt else meeting_date
        except:
            formatted_date = meeting_date
            
        type_str = dict(MEETUP_TYPES).get(meetup_type, meetup_type)
        msg_text = f"📢 New Meetup Scheduled: {title}\nDate: {formatted_date}\nType: {type_str}"
        communityMessage.objects.create(
            senderid=u.userid,
            message=msg_text,
            communityid=c
        )

        return redirect('meetup_list')

    data = {
        'community': c,
    }
    return render(request, 'create_meetup.html', data)


def meetup_detail(request, meetup_id):
    """Public detail page for a single meetup — attracts users to join the community."""
    delete_expired_meetups()
    m = get_object_or_404(meetup, pk=meetup_id)


    userid = request.session.get('userid')
    is_member = False
    is_admin = False
    is_pending = False
    current_usr = None
    if userid:
        current_usr = user.objects.filter(pk=userid).first()
        is_member = communitymember.objects.filter(
            communityid=m.communityid, userid__userid=userid, status=1
        ).exists()
        is_pending = communitymember.objects.filter(
            communityid=m.communityid, userid__userid=userid, status=0
        ).exists()
        is_admin = _is_community_admin(userid, m.communityid)

    member_count = communitymember.objects.filter(communityid=m.communityid, status=1).count()

    # RSVP tracking (newly added)
    rsvp_count = meetup_member.objects.filter(meetupid=m).count()
    has_rsvp = False
    if userid:
        has_rsvp = meetup_member.objects.filter(meetupid=m, userid__userid=userid).exists()

    data = {
        'meetup': m,
        'is_member': is_member,
        'is_admin': is_admin,
        'is_pending': is_pending,
        'member_count': member_count,
        'current_user': current_usr,
        'rsvp_count': rsvp_count,
        'has_rsvp': has_rsvp,
        'is_full': m.member_limit > 0 and rsvp_count >= m.member_limit
    }
    return render(request, 'meetup_detail.html', data)

def join_meetup_rsvp(request, meetup_id):
    """RSVP to a meetup, checking the member limit."""
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    m = get_object_or_404(meetup, pk=meetup_id)
    u = get_object_or_404(user, pk=userid)

    # Check if already joined
    if meetup_member.objects.filter(meetupid=m, userid=u).exists():
        return redirect('meetup_detail', meetup_id=meetup_id)

    # Check member limit
    rsvp_count = meetup_member.objects.filter(meetupid=m).count()
    if m.member_limit > 0 and rsvp_count >= m.member_limit:
        return render(request, 'meetup_detail.html', {
            'meetup': m,
            'error_msg': "This meetup has reached its member limit.",
            'rsvp_count': rsvp_count,
            'is_full': True,
            'is_member': communitymember.objects.filter(communityid=m.communityid, userid=u, status=1).exists()
        })

    # Join
    meetup_member.objects.create(meetupid=m, userid=u)
    return redirect('meetup_detail', meetup_id=meetup_id)

def join_meeting(request, meetup_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    m = get_object_or_404(meetup, pk=meetup_id)
    u = get_object_or_404(user, pk=userid)
    
    # Users can join instantly without any time restrictions or waiting room.
        
    data = {
        'meetup': m,
        'current_user': u,
        'room_name': f"UniVo_Meet_{m.meetupid}_{m.communityid.communityid}", # Unique room name
    }
    return render(request, 'meeting_room.html', data)

def delete_meetup(request, meetup_id):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    m = get_object_or_404(meetup, pk=meetup_id)
    
    # Only allow creator or community admins to delete
    is_admin = _is_community_admin(userid, m.communityid)
    if is_admin or m.created_by.userid == userid:
        m.delete()
        return redirect('meetup_list')
    else:
        return redirect('meetup_detail', meetup_id=meetup_id)

def delete_expired_meetups():
    from django.utils import timezone
    now = timezone.now()
    # Delete if end_date has passed
    meetup.objects.filter(meeting_end_date__lt=now).delete()
    # Also delete if start date is more than 24 hours ago (legacy data cleanup)
    meetup.objects.filter(meeting_date__lt=now - timedelta(days=1)).delete()

def calendar_view(request):
    """View to display the calendar with all meetups."""
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    delete_expired_meetups()

    # Show only upcoming meetups on the calendar as requested
    meetups = meetup.objects.filter(meeting_date__gte=timezone.now())
    events = []
    
    for m in meetups:
        events.append({
            'title': m.title,
            'start': m.meeting_date.isoformat(),
            'end': m.meeting_end_date.isoformat() if m.meeting_end_date else None,
            'allDay': False,
            'extendedProps': {
                'meetupid': m.meetupid,
                'meetup_type': m.meetup_type,
                'description': m.description,
                'location': m.location or m.meeting_link or 'N/A',
                'date_str': m.meeting_date.strftime("%A, %B %d, %Y"),
                'time_str': m.meeting_date.strftime("%I:%M %p"),
            }
        })
    
    data = {
        'meetups_json': json.dumps(events)
    }
    
    return render(request, 'calendar.html', data)
def unified_add_post(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    u = user.objects.get(pk=userid)
    
    # Fetch communities where user can post
    # Can post if: admin OR (member AND can_post=True)
    my_communities = communitymember.objects.filter(
        userid=u, 
        status=1
    ).filter(
        Q(role='admin') | Q(can_post=True)
    ).select_related('communityid')
    
    context = {
        'communities': [cm.communityid for cm in my_communities],
        'current_user': u
    }
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        thumbnail = request.FILES.get('thumbnail')
        post_type = request.POST.get('post_type') # 'buzz' or 'community'
        community_id = request.POST.get('community_id')
        
        c = None
        if post_type == 'community' and community_id:
            c = community.objects.get(pk=community_id)
            
        p = post.objects.create(
            posttitle=title,
            description=description,
            thumbnail=thumbnail,
            userid=u,
            communityid=c,
            isapproved=True # Auto-approve for unified page for simplicity
        )
        p.save()
        
        if c:
            return redirect('community_detail', community_id=c.pk)
        else:
            return redirect('buzz')
            
    return render(request, 'add_post.html', context)
