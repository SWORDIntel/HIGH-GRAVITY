import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "src" / "hmi"
SHADER = HMI / "shaders" / "dashboard.frag"
PUSH = HMI / "include" / "hmi_push.hpp"
INGEST = HMI / "include" / "hmi_vulkan_ingest.hpp"


class HmiProceduralContractTests(unittest.TestCase):
    def test_shader_is_offline_branchless_sdf_contract(self):
        source = SHADER.read_text(encoding="utf-8")

        self.assertIn("#version 450", source)
        self.assertIn("layout(push_constant)", source)
        self.assertIn("gl_FragCoord.xy / res", source)
        self.assertIn("smoothstep", source)
        self.assertIn("sd_box", source)
        self.assertIn("sd_segment", source)
        self.assertIn("ring(", source)
        self.assertIn("mix(", source)
        self.assertIn("step(", source)
        self.assertNotIn("if (", source)
        self.assertNotIn("else", source)
        self.assertNotIn("sampler", source)
        self.assertNotIn(".png", source)
        self.assertNotIn(".jpg", source)

    def test_ingest_documents_offline_glslc_command(self):
        ingest = (HMI / "README.md").read_text(encoding="utf-8")

        self.assertIn("glslc -fshader-stage=frag", ingest)
        self.assertIn("src/hmi/shaders/dashboard.frag", ingest)
        self.assertIn("src/hmi/build/shaders/dashboard.frag.spv", ingest)

    def test_cpp_push_constant_layout_compiles_without_vulkan(self):
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            self.skipTest("C++ compiler unavailable for HMI layout validation")

        program = textwrap.dedent(
            """
            #include "hmi_push.hpp"
            #include "hmi_vulkan_ingest.hpp"

            int main() {
                using hg::hmi::HmiPush;
                static_assert(sizeof(HmiPush) == 96, "size");
                static_assert(alignof(HmiPush) == 16, "align");
                static_assert(hg::hmi::hmi_push_constant_range().size == 96, "range");
                static_assert(hg::hmi::hmi_push_constant_range().size <= 128, "bounded");
                HmiPush push{};
                push.resolution_time_health[0] = 1920.0F;
                return push.resolution_time_health[0] == 1920.0F ? 0 : 1;
            }
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "check_hmi.cpp"
            binary = Path(tmpdir) / "check_hmi"
            source.write_text(program, encoding="utf-8")
            subprocess.run(
                [
                    compiler,
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    f"-I{HMI / 'include'}",
                    str(source),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_shader_compiles_when_glslc_is_available(self):
        glslc = shutil.which("glslc")
        if not glslc:
            self.skipTest("glslc unavailable; static shader contract still validated")

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "dashboard.frag.spv"
            subprocess.run(
                [
                    glslc,
                    "-fshader-stage=frag",
                    str(SHADER),
                    "-o",
                    str(out),
                ],
                check=True,
            )
            self.assertGreater(out.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
