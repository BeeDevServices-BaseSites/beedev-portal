from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views

handler403 = "core.views.custom_permission_denied_view"

admin.site.site_header = "BeeDev Admin"
admin.site.site_title = "BeeDev Admin"
admin.site.index_title = "BeeDev Administration"

admin.site.site_url = reverse_lazy("userApp:employee_home")

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth Home
    path('', include('userApp.urls')),
]
