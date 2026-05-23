from django.core.management.base import BaseCommand
from examples.demo_config import DEMO_ADMIN
from services.demo import DemoSeedService


class Command(BaseCommand):
    help = "Seed two demo tenants and a Tenant One admin user for local development."

    def handle(self, *args, **options):
        result = DemoSeedService.seed()

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("")
        self.stdout.write("Tenants:")
        for tenant in result.tenants:
            self.stdout.write(f"  - {tenant.name} (slug={tenant.slug}, id={tenant.id})")
        self.stdout.write("")
        self.stdout.write("Demo admin (Tenant One):")
        self.stdout.write(f"  username: {DEMO_ADMIN.username}")
        self.stdout.write(f"  password: {DEMO_ADMIN.password}")
        self.stdout.write("")
        self.stdout.write("Next: open http://localhost:8000/api/docs/ and try the demo examples.")
