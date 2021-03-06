import re
from django import forms
from django.contrib.auth.models import User
from profile.models import Profile
from django.conf import settings
from django.forms.extras.widgets import SelectDateWidget
from main.utils import track

w = SelectDateWidget(years=[str(x) for x in range(2012, 1912, -1)])

class RegistrationForm(forms.Form):
    dob = forms.DateField(help_text="For calculating medical durations", widget=w, required=False, label="Date of Birth")
    username = forms.CharField(max_length=30) # @/./+/-/_
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Retype password")

    def clean_password(self):
        if len(self.cleaned_data['password']) < 6:
            raise forms.ValidationError('Password too short, must be 6 characters')
        return self.cleaned_data['password']

    def clean_username(self):
        u = self.cleaned_data['username']
        r = "^" + settings.REGEX_USERNAME + "$"

        if len(u) > 30 or len(u) < 3:
            track('bad-length', {'username': u})
            raise forms.ValidationError('Username must be between 3 and 30 characters in length')

        if not re.match(r, u):
            track('invalid-characters', {'username': u})
            raise forms.ValidationError('Invalid characters in username. Allowed chars: numbers, letters and underscores')

        try:
            user = User.objects.get(username=u)
        except User.DoesNotExist:
            return u

        raise forms.ValidationError('Username %s already taken' % u)

    def clean(self):
        pass1 = self.cleaned_data.get('password')
        pass2 = self.cleaned_data.get('password2')

        if (pass1 and pass2) and (pass1 != pass2):
            raise forms.ValidationError("Passwords must match")

        firstname = self.cleaned_data.get('first_name', '')
        lastname = self.cleaned_data.get('last_name', '')
        letters = lastname[-2:]
        if len(letters) and letters == letters.upper() and firstname.endswith(letters):
            track('spam-detection', {'name': "%s %s" % (firstname, lastname)})
            raise forms.ValidationError("deep derp")

        return self.cleaned_data

    def register(self, *a, **k):
        first_name = self.cleaned_data.get('first_name', '')
        last_name = self.cleaned_data.get('last_name', '')

        u = User.objects.create(
            email=self.cleaned_data['email'],
            username=self.cleaned_data['username'],
            first_name=first_name,
            last_name=last_name,
		)

        u.set_password(self.cleaned_data['password'])
        u.save()

        kwargs = {
            'backup_email': self.cleaned_data.get('email', ''),
            'user': u,
            'real_name': "%s %s" % (first_name, last_name),
        }

        if self.cleaned_data.get('dob', None):
            kwargs['dob'] = self.cleaned_data.get('dob', '')

        p = Profile.objects.create(**kwargs)

        return p