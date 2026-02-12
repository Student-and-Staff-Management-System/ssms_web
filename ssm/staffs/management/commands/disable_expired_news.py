from django.core.management.base import BaseCommand
from django.utils import timezone
from staffs.models import News


class Command(BaseCommand):
    help = 'Disable news items that have passed their end date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be disabled without actually disabling',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find active news that have passed their end date
        expired_news = News.objects.filter(
            is_active=True,
            end_date__lt=today
        )
        
        count = expired_news.count()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would disable {count} expired news item(s)')
            )
            for news in expired_news:
                self.stdout.write(f'  - {news.content[:50]}... (end date: {news.end_date})')
        else:
            expired_news.update(is_active=False)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully disabled {count} expired news item(s)')
            )
