from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views

handler403 = "core.views.custom_permission_denied_view"

admin.site.site_header = "BeeDev Admin"
admin.site.site_title = "BeeDev Admin"
admin.site.index_title = "BeeDev Administration"

admin.site.site_url = reverse_lazy("userApp:staff_home")

urlpatterns = [
    # Auth Home
    path('', include('userApp.urls')),

    #Public


    # Staff
    path('admin/', admin.site.urls),
    path('staff/companies/', include(('companyApp.urls_staff', 'company_staff'), namespace='company_staff')),
    path('staff/onboarding/', include(('onboardingApp.urls', 'onboarding'), namespace='onboarding')),
    path('staff/prospects/', include(('prospectApp.urls', 'prospects'), namespace='prospects')),
    path('staff/tickets/', include(('ticketApp.urls_staff', 'ticket_staff'), namespace='ticket_staff')),


    # Clients
    # path('company/', include(('companyApp.urls_client', 'company_client'), namespace='company_client')),
    # path('tickets/', include(('ticketApp.urls_client', 'ticket_client'), namespace='ticket_client')),
]
