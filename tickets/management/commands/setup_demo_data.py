"""
سكربت إنشاء بيانات تجريبية شاملة
يشمل: الأقسام، المستخدمين، الطلبات، الإشعارات
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from accounts.models import Department, CustomUser
from tickets.models import Ticket, TicketAction, TicketAcknowledgment
from notifications.models import Notification


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية شاملة للنظام'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('بدء إنشاء البيانات التجريبية'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        # 1. إنشاء الأقسام
        departments = self.create_departments()
        
        # 2. إنشاء المستخدمين
        users = self.create_users(departments)
        
        # 3. إنشاء الطلبات
        tickets = self.create_tickets(users, departments)
        
        # 4. إنشاء الإشعارات
        self.create_notifications(users, tickets)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء جميع البيانات التجريبية بنجاح!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.print_credentials(users)

    def create_departments(self):
        self.stdout.write('\n📁 جاري إنشاء الأقسام والكليات...')
        
        departments_data = [
            {'name': 'كلية الفنون التطبيقية', 'description': 'كلية الفنون التطبيقية'},
            {'name': 'كلية العلوم', 'description': 'كلية العلوم'},
            {'name': 'كلية التقنيات الطبية والصحية', 'description': 'كلية التقنيات الطبية والصحية'},
            {'name': 'كلية هندسة الحاسوب', 'description': 'كلية هندسة الحاسوب'},
            {'name': 'كلية الصيدلة', 'description': 'كلية الصيدلة'},
            {'name': 'كلية الادارة والاقتصاد', 'description': 'كلية الإدارة والاقتصاد'},
            {'name': 'كلية القانون', 'description': 'كلية القانون'},
            {'name': 'قسم الدراسات والتخطيط', 'description': 'قسم الدراسات والتخطيط'},
            {'name': 'قسم الشؤون العلمية', 'description': 'قسم الشؤون العلمية'},
            {'name': 'قسم الموارد البشرية', 'description': 'قسم الموارد البشرية'},
            {'name': 'رئاسة الجامعة', 'description': 'رئاسة الجامعة'},
            {'name': 'قسم ضمان الجودة والاعتماد الأكاديمي', 'description': 'قسم ضمان الجودة والاعتماد الأكاديمي'},
            {'name': 'قسم العلاقات والاعلام', 'description': 'قسم العلاقات والإعلام'},
            {'name': 'قسم الحاسبة الالكترونية', 'description': 'قسم الحاسبة الإلكترونية'},
        ]
        
        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={'description': dept_data['description']}
            )
            departments[dept_data['name']] = dept
            status = '✓ تم إنشاء' if created else '• موجود'
            self.stdout.write(f'  {status}: {dept.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n  ✅ إجمالي الأقسام: {len(departments)}'))
        return departments

    def create_users(self, departments):
        self.stdout.write('\n👥 جاري إنشاء المستخدمين...')
        
        users_data = [
            # العمداء (أ.د) - Deans
            {
                'username': 'abdulkareem',
                'first_name': 'عبدالكريم',
                'last_name': 'عبود عودة',
                'email': 'abdulkareem@uoalknooz.edu.iq',
                'role': 'dean',
                'department': 'كلية الفنون التطبيقية',
                'title': 'أ.د',
                'password': 'Dean@123'
            },
            {
                'username': 'azhar',
                'first_name': 'ازهار',
                'last_name': 'علي عبدالله',
                'email': 'azhar@uoalknooz.edu.iq',
                'role': 'dean',
                'department': 'كلية العلوم',
                'title': 'أ.د',
                'password': 'Dean@123'
            },
            {
                'username': 'kawthar',
                'first_name': 'كوثر',
                'last_name': 'هواز مهدي',
                'email': 'kawthar@uoalknooz.edu.iq',
                'role': 'dean',
                'department': 'كلية التقنيات الطبية والصحية',
                'title': 'أ.د',
                'password': 'Dean@123'
            },
            {
                'username': 'abdulmuhsin',
                'first_name': 'عبدالمحسن',
                'last_name': 'محسن عبدالله',
                'email': 'abdulmuhsin@uoalknooz.edu.iq',
                'role': 'dean',
                'department': 'كلية هندسة الحاسوب',
                'title': 'أ.د',
                'password': 'Dean@123'
            },
            # الموظفين (م.م) - Employees
            {
                'username': 'omar',
                'first_name': 'عمر',
                'last_name': 'وليد عاشور',
                'email': 'omar@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'كلية هندسة الحاسوب',
                'title': 'م.م',
                'password': 'User@123'
            },
            # رؤساء الأقسام (أ.م.د) - Heads
            {
                'username': 'ali_hadi',
                'first_name': 'علي',
                'last_name': 'محمد هادي',
                'email': 'ali.hadi@uoalknooz.edu.iq',
                'role': 'head',
                'department': 'كلية الصيدلة',
                'title': 'أ.م.د',
                'password': 'Head@123'
            },
            {
                'username': 'abdulali',
                'first_name': 'عبدالعالي',
                'last_name': 'حميد عبدالعالي',
                'email': 'abdulali@uoalknooz.edu.iq',
                'role': 'head',
                'department': 'كلية الادارة والاقتصاد',
                'title': 'أ.م.د',
                'password': 'Head@123'
            },
            {
                'username': 'sajjad',
                'first_name': 'سجاد',
                'last_name': 'عبدالحسين داود',
                'email': 'sajjad@uoalknooz.edu.iq',
                'role': 'head',
                'department': 'كلية القانون',
                'title': 'أ.م.د',
                'password': 'Head@123'
            },
            {
                'username': 'mohammed_hasan',
                'first_name': 'محمد',
                'last_name': 'عبدالإله حسن',
                'email': 'mohammed.hasan@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'قسم الدراسات والتخطيط',
                'title': 'م.م',
                'password': 'User@123'
            },
            {
                'username': 'salem',
                'first_name': 'سالم',
                'last_name': 'علي الجندي',
                'email': 'salem@uoalknooz.edu.iq',
                'role': 'head',
                'department': 'قسم الشؤون العلمية',
                'title': 'أ.م.د',
                'password': 'Head@123'
            },
            {
                'username': 'suhail',
                'first_name': 'سهيل',
                'last_name': 'نجم مشاري',
                'email': 'suhail@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'قسم الشؤون العلمية',
                'title': 'م.د',
                'password': 'User@123'
            },
            {
                'username': 'khadija',
                'first_name': 'خديجة',
                'last_name': '',
                'email': 'khadija@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'قسم الموارد البشرية',
                'title': '',
                'password': 'User@123'
            },
            # رئيس الجامعة
            {
                'username': 'yousef',
                'first_name': 'يوسف',
                'last_name': 'علي عبد مشاوي',
                'email': 'president@uoalknooz.edu.iq',
                'role': 'president',
                'department': 'رئاسة الجامعة',
                'title': 'أ.د',
                'password': 'President@123'
            },
            # مساعد رئيس الجامعة للشؤون العلمية
            {
                'username': 'miqdad',
                'first_name': 'مقداد',
                'last_name': 'عذاب موسى',
                'email': 'miqdad@uoalknooz.edu.iq',
                'role': 'academic_assistant',
                'department': 'رئاسة الجامعة',
                'title': 'أ.م.د',
                'password': 'Assistant@123'
            },
            # مساعد رئيس الجامعة للشؤون الإدارية
            {
                'username': 'fawzi',
                'first_name': 'فوزي',
                'last_name': '',
                'email': 'fawzi@uoalknooz.edu.iq',
                'role': 'admin_assistant',
                'department': 'رئاسة الجامعة',
                'title': 'د',
                'password': 'Assistant@123'
            },
            {
                'username': 'hiba',
                'first_name': 'هبة',
                'last_name': 'حسن الروضان',
                'email': 'hiba@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'قسم ضمان الجودة والاعتماد الأكاديمي',
                'title': 'م.م',
                'password': 'User@123'
            },
            # رئيس قسم الحاسبة الالكترونية
            {
                'username': 'muntadher',
                'first_name': 'منتظر',
                'last_name': 'حازم ثامر',
                'email': 'muntadher@uoalknooz.edu.iq',
                'role': 'head',
                'department': 'قسم الحاسبة الالكترونية',
                'title': 'م.م',
                'password': 'Head@123'
            },
            {
                'username': 'hassan',
                'first_name': 'حسن',
                'last_name': '',
                'email': 'hassan@uoalknooz.edu.iq',
                'role': 'employee',
                'department': 'قسم العلاقات والاعلام',
                'title': '',
                'password': 'User@123'
            },
        ]
        
        users = {}
        for user_data in users_data:
            dept = departments.get(user_data['department'])
            
            user, created = CustomUser.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email': user_data['email'],
                    'role': user_data['role'],
                    'department': dept,
                }
            )
            
            # Always set password
            user.set_password(user_data['password'])
            user.save()
            
            users[user_data['username']] = {
                'user': user,
                'password': user_data['password'],
                'title': user_data['title']
            }
            
            status = '✓ تم إنشاء' if created else '• تم تحديث'
            title = user_data.get('title', '')
            full_name = f"{title} {user_data['first_name']} {user_data['last_name']}".strip()
            self.stdout.write(f'  {status}: {full_name} ({user.get_role_display()})')
        
        # إنشاء مستخدم admin
        admin_user, admin_created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'مدير',
                'last_name': 'النظام',
                'email': 'admin@uoalknooz.edu.iq',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('Admin@123')
        admin_user.save()
        users['admin'] = {'user': admin_user, 'password': 'Admin@123', 'title': ''}
        
        self.stdout.write(self.style.SUCCESS(f'\n  ✅ إجمالي المستخدمين: {len(users)}'))
        return users

    def create_tickets(self, users, departments):
        self.stdout.write('\n📝 جاري إنشاء الطلبات التجريبية (مناسبة لكل قسم)...')

        DEMO_PREFIX = "[DEMO]"

        # تنظيف آمن: احذف فقط الطلبات التجريبية السابقة
        Ticket.objects.filter(title__startswith=DEMO_PREFIX).delete()

        # بنك طلبات حسب القسم
        dept_ticket_bank = {
            'قسم الحاسبة الالكترونية': [
                ('عطل في مختبر الحاسوب', 'يوجد عدد من الأجهزة لا يقلع، ونحتاج صيانة عاجلة لمختبر (3).', 'urgent'),
                ('تحديث منصة الاختبارات', 'نحتاج تفعيل خصائص منع الغش وتحديث لوحة التقارير قبل الامتحانات.', 'normal'),
                ('تحسين الشبكة والواي فاي', 'ضعف تغطية الشبكة في الطابق الثالث ويؤثر على الدروس العملية.', 'urgent'),
            ],
            'قسم العلاقات والاعلام': [
                ('تحديث أخبار الكلية', 'يرجى إضافة خبر الفعالية الأخيرة مع الصور على الموقع الرسمي.', 'normal'),
                ('تصميم بوستر فعالية', 'نحتاج بوستر بقياسات السوشيال + نسخة للطباعة للفعالية القادمة.', 'normal'),
            ],
            'قسم الموارد البشرية': [
                ('تدقيق أوامر إدارية', 'يرجى تدقيق أمر إداري لتكليف منتسبين وتحديث ملفاتهم.', 'normal'),
                ('استمارات بيانات الموظفين', 'نحتاج تعميم استمارة إلكترونية لتحديث بيانات الموظفين.', 'normal'),
            ],
            'قسم الشؤون العلمية': [
                ('تعميم جدول الامتحانات المشتركة', 'يرجى إعداد تعميم نهائي بمواد الامتحانات المشتركة والتوقيتات.', 'urgent'),
                ('متابعة متطلبات الاعتماد', 'نحتاج رفع تقارير المخرجات التعليمية والتوثيق للأقسام.', 'normal'),
            ],
            'قسم الدراسات والتخطيط': [
                ('تقرير إحصائي للأقسام', 'يرجى إعداد إحصائية محدثة بعدد الطلبة وأعضاء الهيئة التدريسية لكل قسم.', 'normal'),
                ('خطة تطوير البنية التحتية', 'نحتاج خطة أولية لتحسين القاعات والمختبرات للعام القادم.', 'normal'),
            ],
            'قسم ضمان الجودة والاعتماد الأكاديمي': [
                ('تدقيق ملفات الجودة', 'يرجى تدقيق نماذج الجودة للأقسام واستكمال النواقص.', 'urgent'),
                ('تحديث مؤشرات الأداء', 'نحتاج تحديث KPI الخاصة بالتقييمات والتقارير الفصلية.', 'normal'),
            ],
            'رئاسة الجامعة': [
                ('كتاب رسمي للمخاطبات', 'يرجى إعداد كتاب رسمي لمخاطبة الجهات ذات العلاقة بشأن موضوع إداري.', 'normal'),
                ('متابعة مشروع التحول الرقمي', 'نحتاج تحديث حالة المشروع وخطة تنفيذ مختصرة للاجتماع القادم.', 'urgent'),
            ],

            # كليات (طلبات تشغيلية)
            'كلية العلوم': [
                ('تجهيزات مختبرات', 'نحتاج مواد وتجهيزات للمختبرات العملية للأسبوع القادم.', 'urgent'),
                ('صيانة قاعة', 'القاعة (A101) تحتاج صيانة سبورة/إنارة.', 'normal'),
            ],
            'كلية الصيدلة': [
                ('تجهيز مختبر تحليلات', 'نحتاج تنظيم جدول استعمال المختبر وتوفير مستلزمات.', 'urgent'),
                ('دعم امتحان إلكتروني', 'نحتاج فريق دعم أثناء الامتحان الإلكتروني لضمان الاستقرار.', 'urgent'),
            ],
            'كلية الادارة والاقتصاد': [
                ('تحديث بيانات الأقسام', 'يرجى تحديث بيانات الأقسام والبرامج الدراسية على الموقع.', 'normal'),
            ],
            'كلية القانون': [
                ('تجهيز قاعة مناقشات', 'نحتاج حجز وتجهيز قاعة للمناقشات مع جهاز عرض.', 'normal'),
            ],
            'كلية التقنيات الطبية والصحية': [
                ('توفير مستلزمات مختبر', 'مستلزمات مختبرية ناقصة ويجب توفيرها سريعاً.', 'urgent'),
            ],
            'كلية هندسة الحاسوب': [
                ('تثبيت برامج هندسية', 'تثبيت MATLAB/Proteus على أجهزة المختبر للمقررات الجديدة.', 'normal'),
                ('صيانة أجهزة', 'عدد من الأجهزة يعاني من أعطال قرص/نظام تشغيل.', 'urgent'),
            ],
            'كلية الفنون التطبيقية': [
                ('تجهيز قاعة ورشة', 'نحتاج تجهيز قاعة الورش مع أدوات وإضاءة مناسبة.', 'normal'),
            ],
        }

        # Helpers
        def pick_creator_for_dept(dept_obj):
            candidates = [
                u['user'] for u in users.values()
                if getattr(u['user'], 'department_id', None) == dept_obj.id and u['user'].role in ['employee', 'head', 'dean']
            ]
            return random.choice(candidates) if candidates else None

        def pick_assignee_for_dept(dept_obj, exclude_user=None):
            # prefer head/employee within same dept
            candidates = [
                u['user'] for u in users.values()
                if getattr(u['user'], 'department_id', None) == dept_obj.id and u['user'].role in ['head', 'employee']
            ]
            if exclude_user:
                candidates = [c for c in candidates if c.id != exclude_user.id]
            if candidates:
                return random.choice(candidates)

            # fallback: any admin/assistant
            fallback = [
                u['user'] for u in users.values()
                if u['user'].role in ['admin', 'academic_assistant', 'admin_assistant', 'president']
            ]
            if exclude_user:
                fallback = [c for c in fallback if c.id != exclude_user.id]
            return random.choice(fallback) if fallback else exclude_user

        statuses = ['new', 'pending_ack', 'in_progress', 'closed']
        sla_hours = {'normal': 24, 'urgent': 6, 'critical': 2}

        tickets = []

        # أنشئ لكل قسم 2–4 طلبات (حسب وجوده في البنك)
        for dept_name, dept_obj in departments.items():
            bank = dept_ticket_bank.get(dept_name)
            if not bank:
                continue

            num = min(len(bank), random.randint(2, 4))
            samples = random.sample(bank, k=num)

            for (title, desc, priority) in samples:
                creator = pick_creator_for_dept(dept_obj)
                if not creator:
                    # fallback: أي مستخدم منشئ
                    creator_pool = [u['user'] for u in users.values() if u['user'].role in ['employee', 'head', 'dean']]
                    creator = random.choice(creator_pool) if creator_pool else None

                assigned = pick_assignee_for_dept(dept_obj, exclude_user=creator) if creator else None
                status = random.choice(statuses)

                days_ago = random.randint(0, 10)
                created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 12))
                sla_deadline = created_at + timedelta(hours=sla_hours.get(priority, 24))

                ticket = Ticket.objects.create(
                    title=f"{DEMO_PREFIX} {title}",
                    description=f"{desc}\n\n(طلب تجريبي لأغراض الاختبار فقط)",
                    priority=priority,
                    status=status,
                    created_by=creator,
                    assigned_to=assigned,
                    department=dept_obj,
                    sla_deadline=sla_deadline,
                )

                # M2M إن كانت موجودة عندك
                if hasattr(ticket, 'departments'):
                    ticket.departments.add(dept_obj)
                if hasattr(ticket, 'assigned_to_users') and assigned:
                    ticket.assigned_to_users.add(assigned)

                TicketAction.objects.create(
                    ticket=ticket,
                    user=creator if creator else assigned,
                    action_type='created',
                    notes='تم إنشاء الطلب (تجريبي)'
                )

                if status in ['pending_ack', 'in_progress', 'closed'] and assigned:
                    TicketAction.objects.create(
                        ticket=ticket,
                        user=assigned,
                        action_type='acknowledged',
                        notes='تم تأكيد استلام الطلب (تجريبي)'
                    )

                tickets.append(ticket)
                self.stdout.write(f'  ✓ {dept_name}: طلب #{ticket.id} - {title}')

        self.stdout.write(self.style.SUCCESS(f'\n  ✅ إجمالي الطلبات التجريبية: {len(tickets)}'))
        return tickets


    def create_notifications(self, users, tickets):
        self.stdout.write('\n🔔 جاري إنشاء الإشعارات...')
        
        # Delete existing notifications
        Notification.objects.all().delete()
        
        notification_types = [
            ('new_ticket', 'طلب جديد', 'تم إنشاء طلب جديد يحتاج اهتمامك'),
            ('ticket_assigned', 'تم تعيين طلب', 'تم تعيين طلب جديد لك'),
            ('deadline_approaching', 'اقتراب الموعد النهائي', 'موعد التسليم يقترب، يرجى الإسراع'),
            ('ticket_commented', 'تعليق جديد', 'تم إضافة تعليق على الطلب'),
        ]
        
        count = 0
        for username, user_data in users.items():
            user = user_data['user']
            if user.username == 'admin':
                continue
                
            # Create 2-3 notifications per user
            for _ in range(random.randint(2, 3)):
                ticket = random.choice(tickets) if tickets else None
                notif_type = random.choice(notification_types)
                
                Notification.objects.create(
                    user=user,
                    ticket=ticket,
                    notification_type=notif_type[0],
                    title=notif_type[1],
                    message=notif_type[2],
                    is_read=random.choice([True, False])
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ إجمالي الإشعارات: {count}'))

    def print_credentials(self, users):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📋 بيانات تسجيل الدخول:'))
        self.stdout.write('='*70)
        
        role_order = ['president', 'academic_assistant', 'dean', 'head', 'employee', 'admin']
        
        sorted_users = sorted(users.items(), 
                             key=lambda x: role_order.index(x[1]['user'].role) if x[1]['user'].role in role_order else 99)
        
        current_role = None
        for username, data in sorted_users:
            user = data['user']
            if user.role != current_role:
                current_role = user.role
                self.stdout.write(f'\n  [{user.get_role_display()}]')
            
            title = data['title']
            full_name = f"{title} {user.first_name} {user.last_name}".strip()
            dept_name = user.department.name if user.department else '-'
            self.stdout.write(f'    {full_name}')
            self.stdout.write(f'      اسم المستخدم: {username} | كلمة المرور: {data["password"]}')
            self.stdout.write(f'      القسم: {dept_name}')
        
        self.stdout.write('\n' + '='*70)
