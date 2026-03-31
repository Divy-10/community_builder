import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'community_builders.settings')
django.setup()

from django.test import Client

try:
    c = Client()
    # Log in or test without login
    try:
        from user.models import user
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
    except Exception as e:
        pass
        
    c.login(username='admin', password='admin')
    response = c.get('/admin/user/user/')
    print(f"Status code: {response.status_code}")
except Exception as e:
    print("Caught exception:")
    traceback.print_exc()
