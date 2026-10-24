"""Terminal-Bench agent adapter: upstream mini-swe-agent + the `mcp` runtime dep.

Why this exists
---------------
Harbor's bundled `mini-swe-agent` adapter installs the CLI with

    uv tool install mini-swe-agent==X --with litellm --with orjson --with fastapi

Current LiteLLM imports `mcp` on the chat-completion path, so a real model call
fails with `ModuleNotFoundError: No module named 'mcp'` and LiteLLM retries
until the trial times out. The adapter's package list cannot be changed from the
CLI, so this subclass adds one more install step.

This file is OUR code and lives outside the upstream mini-swe-agent checkout: it
does not modify the baseline source used for SWE-bench experiments. When RSI
work eventually needs a modified agent inside Terminal-Bench, this is the same
extension point to use.
"""

from __future__ import annotations

import shlex

from harbor.agents.installed.mini_swe_agent import (
    _MINI_SWE_AGENT_PYTHON_VERSION,
    MiniSweAgent,
)
from harbor.environments.base import BaseEnvironment


class MiniSweAgentWithMcp(MiniSweAgent):
    """Upstream adapter with the missing `mcp` dependency added to the tool env."""

    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)

        version_spec = f"=={self._version}" if self._version else ""
        python_version = shlex.quote(_MINI_SWE_AGENT_PYTHON_VERSION)
        await self.exec_as_agent(
            environment,
            command=(
                'if [ -f "$HOME/.local/bin/env" ]; then . "$HOME/.local/bin/env"; fi; '
                'export PATH="$HOME/.local/bin:$PATH"; '
                f"uv tool install --python {python_version} "
                f"mini-swe-agent{version_spec} "
                "--with litellm --with orjson --with fastapi --with mcp && "
                "mini-swe-agent --help"
            ),
        )
