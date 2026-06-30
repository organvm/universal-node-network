import pytest
from datetime import datetime, timedelta

from src.discovery import DiscoveryAnnouncement, DiscoveryService
from src.node import Node, NodeCapability, NodeStatus

def test_discovery_announcement_is_expired():
    # Not expired
    ann = DiscoveryAnnouncement(
        node_id="node-1",
        organ="core",
        endpoint="http://localhost:8000",
        capabilities=["cap1"],
        ttl_seconds=300
    )
    assert not ann.is_expired()

    # Expired
    ann.timestamp = datetime.now() - timedelta(seconds=301)
    assert ann.is_expired()

def test_discovery_service_init():
    service = DiscoveryService()
    assert service._announcements == {}
    assert service._known_nodes == {}
    assert service.active_count == 0

def test_discovery_service_announce_new_node():
    service = DiscoveryService()
    ann = DiscoveryAnnouncement(
        node_id="node-1",
        organ="core",
        endpoint="http://localhost:8000",
        capabilities=["cap1", "cap2"]
    )
    
    node = service.announce(ann)
    
    assert node.node_id == "node-1"
    assert node.organ == "core"
    assert node.endpoint == "http://localhost:8000"
    assert node.has_capability("cap1")
    assert node.has_capability("cap2")
    assert node.status == NodeStatus.ONLINE
    
    assert service.active_count == 1
    assert service._announcements["node-1"] == ann
    assert service._known_nodes["node-1"] == node

def test_discovery_service_announce_existing_node():
    service = DiscoveryService()
    ann1 = DiscoveryAnnouncement(
        node_id="node-1",
        organ="core",
        endpoint="http://localhost:8000",
        capabilities=["cap1"]
    )
    
    node1 = service.announce(ann1)
    
    ann2 = DiscoveryAnnouncement(
        node_id="node-1",
        organ="core",
        endpoint="http://localhost:8000",
        capabilities=["cap1"]
    )
    node2 = service.announce(ann2)
    
    assert node1 is node2
    assert service.active_count == 1

def test_discovery_service_find_peers():
    service = DiscoveryService()
    
    service.announce(DiscoveryAnnouncement(node_id="node-1", organ="core", endpoint="e1", capabilities=["cap1"]))
    service.announce(DiscoveryAnnouncement(node_id="node-2", organ="edge", endpoint="e2", capabilities=["cap2"]))
    service.announce(DiscoveryAnnouncement(node_id="node-3", organ="core", endpoint="e3", capabilities=["cap1", "cap2"]))
    
    # Find by organ
    core_peers = service.find_peers(organ="core")
    assert len(core_peers) == 2
    assert set(n.node_id for n in core_peers) == {"node-1", "node-3"}
    
    # Find by capability
    cap2_peers = service.find_peers(capability="cap2")
    assert len(cap2_peers) == 2
    assert set(n.node_id for n in cap2_peers) == {"node-2", "node-3"}
    
    # Find by both
    core_cap2_peers = service.find_peers(organ="core", capability="cap2")
    assert len(core_cap2_peers) == 1
    assert core_cap2_peers[0].node_id == "node-3"
    
    # Find all online
    all_peers = service.find_peers()
    assert len(all_peers) == 3
    
    # If a node goes offline, it shouldn't be found
    service._known_nodes["node-1"].go_offline()
    assert len(service.find_peers(organ="core")) == 1

def test_discovery_service_prune_expired():
    service = DiscoveryService()
    
    ann1 = DiscoveryAnnouncement(node_id="node-1", organ="core", endpoint="e1", capabilities=["cap1"])
    ann2 = DiscoveryAnnouncement(node_id="node-2", organ="edge", endpoint="e2", capabilities=["cap2"])
    
    service.announce(ann1)
    service.announce(ann2)
    
    assert service.active_count == 2
    
    # Manually expire ann1
    service._announcements["node-1"].timestamp = datetime.now() - timedelta(seconds=400)
    
    pruned_count = service.prune_expired()
    assert pruned_count == 1
    assert service.active_count == 1
    assert "node-1" not in service._announcements
    assert service._known_nodes["node-1"].status == NodeStatus.OFFLINE
    
    # Node-2 should still be fine
    assert "node-2" in service._announcements
    assert service._known_nodes["node-2"].status == NodeStatus.ONLINE

def test_lens_discovery_discover_lenses():
    from src.discovery import LensDiscovery
    ld = LensDiscovery()
    
    # We will pass a basic task description, assembly will return something.
    lenses = ld.discover_lenses("Some task description", max_lenses=1)
    assert isinstance(lenses, list)

def test_lens_discovery_discover_by_category():
    from src.discovery import LensDiscovery
    ld = LensDiscovery()
    
    lenses = ld.discover_by_category("tooling")
    assert isinstance(lenses, list)
    
    # Test invalid category
    invalid_lenses = ld.discover_by_category("invalid_category")
    assert invalid_lenses == []

def test_lens_discovery_discover_by_stratum():
    from src.discovery import LensDiscovery
    ld = LensDiscovery()
    
    lenses = ld.discover_by_stratum("/boot/")
    assert isinstance(lenses, list)
    
    # Test invalid stratum
    invalid_lenses = ld.discover_by_stratum("/invalid/")
    assert invalid_lenses == []
