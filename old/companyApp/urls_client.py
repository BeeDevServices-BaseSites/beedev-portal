from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# All urls are at base/client/company

app_name = "company_client"

urlpatterns = [
    path('company/<int:pk>/', views.view_my_company_detail, name='my_company_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)