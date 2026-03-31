from django.contrib import admin
from django import forms
from datetime import date
from .models import *

# Register your models here.
admin.site.register(city)
admin.site.register(state)
admin.site.register(category)

GENDER_CHOICES = [('male', 'Male'), ('female', 'Female')]

class UserForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.RadioSelect)
    state_select = forms.ModelChoiceField(
        queryset=state.objects.all(),
        required=False,
        label='State',
        widget=forms.Select(attrs={'id': 'id_state_select'}),
    )

    class Meta:
        model = user
        fields = '__all__'
        widgets = {
            'dob': forms.DateInput(attrs={
                'type': 'date',
                'max': date.today().isoformat(),
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-select the state if editing an existing user
        if self.instance and self.instance.pk and self.instance.cityid:
            self.fields['state_select'].initial = self.instance.cityid.stateid

    class Media:
        js = ('admin/js/admin_state_city.js',)

@admin.register(user)
class UserAdmin(admin.ModelAdmin):
    form = UserForm
    list_display = ('userid', 'username', 'email', 'gender', 'registrationdt')
    search_fields = ('username', 'email')

    class Media:
        js = ('admin/js/admin_state_city.js',)

@admin.register(community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('communityid', 'communitytitle', 'categoryid', 'userid', 'createddt')
    search_fields = ('communitytitle',)
    list_filter = ('categoryid',)

@admin.register(communitymember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ('communitymemberid', 'communityid', 'userid', 'role', 'status', 'addeddt')
    search_fields = ('userid__username', 'userid__email')
    list_filter = ('role', 'status')

@admin.register(communityAdmins)
class CommunityAdminsAdmin(admin.ModelAdmin):
    list_display = ('communityAdminsid', 'communityid', 'adminid', 'addedbyuserid', 'addeddt')
    search_fields = ('adminid__username',)

@admin.register(post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('postid', 'posttitle', 'communityid', 'userid', 'isapproved', 'createddt')
    list_filter = ('isapproved',)
    search_fields = ('posttitle',)

@admin.register(comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('commentid', 'postid', 'userid', 'createddt')

@admin.register(like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('likeid', 'postid', 'userid')

@admin.register(blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('blogid', 'title', 'author', 'createddt')
    search_fields = ('title', 'description')
    list_filter = ('categoryid',)

@admin.register(meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ('meetupid', 'title', 'meetup_type', 'communityid', 'meeting_date', 'created_by', 'createddt')
    search_fields = ('title', 'description')
    list_filter = ('meetup_type', 'communityid')
