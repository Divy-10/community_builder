from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users_manage, name='users'),
    path('communities/', views.communities_manage, name='communities'),
    path('posts/', views.posts_manage, name='posts'),
    path('meetups/', views.meetups_manage, name='meetups'),
    path('contact-messages/', views.contact_messages_manage, name='contact_messages'),

]
