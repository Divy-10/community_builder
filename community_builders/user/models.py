from django.db import models

# Create your models here.

#state
class state(models.Model):
    stateid=models.AutoField(primary_key=True)
    statename=models.TextField(max_length=50)

    def __str__(self):
        return "%d-%s"%(self.stateid,self.statename)
    
#city
class city(models.Model):
    cityid=models.AutoField(primary_key=True)
    cityname=models.TextField(max_length=50)
    stateid=models.ForeignKey(state,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%s"%(self.cityid,self.cityname)

#category
class category(models.Model):
    categoryid=models.AutoField(primary_key=True)
    categoryname=models.TextField(max_length=50)

    def __str__(self):
        return "%d-%s"%(self.categoryid,self.categoryname)
    
#subcategory
class subcategory(models.Model):
    subcategoryid=models.AutoField(primary_key=True)
    subcategoryname=models.TextField(max_length=50)
    categoryid=models.ForeignKey(category,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%s"%(self.subcategoryid,self.subcategoryname)

#user
class user(models.Model):
    userid=models.AutoField(primary_key=True)
    username=models.TextField(max_length=50)
    email=models.TextField(max_length=50)
    password=models.TextField(max_length=50) 
    profile=models.ImageField(upload_to="assets/images/user/")
    bio=models.TextField(max_length=1000)
    gender=models.TextField(max_length=10)
    dob=models.DateField()
    cityid=models.ForeignKey(city,on_delete=models.CASCADE)
    registrationdt=models.DateTimeField(auto_now=True)   

    def __str__(self):
        return "%d-%s"%(self.userid,self.username)
    
#community
class community(models.Model):
    communityid=models.AutoField(primary_key=True)
    communitytitle=models.TextField(max_length=50)
    thumbnail=models.ImageField(upload_to="images/")
    background_image=models.ImageField(upload_to="images/backgrounds/", null=True, blank=True)
    discription=models.TextField(max_length=1000)
    createddt=models.DateTimeField(auto_now=True)
    categoryid=models.ForeignKey(category,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    
    def __str__(self):
        return "%d-%s"%(self.communityid,self.communitytitle)
    
#communitymember
class communitymember(models.Model):
    communitymemberid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    status=models.IntegerField(max_length=50)
    addeddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d"%(self.communityid,self.userid)
    
#post
class post(models.Model):
    postid=models.AutoField(primary_key=True)
    posttitle=models.TextField(max_length=50)
    thumbnail=models.ImageField(upload_to="images/")
    description=models.TextField(max_length=1000)
    createddt=models.DateTimeField(auto_now=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)
    isapproved=models.BooleanField(default=False)

    def __str__(self):
        return "%d-%s"%(self.postid,self.posttitle)
    
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

    def __str__(self):
        return "%d-%d"%(self.postid,self.userid)
    
#follow
class follow(models.Model):
    followid=models.AutoField(primary_key=True)
    followerid=models.IntegerField(max_length=50)
    userid=models.ForeignKey(user,on_delete=models.CASCADE)

    def __str__(self):
        return "%d-%d"%(self.followerid,self.userid)
    
#communityMessage
class communityMessage(models.Model):
    communityMessageid=models.AutoField(primary_key=True)
    senderid=models.IntegerField(max_length=50)
    message=models.TextField(max_length=1000)
    senddt=models.DateTimeField(auto_now=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    
    def __str__(self):
        return "%d-%s"%(self.communityMessageid,self.message)
    
#CommunityAdmins
class communityAdmins(models.Model):
    communityAdminsid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    adminid=models.ForeignKey(user,on_delete=models.CASCADE)
    addedbyuserid=models.IntegerField(max_length=50)
    addeddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d"%(self.communityid,self.adminid)
    
#chat
class chat(models.Model):
    chatid=models.AutoField(primary_key=True)
    senderid=models.IntegerField(max_length=50)
    receiverid=models.IntegerField(max_length=50)#userid
    message=models.TextField(max_length=1000)
    senddt=models.DateTimeField(auto_now=True)
    status=models.IntegerField(max_length=50)

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
        return "%d-%d"%(self.imageid,self.userid)

#CommunityInvite
class CommunityInvite(models.Model):
    inviteid=models.AutoField(primary_key=True)
    communityid=models.ForeignKey(community,on_delete=models.CASCADE)
    senderid=models.IntegerField() # userid of sender
    receiverid=models.ForeignKey(user,on_delete=models.CASCADE)
    status=models.IntegerField(default=0) # 0=Pending, 1=Accepted, 2=Declined
    createddt=models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%d-%d To %d"%(self.inviteid,self.senderid,self.receiverid.userid)
