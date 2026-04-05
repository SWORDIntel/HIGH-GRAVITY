"""OpenAI Codex Agent - AI-powered code generation and review

This agent integrates OpenAI Codex API for intelligent code generation,
refactoring, and code review capabilities within the Claude Agent Framework.

Features:
- Code generation from natural language prompts
- Automated code review and suggestions
- Context-aware refactoring
- Integration with existing agent system

Requirements:
- OPENAI_API_KEY environment variable or config
- openai Python package (pip install openai)
"""

import os
from typing import Any, Dict, List, Optional
import asyncio

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class CodexAgent:
    """AI-powered code generation and review agent using OpenAI Codex API"""

    def __init__(self):
        self.name = "codex"
        self.category = "development"
        self.description = "AI code generation and review using OpenAI Codex"
        self.capabilities = ["code_generation", "code_review", "refactoring", "documentation"]
        self.client = None
        self.model = "gpt-4"  # Codex models deprecated, using GPT-4 for code
        self.initialized = False

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize Codex agent with API credentials

        Args:
            config: Optional configuration dict with 'openai_api_key' and 'model'

        Returns:
            True if initialization successful, False otherwise
        """
        if not OPENAI_AVAILABLE:
            print("Warning: openai package not installed. Run: pip install openai")
            return False

        config = config or {}
        api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            print("Warning: OPENAI_API_KEY not found in config or environment")
            return False

        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.model = config.get("model", "gpt-4")
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error initializing Codex agent: {e}")
            return False

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        context: str = "",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate code using OpenAI Codex/GPT-4

        Args:
            prompt: Natural language description of code to generate
            language: Programming language (python, rust, c, javascript, etc.)
            context: Additional context about the project
            max_tokens: Maximum tokens in response

        Returns:
            Dict with 'code', 'explanation', 'success' keys
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Codex agent not initialized. Call initialize() first."
            }

        # Build comprehensive prompt with project context
        full_prompt = self._build_prompt(prompt, language, context)

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software engineer helping with the Claude Agent Framework v7.0. Generate clean, well-documented code following project standards."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.2  # Lower temperature for more consistent code
            )

            code = response.choices[0].message.content
            return {
                "success": True,
                "code": code,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def review_code(
        self,
        code: str,
        language: str = "python",
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Review code and provide suggestions

        Args:
            code: Source code to review
            language: Programming language
            focus_areas: Optional list of areas to focus on
                        (e.g., ['security', 'performance', 'style'])

        Returns:
            Dict with 'suggestions', 'issues', 'score' keys
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Codex agent not initialized"
            }

        focus = focus_areas or ["security", "performance", "best_practices", "style"]
        focus_str = ", ".join(focus)

        prompt = f"""
Review the following {language} code for the Claude Agent Framework v7.0.

Focus areas: {focus_str}

Project standards:
- Python 3.11+, black formatting, type hints required
- Async/await for I/O operations
- Google-style docstrings
- 80% test coverage minimum
- Security: no eval/exec, validate inputs, use environment variables

Code to review:
```{language}
{code}
```

Provide:
1. Overall assessment (1-10 score)
2. Critical issues (security, bugs)
3. Improvement suggestions
4. Code style issues
5. Performance recommendations
"""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )

            review = response.choices[0].message.content
            return {
                "success": True,
                "review": review,
                "model": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def refactor_code(
        self,
        code: str,
        language: str = "python",
        goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Refactor code with specific goals

        Args:
            code: Source code to refactor
            language: Programming language
            goals: Refactoring goals (e.g., ['performance', 'readability'])

        Returns:
            Dict with 'refactored_code', 'changes', 'explanation' keys
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Codex agent not initialized"
            }

        goals_str = ", ".join(goals or ["improve readability", "optimize performance"])

        prompt = f"""
Refactor the following {language} code for the Claude Agent Framework v7.0.

Goals: {goals_str}

Original code:
```{language}
{code}
```

Provide:
1. Refactored code with improvements
2. List of changes made
3. Explanation of improvements
"""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software engineer specializing in refactoring."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )

            result = response.choices[0].message.content
            return {
                "success": True,
                "result": result,
                "model": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _build_prompt(self, prompt: str, language: str, context: str) -> str:
        """Build comprehensive prompt with project context"""
        base_context = """
Project: Claude Agent Framework v7.0
Architecture: 3-tier system
- Agent Layer (Python 3.11+): 98 specialized agents
- Hook Layer (Python/C): Business logic with NPU acceleration
- Binary Layer (C/Rust): High-performance primitives

Standards:
- Python: black formatting (100 char line), type hints, Google docstrings
- Rust: cargo fmt, clippy lints
- Testing: pytest with 80%+ coverage
- Security: Environment variables for secrets, input validation
- Performance: NPU/AVX2 acceleration for critical paths

Correct imports:
- from claude_agents.orchestration import get_agent_registry
- from claude_agents import get_agent, list_agents
- from hooks.shadowgit.python import Phase3Unified, ShadowGitAVX2
"""

        if context:
            base_context += f"\n\nAdditional Context:\n{context}"

        return f"{base_context}\n\nTask: Generate {language} code for:\n{prompt}"


# Module-level convenience functions
_agent = None


def get_codex_agent() -> CodexAgent:
    """Get or create singleton Codex agent instance"""
    global _agent
    if _agent is None:
        _agent = CodexAgent()
    return _agent


async def generate(prompt: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for code generation"""
    agent = get_codex_agent()
    if not agent.initialized:
        agent.initialize()
    return await agent.generate_code(prompt, **kwargs)


async def review(code: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for code review"""
    agent = get_codex_agent()
    if not agent.initialized:
        agent.initialize()
    return await agent.review_code(code, **kwargs)


async def refactor(code: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for refactoring"""
    agent = get_codex_agent()
    if not agent.initialized:
        agent.initialize()
    return await agent.refactor_code(code, **kwargs)


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        agent = CodexAgent()
        if agent.initialize():
            print("✓ Codex agent initialized")

            # Example: Generate code
            result = await agent.generate_code(
                "Create a Python function to validate email addresses using regex",
                language="python"
            )

            if result["success"]:
                print("\nGenerated code:")
                print(result["code"])
            else:
                print(f"Error: {result['error']}")
        else:
            print("✗ Failed to initialize Codex agent")
            print("Set OPENAI_API_KEY environment variable")

    asyncio.run(main())
