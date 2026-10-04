# Storage and indexing

[Configuration guide](README.md) · Next: [Accounts, access, and hosting](access.md)

AskFlow keeps several kinds of data in different places. A database backup alone does not include uploaded document files or every search index.

## Know what must be retained

Paths below are relative to the API's working directory unless you configure an absolute path.

| Data | Default location | What it contains |
| --- | --- | --- |
| Database | `./askflow.dev.db` | Accounts, messages, tickets, document metadata, tasks, preferences, and other records |
| Uploaded sources | `./data/uploads` | Document source bodies, including published knowledge drafts |
| Revision snapshots | `./data/revisions` | Document versions used for comparison and rollback |
| Keyword and default vector indexes | Process memory | Prepared search data; lost when the process stops |
| Optional Chroma data | Configured directory or Chroma server | Persistent vector-search data |

The current startup does not rebuild the complete in-memory document index from all stored sources. After restarting, a document may still appear `active` in the database but need reindexing to restore full search behavior. Built-in samples can still be searchable and obscure this distinction.

Persist the database, uploads, revisions, and configured Chroma storage together. Have the operator arrange consistent backups and a restore rehearsal. In a container, directories inside the disposable container are not a persistent-storage plan; mount appropriate volumes.

## Use SQLite for a small trial

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
```

This creates or uses the file in the working directory. An absolute Linux path uses four slashes:

```dotenv
DATABASE_URL=sqlite+aiosqlite:////srv/askflow/data/askflow.db
```

Create the parent directory and give the API account access before startup. Keep starting the program from the intended folder. A path typo can create a different empty database, making it look as if all users disappeared.

## Connect PostgreSQL

PostgreSQL is a separate database service. Ask its administrator for the host, port, database name, username, password, and any required transport-security options.

```dotenv
DATABASE_URL=postgresql+asyncpg://askflow:REPLACE_WITH_DATABASE_PASSWORD@db.example.com:5432/askflow
```

The prefix must include the asynchronous driver, `postgresql+asyncpg`. Credentials with URL-special characters need correct URL encoding; ask the database operator to supply a properly formatted connection string.

For **local development dependencies only**, the repository supplies Docker Compose. From the repository root:

```bash
docker compose -f infra/compose/dev/docker-compose.yml up -d postgres redis
```

For an API running directly on that same computer, the development database URL is:

```dotenv
DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow
```

The bundled username/password are development values. The Compose file starts dependencies, not the AskFlow API or web app. It exposes host ports and is not a production deployment template.

Changing `DATABASE_URL` selects a database; it does not transfer records. Before switching an existing service, have the operator migrate and verify the records. Restoring the old URL afterward also does not copy back records created in the new database.

## Set revision storage and upload size

```dotenv
REVISION_STORE_DIR=/srv/askflow/data/revisions
MAX_UPLOAD_BYTES=15728640
```

The upload limit defaults to 15 MiB. It counts file bytes, not pages or characters. The frontend and any reverse proxy may have their own upload limits; the smallest applicable limit wins.

Changing `REVISION_STORE_DIR` does not move old snapshots. Copy or migrate the retained data through the operator before switching. Uploaded source storage is still hardcoded to `./data/uploads` for the standard adapter; there is no `UPLOAD_DIR` environment setting.

## Understand the S3 settings

`S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_BUCKET` are defined, but the standard upload adapter does not use them. Setting them or starting the bundled MinIO container does **not** move uploads or backups to object storage.

Use persistent local/shared storage for the actual upload directory. Object-storage adoption currently requires adapter integration work by a developer. Do not remove local files on the assumption they were copied to S3.

## Add persistent vector search with Chroma

First install the optional dependency in the API virtual environment, from `apps/api`:

```bash
pip install -e ".[vector]"
```

Choose one of the following configurations.

**Local persistent directory:**

```dotenv
CHROMA_PERSIST_DIR=/srv/askflow/data/chroma
CHROMA_COLLECTION=askflow
```

**Chroma server:**

```dotenv
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=askflow
```

For that local server example, start the repository's Chroma service from the repository root:

```bash
docker compose -f infra/compose/dev/docker-compose.yml up -d chroma
```

`CHROMA_HOST` is a host name, not a URL containing `https://` or a path. The bundled host port is 8001. If the API is itself in the same Compose network, the service address would instead use host `chroma` and its internal port `8000`. Similarly, `localhost` inside a container refers to that container, not your computer or another service.

If both host and directory are set, the host takes precedence. No Chroma authentication/TLS configuration is exposed by these settings; have the operator arrange a suitable private connection or adapt the integration as required.

Restart the API, inspect the vector entry in `/health`, and index a known document. Verify it is searchable after a restart. Chroma persists vector data, but it does not make the in-process keyword index shared or automatically restore its full contents.

Chroma initialization or write failures can fall back to memory. Check the health details and logs rather than assuming persistence from a successful upload alone. Model or dimension changes need a compatible collection and full reindexing.

## Run indexing in the background

By default, uploads are indexed during the request. For asynchronous processing:

```dotenv
INDEX_ASYNC=true
INDEX_WORKER_ENABLED=true
INDEX_WORKER_POLL_SECONDS=1
REDIS_URL=redis://localhost:6379/0
INDEX_QUEUE_KEY=askflow:index_jobs
```

A **worker** is a background loop doing queued work. The API starts its built-in index worker when enabled, except in test mode. Uploads can return while the document is still pending; refresh the document list until processing finishes.

Without Redis, the index queue is process-local and can be lost on restart. With Redis, the implementation also keeps a local copy and falls back locally if Redis fails; this is not a guaranteed exactly-once durable job system. Disabling the worker while leaving asynchronous uploads enabled requires another appropriate consumer, otherwise queued work remains pending.

Redis also supports shared cancellation markers; it does not share the keyword index, retrieval cache, or make service tasks durable. Service-task scheduling uses the database independently.

For a single-process trial, leave `INDEX_ASYNC=false` unless you need background uploads. For multi-process deployments, ask the operator to validate index visibility across all serving processes before increasing worker counts.

## Reindex existing documents

The standard browser page has no reindex button. The operator can use the authenticated administrator endpoint `POST /api/v1/embedding/reindex/{document_id}`. In a local development environment, `/docs` provides an interactive request form; [Service operations](service.md#use-an-administrator-api-when-no-screen-exists) explains using it.

Reindexing rebuilds a document's search data from its retained source and creates a revision. It is not the same as uploading another file, which creates another document. Reindex every relevant source when changing embedding methods, restoring memory indexes, or building a new collection, then test representative questions.

## Upgrade an existing database

Stop and plan with the operator before upgrading a retained database. Startup's missing-table creation and the Alembic migration history are separate mechanisms; blindly running migrations over tables already created by startup can fail with “table already exists”.

For a deployment already correctly tracked by Alembic, the operator checks the current revision and applies upgrades from `apps/api` with the correct environment:

```bash
python -m alembic current
python -m alembic upgrade head
```

These are not instructions to initialize every fresh trial or repair unknown migration state. Have the operator compare the retained schema with the migration history before stamping or upgrading an untracked database. See the [database upgrade notes](../../apps/api/README.md#database-upgrades).
