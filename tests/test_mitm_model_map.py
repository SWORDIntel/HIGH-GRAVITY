#!/usr/bin/env python3
"""
Offline unit tests for MITMBridge tier selection and premium model injection.

These tests do NOT require a running proxy. They import MITMBridge directly
and assert that the 2026 (fast, deep) tiered mapping behaves as documented.
"""

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    proxy_path = repo_root / "tools" / "integration" / "highgravity_proxy.py"
    spec = importlib.util.spec_from_file_location("highgravity_proxy", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["highgravity_proxy"] = module
    spec.loader.exec_module(module)
    return module


class MITMModelMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()
        cls.bridge = cls.proxy.MITMBridge()

    # --- tier selector ------------------------------------------------------

    def test_tier_flash_is_fast_by_default(self):
        self.assertEqual(self.bridge._select_tier("hello", "gemini-2.5-flash"), "fast")

    def test_tier_pro_is_deep_by_default(self):
        self.assertEqual(self.bridge._select_tier("hello", "gemini-2.5-pro"), "deep")

    def test_tier_deep_keyword_upgrades_fast(self):
        self.assertEqual(
            self.bridge._select_tier("please debug the root cause", "gpt-4o-mini"),
            "deep",
        )

    def test_tier_long_context_upgrades_to_deep(self):
        prompt = "x" * 7000
        self.assertEqual(self.bridge._select_tier(prompt, "gpt-4o-mini"), "deep")

    # --- gemini upgrades ----------------------------------------------------

    def test_gemini_1_5_pro_upgrades_to_3_pro_preview_on_deep(self):
        body = {
            "model": "gemini-1.5-pro",
            "contents": [{"parts": [{"text": "Audit this architecture for vulnerabilities"}]}],
        }
        self.bridge.inject_premium_model(body, "gemini")
        self.assertEqual(body["model"], "gemini-3-pro-preview")

    def test_gemini_flash_stays_on_fast_tier(self):
        body = {
            "model": "gemini-1.5-flash",
            "contents": [{"parts": [{"text": "hi"}]}],
        }
        self.bridge.inject_premium_model(body, "gemini")
        self.assertEqual(body["model"], "gemini-2.5-flash")

    def test_gemini_pro_plain_prompt_uses_fast_2_5_pro(self):
        # "pro" -> default deep, but no deep keyword + short prompt still keeps
        # default_tier=deep because the *model* name includes "pro".
        body = {
            "model": "gemini-pro",
            "contents": [{"parts": [{"text": "hi"}]}],
        }
        self.bridge.inject_premium_model(body, "gemini")
        self.assertEqual(body["model"], "gemini-3-pro-preview")

    # --- codex upgrades -----------------------------------------------------

    def test_davinci_codex_fast_routes_to_spark(self):
        body = {"model": "davinci-codex", "prompt": "def hello():"}
        self.bridge.inject_premium_model(body, "codex")
        self.assertEqual(body["model"], "gpt-5.3-codex-spark")

    def test_davinci_codex_deep_routes_to_codex_max(self):
        body = {
            "model": "davinci-codex",
            "prompt": "Refactor and audit this module for the root cause of the regression",
        }
        self.bridge.inject_premium_model(body, "codex")
        self.assertEqual(body["model"], "gpt-5.1-codex-max")

    # --- openai upgrades ----------------------------------------------------

    def test_gpt_4o_mini_beats_gpt_4_in_longest_match(self):
        # gpt-4o-mini should match the gpt-4o-mini entry, not gpt-4.
        body = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
        }
        self.bridge.inject_premium_model(body, "openai")
        self.assertEqual(body["model"], "gpt-5.4-mini")

    def test_gpt_4o_deep_routes_to_gpt_5_2(self):
        body = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Design and architect a distributed system"}],
        }
        self.bridge.inject_premium_model(body, "openai")
        self.assertEqual(body["model"], "gpt-5.2")

    def test_o3_deep_routes_to_codex_max(self):
        body = {
            "model": "o3",
            "messages": [{"role": "user", "content": "Prove this complex theorem"}],
        }
        self.bridge.inject_premium_model(body, "openai")
        self.assertEqual(body["model"], "gpt-5.1-codex-max")

    # --- 4-tier thinking-level selection ------------------------------------

    def test_thinking_level_short_fast_prompt_is_low(self):
        self.assertEqual(
            self.bridge._select_thinking_level("hi", "gpt-4o-mini"),
            "low",
        )

    def test_thinking_level_long_fast_prompt_is_medium(self):
        prompt = "Please write a small helper function that " + ("x " * 200)
        self.assertEqual(
            self.bridge._select_thinking_level(prompt, "gpt-4o-mini"),
            "medium",
        )

    def test_thinking_level_deep_keyword_is_high(self):
        self.assertEqual(
            self.bridge._select_thinking_level("debug root cause", "gpt-5.4"),
            "high",
        )

    def test_thinking_level_xhigh_keyword_is_xhigh(self):
        self.assertEqual(
            self.bridge._select_thinking_level(
                "Give me an exhaustive root cause analysis", "gpt-5.4"
            ),
            "xhigh",
        )

    def test_thinking_level_very_long_prompt_is_xhigh(self):
        self.assertEqual(
            self.bridge._select_thinking_level("x" * 16500, "gpt-5.4"),
            "xhigh",
        )

    # --- thinking-level injection (proxy mutation) -------------------------

    def test_openai_reasoning_effort_high_for_deep_keywords(self):
        body = {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "debug root cause"}],
        }
        self.bridge.inject_thinking_level(body, "openai")
        self.assertEqual(body["reasoning_effort"], "high")

    def test_openai_reasoning_effort_xhigh_for_xhigh_keywords(self):
        body = {
            "model": "gpt-5.1-codex-max",
            "messages": [{"role": "user", "content": "Please prove correctness exhaustively"}],
        }
        self.bridge.inject_thinking_level(body, "codex")
        self.assertEqual(body["reasoning_effort"], "xhigh")

    def test_openai_existing_reasoning_effort_preserved(self):
        body = {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "debug root cause"}],
            "reasoning_effort": "minimal",
        }
        self.bridge.inject_thinking_level(body, "openai")
        self.assertEqual(body["reasoning_effort"], "minimal")

    def test_gemini_thinking_budget_high_for_deep(self):
        body = {
            "model": "gemini-3-pro-preview",
            "contents": [{"parts": [{"text": "architect a system"}]}],
        }
        self.bridge.inject_thinking_level(body, "gemini")
        # deep tier now maps to `high` -> 24576, NOT -1 (which is reserved for xhigh)
        self.assertEqual(
            body["generationConfig"]["thinkingConfig"]["thinkingBudget"], 24576
        )

    def test_gemini_thinking_budget_dynamic_for_xhigh(self):
        body = {
            "model": "gemini-3-pro-preview",
            "contents": [{"parts": [{"text": "Please give an exhaustive formal proof"}]}],
        }
        self.bridge.inject_thinking_level(body, "gemini")
        self.assertEqual(
            body["generationConfig"]["thinkingConfig"]["thinkingBudget"], -1
        )

    def test_gemini_fast_tier_short_prompt_uses_low_budget(self):
        body = {
            "model": "gemini-2.5-flash",
            "contents": [{"parts": [{"text": "hi"}]}],
        }
        self.bridge.inject_thinking_level(body, "gemini")
        self.assertEqual(
            body["generationConfig"]["thinkingConfig"]["thinkingBudget"], 1024
        )

    # --- counters --------------------------------------------------------

    def test_inject_premium_model_bumps_counters(self):
        bridge = self.proxy.MITMBridge()  # fresh counters
        body = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Architect this for me please"}],
        }
        bridge.inject_premium_model(body, "openai")
        self.assertEqual(bridge.upgrades_total, 1)
        self.assertEqual(bridge.upgrades_by_service["openai"], 1)
        self.assertEqual(bridge.upgrades_by_tier["deep"], 1)
        self.assertEqual(bridge.recent_events[-1]["kind"], "upgrade")

    def test_inject_thinking_level_bumps_counters(self):
        bridge = self.proxy.MITMBridge()
        body = {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "debug root cause"}],
        }
        bridge.inject_thinking_level(body, "openai")
        self.assertEqual(bridge.thinking_by_level["high"], 1)
        self.assertEqual(bridge.recent_events[-1]["kind"], "thinking")

    # --- apply_mitm_features end-to-end ------------------------------------

    def test_apply_mitm_features_codex_rewrites_max_tokens(self):
        body = {"model": "davinci-codex", "prompt": "def hello():", "max_tokens": 128}
        body, _ = self.bridge.apply_mitm_features(body, {}, "codex")
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["max_completion_tokens"], 128)
        # gpt-5.x codex models are reasoning models -> no temperature override.
        self.assertNotIn("temperature", body)

    def test_apply_mitm_features_gemini_sets_default_temperature(self):
        body = {"model": "gemini-pro", "contents": [{"parts": [{"text": "hi"}]}]}
        body, _ = self.bridge.apply_mitm_features(body, {}, "gemini")
        self.assertIn("generationConfig", body)
        self.assertEqual(body["generationConfig"].get("temperature"), 0.7)

    def test_rate_limit_headers_are_stripped(self):
        headers = {
            "content-type": "application/json",
            "x-ratelimit-limit": "10",
            "x-ratelimit-remaining": "0",
            "retry-after": "5",
        }
        _, out = self.bridge.apply_mitm_features({"model": "gpt-4"}, headers, "openai")
        self.assertNotIn("x-ratelimit-limit", out)
        self.assertNotIn("x-ratelimit-remaining", out)
        self.assertNotIn("retry-after", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
