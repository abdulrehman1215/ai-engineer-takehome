# MCP configuration

No MCP server was needed to build the slices. One connector was used, read-only, at the start:

- Gmail connector: to open the thread with the recruiter and find the brief's PDF attachment. The tools allowed are `search_threads`, `get_thread`, `get_message`. The connector cannot download attachments, so the PDF was taken from the Downloads folder.
- Denied: `send_message`, `reply`, `forward`, `trash_message`, `trash_thread`, `delete_draft`, `delete_label`. Nothing was sent to anyone.

Edits to `dossier/` were also denied by the local permission rules.

Why no model or MCP server inside the slices: no AI provider is on Northgate's Schedule 4 (`dossier/policies/client_data_handling.md`), and the CFO asked that no model touch finance data. Where a model would help later (summarising PR text, drafting a postmortem narrative), it needs an approved provider first.
