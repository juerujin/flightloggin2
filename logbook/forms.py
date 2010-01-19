import re

from django import forms
from django.forms import ModelForm, ModelChoiceField
from django.contrib.admin import widgets
from django.forms.widgets import TextInput, HiddenInput
from django.forms.util import ValidationError

from models import *
from route.forms import RouteField, RouteWidget
from logbook.utils import from_minutes

class BlankHourWidget(TextInput):
    def _format_value_out(self, value):
        """In: decimal number
           Out: a string formatted to HH:MM
           a zero value outputs an empty string"""
        
        if not value or value == 0:
            return ""

        return str(to_minutes(value))

    def render(self, name, value, attrs=None):
        value = self._format_value_out(value)
        attrs.update({"class": "float_line"})
        return super(BlankHourWidget, self).render(name, value, attrs)

    def _has_changed(self, initial, data):
        return super(BlankHourWidget, self).\
                    _has_changed(self._format_value_out(initial), data)
        
class BlankDecimalWidget(BlankHourWidget):
    def _format_value_out(self, value):
        """Prepare value for output in the mass entry form
           In: decimal number
           Out: a string of that decimal number
           a zero value outputs an empty string"""
        
        if not value or value == 0:
            return ""
        else:
            return value
    
class BlankIntWidget(BlankHourWidget):
    def _format_value_out(self, value):
        """Prepare value for outout in the mass entry form
           In: an int
           Out: a string of that int
           a zero value outputs an empty string"""
        
        if not value or value == 0:
            return ""
        else:
            return str(value)

###############################################################################

class BlankHourField(forms.Field):
    widget = BlankHourWidget
    def clean(self, value):
        super(BlankHourField, self).clean(value)
        
        if not value:
            return 0
        
        match = re.match("^([0-9]{1,3}):([0-9]{2})$", value)
        if match:
            dec = str(from_minutes(value))
        else:
            dec = str(value)
            
        try:
            ev = eval(dec)
        except:
            raise ValidationError("Invalid Formatting")
            
        return ev
        
    def __init__(self, *args, **kwargs):
        super(BlankHourField, self).__init__(required=False, *args, **kwargs)
        
class BlankDecimalField(BlankHourField):
    widget = BlankDecimalWidget

class BlankIntField(BlankHourField):
    widget = BlankIntWidget
    
###############################################################################

class FlightForm(ModelForm):
    
    route =    RouteField(
                   required=False,
                   queryset=Route.objects.get_empty_query_set()
               )
    
    plane =    ModelChoiceField(
                   required=True,
                   queryset=Plane.objects.get_empty_query_set()
               )
    
    total =    BlankDecimalField(label="Total Time")
    pic =      BlankDecimalField(label="PIC")
    sic =      BlankDecimalField(label="SIC")
    solo =     BlankDecimalField(label="Solo")
    dual_g =   BlankDecimalField(label="Dual Given")
    dual_r =   BlankDecimalField(label="Dual Received")
    xc =       BlankDecimalField(label="Cross Country")
    act_inst = BlankDecimalField(label="Actual Instrument")
    sim_inst = BlankDecimalField(label="Simulated Instrument")
    night =    BlankDecimalField(label="Night")
    
    day_l =    BlankIntField(label="Day Landings")
    night_l =  BlankIntField(label="Night Landings")
    app =      BlankIntField(label="Approaches")
    
    
    def __init__(self, *args, **kwargs):  
        super(FlightForm, self).__init__(*args, **kwargs)
        
        from share.middleware import share
        from django.db.models import Max
        self.fields['date'].widget = widgets.AdminDateWidget()
        self.fields['plane'].queryset = \
                    Plane.objects\
                    .user_common(share.get_display_user())\
                    .annotate(fd=Max('flight__date')).order_by('-fd')
        self.fields['plane'].default=1
        self.fields['plane'].blank=False
        self.fields['plane'].null=False

    class Meta:
        model = Flight
        exclude = ('user', )

###############################################################################

class FormsetFlightForm(FlightForm):
    """Form used for the mass entry section. It's the same as the normal flight
       form except that it renders the route field as a string, and the
       remarks are in a big textbox
    """
    
    remarks = forms.CharField(
                widget=forms.TextInput(attrs={"class": "remarks_line"}),
                required=False)
                
    person = forms.CharField(
                widget=forms.TextInput(attrs={"class": "person_line"}),
                required=False)
                
    route = RouteField(
                queryset=Route.objects.get_empty_query_set(),
                widget=RouteWidget)
    
    class Meta:
        model = Flight
        exclude = ('user', )
        
        
from django.forms.models import BaseModelFormSet
class FixedPlaneModelFormset(BaseModelFormSet):
    def __init__(self, *args, **kwargs): 
        if kwargs.has_key('planes_queryset'):
            self.custom_queryset = kwargs['planes_queryset']
            del kwargs['planes_queryset']         
        super(FixedPlaneModelFormset, self).__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super(FixedPlaneModelFormset, self).add_fields(form, index)
        form.fields["plane"] = ModelChoiceField(
                queryset=Plane.objects.get_empty_query_set(), required=True)
        form.fields['plane'].queryset = self.custom_queryset
