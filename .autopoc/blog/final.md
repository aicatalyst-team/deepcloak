# Running DeepCloak on OpenShift: A PoC for Bot-Wall-Bypassing Research Agents

When AI research agents hit a Cloudflare challenge page or a Datadome wall, they silently skip the source and move on. You never learn what your report missed. DeepCloak takes a different approach: it detects the wall, escalates to a stealth browser, bypasses the barrier, and tells you exactly what it did. We deployed it on OpenShift to see how this kind of agentic tool fits into a cloud-native AI platform.

## What DeepCloak Does

DeepCloak is a Python CLI tool and MCP server that wraps two open-source projects: local-deep-research (the research loop) and CloakBrowser (the stealth browser). When a plain HTTP fetch returns a bot wall signature, DeepCloak escalates that URL to a headless stealth browser session, recovers the content, and includes it in the final research report. Every bypass is logged in an Evidence Record, so you know exactly which sources were walled and how they were accessed.

The tool supports DuckDuckGo and SearXNG as search backends, works with OpenAI, Anthropic, Gemini, or local Ollama models, and runs entirely on your machine with no data leaving the host.

## Why OpenShift

DeepCloak is a local-first CLI tool. Deploying it on OpenShift tests whether the Python package structure, module imports, and CLI interface survive containerization on a restricted platform. OpenShift's security model (random UIDs, no privileged ports, no root) is a good stress test for any application packaging.

Beyond validation, there is a practical angle: if DeepCloak works in a container, it can serve as a data acquisition step in OpenShift AI Data Science Pipelines, fetching bot-walled content for RAG pipelines or training data collection workflows.

## The Containerization Challenge

DeepCloak's dependency tree is massive. Through `local-deep-research`, it pulls in PyTorch, spaCy, transformers, sentence-transformers, LangChain, crawl4ai, and dozens of other packages. A full install downloads over 2 GB of Python packages. On our OpenShift cluster, this exceeded the build node's ephemeral storage limits repeatedly.

We solved this with a two-tier approach: a lightweight Dockerfile that installs only the deepcloak package itself (using `pip install --no-deps`) plus minimal runtime dependencies. This validates the package structure and module imports while keeping the container image under 500 MB. A production deployment would use multi-stage builds with pre-cached dependency layers.

The Dockerfile uses Red Hat UBI9 Python 3.12 as the base image, runs as non-root user 1001, and includes proper group 0 permissions for OpenShift's arbitrary UID assignment.

## What We Tested

We created a lightweight HTTP health server that exposes DeepCloak's functionality through four endpoints:

**Health check** -- confirms the container is running and the HTTP server responds. This serves as the Kubernetes readiness probe.

**Version check** -- imports `deepcloak.__version__` and returns the version string. Validates that the package installed correctly and is importable.

**CLI check** -- calls `deepcloak.cli.build_parser()` and returns the formatted help text. Validates that the CLI module, argument parser, and all subcommand definitions are functional.

**Import check** -- attempts to import all 9 core deepcloak modules (`cli`, `config`, `evidence`, `bot_wall_detector`, `fetch_router`, `mcp_server`, `progress`, `research_core`, `stealth_downloader`) and reports which ones loaded successfully.

All four tests passed. Every module imported cleanly despite the heavy upstream dependencies being absent, because DeepCloak uses lazy imports throughout its codebase. The research core, MCP server, and stealth downloader only import their heavy dependencies when actually invoked.

## Deployment Architecture

The deployment is straightforward: a single-replica Deployment with a ClusterIP Service on port 8080. Resource requests are 256 Mi RAM and 250m CPU, with limits at 512 Mi and 500m. The health server handles readiness and liveness probes via the `/health` endpoint.

No persistent storage, secrets, or sidecars are required for the validation deployment. A full production deployment would need environment variables for LLM API keys and potentially a PVC for caching stealth browser profiles.

## What We Learned

**Lazy imports matter.** DeepCloak's architecture of deferring heavy imports until function call time means the package installs and imports cleanly even without its transitive dependencies. This is a good pattern for any Python tool with heavy optional dependencies.

**Ephemeral storage is the bottleneck.** On OpenShift build nodes, the limiting factor was not CPU or memory but disk space during `pip install`. ML-adjacent Python projects routinely exceed 5 GB of installed packages. Build strategies need to account for this.

**MCP over stdio does not map to HTTP.** DeepCloak's MCP server uses stdio transport, which works for local agent integration (Claude Code, Codex) but does not expose an HTTP endpoint. Deploying MCP-based tools as Kubernetes services requires either protocol bridging or adoption of HTTP-based MCP transports.

**Health wrappers work.** Wrapping CLI tool validation behind a simple HTTP server is an effective pattern for deploying non-service applications on Kubernetes. The health server adds negligible overhead and enables standard Kubernetes health probing.

## Next Steps

For a production deployment of DeepCloak on OpenShift AI, the path forward includes building a multi-stage Dockerfile with a pre-warmed dependency layer, implementing an HTTP transport adapter for the MCP server, and integrating with Data Science Pipelines as a web content acquisition step. The bot wall detection module could also be extracted as a standalone microservice for use across multiple research pipelines.

The full PoC artifacts, including the Dockerfile, Kubernetes manifests, and test scripts, are available in the [autopoc-artifacts branch](https://github.com/aicatalyst-team/deepcloak/tree/autopoc-artifacts) of the forked repository.
