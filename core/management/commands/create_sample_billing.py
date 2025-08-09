from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.models import Subscription, BillingHistory


class Command(BaseCommand):
    help = 'Create sample subscription and billing data for testing the profile page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to create subscription for (default: admin)'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist. Please create the user first.')
            )
            return

        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'plan_type': Subscription.PlanType.MONTHLY,
                'status': Subscription.Status.ACTIVE,
                'payment_method': 'Credit Card (**** 4242)',
                'amount': Decimal('9.99'),
                'currency': 'USD',
                'started_at': timezone.now() - timedelta(days=30),
                'next_billing_date': timezone.now() + timedelta(days=30),
                'stripe_customer_id': 'cus_sample123',
                'stripe_subscription_id': 'sub_sample123'
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created subscription for user "{username}"')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Subscription already exists for user "{username}"')
            )

        # Create sample billing history
        sample_invoices = [
            {
                'invoice_number': 'INV-2024-001',
                'amount': Decimal('9.99'),
                'description': 'Monthly Pro Plan - December 2024',
                'invoice_date': timezone.now() - timedelta(days=30),
                'paid_at': timezone.now() - timedelta(days=30),
            },
            {
                'invoice_number': 'INV-2024-002',
                'amount': Decimal('9.99'),
                'description': 'Monthly Pro Plan - January 2025',
                'invoice_date': timezone.now() - timedelta(days=1),
                'paid_at': timezone.now() - timedelta(days=1),
            },
            {
                'invoice_number': 'INV-2024-003',
                'amount': Decimal('9.99'),
                'description': 'Monthly Pro Plan - February 2025',
                'invoice_date': timezone.now() + timedelta(days=29),
                'paid_at': None,  # Future invoice
                'status': BillingHistory.Status.PENDING
            }
        ]

        created_invoices = 0
        for invoice_data in sample_invoices:
            invoice, created = BillingHistory.objects.get_or_create(
                user=user,
                invoice_number=invoice_data['invoice_number'],
                defaults={
                    'subscription': subscription,
                    'amount': invoice_data['amount'],
                    'currency': 'USD',
                    'status': invoice_data.get('status', BillingHistory.Status.PAID),
                    'payment_method': 'Credit Card (**** 4242)',
                    'description': invoice_data['description'],
                    'invoice_date': invoice_data['invoice_date'],
                    'paid_at': invoice_data['paid_at'],
                    'stripe_invoice_id': f'in_sample_{invoice_data["invoice_number"][-3:]}',
                    'invoice_pdf_url': f'https://invoice.stripe.com/sample_{invoice_data["invoice_number"][-3:]}'
                }
            )
            
            if created:
                created_invoices += 1

        if created_invoices > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_invoices} sample invoices')
            )
        else:
            self.stdout.write(
                self.style.WARNING('All sample invoices already exist')
            )

        # Update user profile to Pro status
        user.profile.is_pro = True
        user.profile.pro_expiry_date = timezone.now() + timedelta(days=365)
        user.profile.save()

        self.stdout.write(
            self.style.SUCCESS(f'Updated user "{username}" to Pro status')
        )
        self.stdout.write(
            self.style.SUCCESS('Sample data creation completed! You can now test the profile page.')
        ) 