from unittest.mock import Mock

from Data_Ingestion.Synchronisation import SyncService


def test_sync_service_instantiation():

    service = SyncService()

    assert service is not None


def test_sync_service_contains_youtube_service():

    service = SyncService()

    assert service.youtube_service is not None
