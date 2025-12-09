from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView

# All urls are at base/onboarding

app_name = "onboarding"

urlpatterns = [
    #  || General Links ||


    # || Staff/Employee Side ||
    path('', views.onboard_home, name="onboard_home"),
    path('list/<int:pk>/', views.onboarding_list_detail, name="list_detail"),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)