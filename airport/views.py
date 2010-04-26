from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

from share.decorator import secret_key
from annoying.decorators import render_to
from models import Location, HistoricalIdent

################################

@render_to('location_profile.html')
def airport_profile(request, navaid, ident):
    
    from plane.models import Plane
    from logbook.models import Flight
    from django.contrib.auth.models import User
    from django.http import Http404
    

    loc = Location.goof(loc_class__in=(1,2), identifier=ident)
    
    if loc.loc_class == 1 and navaid:
        raise Http404
    
    if loc.loc_class == 2 and not navaid:
        raise Http404
    
    users = Location.get_profiles(ident, 'identifier')
    
    tailnumbers = Plane.objects\
                       .exclude(tailnumber="")\
                       .values_list('tailnumber', flat=True)\
                       .filter(flight__route__routebase__location__identifier=ident)\
                       .order_by('tailnumber')\
                       .distinct()
                       
    t_flights = Flight.objects\
                      .filter(route__routebase__location__identifier=ident)\
                      .count()
                      
    lc = loc.get_loc_class_display().lower()
    
    previous_identifiers = HistoricalIdent.objects\
                               .filter(current_location=loc)
    
    return locals()
    
def location_redirect(request, ident):
    url = reverse('profile-airport', kwargs={'ident': ident})
    return HttpResponseRedirect(url)



@render_to('search_locations.html')
def search_airport(request):

    if not request.GET:
        return locals()
    
    from django.db.models import Q
    
    s = request.GET.get('q')
    
    q = ( Q(identifier__icontains=s) | Q(name__icontains=s) | Q(municipality__icontains=s)
        )
    
    results = Location.objects\
                      .filter(loc_class__in=(1,2,))\
                      .filter(q)
    
    count = results.count()
    did_something = True
    
    return locals()

@render_to('wiki_airport.html', mimetype="application/xml")
def export_to_xml(request, index):
    """
    Export all airports to an XML file for inputting into wikiPLANEia
    """
    
    index = int(index)
    
    size = 5000
    
    start = (index * size)
    
    qs = Location.objects\
                 .select_related()\
                 .filter(country__code='US', loc_class=1, loc_type=1)\
                 .order_by('identifier')[start:start+size]\
                 .iterator()
    
    article_start = 180
    rev_start = 430
    
    airports = []
    for num,a in enumerate(qs):
        a.article_id = num + article_start
        a.rev_id = num + rev_start
        airports.append(a)
               
    return locals()
        

















    
