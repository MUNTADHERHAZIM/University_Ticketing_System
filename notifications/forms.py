from django import forms
from .models import Notification

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'notification_type', 'ticket']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العنوان'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'الرسالة'}),
            'notification_type': forms.Select(attrs={'class': 'form-select'}),
            'ticket': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'العنوان',
            'message': 'الرسالة',
            'notification_type': 'نوع الإشعار',
            'ticket': 'الطلب (اختياري)',
        }
