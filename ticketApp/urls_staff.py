from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView

# All urls are at base/staff/tickets

app_name = "ticketApp_staff"

urlpatterns = [
    #  || General Links ||


    # || Staff/Employee Links ||
    path('', views.staff_ticket_home, name="staff_ticket_home")

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)