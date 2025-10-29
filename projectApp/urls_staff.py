from django.urls import path, reverse_lazy
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# All urls are at base/projects/

app_name = "projects_staff"

urlpatterns = [
    path("", views.project_home, name="project_home"),
    path("new/", views.project_create, name="project_create"),
    path("<slug:slug>/board/", views.project_board, name="project_board"),
    path("mine/", views.my_tasks, name="my_tasks"),
    path("task/<int:pk>/", views.task_detail, name="task_detail"),

    # simple POST endpoints
    path("task/<int:pk>/comment/", views.task_add_comment, name="task_add_comment"),
    path("task/<int:pk>/checklist/add/", views.task_add_checklist_item, name="task_add_checklist_item"),
    path("checklist/<int:item_id>/toggle/", views.task_toggle_checklist_item, name="task_toggle_checklist_item"),
    path("task/<int:pk>/attachment/upload/", views.task_upload_attachment, name="task_upload_attachment"),
    path("task/<int:pk>/move/", views.task_move_status, name="task_move_status"),
    path("task/<int:pk>/sprint/", views.task_assign_sprint, name="task_assign_sprint"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
