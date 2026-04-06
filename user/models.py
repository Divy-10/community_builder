from django.db import models
from django.core.exceptions import ValidationError
from datetime import date

def no_future_date(value):
    if value > date.today():
        raise ValidationError('Date of birth cannot be in the future.')

# Create your models here.

#state
class state(models.Model):
    stateid=models.AutoField(primary_key=True)
    statename=models.CharField(max_length=50)

    def __str__(self):
        return "%d-%s"%(self.stateid,self.statename)
    
#city
class city(models.Model):
    cityid=models.AutoField(primary_key=True)
    cityname=models.CharField(max_length=50)
    stateid=models.ForeignKey(state,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%s"%(self.cityid,self.cityname)

#category
class category(models.Model):
    categoryid=models.AutoField(primary_key=True)
    categoryname=models.CharField(max_length=50)

    def __str__(self):
        return "%d-%s"%(self.categoryid,self.categoryname)
    
#subcategory
class subcategory(models.Model):
    subcategoryid=models.AutoField(primary_key=True)
    subcategoryname=models.CharField(max_length=50)
    categoryid=models.ForeignKey(category,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%s"%(self.subcategoryid,self.subcategoryname)

    class Meta:
        verbose_name = "Sub Category"
        verbose_name_plural = "Sub Categories"

#user
class user(models.Model):
    userid=models.AutoField(primary_key=True)
    username=models.CharField(max_length=50)
    email=models.CharField(max_length=50)
    password=models.CharField(max_length=50) 
    profile=models.ImageField(upload_to="assets/images/user/")
    bio=models.TextField(max_length=1000)
    gender=models.CharField(max_length=10)
    dob=models.DateField(validators=[no_future_date])
    cityid=models.ForeignKey(city,on_delete=models.CASCADE)
    registrationdt=models.DateTimeField(auto_now=True)
    last_checked_chats=models.DateTimeField(null=True, blank=True)
    last_checked_activity=models.DateTimeField(null=True, blank=True)
    last_checked_invites=models.DateTimeField(null=True, blank=True)
    last_seen=models.DateTimeField(null=True, blank=True)
    google_id=models.CharField(max_length=255, null=True, blank=True)  # Google OAuth user ID
    phone=models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return "%d-%s"%(self.userid,self.username)
    
class UserSettings(models.Model):
    user = models.OneToOneField(user, on_delete=models.CASCADE, related_name='settings')
    # Appearance
    dark_mode = models.BooleanField(default=False)
    theme_color = models.CharField(max_length=20, default='blue')
    font_size = models.CharField(max_length=10, default='medium')
    # Notifications
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    meetup_reminders = models.BooleanField(default=True)
    community_updates = models.BooleanField(default=True)
    notification_frequency = models.CharField(max_length=20, default='instant')
    # Language & Region
    language = models.CharField(max_length=20, default='English')
    currency_format = models.CharField(max_length=10, default='USD')
    date_time_format = models.CharField(max_length=20, default='MM/DD/YYYY')
    # Privacy
    profile_visibility = models.CharField(max_length=10, default='public')
    data_usage_consent = models.BooleanField(default=True)
    # Advanced
    ai_recommendations = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Settings for {self.user.username}"
    
#community
class community(models.Model):
    communityid=models.AutoField(primary_key=True)
    communitytitle=models.CharField(max_length=50)
    thumbnail=models.ImageField(upload_to="images/")
    background_image=models.ImageField(upload_to="images/backgrounds/", null=True, blank=True)
    discription=models.TextField(max_length=1000)
    createddt=models.DateTimeField(auto_now=True)
    categoryid=models.ForeignKey(category,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    is_paid=models.BooleanField(default=False)
    price=models.IntegerField(default=0)
    
    def __str__(self):
        return "%d-%s"%(self.communityid,self.communitytitle)
    
#communitymember
ROLE_CHOICES = [('admin', 'Admin'), ('member', 'Member')]

class communitymember(models.Model):
    communitymemberid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    status=models.IntegerField()
    role=models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    can_post=models.BooleanField(default=False)
    # 0 = not requested, 1 = pending request, 2 = approved
    post_request_status=models.IntegerField(default=0)
    addeddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d"%(self.communityid.pk,self.userid.pk)

    class Meta:
        verbose_name = "Community Member"
        verbose_name_plural = "Community Members"
    
#post
class post(models.Model):
    postid=models.AutoField(primary_key=True)
    posttitle=models.CharField(max_length=50)
    thumbnail=models.ImageField(upload_to="images/")
    description=models.TextField(max_length=1000)
    createddt=models.DateTimeField(auto_now=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE, null=True, blank=True)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    isapproved=models.BooleanField(default=False)

    def __str__(self):
        return "%d-%s"%(self.postid,self.posttitle)

    @property
    def is_video(self):
        if self.thumbnail:
            import os
            ext = os.path.splitext(self.thumbnail.name)[1].lower()
            return ext in ['.mp4', '.mov', '.avi', '.wmv', '.webm', '.mkv']
        return False
    
#comment
class comment(models.Model):
    commentid=models.AutoField(primary_key=True)
    comment=models.TextField(max_length=1000)
    createddt=models.DateTimeField(auto_now=True)
    postid=models.ForeignKey(post,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%s"%(self.commentid,self.comment)
    
#like
class like(models.Model):
    likeid=models.AutoField(primary_key=True)
    postid=models.ForeignKey(post,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    createddt=models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return "%d-%d"%(self.postid.pk,self.userid.pk)
    
#follow
class follow(models.Model):
    followid=models.AutoField(primary_key=True)
    followerid=models.IntegerField()
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    createddt=models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return "%d-%d"%(self.followerid,self.userid.pk)
    
#communityMessage
class communityMessage(models.Model):
    communityMessageid=models.AutoField(primary_key=True)
    senderid=models.IntegerField()
    message=models.TextField(max_length=1000)
    image=models.ImageField(upload_to="chat_images/", null=True, blank=True)
    senddt=models.DateTimeField(auto_now=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    
    def __str__(self):
        return "%d-%s"%(self.communityMessageid,self.message)
    
#CommunityAdmins
class communityAdmins(models.Model):
    communityAdminsid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    adminid=models.ForeignKey(user,on_delete=models.CASCADE)
    addedbyuserid=models.IntegerField()
    addeddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d"%(self.communityid.pk,self.adminid.pk)

    class Meta:
        verbose_name = "Community Admin"
        verbose_name_plural = "Community Admins"
    
#chat
class chat(models.Model):
    chatid=models.AutoField(primary_key=True)
    senderid=models.IntegerField(max_length=50)
    receiverid=models.IntegerField()#userid
    message=models.TextField(max_length=1000)
    image=models.ImageField(upload_to="chat_images/", null=True, blank=True)
    senddt=models.DateTimeField(auto_now=True)
    status=models.IntegerField(max_length=50)
    shared_post=models.ForeignKey(post, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return "%d-%d"%(self.senderid,self.receiverid)
    
#images
class images(models.Model):
    imageid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    addeddt=models.DateTimeField(auto_now=True)
    image=models.ImageField(upload_to="images/")

    def __str__(self):
        return "%d-%d"%(self.imageid,self.userid.pk)

#CommunityInvite
class CommunityInvite(models.Model):
    inviteid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    senderid=models.IntegerField() # userid of sender
    receiverid=models.ForeignKey(user,on_delete=models.CASCADE)
    status=models.IntegerField(default=0) # 0=Pending, 1=Accepted, 2=Declined
    createddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d To %d"%(self.inviteid,self.senderid,self.receiverid.pk)
#Story
class story(models.Model):
    storyid = models.AutoField(primary_key=True)
    userid = models.ForeignKey(user, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="stories/")
    createddt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%d-%s" % (self.storyid, self.userid.username)

# StorySeen
class StorySeen(models.Model):
    seenid = models.AutoField(primary_key=True)
    storyid = models.ForeignKey(story, on_delete=models.CASCADE)
    userid = models.ForeignKey(user, on_delete=models.CASCADE)
    seendt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%d - %s seen by %s" % (self.seenid, self.storyid.storyid, self.userid.username)

# Blog
class blog(models.Model):
    blogid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=10000)
    image = models.ImageField(upload_to="blogs/")
    author = models.ForeignKey(user, on_delete=models.CASCADE)
    categoryid = models.ForeignKey(category, on_delete=models.SET_NULL, null=True, blank=True)
    createddt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%d-%s" % (self.blogid, self.title)

# Meetup
MEETUP_TYPES = [
    ('internal', 'Internal Video Meeting'),
    ('external', 'External Link (Google Meet, Zoom, etc.)'),
    ('offline', 'Offline (In-Person)'),
]

class meetup(models.Model):
    meetupid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000)
    meetup_type = models.CharField(max_length=10, choices=MEETUP_TYPES, default='offline')
    meeting_link = models.URLField(max_length=500, null=True, blank=True)  # For online meetings
    location = models.CharField(max_length=200, null=True, blank=True)  # For offline meetings
    meeting_date = models.DateTimeField()
    meeting_end_date = models.DateTimeField(null=True, blank=True)

    thumbnail = models.ImageField(upload_to="meetups/", null=True, blank=True)
    communityid = models.ForeignKey(community, on_delete=models.CASCADE)
    created_by = models.ForeignKey(user, on_delete=models.CASCADE)
    member_limit = models.IntegerField(default=0)  # 0 or Null for unlimited
    createddt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%d-%s" % (self.meetupid, self.title)

class meetup_member(models.Model):
    meetup_member_id = models.AutoField(primary_key=True)
    meetupid = models.ForeignKey(meetup, on_delete=models.CASCADE)
    userid = models.ForeignKey(user, on_delete=models.CASCADE)
    joineddt = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('meetupid', 'userid')
        verbose_name = "Meetup Member"
        verbose_name_plural = "Meetup Members"

    def __str__(self):
        return "%d-%d" % (self.meetupid.pk, self.userid.pk)

# Payment
class Payment(models.Model):
    paymentid = models.AutoField(primary_key=True)
    userid = models.ForeignKey(user, on_delete=models.CASCADE)
    communityid = models.ForeignKey(community, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=200)
    razorpay_payment_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=500, null=True, blank=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=20, default='pending')  # pending, success, failed
    createddt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%d - %s - %s" % (self.paymentid, self.userid.username, self.status)

# FollowRequest
class FollowRequest(models.Model):
    requestid = models.AutoField(primary_key=True)
    sender = models.ForeignKey(user, on_delete=models.CASCADE, related_name='sent_follow_requests')
    receiver = models.ForeignKey(user, on_delete=models.CASCADE, related_name='received_follow_requests')
    status = models.IntegerField(default=0) # 0=Pending, 1=Accepted, 2=Declined
    createddt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request from {self.sender.username} to {self.receiver.username}"
