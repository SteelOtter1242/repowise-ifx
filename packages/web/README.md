# repowise web UI

The local dashboard: a Next.js app that renders the wiki, graph, health, dead
code, decisions and the other views for an indexed repository. `repowise serve`
downloads a prebuilt copy on first run, caches it, and runs it on port 3000.

## Where it sits

This is the `repowise-web` npm workspace in the repowise monorepo. Pages live in
`src/app/`, app-specific components in `src/components/`, and the API client in
`src/lib/api/`. Shared components come from `packages/ui`, shared types from
`packages/types`, and the typed client from `packages/api-client`. It reads
everything from the API in `packages/server`.

## Install the product

```bash
uv tool install repowise      # or: pipx install repowise / pip install repowise
cd your-repo
repowise init
repowise serve                # API on :7337, web UI on :3000
```

## Develop on it

```bash
npm install                   # from the repository root (npm workspaces)
repowise serve --no-ui        # start only the API on :7337
npm run dev                   # web UI with hot reload on :3000
```

The server-side API address defaults to `http://localhost:7337`; set
`REPOWISE_API_URL` to point elsewhere. See
[CONTRIBUTING.md](../../.github/CONTRIBUTING.md).

## Deploy a matching fork frontend

Python installation alone does not replace the version-cached upstream UI.
For a fork-only page, check out the **same commit** used for the Python install,
then build it with Node.js 20+ from the checkout root:

```sh
npm ci --no-audit --no-fund
NEXT_TELEMETRY_DISABLED=1 npm run build --workspace repowise-web
```

Keep the existing service's working directory, database/workspace configuration,
Python executable, credentials and ports unchanged. The working directory also
controls index discovery; moving it into the source checkout can open the wrong
database even when the new frontend works.

For an existing pip-installed service, package the standalone output using the
layout in [the release workflow](../../.github/workflows/publish.yml), then stage
and verify the matching bundle before stopping the service. Back up
`~/.repowise/web` and install the new bundle there: `server.js`, `.next`, `public`
and `node_modules` belong directly inside that cache directory. Its `.version`
marker must equal the installed Python CLI version. Record the full fork commit
separately as well, since fork changes may retain the upstream package version.
Install matching Python code and restart the existing service without changing
its working directory. Retain the old cache and Python commit for rollback.

Do **not** use `--refresh-ui` for an unreleased fork feature: it bypasses the
local build/cache and downloads the upstream UI. Rebuild the same checkout when
upgrading the fork; do not reuse an older standalone directory with newer Python
source. A matching standalone bundle avoids requiring npm or a build on the VM;
Node.js 20+ is still required to run it.

## Documentation

- **Metrics** opens explicitly imported chart-first reports without indexing
  their HTML/JSON. Import local JSON on the page, or use the authenticated
  server-side import documented in [repowise-server](../server/README.md#saved-workspace-metrics-reports).
  Installing Python changes alone does not update a cached web bundle: deploy
  the matching frontend build as well.
- CLI commands, including `serve`: [docs/reference/CLI_REFERENCE.md](../../docs/reference/CLI_REFERENCE.md)
- How the system is built: [docs/architecture/](../../docs/architecture/)
