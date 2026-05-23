import uuid

import pytest
from apps.common.models import Record
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestBaseModelSoftDelete:
    def test_create_record_has_uuid_primary_key(self):
        record = Record.objects.create(title="Alpha")
        assert isinstance(record.id, uuid.UUID)
        assert record.is_deleted is False
        assert record.deleted_at is None

    def test_soft_delete_hides_from_default_manager(self):
        record = Record.objects.create(title="To Delete")
        record_id = record.id

        record.delete()

        assert Record.objects.filter(pk=record_id).exists() is False
        assert Record.all_objects.filter(pk=record_id).exists() is True

        deleted = Record.all_objects.get(pk=record_id)
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None

    def test_soft_delete_sets_deleted_by(self):
        user = User.objects.create_user(
            username="deleter",
            email="deleter@example.com",
            password="SecurePass123!",
        )
        record = Record.objects.create(title="Audited delete", created_by=user)

        record.delete(deleted_by=user)

        deleted = Record.all_objects.get(pk=record.id)
        assert deleted.deleted_by_id == user.pk

    def test_queryset_delete_soft_deletes_multiple(self):
        Record.objects.create(title="One")
        Record.objects.create(title="Two")
        assert Record.objects.count() == 2

        Record.objects.filter(title__in=["One", "Two"]).delete()

        assert Record.objects.count() == 0
        assert Record.all_objects.count() == 2
        assert Record.all_objects.filter(is_deleted=True).count() == 2

    def test_hard_delete_removes_permanently(self):
        record = Record.objects.create(title="Gone")
        record_id = record.id

        record.hard_delete()

        assert Record.all_objects.filter(pk=record_id).exists() is False

    def test_restore_brings_back_to_default_manager(self):
        record = Record.objects.create(title="Restorable")
        record.delete()
        assert Record.objects.filter(pk=record.id).exists() is False

        record.restore()

        assert Record.objects.filter(pk=record.id).exists() is True
        restored = Record.objects.get(pk=record.id)
        assert restored.is_deleted is False
        assert restored.deleted_at is None
        assert restored.deleted_by is None

    def test_updated_at_changes_on_save(self):
        record = Record.objects.create(title="Timestamped")
        original_updated = record.updated_at

        record.title = "Updated"
        record.save()

        record.refresh_from_db()
        assert record.updated_at >= original_updated

    def test_all_objects_includes_active_and_deleted(self):
        active = Record.objects.create(title="Active")
        deleted = Record.objects.create(title="Deleted")
        deleted.delete()

        assert Record.objects.count() == 1
        assert Record.all_objects.count() == 2
        ids = set(Record.all_objects.values_list("id", flat=True))
        assert active.id in ids
        assert deleted.id in ids
