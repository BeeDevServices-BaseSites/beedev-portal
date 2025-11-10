from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# All urls are at base/invoices/

app_name = "invoice_staff"

urlpatterns = [
    path('', views.invoice_home, name='invoice_home'),
    path('invoice/new/', views.create_new_invoice, name='create_new_invoice'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)