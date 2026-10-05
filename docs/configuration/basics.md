# Configuration basics

[Configuration guide](README.md) · Next: [First setup](first-setup.md)

## Where settings live

There are three different places to configure AskFlow:

| Place | Examples | How changes take effect |
| --- | --- | --- |
| Backend environment or `.env` file | Database, model connection, enabled features, limits | Restart the backend |
| Web build environment | `VITE_ASKFLOW_FEATURES` | Restart the web development server, or rebuild and redeploy the web app |
| Stored application settings | Intent mappings, prompt versions, teams, connector records | Save through the relevant page or authorized integration; verify the affected workflow |

Changing `.env` does not change a connector record already stored in the database. Editing the web environment does not configure the backend. This guide identifies the correct place for each task.

## What is an environment variable?

It is a named value supplied to a running program. For example:

```dotenv
HANDOFF_TIMEOUT_SECONDS=300
```

The name is `HANDOFF_TIMEOUT_SECONDS`; the value is `300`. This tells AskFlow to use a five-minute waiting threshold for unclaimed human-support requests.

A **default** is the value used when no value was supplied. You do not need to copy every setting into your configuration file. Start with the few values needed for your installation and leave the rest at their defaults.

## Use the right file and working folder

For the local commands in this guide, use `apps/api/.env` and start the API **from `apps/api`**. The program looks for `.env` in its working folder, not automatically next to every source file. Relative database and storage paths also depend on that folder.

The web app uses its own Vite environment files in `apps/web`, such as `apps/web/.env.local`. Putting `VITE_ASKFLOW_FEATURES` in the API file does not configure the web app.

A hosting service may supply environment variables through its own settings panel instead of a file. Container and service-manager settings must be applied to the actual API process; restarting a container without recreating its environment may leave the old values in place.

## Edit a dotenv file

Use a plain-text editor. The filename is exactly `.env`, including the leading dot, with no extra `.txt` extension.

```dotenv
# Lines starting with # are comments.
ASKFLOW_ENV=development
ASKFLOW_PROFILE=full
SERVICE_TASKS_ENABLED=true
SERVICE_TASK_POLL_SECONDS=5
```

- Put one setting on each line and use the spelling shown in this guide.
- Use `true` or `false` for on/off switches.
- Use ordinary numbers without units or thousands separators: `300`, not `5 minutes`.
- Quote text that contains spaces or special characters.
- Keep one active line per setting.
- Delete or comment out an optional setting to return to its default. An empty value is not always equivalent to an omitted value.

Some values have specific formats:

```dotenv
CORS_ORIGINS='["https://support.example.com","https://portal.example.com"]'
ASKFLOW_FEATURES=+teams,+notify,-mcp
SERVICE_TASKS_GOALS=order_status,ticket_resolution
```

`CORS_ORIGINS` needs a JSON array: square brackets with double-quoted entries. A bare comma-separated origin string currently fails environment parsing. Feature changes and task goals use comma-separated text instead.

`example.com` addresses and values such as `REPLACE_WITH_PROVIDER_KEY` are placeholders, not working services or credentials. Replace them before enabling the associated connection.

## Understand which value wins

For a normal application startup, values supplied to the process by the shell or hosting service override values in `.env`; `.env` values override defaults.

For example, if you previously ran `export ASKFLOW_PROFILE=mvp`, editing the file to say `ASKFLOW_PROFILE=full` will not override that exported value. On a local shell, remove that specific override with:

```bash
unset ASKFLOW_PROFILE
```

Then restart the API from the intended folder. Do not print or share the entire environment while diagnosing a problem: it can contain credentials. Check the specific non-secret value you are investigating.

Unknown settings in `.env` are ignored, so a misspelled name can look like it worked while having no effect. Check the [reference](reference.md) rather than guessing names.

## Restart after changes

For the local development setup:

1. Save your `.env` changes.
2. In the terminal running the API, press **Ctrl+C** and wait for it to stop.
3. From `apps/api`, with its virtual environment activated, run the same API start command again.
4. Open `/health` and test the feature you changed.

Do not rely on `--reload` to detect changes to `.env`. Many clients and settings are cached for the lifetime of the process.

For a shared installation, have its operator restart all affected API processes through the deployment system. Web environment changes require a separate web restart or rebuild. Settings that govern new requests may not change work already accepted; see [Service operations](service.md).

## Keep a way back

Before changing an existing installation, retain the previous configuration in a private location and record what you changed. A configuration copy containing secrets needs the same access restrictions as the original. Keep it out of shared documents and source control.

To undo a simple limit or feature change, restore the previous value and restart. Database moves, document reindexing, key changes, and external business actions have additional consequences: restoring an environment file does not undo those changes.

An API key or token is a credential, like a password for a service. Store it only in the backend's private configuration or the host's secret-management facility. Never put one in a `VITE_` variable: web build values can be exposed to browsers.
