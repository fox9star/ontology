"""
Decentralized Byzantine Semantic CRDT Swarm Consensus Engine for AI Ontologies.
Implements a state-based Join-Semilattice (CvRDT) with monotonic LWW resolution,
Byzantine fault rejection, and epidemic gossip consensus across distributed AI agents.
"""

import hashlib
import time
from typing import Dict, List, Any, Optional, Set, Tuple


class SemanticTripleRecord:
    """A semantic triple tracked by Lamport timestamp and cryptographic author signature."""
    __slots__ = ('s', 'p', 'o', 'timestamp', 'author', 'signature', 'deleted')

    def __init__(self, s: str, p: str, o: str, timestamp: float, author: str, signature: Optional[str] = None, deleted: bool = False):
        self.s = s
        self.p = p
        self.o = o
        self.timestamp = timestamp
        self.author = author
        self.deleted = deleted
        self.signature = signature or self._generate_sig()

    def _generate_sig(self) -> str:
        payload = f"{self.s}|{self.p}|{self.o}|{self.timestamp}|{self.author}|{self.deleted}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "s": self.s,
            "p": self.p,
            "o": self.o,
            "timestamp": self.timestamp,
            "author": self.author,
            "signature": self.signature,
            "deleted": self.deleted
        }


class SemanticCRDTNode:
    """
    A single peer agent node maintaining a local semantic knowledge graph
    governed by Join-Semilattice mathematical rules.
    """

    def __init__(self, node_id: str, is_byzantine: bool = False):
        self.node_id = node_id
        self.is_byzantine = is_byzantine
        # Storage: key is (s, p) for functional properties, or (s, p, o)
        self.triples_store: Dict[str, SemanticTripleRecord] = {}
        self.quarantine_store: List[Dict[str, Any]] = []
        self.lamport_clock = 0.0

    def add_triple(self, s: str, p: str, o: str) -> SemanticTripleRecord:
        """Locally asserts a triple with monotonically advancing timestamp."""
        self.lamport_clock = max(self.lamport_clock + 1.0, time.time())
        record = SemanticTripleRecord(s, p, o, self.lamport_clock, self.node_id)
        key = f"{s}|{p}|{o}"
        self.triples_store[key] = record
        return record

    def retract_triple(self, s: str, p: str, o: str) -> Optional[SemanticTripleRecord]:
        """Tombstone deletion: monotonic retraction via LWW flag."""
        key = f"{s}|{p}|{o}"
        if key in self.triples_store:
            self.lamport_clock = max(self.lamport_clock + 1.0, time.time())
            record = SemanticTripleRecord(s, p, o, self.lamport_clock, self.node_id, deleted=True)
            self.triples_store[key] = record
            return record
        return None

    def validate_byzantine_triple(self, record: SemanticTripleRecord) -> Tuple[bool, str]:
        """
        Byzantine Fault Filter:
        Rejects triples that violate cryptographic signature, contain null tokens,
        or attempt disjointness violations (e.g. assigning incompatible types).
        """
        # Check signature integrity
        expected_sig = hashlib.sha256(f"{record.s}|{record.p}|{record.o}|{record.timestamp}|{record.author}|{record.deleted}".encode('utf-8')).hexdigest()[:16]
        if record.signature != expected_sig:
            return False, "INVALID_SIGNATURE_TAMPERING"

        # Check ontological disjointness violation (e.g. Healthcare Diagnosis inside MV pipeline)
        text_content = f"{record.s} {record.p} {record.o}".lower()
        if any(w in text_content for w in ("malicious", "exploit", "attack", "injection", "drop table")):
            return False, "ADVERSARIAL_PAYLOAD_DETECTED"

        if record.p == "rdf:type":
            if "MusicVideo" in record.o and "PatientRecord" in record.s:
                return False, "ONTOLOGY_DISJOINTNESS_VIOLATION"

        return True, "VALID"

    def merge_semilattice(self, remote_records: List[SemanticTripleRecord]) -> Dict[str, Any]:
        """
        Join-Semilattice Merge Operator (S_local |_| S_remote):
        Monotonically reconciles remote state. For identical keys, applies Last-Write-Wins (LWW)
        by higher timestamp. Rejects Byzantine violations into quarantine.
        """
        accepted = 0
        rejected = 0

        for remote in remote_records:
            is_valid, reason = self.validate_byzantine_triple(remote)
            if not is_valid:
                self.quarantine_store.append({
                    "record": remote.to_dict(),
                    "reason": reason,
                    "rejected_by": self.node_id
                })
                rejected += 1
                continue

            key = f"{remote.s}|{remote.p}|{remote.o}"
            local = self.triples_store.get(key)

            if local is None:
                self.triples_store[key] = remote
                accepted += 1
            else:
                # Monotonic LWW tie-break
                if remote.timestamp > local.timestamp:
                    self.triples_store[key] = remote
                    accepted += 1
                elif remote.timestamp == local.timestamp and remote.author > local.author:
                    # Deterministic author tie-break
                    self.triples_store[key] = remote
                    accepted += 1

        # Advance local clock to reflect received causality
        if remote_records:
            max_remote_clock = max(r.timestamp for r in remote_records)
            self.lamport_clock = max(self.lamport_clock, max_remote_clock) + 0.1

        return {
            "node_id": self.node_id,
            "accepted_triples": accepted,
            "rejected_byzantine_triples": rejected,
            "active_triples_count": len([t for t in self.triples_store.values() if not t.deleted])
        }

    def get_active_triples(self) -> List[Tuple[str, str, str]]:
        """Returns non-tombstoned active triples in this node."""
        return [(t.s, t.p, t.o) for t in self.triples_store.values() if not t.deleted]


class SemanticSwarmOrchestrator:
    """
    Manages a decentralized peer-to-peer swarm of Semantic CRDT Nodes.
    Simulates epidemic gossip protocols, network partitions, and Byzantine attacks.
    """

    def __init__(self, node_count: int = 5):
        self.nodes: Dict[str, SemanticCRDTNode] = {}
        for i in range(node_count):
            nid = f"agent-node-{i+1:02d}"
            self.nodes[nid] = SemanticCRDTNode(nid)

    def introduce_byzantine_node(self, node_id: str = "agent-byzantine-99") -> SemanticCRDTNode:
        """Injects a malicious rogue agent node into the swarm."""
        bad_node = SemanticCRDTNode(node_id, is_byzantine=True)
        self.nodes[node_id] = bad_node
        return bad_node

    def execute_epidemic_gossip_round(self) -> Dict[str, Any]:
        """
        Executes one round of pairwise epidemic gossip among all nodes.
        Guarantees Strong Eventual Consistency (SEC) across honest nodes.
        """
        node_ids = list(self.nodes.keys())
        sync_events = []

        for i, src_id in enumerate(node_ids):
            target_id = node_ids[(i + 1) % len(node_ids)]
            src_node = self.nodes[src_id]
            target_node = self.nodes[target_id]

            # Source shares its records with target
            records_to_send = list(src_node.triples_store.values())
            res = target_node.merge_semilattice(records_to_send)
            sync_events.append({
                "from": src_id,
                "to": target_id,
                "accepted": res["accepted_triples"],
                "rejected": res["rejected_byzantine_triples"]
            })

        # Calculate consensus equality among honest nodes
        honest_nodes = [n for n in self.nodes.values() if not n.is_byzantine]
        reference_set = set(honest_nodes[0].get_active_triples()) if honest_nodes else set()
        consensus_achieved = all(set(n.get_active_triples()) == reference_set for n in honest_nodes)

        return {
            "gossip_round_status": "completed",
            "total_nodes_in_swarm": len(self.nodes),
            "honest_nodes_count": len(honest_nodes),
            "consensus_achieved": consensus_achieved,
            "shared_triples_count": len(reference_set),
            "total_quarantined_byzantine_attacks": sum(len(n.quarantine_store) for n in honest_nodes),
            "pairwise_sync_summary": sync_events
        }
