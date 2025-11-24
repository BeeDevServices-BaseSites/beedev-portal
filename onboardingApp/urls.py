from django.urls import path, reverse_lazy
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView

# All urls are at base/onboarding

app_name = "onboardingApp"

urlpatterns = [
    #  || General Links ||


    # || Staff/Employee Side ||


    # || Client Side ||

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)