# repowise-server

The FastAPI REST API, the MCP server, webhook handlers and the background
scheduler. `repowise serve` and `repowise mcp` start it, and the web UI reads
from its API (port 7337 by default).

**Python >= 3.11 · AGPL-3.0-or-later**

## Where it sits

This is one of the Python packages in the repowise monorepo. Code lives under
`src/repowise/server/`: `app.py` builds the FastAPI app, `routers/` holds the
REST routes, and `mcp_server/` holds the tools: 18 registered MCP tools
(10 advertised by default in single-repo mode). It reads indexes built by
`packages/core`.

Seen from an MCP client, repowise registers 18 MCP tools and advertises **10 by default**.
Workspace mode adds `list_repos`, and the other seven are opt-in through
`repowise mcp --tools` or the `mcp:` config block. See
[docs/agent/MCP_TOOLS.md](../../docs/agent/MCP_TOOLS.md).

It is not published to PyPI on its own. Users get it inside the single
`repowise` distribution built from the root `pyproject.toml`.

## Install the product

```bash
uv tool install repowise      # or: pipx install repowise / pip install repowise
cd your-repo
repowise init
repowise serve                # API on :7337, web UI on :3000
```

## Develop on it

From the repository root, `uv sync --all-packages` installs every package in
editable mode. See [CONTRIBUTING.md](../../.github/CONTRIBUTING.md).

## Saved workspace metrics reports

The optional `repowise-workspace-metrics` extension (0.4.3+ recommended) renders saved JSON evidence
through its existing `metrics-html` renderer. Install it in the server's Python
environment and restart the service. No indexing, Git fetch or new collection
occurs when a report is imported or viewed.

The repository's **Metrics** page accepts local JSON uploads. When evidence is
already on the server, import it directly using the existing API credential:

```sh
curl --fail-with-body \
  -H "Authorization: Bearer $REPOWISE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @/absolute/path/to/snapshot.json \
  http://127.0.0.1:7337/api/repos/REPOSITORY_ID/workspace-metrics
```

Use the deployment's actual API port and repository ID. Never paste the API
key into an issue, report, URL or browser page. `GET` on the same endpoint lists
saved reports; `GET /{report_id}` returns authenticated JSON with the rendered
HTML. There is deliberately no arbitrary filesystem-path or raw-HTML endpoint.
Every alias in the evidence must be inside the selected repository's checkout;
cross-repository workspace reports require a separate workspace-level design.

Imports are private, immutable copies under
`~/.repowise/metrics-reports/<repository-key>/<report-id>/`, outside the measured
checkout. Evidence, rendered HTML and metadata persist across restarts. Snapshot
timestamps and commit IDs remain visible; viewing does not imply current data.
Keep this directory private and include it in the deployment's backup policy.
Original generated files need not be committed or indexed.

API authentication and repository read/write authorization apply as usual:
importing requires write access; listing/viewing require read access. Responses
are `private, no-store`. The browser loads report HTML into an opaque-origin
`sandbox="allow-scripts"` frame, not the application DOM. Missing renderers,
invalid evidence and storage failures are explicit errors.
Extension 0.4.3 opens counter-gap evidence in place; older renderer versions
use a fragment link that does not work inside an opaque-origin frame.

## Further documentation

- MCP tools: [docs/agent/MCP_TOOLS.md](../../docs/agent/MCP_TOOLS.md)
- CLI commands, including `serve` and `mcp`: [docs/reference/CLI_REFERENCE.md](../../docs/reference/CLI_REFERENCE.md)
- How the system is built: [docs/architecture/](../../docs/architecture/)
