from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(city)
admin.site.register(state)
admin.site.register(category)

@admin.register(user)
class UserAdmin(admin.ModelAdmin):
    list_display = ('userid', 'username', 'email', 'gender', 'registrationdt')
    search_fields = ('username', 'email')
