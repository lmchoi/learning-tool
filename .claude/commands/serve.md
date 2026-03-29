# Serve Skill

Kill any existing process on port 8000, start the dev server, and tail logs.

## Usage

`/serve`

## Steps

1. Kill whatever is on port 8000 (if anything):

```bash
lsof -ti :8000 | xargs kill -9 2>/dev/null; true
```

2. Start the server in the background using the Makefile target:

```bash
make serve 2>&1
```

Run this with `run_in_background=true`. Note the output file path from the result.

3. Wait ~10 seconds for startup (embedder model load takes a few seconds).

4. Tail the output file to show the user the startup logs:

```bash
cat <output_file>
```

Print the logs to the user. If startup completed successfully, tell them the server is running at http://localhost:8000 and http://localhost:8000/docs for the API docs.

If startup failed (e.g. address already in use, missing env var), surface the error clearly.
