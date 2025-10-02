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