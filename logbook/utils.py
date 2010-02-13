def to_minutes(flt):
    """converts decimal to HH:MM
    
    >>> to_minutes(.5452)
    '0:33'
    >>> to_minutes(2)
    2:00
    >>> to_minutes(1.2)
    '1:12'
    >>> to_minutes(-1.2)
    '-1:12'
    """
    
    value = str(flt + 0.0)
    h,d = value.split(".")
    minutes = float("0." + d) * 60
    return str(h) + ":" + "%02.f" % minutes
    
def from_minutes(value):
    """converts HH:MM to decimal
    
    >>> from_minutes("1:45")
    1.75
    >>> from_minutes("1:75")
    2.25
    >>> from_minutes("0:17")
    0.28333333333333333
    >>> from_minutes("-4:00")
    -4.0
    """
    
    hh,mm = value.split(":")
    mm = float(mm)
    hh = float(hh)
    return (mm / 60) + hh

def proper_format(val, field, format):
    """
    Returns the value formatted appropriately based on whether it needs
    a decimal, needs to be HH:MM or needs to be an integer
    """
    if field in ('day_l', 'night_l', 'app'):
        return str(int(val))
    
    if field in ('line_dist', 'max_width'):
        return "%.1f" % val
            
    if format == 'decimal':
        return "%.1f" % val
    
    if format == 'minutes':
        return to_minutes(val)
    
def handle_fuel_burn(val, time):
    
    import re
    from django.forms.util import ValidationError
    
    val = val.lower()
    
    ## the value with just the number part, the unit is removed
    ## strip out all non-numeric characters but keep decimal point
    num = re.sub(r'[^\.\d\s]', '', val)
    unit = re.sub(r'[\.\d\s]', '', val)
    try:
        num = float(num)
    except:
        raise ValidationError("Invalid Fuel Burn Value")
    
    if num == 0:
        return (0,0)
    
    ####################### user entered pounds LL/pounds JetA per hour
    
    if unit == 'pphll':
        gph = num / 6
        g = gph * time
        
    elif unit == 'pphj' or unit == 'pph':
        gph = num / 6.8
        g = gph * time
        
    ####################### user entered pounds LL/pounds JetA
    
    elif unit == 'pll':
        g = num * 6
        if time > 0:
            gph = (g / time)
        else:
            gph = 0
        
        
    elif unit == 'p' or unit == 'pj':
        g = num * 6.8
        if time > 0:
            gph = (g / time)
        else:
            gph = 0
                
    ######################## user entered gallons or liters
    
    elif unit == 'g':
        g = num
        if time > 0:
            gph = (g / time)
        else:
            gph = 0
    
    elif unit == 'l':
        g = num / 3.78541178 ## 1 gal = 3.78 liters
        if time > 0:
            gph = (g / time)
        else:
            gph = 0
                
    ####################### user entered gallons/liters per hour
        
    elif unit == 'lph':
        gph = num / 3.78541178
        g = gph * time
        
    elif unit == 'gph' or unit == '':
        g = num * time
        gph = num
    
    else:
        raise ValidationError("Invalid Fuel Burn Unit")
          
    return g, gph


def logbook_url(user, page):
    """
    Redirect the user to their logbook page, if the page==0, just redirect
    them to plain ol' logbook.html
    """
    from django.core.urlresolvers import reverse
    
    if int(page) == 0 or not page:
        kwargs = {'username': user.username}
        view = "logbook"
    else:
        kwargs = {'username': user.username, 'page': page}
        view = "logbook-page"

    return reverse(view, kwargs=kwargs)

def proper_flight_form(profile):
    """
    Prepares the popup flight form based on how the user wants each field
    widget to be rendered as.
    """
    
    from logbook.forms import PopupFlightForm, text_plane_field
    
    if profile.text_plane:
        # if the user wants a text field fo the plane, then swap in this field
        # instead
        PopupFlightForm.base_fields['plane'] = text_plane_field

    return PopupFlightForm   

def expire_page(user=None, page=None, url=None):

    from django.core.cache import cache
    from django.http import HttpRequest
    from django.utils.cache import get_cache_key
    
    if not url:
        url = logbook_url(user, page)
    
    request = HttpRequest()
    request.path = url
    key = get_cache_key(request)
    
    if key and cache.has_key(key):   
        cache.delete(key)
        
def expire_all(user):
    """
    Expire all logbook pages in the passed user's logbook section
    This function is used after the user changes his preferences and it
    effects all pages in his logbook
    """
    
    from logbook.models import Flight
    import math
    
    try:
        per_page = user.get_profile().per_page
    except:
        return
    
    total_flights = Flight.objects.user(user).count()
    last_page = int(math.ceil(total_flights / float(per_page)))

    for page in range(1,last_page):
        expire_page(user, page)


