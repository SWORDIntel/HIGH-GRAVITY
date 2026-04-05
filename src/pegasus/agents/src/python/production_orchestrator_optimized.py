#!/usr/bin/env python3
"""
C-INTERNAL OPTIMIZED PRODUCTION ORCHESTRATOR - Phase 1 Performance Enhancements
NSA Strategic Decision Implementation - Target: 3-5x performance improvement

Enhanced Python Tandem Orchestrator with Phase 1 optimizations:
- Connection pooling for agent communications
- Multi-level caching with intelligent invalidation
- Hardware-aware thread allocation and NUMA optimization
- Advanced async performance patterns
- Memory optimization and object pooling
- Resource monitoring with automatic cleanup

Performance Target: 15-25K operations/sec (from ~5K baseline)
Memory Target: 50% reduction in allocations
Latency Target: <10ms P95 for agent invocation
"""

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import mmap
import multiprocessing as mp
import os
import threading
import time
import weakref
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

import aiofiles
import psutil

# High-performance imports with fallbacks
try:
    import uvloop

    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

try:
    import orjson

    JSON_SERIALIZER = orjson
except ImportError:
    import json

    JSON_SERIALIZER = json

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import numba
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Import original components with fallback
try:
    from claude_agents.core.agent_dynamic_loader import invoke_agent_dynamically
    from claude_agents.orchestration.agent_registry import AgentMetadata, AgentPriority
    from claude_agents.orchestration.agent_registry import (
        AgentStatus as AgentStatusEnum,
    )
    from claude_agents.orchestration.agent_registry import (
        EnhancedAgentRegistry,
        get_enhanced_registry,
        initialize_enhanced_registry,
    )

    REGISTRY_AVAILABLE = True
    ENHANCED_REGISTRY = True
except ImportError:
    try:
        from claude_agents.orchestration.agent_registry import (
            AgentMetadata,
            AgentRegistry,
            get_registry,
        )

        ENHANCED_REGISTRY = False
        REGISTRY_AVAILABLE = True
    except ImportError:
        REGISTRY_AVAILABLE = False
        ENHANCED_REGISTRY = False

        class AgentRegistry:
            """Fallback registry"""

            def __init__(self):
                self.agents = {}

            def register_agent(self, name, config):
                self.agents[name] = config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PERFORMANCE OPTIMIZATION CONSTANTS
# ============================================================================


class PerformanceConfig:
    """Performance optimization configuration"""

    # Connection Pool Settings
    CONNECTION_POOL_SIZE = 50
    CONNECTION_POOL_MAX_OVERFLOW = 20
    CONNECTION_TIMEOUT = 30.0
    CONNECTION_KEEPALIVE = 600.0

    # Cache Configuration
    CACHE_TTL_SHORT = 300  # 5 minutes
    CACHE_TTL_MEDIUM = 1800  # 30 minutes
    CACHE_TTL_LONG = 3600  # 1 hour
    CACHE_MAX_SIZE = 10000  # Maximum cache entries

    # Thread Pool Settings
    MAX_WORKERS_IO = min(32, (os.cpu_count() or 1) * 4)
    MAX_WORKERS_CPU = min(16, (os.cpu_count() or 1) * 2)

    # Memory Settings
    OBJECT_POOL_SIZE = 1000
    BUFFER_SIZE = 65536
    MMAP_THRESHOLD = 1024 * 1024  # 1MB

    # Performance Thresholds
    LATENCY_WARNING_MS = 100
    LATENCY_CRITICAL_MS = 500
    MEMORY_WARNING_PCT = 80
    CPU_WARNING_PCT = 90


# ============================================================================
# HARDWARE TOPOLOGY OPTIMIZATION
# ============================================================================


class OptimizedMeteorLakeTopology:
    """Enhanced hardware topology with NUMA awareness and performance optimization"""

    def __init__(self):
        self.cpu_info = self._detect_cpu_topology()
        self.numa_nodes = self._detect_numa_topology()
        self.p_cores_ultra = self.cpu_info.get("p_cores_ultra", [11, 14, 15, 16])
        self.p_cores_standard = self.cpu_info.get(
            "p_cores_standard", list(range(0, 11))
        )
        self.e_cores = self.cpu_info.get("e_cores", list(range(12, 20)))
        self.lp_e_cores = self.cpu_info.get("lp_e_cores", [20, 21])
        self.total_cores = self.cpu_info.get("total_cores", 22)

        # Performance core allocation strategy
        self.core_allocation = self._optimize_core_allocation()

    def _detect_cpu_topology(self) -> Dict[str, Any]:
        """Detect actual CPU topology"""
        try:
            logical_cores = psutil.cpu_count(logical=True)
            physical_cores = psutil.cpu_count(logical=False)

            # Intel Meteor Lake specific detection
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()

            if "Intel Core Ultra" in cpuinfo:
                # Meteor Lake topology
                return {
                    "total_cores": logical_cores,
                    "physical_cores": physical_cores,
                    "p_cores_ultra": [11, 14, 15, 16],
                    "p_cores_standard": list(range(0, 11)),
                    "e_cores": list(range(12, 20)),
                    "lp_e_cores": [20, 21] if logical_cores >= 22 else [],
                }
            else:
                # Generic topology
                return {
                    "total_cores": logical_cores,
                    "physical_cores": physical_cores,
                    "p_cores_standard": list(range(0, physical_cores)),
                    "e_cores": (
                        list(range(physical_cores, logical_cores))
                        if logical_cores > physical_cores
                        else []
                    ),
                    "p_cores_ultra": [],
                    "lp_e_cores": [],
                }
        except Exception as e:
            logger.warning(f"CPU topology detection failed: {e}")
            return {"total_cores": os.cpu_count() or 4}

    def _detect_numa_topology(self) -> Dict[int, List[int]]:
        """Detect NUMA topology"""
        numa_nodes = {}
        try:
            numa_path = Path("/sys/devices/system/node")
            if numa_path.exists():
                for node_dir in numa_path.glob("node*"):
                    node_id = int(node_dir.name[4:])
                    cpulist_file = node_dir / "cpulist"
                    if cpulist_file.exists():
                        cpulist = cpulist_file.read_text().strip()
                        cpus = self._parse_cpu_list(cpulist)
                        numa_nodes[node_id] = cpus
        except Exception as e:
            logger.warning(f"NUMA detection failed: {e}")
            # Default single node
            numa_nodes[0] = list(range(self.total_cores))

        return numa_nodes

    def _parse_cpu_list(self, cpulist: str) -> List[int]:
        """Parse CPU list format (e.g., '0-3,8-11')"""
        cpus = []
        for part in cpulist.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                cpus.extend(range(start, end + 1))
            else:
                cpus.append(int(part))
        return cpus

    def _optimize_core_allocation(self) -> Dict[str, List[int]]:
        """Optimize core allocation for different workload types"""
        return {
            "critical_sync": (
                self.p_cores_ultra[:2]
                if self.p_cores_ultra
                else self.p_cores_standard[:2]
            ),
            "critical_async": (
                self.p_cores_ultra[2:]
                if len(self.p_cores_ultra) > 2
                else self.p_cores_standard[2:4]
            ),
            "high_performance": self.p_cores_standard[:6],
            "io_bound": (
                self.e_cores[:4] if self.e_cores else self.p_cores_standard[6:8]
            ),
            "background": (
                self.e_cores[4:] if len(self.e_cores) > 4 else self.lp_e_cores
            ),
            "monitoring": (
                self.lp_e_cores if self.lp_e_cores else [self.total_cores - 1]
            ),
        }

    def get_optimal_cores(
        self, workload_type: str, task_priority: str = "MEDIUM"
    ) -> List[int]:
        """Get optimal core allocation for workload type"""
        if task_priority == "CRITICAL":
            return self.core_allocation.get(
                "critical_sync", self.core_allocation["high_performance"]
            )
        elif task_priority == "HIGH":
            return self.core_allocation.get(
                "critical_async", self.core_allocation["high_performance"]
            )
        elif workload_type == "io_bound":
            return self.core_allocation.get(
                "io_bound", self.core_allocation["background"]
            )
        elif workload_type == "cpu_bound":
            return self.core_allocation.get("high_performance", list(range(4)))
        else:
            return self.core_allocation.get("background", list(range(2)))


# ============================================================================
# CONNECTION POOLING SYSTEM
# ============================================================================


@dataclass
class Connection:
    """Connection object with health tracking"""

    id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    is_healthy: bool = True
    agent_type: Optional[str] = None
    socket: Optional[Any] = None

    def mark_used(self):
        """Mark connection as used"""
        self.last_used = datetime.now()
        self.use_count += 1

    def is_expired(self, max_age: timedelta = timedelta(minutes=10)) -> bool:
        """Check if connection is expired"""
        return datetime.now() - self.last_used > max_age


class ConnectionPool:
    """High-performance connection pool with health monitoring"""

    def __init__(self, max_size: int = PerformanceConfig.CONNECTION_POOL_SIZE):
        self.max_size = max_size
        self.connections: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_size))
        self.active_connections: Set[str] = set()
        self.stats = {"created": 0, "reused": 0, "expired": 0, "health_checks": 0}
        self._lock = asyncio.Lock()

    async def get_connection(self, agent_name: str) -> Connection:
        """Get or create connection for agent"""
        async with self._lock:
            pool = self.connections[agent_name]

            # Try to reuse existing connection
            while pool:
                conn = pool.pop()
                if not conn.is_expired() and conn.is_healthy:
                    conn.mark_used()
                    self.active_connections.add(conn.id)
                    self.stats["reused"] += 1
                    return conn
                else:
                    self.stats["expired"] += 1

            # Create new connection
            conn = Connection(
                id=f"{agent_name}_{int(time.time() * 1000)}_{len(self.active_connections)}",
                agent_type=agent_name,
            )
            self.active_connections.add(conn.id)
            self.stats["created"] += 1
            return conn

    async def return_connection(self, connection: Connection) -> None:
        """Return connection to pool"""
        async with self._lock:
            if connection.id in self.active_connections:
                self.active_connections.remove(connection.id)

                if connection.is_healthy and not connection.is_expired():
                    pool = self.connections[connection.agent_type or "default"]
                    pool.append(connection)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connections"""
        async with self._lock:
            total_connections = sum(len(pool) for pool in self.connections.values())
            healthy_connections = 0

            for pool in self.connections.values():
                for conn in pool:
                    if await self._check_connection_health(conn):
                        healthy_connections += 1
                    else:
                        conn.is_healthy = False

            self.stats["health_checks"] += 1

            return {
                "total_pooled": total_connections,
                "active": len(self.active_connections),
                "healthy": healthy_connections,
                "stats": self.stats.copy(),
            }

    async def _check_connection_health(self, connection: Connection) -> bool:
        """Check individual connection health"""
        try:
            # Implement actual health check logic here
            # For now, just check age and use count
            if connection.is_expired(
                timedelta(minutes=PerformanceConfig.CONNECTION_KEEPALIVE)
            ):
                return False
            return True
        except Exception:
            return False


# ============================================================================
# MULTI-LEVEL CACHING SYSTEM
# ============================================================================


class CacheLevel(Enum):
    """Cache levels with different TTL and size characteristics"""

    L1_MEMORY = "l1_memory"  # Hot data, fastest access
    L2_DISK = "l2_disk"  # Warm data, persistent
    L3_DISTRIBUTED = "l3_distributed"  # Cold data, shared


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[float] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at.timestamp() > self.ttl

    def mark_accessed(self):
        """Mark entry as accessed"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class MultiLevelCache:
    """Intelligent multi-level caching system"""

    def __init__(self):
        # L1: In-memory cache (fastest)
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l1_max_size = 1000
        self.l1_ttl = PerformanceConfig.CACHE_TTL_SHORT

        # L2: Disk-based cache (persistent)
        self.l2_cache_dir = Path("/tmp/claude_orchestrator_cache")
        self.l2_cache_dir.mkdir(exist_ok=True)
        self.l2_ttl = PerformanceConfig.CACHE_TTL_MEDIUM

        # L3: Distributed cache (Redis-like, not implemented here)
        self.l3_available = False

        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "l3_hits": 0,
            "l3_misses": 0,
            "evictions": 0,
        }
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, checking all levels"""
        # Try L1 first
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not entry.is_expired():
                entry.mark_accessed()
                self.stats["l1_hits"] += 1
                return entry.value
            else:
                del self.l1_cache[key]

        self.stats["l1_misses"] += 1

        # Try L2 (disk)
        l2_value = await self._get_from_l2(key)
        if l2_value is not None:
            self.stats["l2_hits"] += 1
            # Promote to L1
            await self._promote_to_l1(key, l2_value)
            return l2_value

        self.stats["l2_misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache with intelligent placement"""
        async with self._lock:
            # Calculate size
            try:
                if hasattr(JSON_SERIALIZER, "dumps"):
                    size_bytes = len(JSON_SERIALIZER.dumps(value))
                else:
                    size_bytes = len(JSON_SERIALIZER.dumps(value).encode())
            except Exception:
                size_bytes = 1024  # Estimate

            # Create cache entry
            entry = CacheEntry(
                key=key, value=value, ttl=ttl or self.l1_ttl, size_bytes=size_bytes
            )

            # Always put in L1
            await self._set_l1(key, entry)

            # Conditionally put in L2 for persistence
            if size_bytes < PerformanceConfig.MMAP_THRESHOLD:
                await self._set_l2(key, value, ttl or self.l2_ttl)

    async def _set_l1(self, key: str, entry: CacheEntry) -> None:
        """Set value in L1 cache with eviction"""
        # Evict if at capacity
        if len(self.l1_cache) >= self.l1_max_size:
            await self._evict_l1()

        self.l1_cache[key] = entry

    async def _evict_l1(self) -> None:
        """Evict least recently used items from L1"""
        # Sort by last accessed time
        items = sorted(self.l1_cache.items(), key=lambda x: x[1].last_accessed)

        # Remove oldest 10%
        evict_count = max(1, len(items) // 10)
        for i in range(evict_count):
            key, entry = items[i]
            # Move to L2 if valuable
            if entry.access_count > 1:
                await self._set_l2(key, entry.value, self.l2_ttl)
            del self.l1_cache[key]
            self.stats["evictions"] += 1

    async def _get_from_l2(self, key: str) -> Optional[Any]:
        """Get value from L2 disk cache"""
        try:
            cache_file = (
                self.l2_cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
            )
            if cache_file.exists():
                # Check TTL
                if time.time() - cache_file.stat().st_mtime > self.l2_ttl:
                    cache_file.unlink()
                    return None

                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(cache_file, "rb") as f:
                        data = await f.read()
                        return JSON_SERIALIZER.loads(data)
                else:
                    with open(cache_file, "rb") as f:
                        data = f.read()
                        return JSON_SERIALIZER.loads(data)
        except Exception as e:
            logger.debug(f"L2 cache read error: {e}")

        return None

    async def _set_l2(self, key: str, value: Any, ttl: float) -> None:
        """Set value in L2 disk cache"""
        try:
            cache_file = (
                self.l2_cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
            )
            if hasattr(JSON_SERIALIZER, "dumps"):
                data = JSON_SERIALIZER.dumps(value)
            else:
                data = JSON_SERIALIZER.dumps(value).encode()

            if AIOFILES_AVAILABLE:
                async with aiofiles.open(cache_file, "wb") as f:
                    await f.write(data)
            else:
                with open(cache_file, "wb") as f:
                    if isinstance(data, str):
                        f.write(data.encode())
                    else:
                        f.write(data)
        except Exception as e:
            logger.debug(f"L2 cache write error: {e}")

    async def _promote_to_l1(self, key: str, value: Any) -> None:
        """Promote value from L2 to L1"""
        entry = CacheEntry(key=key, value=value, ttl=self.l1_ttl)
        await self._set_l1(key, entry)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = sum(
            [
                self.stats["l1_hits"],
                self.stats["l1_misses"],
                self.stats["l2_hits"],
                self.stats["l2_misses"],
            ]
        )

        if total_requests == 0:
            return self.stats

        hit_rate = (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "l1_size": len(self.l1_cache),
        }


# ============================================================================
# OBJECT POOLING SYSTEM
# ============================================================================


class ObjectPool:
    """High-performance object pool to reduce allocations"""

    def __init__(
        self, factory: Callable, max_size: int = PerformanceConfig.OBJECT_POOL_SIZE
    ):
        self.factory = factory
        self.max_size = max_size
        self.pool: deque = deque()
        self.stats = {"created": 0, "reused": 0, "returned": 0}
        self._lock = threading.Lock()

    def get(self) -> Any:
        """Get object from pool or create new one"""
        with self._lock:
            if self.pool:
                obj = self.pool.pop()
                self.stats["reused"] += 1
                return obj
            else:
                obj = self.factory()
                self.stats["created"] += 1
                return obj

    def return_object(self, obj: Any) -> None:
        """Return object to pool"""
        with self._lock:
            if len(self.pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, "reset"):
                    obj.reset()
                self.pool.append(obj)
                self.stats["returned"] += 1


# Create global object pools
dict_pool = ObjectPool(dict)
list_pool = ObjectPool(list)
set_pool = ObjectPool(set)

# ============================================================================
# OPTIMIZED ORCHESTRATOR
# ============================================================================


class OptimizedProductionOrchestrator:
    """
    C-INTERNAL optimized production orchestrator with Phase 1 enhancements
    Target: 15-25K operations/sec (3-5x improvement from baseline)
    """

    def __init__(self):
        # Core components
        self.registry = None
        self.is_initialized = False

        # High-performance components
        self.connection_pool = ConnectionPool()
        self.cache = MultiLevelCache()
        self.hardware_topology = OptimizedMeteorLakeTopology()

        # Optimized async components
        self.message_queue = asyncio.Queue(maxsize=10000)
        self.high_priority_queue = asyncio.Queue(maxsize=1000)
        self.command_history = deque(maxlen=10000)
        self.active_commands = {}
        self.agent_status = {}

        # Thread pools for different workloads
        self.io_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=PerformanceConfig.MAX_WORKERS_IO,
            thread_name_prefix="orchestrator_io",
        )
        self.cpu_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=PerformanceConfig.MAX_WORKERS_CPU,
            thread_name_prefix="orchestrator_cpu",
        )

        # Performance tracking
        self.start_time = time.time()
        self.metrics = defaultdict(int)
        self.latency_tracker = deque(maxlen=10000)
        self.resource_monitor = None

        # Optimization flags
        self.use_uvloop = UVLOOP_AVAILABLE
        self.use_numpy = NUMPY_AVAILABLE

        # Background tasks
        self.background_tasks = set()

    async def initialize(self) -> bool:
        """Initialize optimized orchestrator"""
        try:
            logger.info("Initializing C-INTERNAL Optimized Production Orchestrator...")

            # Set up high-performance event loop
            if self.use_uvloop and not isinstance(
                asyncio.get_event_loop(), uvloop.Loop
            ):
                uvloop.install()
                logger.info("✅ UV Loop installed for enhanced performance")

            # Initialize agent registry
            await self._initialize_registry()

            # Start background optimization tasks
            await self._start_background_tasks()

            # Initialize resource monitoring
            self.resource_monitor = ResourceMonitor()

            self.is_initialized = True
            logger.info("✅ Optimized orchestrator initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    async def _initialize_registry(self) -> None:
        """Initialize registry with fallback support"""
        if ENHANCED_REGISTRY:
            logger.info("Using Enhanced Agent Registry with Python fallback")
            self.registry = get_enhanced_registry()
            success = await self.registry.initialize()
            if success:
                for agent_name in self.registry.agents:
                    self.agent_status[agent_name] = AgentStatusEnum.IDLE
                logger.info(f"Registry loaded {len(self.registry.agents)} agents")
            else:
                logger.warning("Enhanced registry failed, using fallback")
                await self._discover_agents_fallback()
        else:
            logger.warning("Using fallback agent discovery")
            await self._discover_agents_fallback()

    async def _discover_agents_fallback(self) -> None:
        """Fallback agent discovery"""
        agents_root = os.environ.get(
            "CLAUDE_AGENTS_ROOT", '${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents'
        )
        agents_dir = Path(agents_root)

        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                agent_name = agent_file.stem.lower()
                if agent_name not in ["template", "readme"]:
                    self.agent_status[agent_name] = AgentStatusEnum.IDLE

    async def _start_background_tasks(self) -> None:
        """Start optimized background tasks"""
        tasks = [
            self._optimized_message_processor(),
            self._priority_queue_processor(),
            self._health_monitor(),
            self._performance_monitor(),
            self._cache_maintenance(),
            self._connection_pool_maintenance(),
        ]

        for coro in tasks:
            task = asyncio.create_task(coro)
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

    # ========================================================================
    # OPTIMIZED MESSAGE PROCESSING
    # ========================================================================

    async def _optimized_message_processor(self) -> None:
        """High-performance message processor with batching"""
        batch_size = 100
        batch_timeout = 0.010  # 10ms

        while True:
            try:
                batch = []
                deadline = time.time() + batch_timeout

                # Collect batch of messages
                while len(batch) < batch_size and time.time() < deadline:
                    try:
                        message = await asyncio.wait_for(
                            self.message_queue.get(), timeout=deadline - time.time()
                        )
                        batch.append(message)
                    except asyncio.TimeoutError:
                        break

                # Process batch if we have messages
                if batch:
                    await self._process_message_batch(batch)

            except Exception as e:
                logger.error(f"Message processor error: {e}")
                await asyncio.sleep(0.1)

    async def _priority_queue_processor(self) -> None:
        """Process high-priority messages with minimal latency"""
        while True:
            try:
                message = await self.high_priority_queue.get()
                start_time = time.time()

                # Process immediately
                await self._process_message(message)

                # Track latency
                latency = (time.time() - start_time) * 1000
                self.latency_tracker.append(latency)

                if latency > PerformanceConfig.LATENCY_WARNING_MS:
                    logger.warning(f"High latency detected: {latency:.2f}ms")

            except Exception as e:
                logger.error(f"Priority queue processor error: {e}")

    async def _process_message_batch(self, batch: List[Any]) -> None:
        """Process batch of messages in parallel"""
        if not batch:
            return

        tasks = []
        for message in batch:
            task = asyncio.create_task(self._process_message(message))
            tasks.append(task)

        # Wait for all messages to process
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update metrics
        self.metrics["messages_processed"] += len(batch)
        self.metrics["batch_operations"] += 1

        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Message {i} failed: {result}")
                self.metrics["message_errors"] += 1

    async def _process_message(self, message: Any) -> Any:
        """Process individual message with caching and connection pooling"""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(message)
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                self.metrics["cache_hits"] += 1
                return cached_result

            self.metrics["cache_misses"] += 1

            # Get connection from pool
            connection = await self.connection_pool.get_connection(
                getattr(message, "target_agent", "default")
            )

            try:
                # Process message
                result = await self._execute_message(message, connection)

                # Cache result if cacheable
                if self._is_cacheable(message, result):
                    await self.cache.set(cache_key, result, ttl=300)

                return result

            finally:
                await self.connection_pool.return_connection(connection)

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            self.metrics["processing_errors"] += 1
            raise

    def _generate_cache_key(self, message: Any) -> str:
        """Generate cache key for message"""
        try:
            # Create deterministic key from message content
            if hasattr(message, "__dict__"):
                content = str(sorted(message.__dict__.items()))
            else:
                content = str(message)
            return hashlib.sha256(content.encode()).hexdigest()[:32]
        except Exception:
            return str(hash(str(message)))[:32]

    def _is_cacheable(self, message: Any, result: Any) -> bool:
        """Determine if message result should be cached"""
        # Don't cache errors or empty results
        if isinstance(result, Exception) or not result:
            return False

        # Don't cache time-sensitive operations
        if hasattr(message, "action"):
            non_cacheable = ["deploy", "monitor", "real_time", "status"]
            if any(keyword in str(message.action).lower() for keyword in non_cacheable):
                return False

        return True

    async def _execute_message(self, message: Any, connection: Connection) -> Any:
        """Execute message with hardware-aware scheduling"""
        try:
            # Determine optimal execution strategy
            execution_info = await self._analyze_execution_requirements(message)

            # Set CPU affinity if specified
            if execution_info.get("cpu_affinity"):
                await self._set_cpu_affinity(execution_info["cpu_affinity"])

            # Choose execution path
            if execution_info.get("io_bound"):
                return await self._execute_io_bound(message, connection)
            elif execution_info.get("cpu_bound"):
                return await self._execute_cpu_bound(message, connection)
            else:
                return await self._execute_balanced(message, connection)

        except Exception as e:
            connection.is_healthy = False
            raise

    async def _analyze_execution_requirements(self, message: Any) -> Dict[str, Any]:
        """Analyze message to determine optimal execution strategy"""
        info = dict_pool.get()

        try:
            # Default values
            info.update(
                {
                    "io_bound": False,
                    "cpu_bound": False,
                    "priority": "MEDIUM",
                    "estimated_duration": 0.1,
                }
            )

            # Analyze message type and content
            if hasattr(message, "action"):
                action = str(message.action).lower()

                # IO-bound operations
                if any(
                    keyword in action
                    for keyword in ["read", "write", "fetch", "save", "load"]
                ):
                    info["io_bound"] = True
                    info["cpu_affinity"] = self.hardware_topology.get_optimal_cores(
                        "io_bound"
                    )

                # CPU-bound operations
                elif any(
                    keyword in action
                    for keyword in ["compile", "analyze", "process", "optimize"]
                ):
                    info["cpu_bound"] = True
                    info["cpu_affinity"] = self.hardware_topology.get_optimal_cores(
                        "cpu_bound"
                    )

                # High priority operations
                if any(
                    keyword in action for keyword in ["critical", "urgent", "emergency"]
                ):
                    info["priority"] = "CRITICAL"
                    info["cpu_affinity"] = self.hardware_topology.get_optimal_cores(
                        "cpu_bound", "CRITICAL"
                    )

            return info

        finally:
            # Return info dict to pool after copying
            result = dict(info)
            dict_pool.return_object(info)
            return result

    async def _set_cpu_affinity(self, cpu_list: List[int]) -> None:
        """Set CPU affinity for current thread"""
        try:
            # This would require additional libraries for actual implementation
            # For now, just log the intention
            logger.debug(f"Setting CPU affinity to cores: {cpu_list}")
        except Exception as e:
            logger.debug(f"CPU affinity setting failed: {e}")

    async def _execute_io_bound(self, message: Any, connection: Connection) -> Any:
        """Execute IO-bound operation in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.io_executor, self._sync_io_operation, message, connection
        )

    async def _execute_cpu_bound(self, message: Any, connection: Connection) -> Any:
        """Execute CPU-bound operation in optimized thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.cpu_executor, self._sync_cpu_operation, message, connection
        )

    async def _execute_balanced(self, message: Any, connection: Connection) -> Any:
        """Execute balanced operation with async/await"""
        # Simulate agent execution with minimal overhead
        await asyncio.sleep(0.001)  # Minimal simulation

        return {
            "status": "completed",
            "message_id": getattr(message, "id", "unknown"),
            "connection_id": connection.id,
            "timestamp": time.time(),
        }

    def _sync_io_operation(self, message: Any, connection: Connection) -> Any:
        """Synchronous IO operation for thread pool execution"""
        # Simulate IO operation
        time.sleep(0.01)
        return {"status": "io_completed", "connection": connection.id}

    def _sync_cpu_operation(self, message: Any, connection: Connection) -> Any:
        """Synchronous CPU operation for thread pool execution"""
        # Simulate CPU-intensive operation
        if self.use_numpy and NUMPY_AVAILABLE:
            # Use NumPy for performance if available
            data = np.random.random(1000)
            result = np.mean(data)
            return {"status": "cpu_completed", "result": float(result)}
        else:
            # Fallback computation
            result = sum(range(1000)) / 1000
            return {"status": "cpu_completed", "result": result}

    # ========================================================================
    # MONITORING AND MAINTENANCE
    # ========================================================================

    async def _health_monitor(self) -> None:
        """Optimized health monitoring with minimal overhead"""
        while True:
            try:
                # Perform lightweight health checks
                await self._check_system_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)

    async def _performance_monitor(self) -> None:
        """Monitor performance metrics and detect anomalies"""
        while True:
            try:
                # Collect performance metrics
                metrics = await self._collect_performance_metrics()

                # Check for performance issues
                await self._analyze_performance(metrics)

                await asyncio.sleep(60)  # Monitor every minute
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(60)

    async def _cache_maintenance(self) -> None:
        """Maintain cache health and performance"""
        while True:
            try:
                # Clean expired entries
                await self._clean_expired_cache()

                # Log cache statistics
                stats = self.cache.get_stats()
                if stats["total_requests"] > 0:
                    logger.debug(
                        f"Cache stats: {stats['hit_rate']:.2%} hit rate, "
                        f"{stats['l1_size']} L1 entries"
                    )

                await asyncio.sleep(300)  # Maintain every 5 minutes
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
                await asyncio.sleep(300)

    async def _connection_pool_maintenance(self) -> None:
        """Maintain connection pool health"""
        while True:
            try:
                # Perform health check on connections
                health_info = await self.connection_pool.health_check()

                # Log pool statistics
                if health_info["total_pooled"] > 0:
                    logger.debug(
                        f"Connection pool: {health_info['healthy']} healthy, "
                        f"{health_info['active']} active"
                    )

                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error(f"Connection pool maintenance error: {e}")
                await asyncio.sleep(120)

    async def _check_system_health(self) -> None:
        """Lightweight system health check"""
        try:
            # Check queue sizes
            msg_queue_size = self.message_queue.qsize()
            priority_queue_size = self.high_priority_queue.qsize()

            if msg_queue_size > 5000:
                logger.warning(f"Message queue backlog: {msg_queue_size}")

            if priority_queue_size > 100:
                logger.warning(f"Priority queue backlog: {priority_queue_size}")

            # Check thread pool health
            if self.io_executor._threads:
                active_io_threads = len(
                    [t for t in self.io_executor._threads if t.is_alive()]
                )
                if active_io_threads < PerformanceConfig.MAX_WORKERS_IO * 0.5:
                    logger.warning(f"Low IO thread count: {active_io_threads}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive performance metrics"""
        metrics = dict_pool.get()

        try:
            # Basic metrics
            uptime = time.time() - self.start_time
            metrics.update(
                {
                    "uptime_seconds": uptime,
                    "messages_processed": self.metrics["messages_processed"],
                    "cache_hit_rate": self._calculate_cache_hit_rate(),
                    "avg_latency_ms": self._calculate_average_latency(),
                    "p95_latency_ms": self._calculate_p95_latency(),
                    "queue_sizes": {
                        "main": self.message_queue.qsize(),
                        "priority": self.high_priority_queue.qsize(),
                    },
                }
            )

            # Resource metrics
            if self.resource_monitor:
                resource_metrics = await self.resource_monitor.get_metrics()
                metrics["resources"] = resource_metrics

            # Connection pool metrics
            pool_health = await self.connection_pool.health_check()
            metrics["connection_pool"] = pool_health

            return dict(metrics)

        finally:
            dict_pool.return_object(metrics)

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        hits = self.metrics["cache_hits"]
        misses = self.metrics["cache_misses"]
        total = hits + misses
        return (hits / total) if total > 0 else 0.0

    def _calculate_average_latency(self) -> float:
        """Calculate average latency from recent samples"""
        if not self.latency_tracker:
            return 0.0
        return sum(self.latency_tracker) / len(self.latency_tracker)

    def _calculate_p95_latency(self) -> float:
        """Calculate 95th percentile latency"""
        if not self.latency_tracker:
            return 0.0

        sorted_latencies = sorted(self.latency_tracker)
        index = int(len(sorted_latencies) * 0.95)
        return (
            sorted_latencies[index]
            if index < len(sorted_latencies)
            else sorted_latencies[-1]
        )

    async def _analyze_performance(self, metrics: Dict[str, Any]) -> None:
        """Analyze performance and trigger optimizations"""
        # Check latency thresholds
        avg_latency = metrics.get("avg_latency_ms", 0)
        if avg_latency > PerformanceConfig.LATENCY_WARNING_MS:
            logger.warning(f"High average latency: {avg_latency:.2f}ms")
            await self._trigger_latency_optimization()

        # Check cache performance
        cache_hit_rate = metrics.get("cache_hit_rate", 0)
        if cache_hit_rate < 0.8:  # Less than 80% hit rate
            logger.warning(f"Low cache hit rate: {cache_hit_rate:.2%}")
            await self._trigger_cache_optimization()

        # Check resource usage
        resources = metrics.get("resources", {})
        if resources.get("memory_percent", 0) > PerformanceConfig.MEMORY_WARNING_PCT:
            logger.warning(f"High memory usage: {resources['memory_percent']:.1f}%")
            await self._trigger_memory_optimization()

    async def _trigger_latency_optimization(self) -> None:
        """Trigger latency optimization measures"""
        # Increase priority queue processing
        # Reduce batch sizes temporarily
        # Could adjust thread pool sizes here
        logger.info("Triggering latency optimization measures")

    async def _trigger_cache_optimization(self) -> None:
        """Trigger cache optimization measures"""
        # Adjust cache TTL
        # Increase cache sizes if memory allows
        logger.info("Triggering cache optimization measures")

    async def _trigger_memory_optimization(self) -> None:
        """Trigger memory optimization measures"""
        # Force cache cleanup
        await self._clean_expired_cache()
        # Could trigger garbage collection here
        logger.info("Triggering memory optimization measures")

    async def _clean_expired_cache(self) -> None:
        """Clean expired cache entries"""
        try:
            # Clean L1 cache
            expired_keys = []
            for key, entry in self.cache.l1_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache.l1_cache[key]

            if expired_keys:
                logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")

        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")

    # ========================================================================
    # PUBLIC API (ENHANCED VERSIONS)
    # ========================================================================

    async def execute_agent_optimized(
        self, agent_name: str, action: str, params: Dict = None
    ) -> Any:
        """Execute agent with full optimizations"""
        if params is None:
            params = dict_pool.get()
            should_return_params = True
        else:
            should_return_params = False

        try:
            start_time = time.time()

            # Create optimized message
            message = type(
                "Message",
                (),
                {
                    "target_agent": agent_name,
                    "action": action,
                    "params": params,
                    "id": f"{agent_name}_{int(time.time()*1000)}",
                    "priority": "MEDIUM",
                    "timestamp": start_time,
                },
            )()

            # Route to appropriate queue based on priority
            if getattr(message, "priority", "MEDIUM") == "CRITICAL":
                await self.high_priority_queue.put(message)
            else:
                await self.message_queue.put(message)

            # For demonstration, return immediately
            # In real implementation, would wait for result
            result = {
                "agent": agent_name,
                "action": action,
                "status": "queued",
                "message_id": message.id,
                "queued_at": start_time,
            }

            # Track metrics
            self.metrics["agent_invocations"] += 1

            return result

        finally:
            if should_return_params:
                dict_pool.return_object(params)

    def get_optimized_metrics(self) -> Dict[str, Any]:
        """Get comprehensive optimized metrics"""
        base_metrics = {
            "uptime_seconds": time.time() - self.start_time,
            "messages_processed": self.metrics["messages_processed"],
            "agent_invocations": self.metrics["agent_invocations"],
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "avg_latency_ms": self._calculate_average_latency(),
            "p95_latency_ms": self._calculate_p95_latency(),
        }

        # Add cache statistics
        cache_stats = self.cache.get_stats()
        base_metrics["cache"] = cache_stats

        # Add connection pool statistics
        pool_stats = {
            "active_connections": len(self.connection_pool.active_connections),
            "pool_stats": self.connection_pool.stats,
        }
        base_metrics["connection_pool"] = pool_stats

        # Add hardware topology info
        base_metrics["hardware"] = {
            "total_cores": self.hardware_topology.total_cores,
            "numa_nodes": len(self.hardware_topology.numa_nodes),
            "core_allocation": {
                k: len(v) for k, v in self.hardware_topology.core_allocation.items()
            },
        }

        return base_metrics

    async def shutdown(self) -> None:
        """Graceful shutdown with cleanup"""
        logger.info("Shutting down optimized orchestrator...")

        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Shutdown thread pools
        self.io_executor.shutdown(wait=True)
        self.cpu_executor.shutdown(wait=True)

        # Clean up resources
        if hasattr(self.cache, "cleanup"):
            await self.cache.cleanup()

        logger.info("✅ Optimized orchestrator shutdown complete")


# ============================================================================
# RESOURCE MONITORING
# ============================================================================


class ResourceMonitor:
    """System resource monitoring for optimization"""

    def __init__(self):
        self.process = psutil.Process()

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics"""
        try:
            # CPU metrics
            cpu_percent = self.process.cpu_percent()
            cpu_times = self.process.cpu_times()

            # Memory metrics
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            # System metrics
            system_cpu = psutil.cpu_percent(interval=None)
            system_memory = psutil.virtual_memory()

            return {
                "process": {
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "memory_percent": memory_percent,
                    "threads": self.process.num_threads(),
                    "cpu_user_time": cpu_times.user,
                    "cpu_system_time": cpu_times.system,
                },
                "system": {
                    "cpu_percent": system_cpu,
                    "memory_percent": system_memory.percent,
                    "memory_available_mb": system_memory.available / 1024 / 1024,
                    "load_average": (
                        os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0]
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")
            return {}


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Maintain backward compatibility
ProductionOrchestrator = OptimizedProductionOrchestrator

# Legacy imports from original
from dataclasses import dataclass, field
from enum import Enum, IntEnum


class ExecutionMode(Enum):
    """How commands should be executed"""

    INTELLIGENT = "intelligent"
    REDUNDANT = "redundant"
    CONSENSUS = "consensus"
    SPEED_CRITICAL = "speed"
    PYTHON_ONLY = "python_only"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class Priority(IntEnum):
    """Execution priority levels"""

    CRITICAL = 1
    HIGH = 3
    MEDIUM = 5
    LOW = 7
    BACKGROUND = 10


class CommandType(Enum):
    """Command abstraction levels"""

    ATOMIC = "atomic"
    SEQUENCE = "sequence"
    WORKFLOW = "workflow"
    ORCHESTRATION = "orchestration"
    CAMPAIGN = "campaign"


class HardwareAffinity(Enum):
    """Hardware affinity settings"""

    AUTO = "auto"
    P_CORE = "p_core"
    P_CORE_ULTRA = "p_core_ultra"
    E_CORE = "e_core"
    LP_E_CORE = "lp_e_core"


@dataclass
class CommandStep:
    """Single command step"""

    agent: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    retry_count: int = 3
    fallback: Optional["CommandStep"] = None
    hardware_affinity: HardwareAffinity = HardwareAffinity.AUTO
    dependencies: List[str] = field(default_factory=list)


@dataclass
class CommandSet:
    """Collection of command steps"""

    name: str
    description: str
    steps: List[CommandStep]
    mode: ExecutionMode = ExecutionMode.INTELLIGENT
    priority: Priority = Priority.MEDIUM
    type: CommandType = CommandType.WORKFLOW
    timeout: float = 300.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    "OptimizedProductionOrchestrator",
    "ProductionOrchestrator",  # Backward compatibility
    "ConnectionPool",
    "MultiLevelCache",
    "ObjectPool",
    "OptimizedMeteorLakeTopology",
    "PerformanceConfig",
    "ResourceMonitor",
    "ExecutionMode",
    "Priority",
    "CommandType",
    "HardwareAffinity",
    "CommandStep",
    "CommandSet",
]

if __name__ == "__main__":

    async def test_optimized_orchestrator():
        """Test the optimized orchestrator"""
        orchestrator = OptimizedProductionOrchestrator()

        try:
            # Initialize
            success = await orchestrator.initialize()
            if not success:
                print("❌ Failed to initialize orchestrator")
                return

            print("✅ Optimized orchestrator initialized")

            # Test agent execution
            result = await orchestrator.execute_agent_optimized(
                "director", "create_plan", {"project": "test_optimization"}
            )
            print(f"✅ Agent execution result: {result}")

            # Get metrics
            metrics = orchestrator.get_optimized_metrics()
            print(f"📊 Performance metrics:")
            print(f"   Cache hit rate: {metrics['cache_hit_rate']:.2%}")
            print(f"   Average latency: {metrics['avg_latency_ms']:.2f}ms")
            print(f"   P95 latency: {metrics['p95_latency_ms']:.2f}ms")
            print(f"   Hardware cores: {metrics['hardware']['total_cores']}")

            # Wait a bit to see background tasks
            await asyncio.sleep(2)

        finally:
            await orchestrator.shutdown()

    # Run test
    asyncio.run(test_optimized_orchestrator())
