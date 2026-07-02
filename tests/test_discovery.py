"""Tests for the discovery module."""

from datetime import datetime, timedelta
import pytest

from src.discovery import DiscoveryAnnouncement, DiscoveryService, LensDiscovery
from src.node import NodeStatus


def test_discovery_announcement_is_expired():
    ann = DiscoveryAnnouncement(
        node_id="test-node",
        organ="test-organ",
        endpoint="http://localhost",
        capabilities=[],
        ttl_seconds=10
    )
    assert not ann.is_expired()
    
    # Make it expired by moving timestamp to the past
    ann.timestamp = datetime.now() - timedelta(seconds=20)
    assert ann.is_expired()


def test_discovery_service_announce_new_node():
    service = DiscoveryService()
    ann = DiscoveryAnnouncement(
        node_id="node-1",
        organ="organ-a",
        endpoint="http://host1",
        capabilities=["search", "store"]
    )
    node = service.announce(ann)
    
    assert node.node_id == "node-1"
    assert node.organ == "organ-a"
    assert node.endpoint == "http://host1"
    assert node.status == NodeStatus.ONLINE
    assert node.has_capability("search")
    assert node.has_capability("store")
    assert not node.has_capability("nonexistent")
    assert service.active_count == 1


def test_discovery_service_announce_existing_node():
    service = DiscoveryService()
    ann1 = DiscoveryAnnouncement(
        node_id="node-1",
        organ="organ-a",
        endpoint="http://host1",
        capabilities=["search"]
    )
    node1 = service.announce(ann1)
    
    # Second announcement for the same node
    ann2 = DiscoveryAnnouncement(
        node_id="node-1",
        organ="organ-a",
        endpoint="http://host1",
        capabilities=["search"]
    )
    node2 = service.announce(ann2)
    
    # Should return the same node instance
    assert node1 is node2
    assert service.active_count == 1


def test_discovery_service_find_peers():
    service = DiscoveryService()
    
    # Add a few nodes
    service.announce(DiscoveryAnnouncement(
        node_id="node-1", organ="organ-a", endpoint="http://host1", capabilities=["search"]
    ))
    service.announce(DiscoveryAnnouncement(
        node_id="node-2", organ="organ-a", endpoint="http://host2", capabilities=["store"]
    ))
    service.announce(DiscoveryAnnouncement(
        node_id="node-3", organ="organ-b", endpoint="http://host3", capabilities=["search"]
    ))
    
    # Filter by organ
    peers_organ_a = service.find_peers(organ="organ-a")
    assert len(peers_organ_a) == 2
    assert {p.node_id for p in peers_organ_a} == {"node-1", "node-2"}
    
    # Filter by capability
    peers_search = service.find_peers(capability="search")
    assert len(peers_search) == 2
    assert {p.node_id for p in peers_search} == {"node-1", "node-3"}
    
    # Filter by both
    peers_both = service.find_peers(organ="organ-a", capability="search")
    assert len(peers_both) == 1
    assert peers_both[0].node_id == "node-1"
    
    # No filters
    all_peers = service.find_peers()
    assert len(all_peers) == 3


def test_discovery_service_find_peers_only_online():
    service = DiscoveryService()
    node = service.announce(DiscoveryAnnouncement(
        node_id="node-1", organ="organ-a", endpoint="http://host1", capabilities=[]
    ))
    
    assert len(service.find_peers()) == 1
    
    # Take node offline
    node.go_offline()
    assert len(service.find_peers()) == 0


def test_discovery_service_prune_expired():
    service = DiscoveryService()
    
    ann_fresh = DiscoveryAnnouncement(
        node_id="node-1", organ="organ-a", endpoint="http://host1", capabilities=[]
    )
    ann_expired = DiscoveryAnnouncement(
        node_id="node-2", organ="organ-b", endpoint="http://host2", capabilities=[]
    )
    
    service.announce(ann_fresh)
    service.announce(ann_expired)
    
    assert service.active_count == 2
    
    # Manually make the second announcement expired in the internal store
    service._announcements["node-2"].timestamp = datetime.now() - timedelta(seconds=400)
    
    pruned = service.prune_expired()
    
    assert pruned == 1
    assert service.active_count == 1
    assert "node-1" in service._announcements
    assert "node-2" not in service._announcements
    assert service._known_nodes["node-2"].status == NodeStatus.OFFLINE


def test_lens_discovery_discover_lenses(monkeypatch):
    from unittest.mock import MagicMock
    
    def mock_assemble(*args, **kwargs):
        mock_result = MagicMock()
        mock_lens1 = MagicMock()
        mock_lens1.lens_id = "lens-1"
        mock_lens2 = MagicMock()
        mock_lens2.lens_id = "lens-2"
        mock_result.summoned_lenses = [mock_lens1, mock_lens2]
        return mock_result
        
    monkeypatch.setattr("src.assembly.assemble", mock_assemble)
    
    ld = LensDiscovery()
    lenses = ld.discover_lenses("do something")
    assert lenses == ["lens-1", "lens-2"]


def test_lens_discovery_by_category():
    ld = LensDiscovery()
    
    # Test valid category
    lenses = ld.discover_by_category("tooling")
    assert isinstance(lenses, list)
    
    # Test invalid category
    invalid_lenses = ld.discover_by_category("not-a-category")
    assert invalid_lenses == []


def test_lens_discovery_by_stratum():
    ld = LensDiscovery()
    
    # Test valid stratum
    lenses = ld.discover_by_stratum("/boot/")
    assert isinstance(lenses, list)
    
    # Test invalid stratum
    invalid_lenses = ld.discover_by_stratum("/invalid/")
    assert invalid_lenses == []
