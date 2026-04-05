from django.core.management.base import BaseCommand
from equipment.tasks import refresh_report_counts, prewarm_all_reports

class Command(BaseCommand):
    help = "Manually trigger background report pre-warming tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run tasks synchronously (blocking) instead of background async.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore Redis task locks and force execution.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Triggering report counts refresh..."))
        
        if options["sync"]:
            # Run local (good for debugging)
            refresh_report_counts(ignore_lock=options["force"])
            self.stdout.write(self.style.NOTICE("Triggering all report pre-warming (sync)..."))
            prewarm_all_reports()
        else:
            # Run background (correct way for production)
            refresh_report_counts.apply_async(kwargs={"ignore_lock": options["force"]})
            self.stdout.write(self.style.NOTICE("Triggering all report pre-warming (background queue)..."))
            prewarm_all_reports.delay()

        self.stdout.write(self.style.SUCCESS("Successfully dispatched pre-warm tasks to Celery!"))
        self.stdout.write(self.style.WARNING("Note: With 50M rows, this may take several minutes to complete."))
