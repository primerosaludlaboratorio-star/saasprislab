import io
from unittest.mock import patch

from django.test import SimpleTestCase

from config.storage_backends import GoogleDriveStorage


class _FakeExecute:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeFilesResource:
    def __init__(self):
        self.create_calls = []
        self.list_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return _FakeExecute({'id': 'file-123', 'name': 'demo.txt', 'webViewLink': 'https://example.com'})

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return _FakeExecute({'files': []})


class _FakePermissionsResource:
    def __init__(self):
        self.create_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return _FakeExecute({})


class _FakeDriveService:
    def __init__(self):
        self.files_resource = _FakeFilesResource()
        self.permissions_resource = _FakePermissionsResource()

    def files(self):
        return self.files_resource

    def permissions(self):
        return self.permissions_resource


class GoogleDriveStorageSecurityTests(SimpleTestCase):
    def test_save_does_not_make_file_public_and_supports_all_drives(self):
        storage = GoogleDriveStorage(credentials=object(), folder_id='root-folder')
        storage._service = _FakeDriveService()

        with patch.object(storage, '_get_or_create_folder_path', return_value='parent-folder'):
            saved_name = storage._save('tenant/resultados/demo.txt', io.BytesIO(b'hello'))

        self.assertEqual(saved_name, 'tenant/resultados/demo.txt')
        self.assertEqual(len(storage.service.permissions().create_calls), 0)
        self.assertTrue(storage.service.files().create_calls)
        self.assertTrue(storage.service.files().create_calls[0]['supportsAllDrives'])

    def test_find_folder_searches_across_shared_drives(self):
        storage = GoogleDriveStorage(credentials=object(), folder_id='root-folder')
        storage._service = _FakeDriveService()

        storage._find_folder('tenant', 'root-folder')

        self.assertTrue(storage.service.files().list_calls)
        call = storage.service.files().list_calls[0]
        self.assertEqual(call['corpora'], 'allDrives')
        self.assertTrue(call['supportsAllDrives'])
        self.assertTrue(call['includeItemsFromAllDrives'])
