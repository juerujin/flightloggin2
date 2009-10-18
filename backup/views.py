import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from annoying.decorators import render_to

from classes import Backup, EmailBackup

@login_required()   
def backup(request, shared, display_user):
    
    # get a zip file of the csv of the users data
    sio = Backup(display_user).output_zip()
    
    DATE = datetime.date.today()
    
    response = HttpResponse(sio.getvalue(), mimetype='application/zip')
    response['Content-Disposition'] = \
                'attachment; filename=logbook-backup-%s.tsv.zip' % DATE

    return response

#################################
#################################
#################################

from share.decorator import no_share, secret_key

@no_share
@login_required() 
def emailbackup(request, shared, display_user):
    """Send email backup to the user"""
    
    email = EmailBackup(display_user)
    sent = email.send()
    
    return HttpResponse("email sent to %s" % sent, mimetype='text-plain')

@secret_key
@login_required()
def email_schedule(request):
    return HttpResponse('omg')
