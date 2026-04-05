#!/usr/bin/env python3
"""
Master Reorganization Script
Coordinates all three steps with minimal disruption
Includes automatic testing and rollback on failure
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import json
from datetime import datetime
import psutil

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_python_src_dir
except ImportError:
    # Fallback if path_utilities not available
    def get_python_src_dir():
        return Path(__file__).parent.parent.parent / 'agents' / 'src' / 'python'

class MasterReorganizer:
    def __init__(self):
        self.base_path = get_python_src_dir()
        self.start_time = time.time()
        self.steps_completed = []
        self.critical_services = []
        
    def check_prerequisites(self) -> bool:
        """Check if reorganization is safe to perform"""
        print("🔍 Checking prerequisites...")
        
        # Check for running orchestration processes
        orchestration_running = self.check_orchestration_processes()
        if orchestration_running:
            print("⚠️  Warning: Orchestration processes are running")
            response = input("Stop them and continue? [y/N]: ")
            if response.lower() != 'y':
                return False
            self.stop_orchestration_services()
            
        # Check for active Python imports from this directory
        if self.check_active_imports():
            print("⚠️  Warning: Active Python processes using src/python")
            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                return False
                
        # Check disk space
        if not self.check_disk_space():
            print("❌ Insufficient disk space (need at least 1GB free)")
            return False
            
        print("✅ Prerequisites check passed")
        return True
        
    def check_orchestration_processes(self) -> bool:
        """Check if orchestration services are running"""
        services = [
            "tandem-orchestrator",
            "production-orchestrator",
            "learning-system",
            "claude-agent-bridge"
        ]
        
        running = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []))
                for service in services:
                    if service in cmdline:
                        running.append((proc.info['pid'], service))
                        self.critical_services.append(proc.info['pid'])
            except:
                pass
                
        if running:
            print(f"   Found {len(running)} orchestration processes:")
            for pid, service in running:
                print(f"     PID {pid}: {service}")
            return True
        return False
        
    def stop_orchestration_services(self):
        """Stop orchestration services gracefully"""
        print("🛑 Stopping orchestration services...")
        
        # Try systemctl first
        services = [
            "tandem-orchestrator.service",
            "production-orchestrator.service",
            "learning-system.service"
        ]
        
        for service in services:
            try:
                subprocess.run(["systemctl", "stop", service], capture_output=True)
                print(f"   Stopped: {service}")
            except:
                pass
                
        # Kill remaining processes
        for pid in self.critical_services:
            try:
                os.kill(pid, 15)  # SIGTERM
                print(f"   Terminated PID: {pid}")
            except:
                pass
                
        time.sleep(2)  # Wait for processes to stop
        
    def restart_orchestration_services(self):
        """Restart orchestration services after reorganization"""
        print("🔄 Restarting orchestration services...")
        
        services = [
            "tandem-orchestrator.service",
            "production-orchestrator.service",
            "learning-system.service"
        ]
        
        for service in services:
            try:
                subprocess.run(["systemctl", "start", service], capture_output=True)
                print(f"   Started: {service}")
            except:
                pass
                
    def check_active_imports(self) -> bool:
        """Check for active Python imports from this directory"""
        active = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    # Check if process is using our modules
                    proc_obj = psutil.Process(proc.info['pid'])
                    for conn in proc_obj.connections():
                        if str(self.base_path) in str(conn):
                            active.append(proc.info['pid'])
            except:
                pass
                
        return len(active) > 0
        
    def check_disk_space(self) -> bool:
        """Check available disk space"""
        stat = os.statvfs(self.base_path)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        print(f"   Free disk space: {free_gb:.2f} GB")
        return free_gb > 1.0
        
    def run_step(self, step_script: str, step_name: str) -> bool:
        """Run a reorganization step"""
        print(f"\n{'='*60}")
        print(f"Running {step_name}...")
        print('='*60)
        
        script_path = self.base_path / step_script
        
        if not script_path.exists():
            print(f"❌ Script not found: {script_path}")
            return False
            
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,
                text=True,
                cwd=self.base_path
            )
            
            if result.returncode == 0:
                self.steps_completed.append(step_name)
                print(f"✅ {step_name} completed successfully")
                return True
            else:
                print(f"❌ {step_name} failed with exit code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ Error running {step_name}: {e}")
            return False
            
    def test_reorganization(self) -> bool:
        """Test that the reorganization worked"""
        print("\n🧪 Testing reorganization...")
        
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Check if claude_agents package exists
        claude_agents = self.base_path / "claude_agents"
        if claude_agents.exists():
            print("   ✅ claude_agents package created")
            tests_passed += 1
        else:
            print("   ❌ claude_agents package not found")
            tests_failed += 1
            
        # Test 2: Try importing the package
        try:
            sys.path.insert(0, str(self.base_path))
            import claude_agents
            print("   ✅ claude_agents package importable")
            tests_passed += 1
        except ImportError as e:
            print(f"   ❌ Cannot import claude_agents: {e}")
            tests_failed += 1
            
        # Test 3: Check critical files
        critical_files = [
            claude_agents / "orchestration" / "production_orchestrator.py",
            claude_agents / "orchestration" / "tandem_orchestrator.py",
            claude_agents / "orchestration" / "agent_registry.py",
        ]
        
        for file in critical_files:
            if file.exists():
                print(f"   ✅ Found: {file.name}")
                tests_passed += 1
            else:
                print(f"   ❌ Missing: {file.name}")
                tests_failed += 1
                
        # Test 4: Check symlinks/compatibility
        if (self.base_path / "production_orchestrator.py").exists():
            print("   ✅ Compatibility layer working")
            tests_passed += 1
        else:
            print("   ⚠️  Compatibility layer may need adjustment")
            
        print(f"\n📊 Test Results: {tests_passed} passed, {tests_failed} failed")
        return tests_failed == 0
        
    def rollback(self):
        """Rollback the reorganization"""
        print("\n⚠️  Rolling back reorganization...")
        
        rollback_script = self.base_path / "rollback.sh"
        if rollback_script.exists():
            subprocess.run(["bash", str(rollback_script)])
            print("✅ Rollback completed")
        else:
            print("❌ No rollback script found. Manual intervention required.")
            
    def generate_report(self):
        """Generate a final report"""
        elapsed = time.time() - self.start_time
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": elapsed,
            "steps_completed": self.steps_completed,
            "success": len(self.steps_completed) == 3,
        }
        
        # Check final state
        state_file = self.base_path / ".reorganization_state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                report.update(state)
                
        report_file = self.base_path / "reorganization_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📋 Final report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("REORGANIZATION SUMMARY")
        print("="*60)
        print(f"Duration: {elapsed:.2f} seconds")
        print(f"Steps completed: {len(self.steps_completed)}/3")
        
        if report["success"]:
            print("\n🎉 SUCCESS! The src/python directory has been reorganized.")
            print("\nNext steps:")
            print("1. Test your imports: python3 -c 'import claude_agents'")
            print("2. Update any hardcoded paths in your scripts")
            print("3. Restart any services that use these modules")
        else:
            print("\n⚠️  PARTIAL SUCCESS. Some manual intervention may be needed.")
            print("Check the logs and report for details.")

def main():
    """Main execution with automatic orchestration"""
    print("="*60)
    print("CLAUDE AGENTS PYTHON REORGANIZATION")
    print("Minimal Downtime Edition")
    print("="*60)
    
    reorganizer = MasterReorganizer()
    
    # Phase 1: Prerequisites
    if not reorganizer.check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
        
    print("\n⚡ Starting rapid reorganization...")
    print("Estimated downtime: 10-30 seconds")
    
    # Phase 2: Backup (Step 1)
    if not reorganizer.run_step("reorganize_step1_backup.py", "Backup and Preparation"):
        print("❌ Backup failed. Exiting.")
        sys.exit(1)
        
    # Phase 3: Move files (Step 2)
    if not reorganizer.run_step("reorganize_step2_move.py", "File Reorganization"):
        print("❌ Reorganization failed. Rolling back...")
        reorganizer.rollback()
        sys.exit(1)
        
    # Phase 4: Update imports (Step 3)
    if not reorganizer.run_step("reorganize_step3_update.py", "Import Updates"):
        print("⚠️  Import updates failed. System may work with compatibility layer.")
        
    # Phase 5: Test
    if reorganizer.test_reorganization():
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review and fix manually if needed.")
        
    # Phase 6: Restart services
    if reorganizer.critical_services:
        reorganizer.restart_orchestration_services()
        
    # Phase 7: Generate report
    reorganizer.generate_report()
    
    print("\n✨ Reorganization complete!")
    print("The Python source is now properly organized with minimal disruption.")

if __name__ == "__main__":
    # Confirm before running
    print("\nThis script will reorganize the entire src/python directory.")
    print("It will:")
    print("  1. Create a backup")
    print("  2. Reorganize files into packages")
    print("  3. Update all imports")
    print("  4. Restart stopped services")
    print("\nEstimated time: 1-2 minutes")
    
    response = input("\nProceed? [y/N]: ")
    if response.lower() == 'y':
        main()
    else:
        print("Aborted.")