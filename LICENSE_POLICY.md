# License Policy

Status: project policy draft
Date: 2026-05-09

Mneme is intended to become open source.

This means dependency choices are architectural choices, not incidental implementation details.

## Project License

The final project license is not chosen yet.

Preferred candidates:

- Apache-2.0
- MIT

Recommendation:

```text
Apache-2.0 for Mneme core/backend.
```

Reason:

- permissive open-source license
- explicit patent grant
- common for infrastructure projects
- aligns well with the MCP ecosystem's current Apache-2.0 transition

Do not publish a public release before adding a root `LICENSE` file.

## Dependency Rule

Default allowed:

- Apache-2.0
- MIT
- BSD-2-Clause
- BSD-3-Clause
- ISC
- MPL-2.0, only when the file-level copyleft boundary is understood

Requires explicit discussion before use:

- GPL
- LGPL
- AGPL
- SSPL
- BUSL
- Elastic License
- PolyForm licenses
- custom source-available licenses
- licenses with network-use, field-of-use, or commercial restrictions

Default rule:

```text
No strong copyleft or source-available dependency in the backend path
unless Denis explicitly chooses that tradeoff.
```

## First Known Dependency

Candidate:

```text
github.com/modelcontextprotocol/go-sdk
```

Observed license status:

```text
MCP project is transitioning from MIT to Apache-2.0.
The Go SDK LICENSE contains Apache-2.0 terms, MIT terms for older contributions,
and CC-BY-4.0 for documentation excluding specifications.
```

Assessment:

```text
Acceptable for Mneme's open-source direction.
```

Source:

```text
https://github.com/modelcontextprotocol/go-sdk/blob/main/LICENSE
```

## Audit Practice

Before adding a Go dependency:

```powershell
go list -m -json all
```

Then check licenses with one of:

```powershell
go-licenses report ./...
govulncheck ./...
```

If tooling is not installed yet, record the dependency and license manually in this file before committing.

## Mneme-Specific Rule

Memory infrastructure should stay easy to fork, inspect, and self-host.

Avoid dependencies that make Mneme:

- cloud-bound by default
- license-ambiguous
- impossible to package as a local binary
- dependent on proprietary services for core recall
- risky for personal/private memory

## Compression

```text
Open source is not only publishing code.
It is keeping the memory organ forkable, inspectable, and free enough to trust.
```

