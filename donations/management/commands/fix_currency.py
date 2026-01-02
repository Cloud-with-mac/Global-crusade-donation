# File: donations/management/commands/fix_currency.py
# Run with: python manage.py fix_currency

from django.core.management.base import BaseCommand
from donations.models import Donation


class Command(BaseCommand):
    help = 'Fix currency for existing donations based on amount ranges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--ngn-threshold',
            type=float,
            default=5000,
            help='Amounts above this are considered NGN (default: 5000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['ngn_threshold']

        self.stdout.write(self.style.WARNING(f'\nCurrency Fix Script'))
        self.stdout.write(f'NGN threshold: amounts > {threshold:,.2f}')
        self.stdout.write(f'Dry run: {dry_run}\n')

        donations = Donation.objects.all()

        ngn_count = 0
        usd_count = 0

        for donation in donations:
            old_currency = donation.currency

            # Determine currency based on amount
            # Large amounts (> threshold) are likely NGN
            if donation.amount > threshold:
                new_currency = 'NGN'
            else:
                new_currency = 'USD'

            if old_currency != new_currency or old_currency == 'USD':
                self.stdout.write(
                    f'  Donation #{donation.id}: {donation.donor.full_name} - '
                    f'{donation.amount:,.2f} -> {new_currency}'
                )

                if new_currency == 'NGN':
                    ngn_count += 1
                else:
                    usd_count += 1

                if not dry_run:
                    donation.currency = new_currency
                    donation.save()

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('Changes applied!'))

        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  NGN donations: {ngn_count}')
        self.stdout.write(f'  USD donations: {usd_count}')
        self.stdout.write('')
