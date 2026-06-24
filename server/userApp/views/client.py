from django.http import HttpResponse







def accept_invite(request, token):
    return HttpResponse("Invite received. Client signup flow coming next.")