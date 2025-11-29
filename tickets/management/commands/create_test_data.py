from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import Department, CustomUser
from tickets.models import Ticket, TicketAction


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للنظام'

    def handle(self, *args, **kwargs):
        self.stdout.write('جاري إنشاء البيانات التجريبية...\n')

        # إنشاء الأقسام
        departments = [
            Department.objects.get_or_create(name='المالية', description='قسم الشؤون المالية')[0],
            Department.objects.get_or_create(name='التسجيل', description='قسم التسجيل والقبول')[0],
            Department.objects.get_or_create(name='الحاسبة الإلكترونية', description='قسم علوم الحاسوب')[0],
            Department.objects.get_or_create(name='الموارد البشرية', description='قسم شؤون الموظفين')[0],
            Department.objects.get_or_create(name='الصيانة', description='قسم الصيانة والخدمات')[0],
        ]
        self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(departments)} قسم'))

        # إنشاء المستخدمين
        # رئيس الجامعة
        president, _ = CustomUser.objects.get_or_create(
            username='president',
            defaults={
                'first_name': 'محمد',
                'last_name': 'الرئيس',
                'email': 'president@university.edu',
                'role': 'president',
                'is_staff': True,
            }
        )
        president.set_password('password123')
        president.save()
        self.stdout.write(self.style.SUCCESS('✓ تم إنشاء حساب رئيس الجامعة (username: president, password: password123)'))

        # عميد
        dean, _ = CustomUser.objects.get_or_create(
            username='dean',
            defaults={
                'first_name': 'أحمد',
                'last_name': 'العميد',
                'email': 'dean@university.edu',
                'role': 'dean',
                'department': departments[2],
                'is_staff': True,
            }
        )
        dean.set_password('password123')
        dean.save()
        self.stdout.write(self.style.SUCCESS('✓ تم إنشاء حساب العميد (username: dean, password: password123)'))

        # رؤساء أقسام
        heads = []
        for i, dept in enumerate(departments[:3]):
            head, _ = CustomUser.objects.get_or_create(
                username=f'head{i+1}',
                defaults={
                    'first_name': f'رئيس{i+1}',
                    'last_name': dept.name,
                    'email': f'head{i+1}@university.edu',
                    'role': 'head',
                    'department': dept,
                    'is_staff': True,
                }
            )
            head.set_password('password123')
            head.save()
            heads.append(head)
        self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(heads)} رئيس قسم'))

        # موظفون
        employees = []
        for i, dept in enumerate(departments):
            for j in range(2):  # موظفان لكل قسم
                emp, _ = CustomUser.objects.get_or_create(
                    username=f'emp{i}{j}',
                    defaults={
                        'first_name': f'موظف{i}{j}',
                        'last_name': dept.name,
                        'email': f'emp{i}{j}@university.edu',
                        'role': 'employee',
                        'department': dept,
                    }
                )
                emp.set_password('password123')
                emp.save()
                employees.append(emp)
        self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(employees)} موظف'))

        # إنشاء طلبات تجريبية
        now = timezone.now()
        
        tickets_data = [
            {
                'title': 'طلب صيانة مختبر الحاسوب',
                'description': 'توجد مشكلة في أجهزة المختبر رقم 3، يرجى الصيانة العاجلة',
                'priority': 'urgent',
                'department': departments[4],
                'assigned_to': employees[8],
                'created_by': dean,
                'status': 'in_progress',
                'days_ago': 1,
            },
            {
                'title': 'طلب كشف درجات',
                'description': 'الطالب يحتاج كشف درجات معتمد من قسم التسجيل',
                'priority': 'normal',
                'department': departments[1],
                'assigned_to': employees[2],
                'created_by': president,
                'status': 'pending_ack',
                'days_ago': 0,
            },
            {
                'title': 'مشكلة في نظام الرواتب',
                'description': 'لم يتم صرف الراتب للموظف الجديد، يرجى المتابعة',
                'priority': 'critical',
                'department': departments[0],
                'assigned_to': employees[0],
                'created_by': heads[2],
                'status': 'violated',  # متأخر عن الموعد
                'days_ago': 3,
            },
            {
                'title': 'طلب تحديث بيانات موظف',
                'description': 'تحديث معلومات الاتصال والعنوان',
                'priority': 'normal',
                'department': departments[3],
                'assigned_to': employees[6],
                'created_by': employees[4],
                'status': 'resolved',
                'days_ago': 5,
            },
            {
                'title': 'طلب شراء معدات جديدة',
                'description': 'يحتاج القسم لشراء 10 أجهزة كمبيوتر جديدة',
                'priority': 'normal',
                'department': departments[0],
                'assigned_to': employees[1],
                'created_by': heads[0],
                'status': 'in_progress',
                'days_ago': 2,
            },
        ]

        for ticket_data in tickets_data:
            days_ago = ticket_data.pop('days_ago')
            created_at = now - timedelta(days=days_ago)
            
            ticket, created = Ticket.objects.get_or_create(
                title=ticket_data['title'],
                defaults={
                    **ticket_data,
                    'created_at': created_at,
                }
            )
            
            if created:
                # تعديل تاريخ الإنشاء يدوياً
                ticket.created_at = created_at
                
                # حساب SLA deadline
                if ticket.priority == 'critical':
                    ticket.sla_deadline = created_at + timedelta(hours=2)
                elif ticket.priority == 'urgent':
                    ticket.sla_deadline = created_at + timedelta(hours=4)
                else:
                    ticket.sla_deadline = created_at + timedelta(hours=24)
                
                ticket.save()
                
                # إنشاء سجل الإجراء
                TicketAction.objects.create(
                    ticket=ticket,
                    action_type='created',
                    user=ticket.created_by,
                    notes='تم إنشاء الطلب',
                    created_at=created_at
                )

        self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(tickets_data)} طلب تجريبي'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('✓ اكتمل إنشاء البيانات التجريبية بنجاح!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write('\nمعلومات الدخول:')
        self.stdout.write('  - رئيس الجامعة: username=president, password=password123')
        self.stdout.write('  - العميد: username=dean, password=password123')
        self.stdout.write('  - رئيس قسم: username=head1, password=password123')
        self.stdout.write('  - موظف: username=emp00, password=password123')
