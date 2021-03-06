import re

from django.contrib.gis.db import models
from django.db.models import Q

from share.middleware import share
from airport.models import Location, HistoricalIdent

from main.enhanced_model import QuerySetManager, EnhancedModel

###############################################################################

class RouteBase(models.Model):
    
    route =    models.ForeignKey("Route")
    
    location =  models.ForeignKey(Location, null=True, blank=True)
    unknown =  models.CharField(max_length=30, blank=True, null=True)
    sequence = models.PositiveIntegerField()
    
    land = models.BooleanField()
    
    def __unicode__(self):
        
        loc_class = self.loc_class
        
        if loc_class == 0:
            ret = "unknown: %s" % self.unknown
        
        elif loc_class == 1:
            ret = "airport: %s" % self.location.identifier
        
        elif loc_class == 2:
            ret = "navaid: %s" % self.location.identifier
            
        elif loc_class == 3:
            ret = "custom: %s" % self.location.identifier
        
        if not self.land:
            ret = ret + " (NO LAND)"
            
        return ret
    
    def custom(self):
        """
        Returns true if the location is a custom identifier
        """
        
        return self.location.loc_class == 3
        
    def destination(self):
        """
        Returns the location object, or a string that represents the
        identifier if unknown
        """
        
        return self.location or self.unknown
    
    @property
    def loc_class(self):
        """
        Return the type of location, zero if it has no location
        """
        
        return getattr(self.destination(), "loc_class", 0)
    
    def admin_loc_class(self):
        try:
            return getattr(self.destination(), "get_loc_class_display")() 
        except:
            return "Unknown"
    
    def owner(self):
        """
        Return the owner of the routebase. Only used in the admin
        """
        
        try:
            return self.route.flight.all()[0].user.username
        except IndexError:
            return "not connected to any flights"
    
###############################################################################

class Route(EnhancedModel):
    """
    Represents a route the user went on for the flight
    """
    
    objects =  QuerySetManager(name="RouteQuerySet")

    fancy_rendered =  models.TextField(blank=True, null=True)
    fallback_string = models.TextField(blank=True, null=True)
    simple_rendered = models.TextField(blank=True, null=True, db_index=True)
    kml_rendered =    models.TextField(blank=True, null=True)
    
    max_width_all =   models.FloatField(null=True, default=0)
    max_width_land =  models.FloatField(null=True, default=0)
    
    max_start_all =   models.FloatField(null=True, default=0)
    max_start_land =  models.FloatField(null=True, default=0)
    
    total_line_all =  models.FloatField(null=True, default=0)
    total_line_land = models.FloatField(null=True, default=0)
    
    p2p = models.BooleanField(default=False)
    
    # a queryset of all landing points and all points, internal only
    land_points = None
    all_points = None
    
    def __unicode__(self):
        return self.simple_rendered or "Empty"
    
    def owner(self):
        """
        Return the owner of the route. Only used in the admin
        """
        
        try:
            return self.flight.all()[0].user.username
        except IndexError:
            return "??"
    
    ##################################
    
    @classmethod
    def get_profiles(cls, val, field):
        """
        Returns the profiles of the users who have flown in this
        route
        """
        
        kwarg = {"user__flight__route__%s__iexact" % field: val}
        
        from profile.models import Profile
        return Profile.objects\
                   .filter(**kwarg)\
                   .filter(social=True)\
                   .values('user__username', 'user__id', 'logbook_share')\
                   .order_by('user__username')\
                   .distinct()
    
    
    @classmethod
    def render_custom(cls, user):
        qs = cls.objects.filter(flight__user=user)\
                    .filter(routebase__location__loc_class=3)
        for r in qs:
            r.easy_render()
        return qs.count()
    
    @classmethod
    def easy_render_all(cls, only_unknowns=False):
        """
        Re-renders ALL instances of Routes in the database. Easy render
        is not an expensive operation (relatively), so this isn't
        needing to be done in patches like hard_render.
        """

        qs = cls.objects.order_by('-id')
        
        if only_unknowns:
            qs = qs.filter(routebase__unknown__isnull=False)
        
        for r in qs.iterator():
            r.easy_render()            
            
    
    @classmethod
    def hard_render_user(cls, user):
        """
        Hard re-render all routes for the given username. This function makes
        sure to not orphan any route objects during re-rendering.
        """
            
        from django.db.models import Max
        qs = cls.objects.user(user)\
                        .distinct()\
                        .annotate(fid=Max('flight__id')) # max id == only id
                        
        for r in qs.iterator():
            r.hard_render(user=user, flight_id=r.fid)
            print r.fancy_rendered
            print "////////////////////////////////////"
            #r.save()
            
        return qs.count()
        
    @classmethod
    def from_string(cls, raw_route_string, user=None, date=None):
        """
        Create a route object from a raw string
        """
        
        from make_route import MakeRoute
        
        if not user:
            # for legacy only
            user = share.get_display_user()
            
        return MakeRoute(raw_route_string, user=user, date=date).get_route()
    
    #################################
    
    def render_distances(self):
        all_points = self._get_AllPoints()
        
        if not all_points or all_points.count() == 1:
            return ## nothing to measure, keep the defaults
        
        land_points = self._get_LandingPoints()
        
        self.max_start_all = self.calc_max_start(all_points)
        self.max_start_land = self.calc_max_start(land_points)
        
        self.max_width_all = self.calc_max_width(all_points)
        self.max_width_land = self.calc_max_width(land_points)
        
        self.total_line_all = self.calc_total_line(points="all")
        self.total_line_land = self.calc_total_line(points="land")
        
    #################################
    
    def _get_LandingPoints(self):
        """
        return a queryset containing all points where a landing took place.
        """
        
        if not self.land_points:
            self.land_points = Location.objects.filter(
                    location__isnull=False,    # has valid coordinates
                    routebase__route=self,     # is connected to this route
                    routebase__land=True,      # depicts a landing
            ).distinct()
            
        return self.land_points
    
    def _get_AllPoints(self):
        """
        Return a queryset of all points, regardless whether a landing
        was done there or not
        """
        
        if not self.all_points:
            self.all_points = Location.objects.filter(
                    location__isnull=False,
                    routebase__route=self,
            ).distinct()
            
            #self.line_kml = self.all_points.make_line().kml
            
        return self.all_points
    
    def calc_max_width(self, a=None):
        """
        Returns the max distance between any two points in the route
        """
        
        if not a:
            a = self._get_AllPoints()
        
        mp = a.collect()
        
        dist = []
        from utils import coord_dist
        for i,point1 in enumerate(mp):
            for j,point2 in enumerate(mp):
                dist.append(coord_dist(point1, point2))
        
        diameter = max(dist)
        
        return diameter
    
    def get_users(self):
        """
        Returns all users who have flown this exact route
        """
        
        from django.contrib.auth.models import User
        return User.objects.filter(profile__social=True)\
                   .filter(flight__route__simple_rendered=self.simple_rendered)
    
    ################################
    
    def calc_max_start(self, a=None):
        """
        Returns the max distance between any point in the route and the
        starting point. Used for ATP XC distance.
        """
        
        if not a:
            a = self._get_AllPoints()
        
        mp = a.collect()
        start = a[0].location
        
        dist = []
        from utils import coord_dist
        for i,po in enumerate(mp):
            dist.append(coord_dist(po, start))
         
        return max(dist)
    
    def calc_total_line(self, points="all"):
        """
        returns the distance between each point in the route
        """
        
        rbs = self.routebase_set.order_by('sequence')          
            
        if points == "land":
            rbs = rbs.exclude(land=False)
        
        # convert to [(lat,lng), ...] while maintaining the same order
        # skipping any routebase that has no location
        points = [(rb.location.location.x, rb.location.location.y)
                        for rb in rbs if rb.location and rb.location.location]
        
        dist = []
        from utils import coord_dist
        for i,po in enumerate(points):
            try:
                next = points[1+i]
            except IndexError:
                pass
            else:
                from django.contrib.gis.geos import Point
                dist.append(coord_dist(Point(po), Point(next)))
         
        return sum(dist)
    
    ################################
    
    def easy_render(self):
        """
        Rerenders the HTML for displaying the route. Takes info from the
        already defines routebases. For rerendering after updating Airport
        info, use hard_render()
        """
        
        fancy = []
        simple = []
        kml = []
        
        rbs = self.routebase_set.all().order_by('sequence')
        
        if not rbs:
            # a route was made, but no routebases were attached, must
            # be a local flight
            simple = ["Local"]
            fancy = ["<span title='Local Flight' class='local'>Local</span>"]
        
        for rb in rbs:
            
            dest = rb.destination()
            loc_class = rb.loc_class
            
            if loc_class == 1:
                class_ = "found_airport"
            elif loc_class == 2:
                class_ = "found_navaid"
            elif loc_class == 3:
                class_ = "found_custom"
            elif loc_class == 0:
                class_ = "not_found"
                
            if not rb.land:
                class_ += " noland"
            else:
                class_ += " land"
                
            # only write a kml if coordinates are known
            if getattr(dest, "location", None):
                kml.append("%s,%s" % (dest.location.x, dest.location.y), )
                
            if loc_class > 0:   
                fancy.append("<span title=\"%s\" class=\"%s\">%s</span>" %
                            (dest.title_display(), class_, dest.identifier ), )
                simple.append(rb.destination().identifier)
                
            elif loc_class == 0:
                fancy.append("<span title=\"%s\" class=\"%s\">%s</span>" %
                            (dest, class_, dest ), )
                simple.append(rb.destination())
            
        self.kml_rendered = "\n".join(kml)
        self.fancy_rendered = "-".join(fancy)
        self.simple_rendered = "-".join(simple)
        
        self.render_distances()
        
        self.save()
        
    def hard_render(self, user=None, username=None, flight_id=None):
        """
        Spawns a new Route object based on it's own fallback_string,
        connects it to the flight that the old route was connected to.
        Then returns the newly created Route instance. This is used to
        redo all the routebases after the navaid/airport database has been
        updated and new identifiers are present.
        """
        
        from make_route import MakeRoute
        from logbook.models import Flight
        from django.contrib.auth.models import User
        
        if not flight_id:
            # no flight id was provided, try to get it
            try:
                f = self.flight.all()[0]
                
            except IndexError:  
                # route is orphaned, go no further
                return
                
        else:
            f = Flight.objects.get(pk=flight_id)    

        flight_id = f.id
        user = f.user
        date = f.date
                
        if (not user) and username:
            user = User.objects.get(username=username)
        
        # get the falllback string from either the route or the flight
        fallback = f.route_string or self.fallback_string
        
        new_route = MakeRoute(fallback, user, date=date).get_route()

        f.route = new_route
        f.save(no_badges=True)
        
        return new_route
