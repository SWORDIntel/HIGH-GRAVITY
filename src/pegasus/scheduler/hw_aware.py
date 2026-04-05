import psutil

class HardwareScheduler:
    def get_optimal_backend(self):
        # Checks for NPU/AMX support
        cpu_flags = open("/proc/cpuinfo").read()
        if "avx512" in cpu_flags:
            return "AVX512_PARALLEL"
        return "CPU_SCALAR"
