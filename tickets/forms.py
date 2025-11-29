from django import forms
from .models import Ticket
from accounts.models import Department, CustomUser


class CreateTicketForm(forms.ModelForm):
    """
    نموذج إنشاء طلب جديد
    """
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='الأقسام المعنية',
        help_text='اختر قسماً واحداً أو أكثر',
        required=True
    )
    
    assigned_to_users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(role__in=['employee', 'head', 'dean']),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='المعينون لهم',
        help_text='اختر موظفاً واحداً أو أكثر',
        required=True
    )
    
    attachment = forms.FileField(
        required=False,
        label='مرفق',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
        })
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'departments', 'assigned_to_users', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان الطلب',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'وصف تفصيلي للطلب',
                'required': True
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }
        labels = {
            'title': 'العنوان',
            'description': 'الوصف',
            'priority': 'الأولوية',
        }


class CloseTicketForm(forms.Form):
    """
    نموذج إغلاق الطلب - يتطلب معلومات إلزامية
    """
    close_notes = forms.CharField(
        label='ما الذي تم عمله؟',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'يرجى تفصيل الإجراءات المتخذة لحل هذا الطلب...',
            'required': True
        }),
        help_text='هذا الحقل إلزامي - يجب توضيح الإجراءات المتخذة'
    )
    
    execution_time = forms.CharField(
        label='الوقت المستغرق',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثال: ساعتين، يوم واحد',
            'required': True
        }),
        help_text='الوقت الذي استغرقه تنفيذ الطلب'
    )
    
    close_attachments = forms.FileField(
        label='مرفقات (اختياري)',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
        }),
        help_text='يمكنك إرفاق صور أو مستندات توضح العمل المنجز'
    )
    
    def clean_close_notes(self):
        notes = self.cleaned_data.get('close_notes')
        if len(notes) < 20:
            raise forms.ValidationError('يجب أن يكون الوصف 20 حرفاً على الأقل')
        return notes


class AcknowledgeTicketForm(forms.Form):
    """
    نموذج تأكيد استلام الطلب
    """
    ticket_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True
    )


class CommentForm(forms.Form):
    """
    نموذج إضافة تعليق على الطلب
    """
    comment = forms.CharField(
        label='إضافة تعليق',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'اكتب تعليقك هنا...',
            'required': True
        }),
        min_length=5,
        error_messages={
            'required': 'يرجى كتابة تعليق',
            'min_length': 'التعليق قصير جداً'
        }
    )
