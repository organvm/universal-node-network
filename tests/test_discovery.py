from __future__ import annotations

from datetime import datetime, timedelta

from src.discovery import DiscoveryAnnouncement, DiscoveryService
from src.node import NodeStatus


def test_discovery_service_announces_new_node_and_tracks_activity() -> None:
    service = DiscoveryService()
    announcement = DiscoveryAnnouncement(
        node_id="node-1",
        organ="/boot/",
        endpoint="https://node1.local",
        capabilities=["routing", "telemetry"],
    )

    node = service.announce(announcement)

    assert node.node_id == "node-1"
    assert node.status == NodeStatus.ONLINE
    assert service.active_count == 1
    assert node.has_capability("routing")
    assert node.has_capability("telemetry")


def test_discovery_service_reannounces_existing_node_as_online() -> None:
    service = DiscoveryService()
    announcement = DiscoveryAnnouncement(
        node_id="node-2",
        organ="/dev/",
        endpoint="https://node2.local",
        capabilities=["analysis"],
    )

    node = service.announce(announcement)
    assert node.status == NodeStatus.ONLINE
    node.last_heartbeat = datetime(2000, 1, 1)

    renewed_node = service.announce(
        DiscoveryAnnouncement(
            node_id="node-2",
            organ="/dev/",
            endpoint="https://node2.local",
            capabilities=["analysis"],
        )
    )

    assert renewed_node is node
    assert renewed_node.status == NodeStatus.ONLINE
    assert renewed_node.last_heartbeat > datetime(2000, 1, 1)


def test_discovery_service_find_peers_filters_by_organ_and_capability() -> None:
    service = DiscoveryService()
    service.announce(
        DiscoveryAnnouncement(
            node_id="node-a",
            organ="/boot/",
            endpoint="https://boot.local",
            capabilities=["routing", "telemetry"],
        )
    )
    service.announce(
        DiscoveryAnnouncement(
            node_id="node-b",
            organ="/dev/",
            endpoint="https://dev.local",
            capabilities=["analysis", "routing"],
        )
    )

    boot_nodes = service.find_peers(organ="/boot/")
    assert len(boot_nodes) == 1
    assert boot_nodes[0].node_id == "node-a"

    routing_nodes = service.find_peers(capability="routing")
    assert {n.node_id for n in routing_nodes} == {"node-a", "node-b"}

    dev_routing_nodes = service.find_peers(organ="/dev/", capability="routing")
    assert len(dev_routing_nodes) == 1
    assert dev_routing_nodes[0].node_id == "node-b"

    offline_node = service.find_peers(organ="/dev/")
    offline_node[0].go_offline()
    assert service.find_peers(organ="/dev/") == []


def test_discovery_service_prune_expired_announcements_marks_nodes_offline() -> None:
    service = DiscoveryService()
    now = datetime.now()

    service.announce(
        DiscoveryAnnouncement(
            node_id="live-node",
            organ="/boot/",
            endpoint="https://live.local",
            capabilities=["routing"],
            timestamp=now,
            ttl_seconds=300,
        )
    )
    service.announce(
        DiscoveryAnnouncement(
            node_id="stale-node",
            organ="/dev/",
            endpoint="https://stale.local",
            capabilities=["analysis"],
            timestamp=now - timedelta(minutes=10),
            ttl_seconds=60,
        )
    )

    pruned = service.prune_expired()

    assert pruned == 1
    assert service.active_count == 1
    assert service.find_peers() == [n for n in service.find_peers() if n.node_id == "live-node"]
    assert service._known_nodes["stale-node"].status == NodeStatus.OFFLINE
