from .models import GlobalMail

def global_mails(request):
    return {
        'global_mails': GlobalMail.objects.all()[:5]
    }
