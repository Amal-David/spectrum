# Curl quickstart

Start the API first:

```bash
pnpm api:dev
```

Create a session:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/sessions \
  -H 'content-type: application/json' \
  -d '{"analysis_mode":"full","metadata":{"title":"Curl quickstart"}}'
```

Upload audio:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/sessions/<job_id>/upload \
  -F file=@examples/sample.wav
```

Process it:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/sessions/<job_id>/process \
  -H 'content-type: application/json' \
  -d '{"metadata":{}}'
```

Fetch the bundle:

```bash
curl -s http://127.0.0.1:8000/api/v1/sessions/<job_id>/bundle | jq
```
