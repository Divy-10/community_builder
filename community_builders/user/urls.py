from django.urls import path
from . import views
urlpatterns = [
    path('home',views.home,name="home"),
    path('signup/',views.signup,name="signup"),
    path('signin/',views.signin,name="signin"),
    path('group/',views.group,name="group"),
    path('create-group/',views.create_group,name="create_group"),
    path('users/', views.users_list, name='users_list'),
    path('follow/<int:target_userid>/', views.toggle_follow, name='toggle_follow'),
    path('invite_user/<int:target_userid>/', views.invite_user, name='invite_user'),
    path('invitations/', views.invitations_list, name='invitations_list'),
    path('invitation/respond/<int:inviteid>/<str:action>/', views.respond_invite, name='respond_invite'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/delete/', views.delete_profile, name='delete_profile'),
    path('profile/<int:target_userid>/', views.user_profile, name='user_profile'),
    path('profile/', views.user_profile, name='my_profile'),
]