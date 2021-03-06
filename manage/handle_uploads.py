from django.conf import settings
UPLOADS_DIR = settings.UPLOADS_DIR
import datetime

def get_last(uid):
    """
    Goes through the uploads directory and returns the latest file (based
    on modified date/time in metadata) that starts with the user's ID.
    returns the file, and then a dict with some metadata
    """
    import os
    filenames = os.listdir(UPLOADS_DIR)
    
    # find all files in teh directory that have the user's username in the
    # filename
    hits=[]
    st = "%s-" % uid
    for filename in filenames:
        if filename.startswith(st):
            hits.append(filename)

    # no file found
    if len(hits) == 0:
        return None, None
        
    else:
        # at least one file found, return the last modified one
        modified = 0
        our_file = None
        for filename in hits:
            full_fn = UPLOADS_DIR + "/" + filename
            new_modified = os.path.getmtime(full_fn)
            if new_modified > modified:
                modified = new_modified
                our_file = full_fn
                
        f = open(our_file, 'rU')
            
    size = "%.2f" % (os.path.getsize(our_file) / 1024.0)
    ago = str(datetime.datetime.now() -\
                        datetime.datetime.fromtimestamp(modified))
    previous = {}
    
    if f:
        previous['age'] = "Uploaded %s Ago" % ago[:-10]
        previous['size'] = "%s KB<br>" % size
    else:
        previous['age'] = "<i>You have not uploaded anything yet</i>"
        previous['size'] = ""
        
    return f, previous

def make_filename(user):
    return "%s/%s-%s-%s.txt" %\
        (UPLOADS_DIR,
         user.id,
         datetime.datetime.now().microsecond,
         user.username)

def save_upload(f, user):
    """
    Saves a UploadFile instance to the uploads direrctory
    """
    
    filename = make_filename(user)
    dest = open(filename, 'wb+')
    
    for chunk in f.chunks():
        dest.write(chunk)
    dest.close()
    
def save_php(f, user):
    """
    Saves an addinfourl file object to the uploads directory
    """
    
    filename = make_filename(user)
    dest = open(filename, 'wb+')
    
    for line in f.read():
        dest.write(line)
    dest.close()    
