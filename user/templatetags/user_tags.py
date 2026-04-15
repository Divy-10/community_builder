from django import template
from django.utils import timezone

register = template.Library()

@register.filter(name='format_currency')
def format_currency(amount, settings_obj=None):
    if amount is None:
        return ""
    try:
        amount = float(amount)
    except ValueError:
        return amount

    currency_format = 'INR'
    if settings_obj and hasattr(settings_obj, 'currency_format'):
        currency_format = settings_obj.currency_format

    if currency_format == 'USD':
        # approx ₹83 = $1
        converted = amount / 83.0
        return f"${converted:.2f}"
    elif currency_format == 'EUR':
        # approx ₹90 = €1
        converted = amount / 90.0
        return f"€{converted:.2f}"
    else:
        # Default INR
        return f"₹{amount:g}"

@register.filter(name='format_datetime')
def format_datetime(value, settings_obj=None):
    if not value:
        return ""
    
    from django.utils.timezone import localtime
    try:
        # Convert to local timezone if aware
        if hasattr(value, 'tzinfo') and value.tzinfo:
            value = localtime(value)
            
        date_format = "MM/DD/YYYY"
        if settings_obj and hasattr(settings_obj, 'date_time_format'):
            date_format = settings_obj.date_time_format

        if date_format == "DD/MM/YYYY":
            return value.strftime("%d/%m/%Y %I:%M %p")
        elif date_format == "MM/DD/YYYY":
            return value.strftime("%m/%d/%Y %I:%M %p")
        elif date_format == "YYYY-MM-DD":
            return value.strftime("%Y-%m-%d %H:%M")
        else:
            return value.strftime("%b %d, %Y")
    except (AttributeError, ValueError):
        return value

@register.filter(name='is_following')
def is_following(user_obj, author_obj):
    from user.models import follow
    if not user_obj or not author_obj:
        return False
    return follow.objects.filter(followerid=user_obj.userid, userid=author_obj).exists()

@register.filter(name='is_member_of')
def is_member_of(user_obj, community_obj):
    from user.models import communitymember
    if not user_obj or not community_obj:
        return False
    return communitymember.objects.filter(userid=user_obj, communityid=community_obj, status=1).exists()
