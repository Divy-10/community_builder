from django.shortcuts import render,redirect
from django.http import HttpResponse
from .models import *

# Create your views here.
def home(request):
    return render(request,'home.html')

def signup(request):
    data={
        "cities":city.objects.all()
    }
    if request.POST.get('sign-up-btn'):
        username=request.POST.get('name')
        email=request.POST.get('email')
        password=request.POST.get('password')
        profile=request.FILES.get('fup')
        bio=request.POST.get('bio')
        gender=request.POST.get('gender')
        dob=request.POST.get('dob')
        cityid=request.POST.get('city')
        u=user.objects.create(userid=None,username=username,email=email,password=password,profile=profile,bio=bio,gender=gender,dob=dob,cityid=city.objects.get(pk=cityid))
        u.save()
        return redirect('signin')
    return render(request,'sign-up.html',data)


def signin(request):
    if request.POST.get('sign-in-btn'):
        email=request.POST.get('email')
        password=request.POST.get('password')
        u=user.objects.filter(email=email,password=password).first()
        if u==None:
            data={"simsg":"invalid email or password"}
            return render(request,'sign-in.html',data)
        else:
            request.session['userid']=u.userid
            request.session['username']=u.username
            return redirect('home')

    return render(request,'sign-in.html')

def group(request):
    communities = community.objects.all().order_by('-createddt')
    data = {
        'communities': communities
    }
    return render(request, 'group.html', data)

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
        cat_id = request.POST.get('category')
        
        userid = request.session.get('userid')
        if not userid:
            return redirect('signin')

        u = user.objects.get(pk=userid)
        cat = category.objects.get(pk=cat_id)

        c = community.objects.create(
            communitytitle=title, 
            discription=desc, 
            thumbnail=thumb, 
            categoryid=cat, 
            userid=u
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
            status=1
        )
        cm.save()
        
        return redirect('group')
        
    return render(request, 'create-group.html', data)


def users_list(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
    
    current_user = user.objects.get(pk=userid)
    all_users = user.objects.exclude(pk=userid)
    
    # Get IDs of users current user is following
    following_ids = follow.objects.filter(followerid=userid).values_list('userid_id', flat=True)
    
    # Get communities where current user is admin or member (can invite others to these)
    my_communities = communitymember.objects.filter(userid=current_user, status=1).values_list('communityid', flat=True)
    comms_to_invite = community.objects.filter(pk__in=my_communities)
    
    data = {
        'users': all_users,
        'following_ids': following_ids,
        'comms_to_invite': comms_to_invite
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
        
    # Get user posts
    user_posts = post.objects.filter(userid=user_profile).order_by('-createddt')
    
    # Get user communities (where they are a member)
    user_communities = community.objects.filter(communitymember__userid=user_profile, communitymember__status=1).distinct()

    data = {
        'user_profile': user_profile,
        'is_following': is_following,
        'is_own_profile': is_own_profile,
        'user_posts': user_posts,
        'user_communities': user_communities
    }
    return render(request, 'user_profile.html', data)

def edit_profile(request):
    userid = request.session.get('userid')
    if not userid:
        return redirect('signin')
        
    u = user.objects.get(pk=userid)
    data = {
        "cities": city.objects.all(),
        "user_profile": u
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
