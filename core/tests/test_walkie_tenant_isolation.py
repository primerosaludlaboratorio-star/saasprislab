from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.test import SimpleTestCase

from core.consumers import WalkieTalkieConsumer


class WalkieTenantIsolationTests(SimpleTestCase):
    def test_room_group_is_namespaced_by_empresa(self):
        self.assertEqual(
            WalkieTalkieConsumer.build_room_group_name(7, "farmacia"),
            "walkie_t7_farmacia",
        )
        self.assertNotEqual(
            WalkieTalkieConsumer.build_room_group_name(7, "farmacia"),
            WalkieTalkieConsumer.build_room_group_name(8, "farmacia"),
        )

    def test_room_name_is_normalized_and_restricted(self):
        self.assertEqual(
            WalkieTalkieConsumer.build_room_group_name(7, " Farmacia "),
            "walkie_t7_farmacia",
        )
        with self.assertRaises(ValueError):
            WalkieTalkieConsumer.build_room_group_name(7, "farmacia/otro")

    async def test_connect_without_tenant_is_rejected(self):
        consumer = WalkieTalkieConsumer(
            {
                "url_route": {"kwargs": {"room_name": "farmacia"}},
            }
        )
        consumer.scope = {
            "url_route": {"kwargs": {"room_name": "farmacia"}},
            "user": SimpleNamespace(
            is_anonymous=False,
            empresa_id=None,
            id=10,
            ),
        }
        consumer.close = AsyncMock()
        consumer.channel_layer = SimpleNamespace(group_add=AsyncMock())

        await consumer.connect()

        consumer.close.assert_awaited_once_with()
        consumer.channel_layer.group_add.assert_not_awaited()
