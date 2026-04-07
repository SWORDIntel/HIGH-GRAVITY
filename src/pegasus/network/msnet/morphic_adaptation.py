"""
Morphic Protocol Adaptation (MPA) - Enhancement 3

AI-powered distributed protocol research and testing system.
Hub nodes and MEMSHADOW nodes propose adaptations, test them, and vote on acceptance.
Similar to how MEMSHADOW nodes handle updates - distributed consensus.
"""

import struct
import json
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

try:
    from .dsmil_protocol import MessageType, MessageFlags, MemshadowMessage
except ImportError:
    # Fallback for testing
    MessageType = None
    MessageFlags = None
    MemshadowMessage = None


class AdaptationType(IntEnum):
    """Types of protocol adaptations"""
    HEADER_FORMAT = 1  # Change header structure
    COMPRESSION_ALGORITHM = 2  # New compression algorithm
    ROUTING_STRATEGY = 3  # New routing method
    ENCRYPTION_METHOD = 4  # New encryption scheme
    FLAG_EXTENSION = 5  # New message flags
    PAYLOAD_FORMAT = 6  # New payload structure
    PERFORMANCE_OPTIMIZATION = 7  # General performance improvement


class AdaptationStatus(IntEnum):
    """Status of protocol adaptation"""
    PROPOSED = 0  # Initial proposal
    RESEARCHING = 1  # AI research phase
    TESTING = 2  # Network testing phase
    VOTING = 3  # Consensus voting phase
    ACCEPTED = 4  # Accepted by consensus
    REJECTED = 5  # Rejected by consensus
    DEPRECATED = 6  # Accepted but later deprecated


class VoteType(IntEnum):
    """Vote types for adaptation"""
    ACCEPT = 1
    REJECT = 2
    ABSTAIN = 3


@dataclass
class AdaptationProposal:
    """
    Protocol adaptation proposal.
    
    Can be created by:
    - Hub nodes (AI research)
    - MEMSHADOW nodes (distributed research)
    - Manual proposals
    """
    adaptation_id: bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    adaptation_type: int = AdaptationType.PERFORMANCE_OPTIMIZATION
    proposer_node_id: bytes = b""
    description: str = ""
    research_data: Dict = field(default_factory=dict)  # AI research results
    adaptation_spec: Dict = field(default_factory=dict)  # Technical specification
    test_results: Dict = field(default_factory=dict)  # Network test results
    status: int = AdaptationStatus.PROPOSED
    created_at: int = field(default_factory=lambda: int(time.time() * 1e9))
    research_deadline: int = 0  # Nanoseconds
    test_deadline: int = 0  # Nanoseconds
    vote_deadline: int = 0  # Nanoseconds
    votes: Dict[bytes, int] = field(default_factory=dict)  # node_id -> VoteType
    metrics: Dict = field(default_factory=dict)  # Performance metrics
    
    def pack(self) -> bytes:
        """Pack adaptation proposal to binary"""
        description_bytes = self.description.encode('utf-8')
        research_json = json.dumps(self.research_data).encode('utf-8')
        spec_json = json.dumps(self.adaptation_spec).encode('utf-8')
        test_json = json.dumps(self.test_results).encode('utf-8')
        metrics_json = json.dumps(self.metrics).encode('utf-8')
        
        votes_data = b"".join([
            struct.pack(">16sI", node_id, vote_type)
            for node_id, vote_type in self.votes.items()
        ])
        
        return struct.pack(
            ">16sH16sIIIQQQQHHHH",
            self.adaptation_id,
            self.adaptation_type,
            len(self.proposer_node_id),
            len(description_bytes),
            len(research_json),
            len(spec_json),
            len(test_json),
            len(metrics_json),
            self.status,
            self.created_at,
            self.research_deadline,
            self.test_deadline,
            self.vote_deadline,
            len(self.votes),
        ) + self.proposer_node_id + description_bytes + research_json + spec_json + test_json + metrics_json + votes_data
    
    @classmethod
    def unpack(cls, data: bytes) -> "AdaptationProposal":
        """Unpack adaptation proposal from binary"""
        if len(data) < 50:
            raise ValueError("Adaptation proposal data too short")
        
        header = struct.unpack(
            ">16sH16sIIIQQQQHHHH",
            data[:50]
        )
        
        (adaptation_id, adaptation_type, proposer_len, desc_len,
         research_len, spec_len, test_len, metrics_len, status,
         created_at, research_deadline, test_deadline, vote_deadline,
         vote_count) = header
        
        offset = 50
        proposer_node_id = data[offset:offset + proposer_len]
        offset += proposer_len
        description = data[offset:offset + desc_len].decode('utf-8')
        offset += desc_len
        research_data = json.loads(data[offset:offset + research_len].decode('utf-8'))
        offset += research_len
        adaptation_spec = json.loads(data[offset:offset + spec_len].decode('utf-8'))
        offset += spec_len
        test_results = json.loads(data[offset:offset + test_len].decode('utf-8'))
        offset += test_len
        metrics = json.loads(data[offset:offset + metrics_len].decode('utf-8'))
        offset += metrics_len
        
        votes = {}
        for _ in range(vote_count):
            node_id = data[offset:offset + 16]
            vote_type = struct.unpack(">I", data[offset + 16:offset + 20])[0]
            votes[node_id] = vote_type
            offset += 20
        
        return cls(
            adaptation_id=adaptation_id,
            adaptation_type=adaptation_type,
            proposer_node_id=proposer_node_id,
            description=description,
            research_data=research_data,
            adaptation_spec=adaptation_spec,
            test_results=test_results,
            status=status,
            created_at=created_at,
            research_deadline=research_deadline,
            test_deadline=test_deadline,
            vote_deadline=vote_deadline,
            votes=votes,
            metrics=metrics,
        )
    
    def add_research_data(self, research_results: Dict):
        """Add AI research results"""
        self.research_data.update(research_results)
        self.status = AdaptationStatus.RESEARCHING
    
    def add_test_results(self, test_results: Dict):
        """Add network test results"""
        self.test_results.update(test_results)
        self.status = AdaptationStatus.TESTING
    
    def vote(self, node_id: bytes, vote_type: int):
        """Record a vote on this adaptation"""
        self.votes[node_id] = vote_type
        if self.status == AdaptationStatus.TESTING:
            self.status = AdaptationStatus.VOTING
    
    def get_consensus(self, total_nodes: int) -> Tuple[bool, float]:
        """
        Calculate consensus status.
        
        Returns:
            (is_accepted, acceptance_ratio)
        """
        if not self.votes:
            return False, 0.0
        
        accept_count = sum(1 for v in self.votes.values() if v == VoteType.ACCEPT)
        reject_count = sum(1 for v in self.votes.values() if v == VoteType.REJECT)
        total_votes = len(self.votes)
        
        if total_votes == 0:
            return False, 0.0
        
        acceptance_ratio = accept_count / total_votes
        
        # Consensus threshold: 66% acceptance, minimum 50% of nodes voted
        min_votes_required = total_nodes * 0.5
        consensus_threshold = 0.66
        
        if total_votes >= min_votes_required and acceptance_ratio >= consensus_threshold:
            return True, acceptance_ratio
        
        return False, acceptance_ratio


class MorphicAdaptationManager:
    """
    Manages protocol adaptations through distributed AI research and testing.
    
    Process:
    1. Hub/MEMSHADOW node proposes adaptation
    2. AI research phase (hub nodes perform research)
    3. Network testing phase (nodes test adaptation)
    4. Voting phase (nodes vote accept/reject)
    5. Consensus reached -> adaptation accepted/rejected
    """
    
    def __init__(self, node_id: bytes):
        self.node_id = node_id
        self.proposals: Dict[bytes, AdaptationProposal] = {}
        self.active_tests: Dict[bytes, Dict] = {}  # adaptation_id -> test data
        self.accepted_adaptations: Set[bytes] = set()
    
    def propose_adaptation(
        self,
        adaptation_type: int,
        description: str,
        adaptation_spec: Dict,
        research_deadline: Optional[int] = None,
    ) -> bytes:
        """
        Propose a new protocol adaptation.
        
        Args:
            adaptation_type: Type of adaptation
            description: Human-readable description
            adaptation_spec: Technical specification
            research_deadline: Deadline for AI research phase
        
        Returns:
            Adaptation ID
        """
        proposal = AdaptationProposal(
            adaptation_id=uuid.uuid4().bytes,
            adaptation_type=adaptation_type,
            proposer_node_id=self.node_id,
            description=description,
            adaptation_spec=adaptation_spec,
            research_deadline=research_deadline or (int(time.time() * 1e9) + 7 * 24 * 3600 * 1e9),  # 7 days default
            status=AdaptationStatus.PROPOSED,
        )
        
        self.proposals[proposal.adaptation_id] = proposal
        return proposal.adaptation_id
    
    def perform_ai_research(
        self,
        adaptation_id: bytes,
        research_results: Dict,
    ) -> bool:
        """
        Perform AI research on an adaptation (hub node or MEMSHADOW node).
        
        Args:
            adaptation_id: Adaptation to research
            research_results: AI research findings
        
        Returns:
            True if research added successfully
        """
        if adaptation_id not in self.proposals:
            return False
        
        proposal = self.proposals[adaptation_id]
        proposal.add_research_data(research_results)
        return True
    
    def start_testing(
        self,
        adaptation_id: bytes,
        test_duration: int = 7 * 24 * 3600 * 1e9,  # 7 days default
    ) -> bool:
        """
        Start network testing phase for an adaptation.
        
        Args:
            adaptation_id: Adaptation to test
            test_duration: Test duration in nanoseconds
        
        Returns:
            True if testing started successfully
        """
        if adaptation_id not in self.proposals:
            return False
        
        proposal = self.proposals[adaptation_id]
        
        if proposal.status != AdaptationStatus.RESEARCHING:
            return False
        
        proposal.status = AdaptationStatus.TESTING
        proposal.test_deadline = int(time.time() * 1e9) + test_duration
        
        # Initialize test tracking
        self.active_tests[adaptation_id] = {
            "start_time": int(time.time() * 1e9),
            "test_nodes": set(),
            "metrics": {},
        }
        
        return True
    
    def report_test_metrics(
        self,
        adaptation_id: bytes,
        metrics: Dict,
    ) -> bool:
        """
        Report test metrics from a node testing the adaptation.
        
        Args:
            adaptation_id: Adaptation being tested
            metrics: Performance metrics
        
        Returns:
            True if metrics recorded successfully
        """
        if adaptation_id not in self.proposals:
            return False
        
        if adaptation_id not in self.active_tests:
            return False
        
        proposal = self.proposals[adaptation_id]
        proposal.add_test_results(metrics)
        
        # Aggregate metrics
        test_data = self.active_tests[adaptation_id]
        test_data["metrics"].update(metrics)
        
        return True
    
    def vote_on_adaptation(
        self,
        adaptation_id: bytes,
        vote_type: int,
    ) -> bool:
        """
        Vote on an adaptation (accept/reject/abstain).
        
        Args:
            adaptation_id: Adaptation to vote on
            vote_type: VoteType.ACCEPT, REJECT, or ABSTAIN
        
        Returns:
            True if vote recorded successfully
        """
        if adaptation_id not in self.proposals:
            return False
        
        proposal = self.proposals[adaptation_id]
        
        if proposal.status not in (AdaptationStatus.TESTING, AdaptationStatus.VOTING):
            return False
        
        proposal.vote(self.node_id, vote_type)
        
        # Check if voting phase should start
        if proposal.status == AdaptationStatus.TESTING:
            # Transition to voting after test deadline
            if time.time_ns() >= proposal.test_deadline:
                proposal.status = AdaptationStatus.VOTING
                proposal.vote_deadline = int(time.time() * 1e9) + 3 * 24 * 3600 * 1e9  # 3 days voting
        
        return True
    
    def check_consensus(
        self,
        adaptation_id: bytes,
        total_nodes: int,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if consensus has been reached on an adaptation.
        
        Args:
            adaptation_id: Adaptation to check
            total_nodes: Total number of nodes in network
        
        Returns:
            (consensus_reached, new_status) or (False, None)
        """
        if adaptation_id not in self.proposals:
            return False, None
        
        proposal = self.proposals[adaptation_id]
        
        if proposal.status != AdaptationStatus.VOTING:
            return False, None
        
        # Check if voting deadline passed
        if time.time_ns() < proposal.vote_deadline:
            return False, None
        
        is_accepted, acceptance_ratio = proposal.get_consensus(total_nodes)
        
        if is_accepted:
            proposal.status = AdaptationStatus.ACCEPTED
            self.accepted_adaptations.add(adaptation_id)
            return True, AdaptationStatus.ACCEPTED
        else:
            proposal.status = AdaptationStatus.REJECTED
            return True, AdaptationStatus.REJECTED
    
    def apply_adaptation(self, adaptation_id: bytes) -> bool:
        """
        Apply an accepted adaptation to the protocol.
        
        Args:
            adaptation_id: Accepted adaptation to apply
        
        Returns:
            True if adaptation applied successfully
        """
        if adaptation_id not in self.proposals:
            return False
        
        proposal = self.proposals[adaptation_id]
        
        if proposal.status != AdaptationStatus.ACCEPTED:
            return False
        
        # Apply adaptation based on type
        # This would modify protocol behavior
        # Implementation depends on adaptation_spec
        
        return True
    
    def get_proposals_by_status(self, status: int) -> List[AdaptationProposal]:
        """Get all proposals with a specific status"""
        return [
            proposal for proposal in self.proposals.values()
            if proposal.status == status
        ]


class MorphicProtocolAdapter:
    """
    Morphic Protocol Adapter - Simple adaptation interface

    Provides basic morphic adaptation functionality for testing.
    """

    def __init__(self):
        self.manager = MorphicAdaptationManager(b"test_node")

    def propose_adaptation(self, feature: str, params: Dict) -> Optional[bytes]:
        """
        Propose a protocol adaptation - compatible with test interface

        Args:
            feature: Feature name
            params: Adaptation parameters

        Returns:
            Adaptation ID or None if failed
        """
        try:
            return self.manager.propose_adaptation(
                adaptation_type=AdaptationType.PERFORMANCE_OPTIMIZATION,
                description=f"Adaptation for {feature}",
                adaptation_spec=params
            )
        except Exception:
            return None
