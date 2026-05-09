# Mneme Integrations

Mneme should be portable across agent frameworks.

The preferred integration surface is MCP over `stdio`.

## Generic MCP Client

Use a local server command:

```json
{
  "mcpServers": {
    "mneme": {
      "command": "C:\\Projects\\Nira_kernel\\projects\\mneme\\target\\release\\mneme-mcp.exe",
      "args": [],
      "cwd": "C:\\Projects\\Nira_kernel\\projects\\mneme"
    }
  }
}
```

If the client does not support `cwd`, pass environment variables:

```json
{
  "mcpServers": {
    "mneme": {
      "command": "C:\\Projects\\Nira_kernel\\projects\\mneme\\target\\release\\mneme-mcp.exe",
      "args": [],
      "env": {
        "MNEME_PROJECT_ROOT": "C:\\Projects\\Nira_kernel\\projects\\mneme",
        "MNEME_KERNEL_ROOT": "C:\\Projects\\Nira_kernel"
      }
    }
  }
}
```

## Intended Resources

- `mneme://state`
- `mneme://profile-index`
- `mneme://active-read-set`
- `mneme://affect`
- `mneme://events/recent`

## Intended Tools

- `select`
- `touch`
- `observe`
- `explain`

## Agent-Side Rule

At session start:

```text
Read mneme://state and mneme://active-read-set.
Load only the selected files that match the current task.
Use touch when a memory node actually shaped the work.
Use observe when a new event should alter future memory routing.
```

## Notes For Codex / OpenClaw / Hermes

Do not make Mneme depend on one host's memory format.

Host-specific adapters may exist, but the core contract should stay:

```text
MCP resources expose state.
MCP tools mutate with trace.
Data stays local and inspectable.
```
