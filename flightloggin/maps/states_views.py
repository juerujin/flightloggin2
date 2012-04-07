from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from share.decorator import secret_key, no_share
from django.views.decorators.cache import cache_page

from states import CountStateMap, UniqueStateMap, FlatStateMap

@cache_page(60 * 60 * 6)
def render_image(request, type_, ext):
    if type_ == "unique":
        return UniqueStateMap(request.display_user, ext=ext).as_response()
    
    if type_ == 'count':
        return CountStateMap(request.display_user, ext=ext).as_response()
    
    if type_ == 'colored':
        return FlatStateMap(request.display_user, ext=ext).as_response()

def image_redirect(request, type_):
    """
    Redirect to the pre-rendered png image, kept for legacy reasons
    will be removed at some point in time
    """

    path = "%s/%s/%s" % (settings.SITE_URL,
                         settings.STATES_URL,
                         request.display_user.id)
    
    return HttpResponseRedirect("%s/states-%s.png" % (path, type_))

@no_share('NEVER')
@login_required
def render_me(request):
    
    render_for_user(request.display_user)

    # return the user to their maps page with spiffy new updated images
    from django.core.urlresolvers import reverse
    url = reverse('maps', args=(request.display_user.username,) )

    return HttpResponseRedirect(url)