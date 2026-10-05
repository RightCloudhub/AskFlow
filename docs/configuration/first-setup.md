# First setup: a local trial

[Configuration guide](README.md) · Previous: [Configuration basics](basics.md) · Next: [Features](features.md)

This walkthrough starts both parts of AskFlow on one computer. It uses SQLite, local uploaded files, offline search embeddings, and extractive answers. You do not need a paid model connection or Docker for it.

The commands use a Linux/macOS-style shell. On Windows, use a suitable Linux environment such as WSL or ask your operator to adapt the setup. A **terminal** is an application where you type commands; press Enter after each command and wait for it to finish.

## 1. Get the software

Install Git, Python 3.11 or newer, and Node.js 20 with npm. If you already have the repository, open a terminal in its root folder instead of cloning another copy.

```bash
git clone https://github.com/RightCloudhub/AskFlow.git
cd AskFlow
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The **virtual environment** is a private folder of Python dependencies for this project. `source .venv/bin/activate` selects it for the current terminal. Run that activation again when opening a new API terminal.

## 2. Create the API settings file

If `apps/api/.env` already exists, inspect it privately and preserve its settings instead of replacing it. For a fresh installation, create `.env` in `apps/api` with:

```dotenv
ASKFLOW_ENV=development
SECRET_KEY=REPLACE_WITH_A_GENERATED_SECRET
DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
ASKFLOW_PROFILE=full
SERVICE_TASKS_ENABLED=false
```

Generate your own secret locally:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Paste the output as the `SECRET_KEY` value and save the file. This key signs logins; it is not your account password. Keep the same key across restarts. On Linux/macOS, restrict file access with:

```bash
chmod 600 .env
```

This trial explicitly disables saved background service tasks until you have a real business connection to test. Other enabled features may still display demonstration or fallback behavior. You can enable tasks later using [Service operations](service.md).

Leave model, Redis, Chroma, and S3 settings **omitted** for now. Clear earlier shell overrides if you have been following another setup. A copied example file may include outdated URL advice; use [Models](models.md) before enabling a model.

## 3. Start the backend

Still in `apps/api`, run:

```bash
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running. Open `http://localhost:8000/health` in a browser. Look for `status: "ok"` and a database dependency marked `up`. `localhost` means this computer; another person's computer cannot use your `localhost` address to reach this trial.

The first start creates missing database tables. You do not need to run database migration commands on this fresh trial. For an existing database, read [Storage and indexing](storage.md) before upgrading.

## 4. Prepare and start the web app

Open a second terminal in the repository root:

```bash
cd apps/web
npm ci
```

For this `full`-profile trial, create `apps/web/.env.local` with this non-secret value:

```dotenv
VITE_ASKFLOW_FEATURES=core,rag,agent,tools,ticket,handoff,knowledge,ops,cost,sla,notify,sso,teams,connectors,launch,analytics,mcp,widget,feishu,wecom,dingtalk,qc
```

This supplies the enabled feature list to the interface. It also lets ordinary customer accounts see appropriate links despite the current staff-only feature-discovery endpoint. It does not grant permissions or enable backend features. Keep it aligned with the backend when changing profiles; see [Features](features.md).

Start the web app:

```bash
npm run dev
```

Open the address printed by the terminal, normally `http://localhost:5173`. The web development server forwards API requests to port 8000. If either program stops, part of the application will stop working.

## 5. Create the first account and test knowledge

1. On the login page, click **没有账号？注册 (No account? Register)**.
2. Enter a username, email, and password; click **注册并登录 (Register and sign in)**.
3. In a fresh development database, the first registered account becomes an administrator. Check **Admin → 用户管理 (User management)**. Later registrations are ordinary users.
4. Create a small `.txt` file with a few sentences of approved information.
5. Upload it under **Admin → 知识文档 (Knowledge documents)** and wait for **启用 (`active`)** with a nonzero chunk count.
6. Return to **用户台 (User workspace)**, create a conversation, and ask a question answered by that file.
7. Open **查看引用 (View references)** and verify the answer uses the expected passage.

An extractive answer may quote the document directly. That is expected without a model. Built-in sample knowledge may also be present; a reply about sample data is not proof that your own content was indexed.

For detailed screen instructions, use the [knowledge guide](../user-guide/knowledge.md). If you cannot reach the admin pages, the database may already contain an account; registration does not promote you just because you changed a setting.

## 6. Stop and resume

Press **Ctrl+C** in each running terminal to stop the trial. Restart from the same folders using the same database path and secret. Your database and uploaded source files remain on disk.

The default search indexes are process-local and are not automatically rebuilt from all uploaded documents after restarting. Documents can still appear in the list while search needs maintenance. Before relying on restart persistence, follow [Storage and indexing](storage.md).

## Move toward a shared service

Do not simply share this development server as your production setup. Arrange a public or internal HTTPS address, production-mode settings, persistent storage, backups, proper account provisioning, and a process manager with the hosting operator. [Accounts, access, and hosting](access.md) explains the required configuration decisions.
