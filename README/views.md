# Views / URLS and Status
- Updated as of 10/2

## All
| URL | Page | App | Status |
|-----|:----:|:---:|-------:|
| / | Login | userApp | Done |
| /logout | Logout | userApp | Done |
|||||

## Staff
| URL | Page | App | Permissions| Notes | Status |
|:----|:-----|:---:|:----------:|:-----:|-------:|
| /admin | Django Admin | -- | All Staff | -- | Done |
| /employee | Dashboard | userApp | All Staff | Basic Styling done needs content | Created |
| /employee/profile | Profile | userApp | User | Needs Edit Button | Done |
| /employee/profile/edit | Edit Profile | userApp | User | -- | -- |
| /staff | Admin | userApp | All Staff | Redirect | Done |
| /team | Staff Admin | userApp | HR/Admin+ | Add Staff button needed | Created |
| /team/# | Staff Profile | userApp | HR/Admin+ | Edit Profile needed | Created |
| /clients | Contacts Admin | userApp | Staff -HR | DNC Table Needed | Created |
| /clients/# | One Client Profile | userApp | Staff -HR | -- | -- |
| /clients/new | New Client | userApp | Staff -HR | Pre-App Clients or One off adds | -- |
| /prospects/# | One Prospect | prospectApp | Staff -HR | Hide Won Gate needed | Created |
| /prospects/new | Create Prospect | prospectApp | Staff -HR | CSS | Created |
| /prospects/#/edit | Edit Prospect Detail | prospectApp | Staff -HR | CSS | Created |
| /prospects/#/status | Updated Prospect Status | prospectApp | Staff -HR | Won Converts to Company not client as no log in yet | Created |
| /companies | Company Admin | companyApp | Staff -HR | CSS | Created |
| /companies/company/# | One Company | companyApp | Staff -HR | CSS | Created |
| /companies/company/add | Create Company | companyApp | Staff -HR | CSS | Created |
| /proposals | Proposal Admin | proposalApp | Staff -HR | CSS | Created |
| /proposals/draft/new | Create Draft | proposalApp | Staff -HR | -- | -- |
| /proposals/draft/# | One Draft | proposalApp | Staff -HR | -- | Created |
| /proposals/draft/#/update | Update Draft | proposalApp | -- | -- | -- |
| /proposals/proposal/# | One Proposal | proposalApp | -- | -- | Created |
| /invoices | Invoice Admin | invoiceApp | -- | -- | Created |
| /invoices/# | One Invoice | invoiceApp | -- | -- | -- |
| /invoices/new | Create Invoice | invoiceApp | -- | -- | -- |
| /projects | Project Admin | projectApp | -- | -- | -- |
| /projects/# | One Project | projectApp | -- | -- | -- |
| /projects/new | Create Project | projectApp | -- | -- | -- |
| /projects/#/update | Update Project | projectApp | -- | -- | -- |
| /tickets | Ticket Admin | ticketApp | -- | -- | -- |
| /tickets/current/# | One Current Ticket | ticketApp | -- | -- | -- |
| /tickets/archived/# | One Archived Ticket | ticketApp | -- | -- | -- |
||||||


## Client
| URL | Page | App | Notes | Status |
|:----|-----:|:---:|:-----:|-------:|
| /client | Dashboard | userApp | -- |Created |
| /client/profile | Profile | userApp | -- | Done |
| /client/tickets | Ticket Home | ticketApp | -- | -- |
| /client/tickets/# | One Ticket | ticketApp | -- | -- |
| /client/tickets/new | Create Ticket | ticketApp | -- | -- |
| /client/projects | Project Home | projectApp | -- | -- |
| /client/projects/# | One Project| projectApp | -- | -- |
| /client/invoices | Invoice Home | invoiceApp | -- | -- |
| /client/invoices/# | One Invoice | invoiceApp | -- | -- |
| /client/proposals | All Proposals | proposalApp | -- | -- |
||||||

# Django Error Routes/URLS
- __reload__/
- proposals/s/<str:token>/ [name='view']
- proposals/s/<str:token>/pdf/ [name='pdf']
- [name='login']
- post-login/ [name='post_login']
- logout/ [name='logout']
- staff/ [name='staff_home']
- employee/ [name='employee_home']
- employee/profile/ [name='view_employee_profile']
- team/ [name='view_all_staff']
- team/<int:pk>/ [name='profile_detail']
- clients/ [name='view_all_clients']
- client/ [name='client_home']
- client/profile/ [name='view_client_profile']
- ^media/(?P<path>.*)$
- admin/
- companies/
- proposals/ [name='proposal_home']
- proposals/ draft/new/ [name='create_new_draft']
- proposals/ draft/<int:pk>/ [name='draft_detail']
- proposals/ proposal/<int:pk>/ [name='proposal_detail']
- proposals/ proposal/<int:pk>/pdf/generate/ [name='proposal_generate_pdf']
- proposals/ proposal/<int:pk>/pdf/ [name='proposal_pdf']
- proposals/ proposals/<int:pk>/send/ [name='proposal_send']
- proposals/ ^media/(?P<path>.*)$
- projects/
- invoices/
- tickets/
- prospects/
- client/company/
- client/proposals/
- client/invoices/
- client/projects/
- client/tickets/


## As of 10/28:

### Base:
urlpatterns = [
    path('__reload__/', include('django_browser_reload.urls')),

    # Public URLS, token-based
    path('', include(('proposalApp.urls.public', 'proposal_public'), namespace='proposal_public')),

    # Auth Home
    path('', include('userApp.urls')),

    # Admin
    path('admin/', admin.site.urls),

    # Staff
    path('companies/', include(('companyApp.urls_staff', 'company_staff'), namespace='company_staff')),
    path('proposals/', include(('proposalApp.urls.staff', 'proposal_staff'), namespace='proposal_staff')),
    path('projects/', include(('projectApp.urls_staff', 'projects_staff'), namespace='projects_staff')),
    path('invoices/', include(('invoiceApp.urls_staff', 'invoice_staff'), namespace='invoice_staff')),
    path('tickets/', include(('ticketApp.urls_staff', 'ticket_staff'), namespace='ticket_staff')),
    path('prospects/', include(('prospectApp.urls', 'prospects'), namespace='prospects')),
    # path('time/', include(('timeApp.urls', 'time'), namespace='time')),
    
    # Client
    path('client/company/', include(('companyApp.urls_client', 'company_client'), 
    namespace='company_client')),
    path('client/proposals/', include(('proposalApp.urls.client', 'proposal_client'), namespace='proposal_client')),
    path('client/invoices/', include(('invoiceApp.urls_client', 'invoice_client'), namespace='invoice_client')),
    path('client/projects/', include(('projectApp.urls_client', 'project_client'), namespace='project_client')),
    path('client/tickets/', include(('ticketApp.urls_client', 'ticket_client'), namespace='ticket_client')),
]

### CompanyApp
app_name = "company_client"

urlpatterns = [
    path('company/<int:pk>/', views.view_my_company_detail, name='my_company_detail'),
]

app_name = "company_staff"

urlpatterns = [
    path('', views.company_home, name="company_home"),
    path('company/<int:pk>/', views.view_company_detail, name='company_detail'),
    path('company/<int:pk>/edit', views.edit_company, name='edit_company_detail'),
    path('add/', views.add_company, name="add_company"),
    path("ajax/primary/<int:pk>/", views.ajax_primary_contact, name="ajax_primary_contact"),
]

### InvoiceApp
app_name = "invoice_client"

urlpatterns = [
    # path('', views.view_all_client_invoices, name='view_all_client_invoices'),
]

app_name = "invoice_staff"

urlpatterns = [
    path('', views.invoice_home, name='invoice_home'),
]

### ProjectApp
app_name = "project_client"

urlpatterns = [
    # path('', views.view_all_client_projects, name='view_all_client_projects'),
]

app_name = "projects_staff"

urlpatterns = [
    # path('', views.project_home, name='project_home'),
]

### ProposalApp
app_name = "proposal_client"

urlpatterns = [
    path('', views.view_all_client_proposals, name='view_all_client_proposals'),
]

app_name = "proposal_public"

urlpatterns = [
    path("p/<slug:token>/", views.public_proposal_view, name="proposal_public_view"),
    path("p/<slug:token>/sign/", public.public_proposal_sign, name="proposal_public_sign"),
    path("invite/<str:token>/", redeem_invite_and_register, name="proposal_account_invite"),

]

app_name = "proposal_staff"

urlpatterns = [
    path('', views.proposal_home, name='proposal_home'),
    path('draft/new/', views.create_new_draft, name='create_new_draft'),
    path('draft/<int:pk>/', views.view_draft_detail, name='draft_detail'),
    path('draft/<int:pk>/edit/', views.edit_proposal_draft, name="draft_edit"),
    path('proposal/<int:pk>/', views.view_proposal_detail, name="proposal_detail"),
    path("proposal/<int:pk>/pdf/generate/", views.generate_proposal_pdf_view, name="proposal_generate_pdf"),
    path("proposal/<int:pk>/pdf/", views.view_proposal_pdf, name="proposal_pdf"),
    path("proposals/<int:pk>/send/", views.send_proposal, name="proposal_send"),
]

### ProspectApp
app_name = "prospects"

urlpatterns = [
    path('new', views.add_prospect, name="add_prospect"),
    path('<int:pk>', views.view_prospect, name="view_one_prospect"),
    path("<int:pk>/edit/", views.edit_prospect, name="prospect_edit"),
    path("<int:pk>/status/", views.update_prospect_status, name="prospect_status"),
]

### TicketApp
app_name = "ticket_client"

urlpatterns = [
    # path('', views.view_all_client_tickets, name='view_all_client_tickets'),
]

app_name = "ticket_staff"

urlpatterns = [
    # path('', views.ticket_admin, name='ticket_admin'),
]

### TimeApp
app_name = "timeApp"

urlpatterns = [
    # path("", , name=""),

]

### UserApp
app_name = "userApp"

urlpatterns = [
    #  || General Links ||
    path("", PortalLogin.as_view(), name="login"),
    path("post-login/", post_login, name="post_login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # || Staff/Employee Links ||
    path("staff/", staff_home, name="staff_home"), # redirects to admin
    path("employee/", employee_home, name="employee_home"),
    path("employee/profile/", view_employee_profile, name="view_employee_profile"),
    path("team/", view_all_staff, name="view_all_staff"),
    path("team/add/", add_staff, name="add_staff"),
    path("team/<int:pk>/", view_staff_profile, name="profile_detail"),
    path("team/<int:pk>/edit", edit_staff_profile, name="edit_staff_profile"),
    path("clients/", view_all_clients, name="view_all_clients"),
    path("clients/<int:pk>/", view_client_profile, name="client_profile_staff"),

    # || Client Links ||
    path("client/", client_home, name="client_home"),
    path("client/profile/", view_client_profile, name="client_profile_me"),
    
]
