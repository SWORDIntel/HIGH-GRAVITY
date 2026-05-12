import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HmiContractTests(unittest.TestCase):
    def test_hmi_build_check_compiles_shader_and_validates_push_layout(self):
        result = subprocess.run(
            ["make", "-C", "src/hmi", "check"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hmi_push_size=96", result.stdout)
        self.assertTrue((ROOT / "src/hmi/build/shaders/dashboard.frag.spv").exists())
        self.assertTrue((ROOT / "src/hmi/build/shaders/dashboard.vert.spv").exists())

    def test_hmi_docs_publish_exact_offline_glslc_commands(self):
        result = subprocess.run(
            ["make", "-C", "src/hmi", "print-compile-commands"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("glslc -fshader-stage=vert", result.stdout)
        self.assertIn("glslc -fshader-stage=frag", result.stdout)


if __name__ == "__main__":
    unittest.main()
