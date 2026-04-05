#!/usr/bin/env python3
import asyncio
import sys

sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')


class QuickVoice:
    def __init__(self):
        self.agents = {
            "director": ["plan", "strategy", "coordinate"],
            "planner": ["timeline", "roadmap", "schedule"],
            "architect": ["design", "architecture", "build"],
            "security": ["security", "audit", "vulnerability"],
        }

    def parse_command(self, text):
        text = text.lower()
        for wake in ["claude", "agent", "hey claude"]:
            text = text.replace(wake, "").strip()

        for agent, keywords in self.agents.items():
            if any(k in text for k in keywords):
                return agent.upper(), text
        return "DIRECTOR", text

    async def execute(self, voice_input):
        from claude_agent_bridge import task_agent_invoke

        agent, command = self.parse_command(voice_input)
        result = await task_agent_invoke(agent, command)
        return f'{agent}: {result.get("status", "completed")}'


voice = QuickVoice()


async def demo():
    commands = [
        "Claude, plan my project deployment",
        "Ask security to audit the system",
        "Have architect design the API",
    ]

    for cmd in commands:
        try:
            result = await voice.execute(cmd)
            print(f'✅ "{cmd}" → {result}')
        except Exception as e:
            print(f'❌ "{cmd}" → {e}')


asyncio.run(demo())
