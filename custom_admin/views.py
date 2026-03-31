from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from user.models import user, community, post, communitymember, like, comment, follow

@staff_member_required
def dashboard(request):
    total_users = user.objects.count()
    total_communities = community.objects.count()
    total_posts = post.objects.count()
    recent_users = user.objects.order_by('-registrationdt')[:5]
    recent_posts = post.objects.order_by('-createddt')[:5]
    recent_communities = community.objects.order_by('-createddt')[:5]

    context = {
        'total_users': total_users,
        'total_communities': total_communities,
        'total_posts': total_posts,
        'recent_users': recent_users,
        'recent_posts': recent_posts,
        'recent_communities': recent_communities,
    }
    return render(request, 'custom_admin/dashboard.html', context)

@staff_member_required
def users_manage(request):
    users = user.objects.all().order_by('-registrationdt')
    context = {
        'users': users
    }
    return render(request, 'custom_admin/users.html', context)

@staff_member_required
def communities_manage(request):
    communities = community.objects.all().order_by('-createddt')
    context = {
        'communities': communities
    }
    return render(request, 'custom_admin/communities.html', context)

@staff_member_required
def posts_manage(request):
    posts = post.objects.all().order_by('-createddt')
    context = {
        'posts': posts
    }
    return render(request, 'custom_admin/posts.html', context)
