from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear cached report files from Redis."

    def handle(self, *args, **options):
        deleted = 0
        prefixes = [
            "report:pdf:equipment:",
            "report:xlsx:equipment:",
            "report:pdf:stock:",
            "report:xlsx:stock:",
            "report:pdf:unit:",
            "report:xlsx:unit:",
            "report:pdf:region:",
            "report:xlsx:region:",
            "report:pdf:dpu:",
            "report:xlsx:dpu:",
        ]

        try:
            redis_client = cache.client.get_client(write=True)
        except AttributeError:
            self.stdout.write(
                self.style.WARNING(
                    "Cache backend does not support key pattern deletes. "
                    "Use cache.clear() manually."
                )
            )
            return

        for prefix in prefixes:
            keys = redis_client.keys(f"*{prefix}*")
            if keys:
                redis_client.delete(*keys)
                deleted += len(keys)

        self.stdout.write(self.style.SUCCESS(f"Cleared {deleted} cached report keys."))
