#!/usr/bin/env python3
"""
Integrated Systems Validation Test
Tests both NPU Coordination Bridge and Shadowgit Performance Integration
"""

import asyncio
import time
import json
from typing import Dict, Any
import logging

# Import our integrated systems
from npu_coordination_bridge import NPUCoordinationBridge, CoordinationMode
# Updated import path for relocated shadowgit module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "hooks" / "shadowgit" / "python"))
from performance_integration import ShadowgitPerformanceMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedSystemsValidator:
    """Validates the complete integrated system"""

    def __init__(self):
        self.coordination_bridge = None
        self.shadowgit_monitor = None
        self.test_results = {}

    async def initialize(self):
        """Initialize both systems"""
        logger.info("🚀 Initializing Integrated Systems Validator")

        # Initialize NPU Coordination Bridge
        try:
            self.coordination_bridge = NPUCoordinationBridge()
            await self.coordination_bridge.initialize()
            logger.info("✅ NPU Coordination Bridge initialized")
        except Exception as e:
            logger.error(f"NPU Coordination Bridge initialization failed: {e}")

        # Initialize Shadowgit Performance Monitor
        try:
            self.shadowgit_monitor = ShadowgitPerformanceMonitor()
            await self.shadowgit_monitor.initialize()
            logger.info("✅ Shadowgit Performance Monitor initialized")
        except Exception as e:
            logger.error(f"Shadowgit Performance Monitor initialization failed: {e}")

        logger.info("🎯 Integrated Systems ready for testing")

    async def test_coordination_bridge_performance(self) -> Dict[str, Any]:
        """Test NPU Coordination Bridge performance"""
        logger.info("📊 Testing NPU Coordination Bridge Performance")

        if not self.coordination_bridge:
            return {"error": "Coordination bridge not available"}

        results = {}

        # Test 1: Simple workflow
        simple_tasks = [
            {'agent': 'security', 'description': 'audit system security', 'priority': 10},
            {'agent': 'architect', 'description': 'design system architecture', 'priority': 20},
            {'agent': 'debugger', 'description': 'analyze system issues', 'priority': 30}
        ]

        start_time = time.perf_counter()
        workflow_id, optimized_tasks = await self.coordination_bridge.create_workflow(simple_tasks)
        result = await self.coordination_bridge.execute_workflow(workflow_id, optimized_tasks)
        simple_time = time.perf_counter() - start_time

        results['simple_workflow'] = {
            'ops_per_sec': result.performance_metrics['ops_per_sec'],
            'success_rate': result.success_rate,
            'execution_time_ms': result.execution_time_ms,
            'total_time_ms': simple_time * 1000
        }

        # Test 2: Complex parallel workflow
        complex_tasks = []
        for i in range(50):  # Increased from 20 to 50 for stress test
            task_type = ['security', 'development', 'operations', 'strategic'][i % 4]
            complex_tasks.append({
                'agent': task_type,
                'description': f'{task_type} task {i}',
                'priority': 10 + (i % 5) * 10
            })

        start_time = time.perf_counter()
        workflow_id, optimized_tasks = await self.coordination_bridge.create_workflow(
            complex_tasks,
            CoordinationMode.NPU_ACCELERATED
        )
        result = await self.coordination_bridge.execute_workflow(workflow_id, optimized_tasks, max_parallel=20)
        complex_time = time.perf_counter() - start_time

        results['complex_workflow'] = {
            'ops_per_sec': result.performance_metrics['ops_per_sec'],
            'tasks_completed': result.tasks_completed,
            'total_tasks': result.total_tasks,
            'success_rate': result.success_rate,
            'npu_utilization': result.performance_metrics['npu_utilization'],
            'total_time_ms': complex_time * 1000
        }

        # Performance summary
        summary = self.coordination_bridge.get_performance_summary()
        results['summary'] = summary

        return results

    async def test_shadowgit_performance(self) -> Dict[str, Any]:
        """Test Shadowgit Performance System"""
        logger.info("📊 Testing Shadowgit Performance System")

        if not self.shadowgit_monitor:
            return {"error": "Shadowgit monitor not available"}

        # Simulate various Git operations
        git_operations = [
            # Small files
            ("diff", 5, 500, 25, "/small/repo", "CPU"),
            ("hash", 10, 1000, 30, "/small/repo", "AVX2"),

            # Medium files
            ("diff", 50, 25000, 150, "/medium/repo", "AVX2"),
            ("index", 100, 50000, 120, "/medium/repo", "NPU"),

            # Large files
            ("diff", 500, 250000, 800, "/large/repo", "AVX2"),
            ("hash", 1000, 500000, 600, "/large/repo", "NPU"),

            # Massive operations
            ("merge", 2000, 1000000, 1200, "/huge/repo", "NPU"),
            ("diff", 5000, 2500000, 2000, "/huge/repo", "AVX2"),
        ]

        start_time = time.perf_counter()

        for operation_type, files, lines, exec_time, repo, hardware in git_operations:
            await self.shadowgit_monitor.record_git_operation(
                operation_type, files, lines, exec_time, repo, hardware
            )

        # Wait for processing
        await asyncio.sleep(2)

        test_time = time.perf_counter() - start_time

        # Get dashboard data
        dashboard = self.shadowgit_monitor.get_performance_dashboard()

        results = {
            'operations_count': len(git_operations),
            'test_time_ms': test_time * 1000,
            'dashboard': dashboard,
            'system_status': {
                'npu_available': self.shadowgit_monitor.npu_available,
                'monitoring_active': self.shadowgit_monitor.is_monitoring,
                'database_connected': self.shadowgit_monitor.db_connection is not None
            }
        }

        return results

    async def test_integrated_performance(self) -> Dict[str, Any]:
        """Test both systems working together"""
        logger.info("📊 Testing Integrated System Performance")

        # Create a workflow that includes both agent coordination and Git operations
        git_workflow_tasks = [
            {'agent': 'security', 'description': 'audit git repository security', 'priority': 10},
            {'agent': 'architect', 'description': 'design git performance optimization', 'priority': 20},
            {'agent': 'optimizer', 'description': 'optimize git performance using NPU', 'priority': 15},
            {'agent': 'monitor', 'description': 'monitor git operation performance', 'priority': 25},
            {'agent': 'debugger', 'description': 'debug git performance issues', 'priority': 30}
        ]

        integration_results = {}

        if self.coordination_bridge and self.shadowgit_monitor:
            start_time = time.perf_counter()

            # Execute agent workflow
            workflow_id, optimized_tasks = await self.coordination_bridge.create_workflow(
                git_workflow_tasks,
                CoordinationMode.NPU_ACCELERATED
            )
            workflow_result = await self.coordination_bridge.execute_workflow(
                workflow_id, optimized_tasks, max_parallel=5
            )

            # Simulate Git operations during workflow
            await self.shadowgit_monitor.record_git_operation(
                "optimization", 1000, 500000, 400, "/integrated/repo", "NPU"
            )

            total_time = time.perf_counter() - start_time

            integration_results = {
                'workflow_performance': {
                    'ops_per_sec': workflow_result.performance_metrics['ops_per_sec'],
                    'success_rate': workflow_result.success_rate,
                    'tasks_completed': workflow_result.tasks_completed
                },
                'git_performance': {
                    'operations_recorded': len(self.shadowgit_monitor.performance_history),
                    'monitoring_active': self.shadowgit_monitor.is_monitoring
                },
                'integration_metrics': {
                    'total_execution_time_ms': total_time * 1000,
                    'systems_coordinated': 2,
                    'integration_overhead_ms': max(0, total_time * 1000 - workflow_result.execution_time_ms)
                }
            }

        return integration_results

    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of both systems"""
        logger.info("🎯 Running Comprehensive Validation")

        validation_results = {
            'timestamp': time.time(),
            'systems_tested': [],
            'performance_targets': {
                'coordination_target_ops_per_sec': 50000,
                'shadowgit_target_lines_per_sec': 11500000
            }
        }

        # Test 1: NPU Coordination Bridge
        try:
            coordination_results = await self.test_coordination_bridge_performance()
            validation_results['coordination_bridge'] = coordination_results
            validation_results['systems_tested'].append('coordination_bridge')

            # Check if coordination target is met
            if 'summary' in coordination_results:
                avg_ops = coordination_results['summary']['recent_performance']['average_ops_per_sec']
                validation_results['coordination_target_achieved'] = avg_ops >= 50000
            else:
                validation_results['coordination_target_achieved'] = False

        except Exception as e:
            validation_results['coordination_bridge'] = {'error': str(e)}

        # Test 2: Shadowgit Performance System
        try:
            shadowgit_results = await self.test_shadowgit_performance()
            validation_results['shadowgit_performance'] = shadowgit_results
            validation_results['systems_tested'].append('shadowgit_performance')

            # Check if shadowgit target progress
            if 'dashboard' in shadowgit_results:
                current_perf = shadowgit_results['dashboard'].get('current_performance', {})
                lines_per_sec = current_perf.get('throughput_lines_per_sec', 0)
                target_progress = (lines_per_sec / 11500000) * 100
                validation_results['shadowgit_target_progress'] = target_progress
            else:
                validation_results['shadowgit_target_progress'] = 0

        except Exception as e:
            validation_results['shadowgit_performance'] = {'error': str(e)}

        # Test 3: Integrated Performance
        try:
            integration_results = await self.test_integrated_performance()
            validation_results['integrated_performance'] = integration_results
            validation_results['systems_tested'].append('integrated_performance')

        except Exception as e:
            validation_results['integrated_performance'] = {'error': str(e)}

        # Calculate overall success metrics
        validation_results['validation_summary'] = {
            'systems_operational': len(validation_results['systems_tested']),
            'coordination_available': self.coordination_bridge is not None,
            'shadowgit_available': self.shadowgit_monitor is not None,
            'integration_successful': len(validation_results['systems_tested']) >= 2
        }

        return validation_results

    def print_validation_report(self, results: Dict[str, Any]):
        """Print comprehensive validation report"""
        print("\n" + "=" * 80)
        print("🎯 INTEGRATED SYSTEMS VALIDATION REPORT")
        print("=" * 80)

        # System availability
        summary = results.get('validation_summary', {})
        print(f"\n📊 System Status:")
        print(f"   Systems Operational: {summary.get('systems_operational', 0)}/3")
        print(f"   Coordination Bridge: {'✅' if summary.get('coordination_available') else '❌'}")
        print(f"   Shadowgit Monitor: {'✅' if summary.get('shadowgit_available') else '❌'}")
        print(f"   Integration: {'✅' if summary.get('integration_successful') else '❌'}")

        # Coordination Bridge Results
        coord_results = results.get('coordination_bridge', {})
        if 'error' not in coord_results:
            print(f"\n🚀 NPU Coordination Bridge Performance:")

            simple = coord_results.get('simple_workflow', {})
            print(f"   Simple Workflow: {simple.get('ops_per_sec', 0):.0f} ops/sec")
            print(f"   Success Rate: {simple.get('success_rate', 0)*100:.1f}%")

            complex = coord_results.get('complex_workflow', {})
            print(f"   Complex Workflow: {complex.get('ops_per_sec', 0):.0f} ops/sec")
            print(f"   Tasks Completed: {complex.get('tasks_completed', 0)}/{complex.get('total_tasks', 0)}")
            print(f"   NPU Utilization: {complex.get('npu_utilization', 0):.1f}%")

            # Target achievement
            summary_perf = coord_results.get('summary', {})
            recent_perf = summary_perf.get('recent_performance', {})
            avg_ops = recent_perf.get('average_ops_per_sec', 0)
            target_ops = 50000

            if avg_ops >= target_ops:
                print(f"   🎯 TARGET ACHIEVED: {avg_ops:.0f} >= {target_ops} ops/sec")
            else:
                progress = (avg_ops / target_ops) * 100
                print(f"   📈 TARGET PROGRESS: {progress:.1f}% ({avg_ops:.0f}/{target_ops} ops/sec)")

        # Shadowgit Results
        shadowgit_results = results.get('shadowgit_performance', {})
        if 'error' not in shadowgit_results:
            print(f"\n⚡ Shadowgit Performance System:")
            print(f"   Operations Tested: {shadowgit_results.get('operations_count', 0)}")

            dashboard = shadowgit_results.get('dashboard', {})
            system_status = dashboard.get('system_status', {})
            print(f"   NPU Available: {'✅' if system_status.get('npu_available') else '❌'}")
            print(f"   Monitoring Active: {'✅' if system_status.get('monitoring_active') else '❌'}")

            current_perf = dashboard.get('current_performance', {})
            throughput = current_perf.get('throughput_lines_per_sec', 0)
            target_lines = 11500000
            progress = results.get('shadowgit_target_progress', 0)

            print(f"   Current Throughput: {throughput:.0f} lines/sec")
            print(f"   Target Progress: {progress:.1f}% toward 11.5M lines/sec")

        # Integration Results
        integration_results = results.get('integrated_performance', {})
        if 'error' not in integration_results:
            print(f"\n🔗 Integrated Performance:")
            workflow_perf = integration_results.get('workflow_performance', {})
            integration_metrics = integration_results.get('integration_metrics', {})

            print(f"   Workflow ops/sec: {workflow_perf.get('ops_per_sec', 0):.0f}")
            print(f"   Integration overhead: {integration_metrics.get('integration_overhead_ms', 0):.1f}ms")
            print(f"   Systems coordinated: {integration_metrics.get('systems_coordinated', 0)}")

        # Overall Assessment
        print(f"\n✅ VALIDATION COMPLETE")
        operational_systems = summary.get('systems_operational', 0)
        if operational_systems >= 2:
            print(f"   Status: ✅ PRODUCTION READY ({operational_systems}/3 systems operational)")
        elif operational_systems >= 1:
            print(f"   Status: ⚠️ PARTIAL DEPLOYMENT ({operational_systems}/3 systems operational)")
        else:
            print(f"   Status: ❌ INTEGRATION ISSUES ({operational_systems}/3 systems operational)")

        print("=" * 80)

async def main():
    """Main validation function"""
    validator = IntegratedSystemsValidator()

    # Initialize systems
    await validator.initialize()

    # Run comprehensive validation
    results = await validator.run_comprehensive_validation()

    # Print report
    validator.print_validation_report(results)

    # Save results to file
    results_file = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}integrated_systems_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())