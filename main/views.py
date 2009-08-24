from annoying.decorators import render_to
from annoying.functions import get_object_or_None
from models import NewsItem

@render_to("news.html")
def news(request):
    title = "News"
    news = NewsItem.objects.all()[:15]
    return locals()

@render_to("preferences.html")
def prefs(request):
    title="Preferences"
    return locals()

@render_to("faq.html")
def faq(request):
    title="FAQ"
    return locals()
    
@render_to("help.html")
def help(request):
    title="Help"
    return locals()

