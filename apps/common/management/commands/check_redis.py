from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify Redis connectivity via Django cache (REDIS_URL)."

    def handle(self, *args, **options):
        key = "mgmt:redis_ping"
        try:
            cache.set(key, "pong", timeout=10)
            value = cache.get(key)
            cache.delete(key)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Redis check failed: {exc}"))
            raise SystemExit(1) from exc

        if value != "pong":
            self.stderr.write(self.style.ERROR("Redis read/write mismatch."))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Redis OK (cache backend reachable)."))
