# Golden Example

User:

`/notebook Erstelle aus ~/Documents/company/strategy.pdf und ~/Documents/company/notes.md ein Quellen-Notebook und beantworte: Welche Risiken sind priorisiert?`

Required behavior:

1. Call `create_source_notebook` with both paths.
2. Call `query_source_notebook` with the returned `SOURCE_NOTEBOOK_FILE`.
3. Answer with citations next to every claim.
4. If requested as a deliverable, call `export_source_brief` and return the saved path.

Good answer shape:

The indexed sources prioritize execution risk and budget sequencing. The strategy PDF frames delivery capacity as the limiting constraint `[S001-C003]`; the notes file adds that vendor onboarding remains unresolved `[S002-C001]`.

Evidence:
- `[S001-C003]` strategy.pdf: ...
- `[S002-C001]` notes.md: ...
