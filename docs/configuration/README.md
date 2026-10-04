# AskFlow configuration guide

Configuration tells AskFlow where to keep its records, which features to offer, and how to connect to other services. This guide is for the person setting up or managing an installation, including someone doing it for the first time.

Customers using an existing website do not need to configure the server. Start with the [user guide](../user-guide/README.md) if you just want to sign in and ask questions.

## Choose your starting point

| Your situation | Start here |
| --- | --- |
| “I do not know what an environment variable is.” | [Configuration basics](basics.md) |
| “I want a working trial on my computer.” | [First setup](first-setup.md) |
| “I need to choose which features appear.” | [Features and the web interface](features.md) |
| “I want to connect a language model.” | [Models and answer quality](models.md) |
| “I need persistent records and document search.” | [Storage and indexing](storage.md) |
| “I need staff accounts or company sign-in.” | [Accounts, access, and hosting](access.md) |
| “I need order lookup, human support, or notifications.” | [Service operations](service.md) |
| “I need a website widget or messaging bot.” | [Channels and extensions](channels.md) |
| “A setting did not work.” | [Verification and troubleshooting](troubleshooting.md) |
| “What does this exact setting mean?” | [Complete settings reference](reference.md) |

The guide uses the current repository behavior as of **October 4, 2026**. Screen names use the Chinese labels actually shown by the app, followed by English translations. There is no single browser page containing all settings.

## Understand the pieces

| Piece | Plain meaning | Do you need it immediately? |
| --- | --- | --- |
| Web app | The pages people open in their browser | Yes, for the standard interface |
| API/backend | The running program that processes requests | Yes |
| Database | Stores accounts, messages, tickets, and task progress | Yes; a local SQLite file works for a trial |
| Uploaded files | The source documents used for answers | Add your own approved content |
| Search index | Prepared copies of document text for searching | Created when you upload/index documents |
| Language-model service | Optional service for generating answers | No; basic extractive answers work without it |
| Embedding service | Turns text into numbers for similarity search | An offline implementation is included |
| Redis | Optional shared queue and cancellation support | No |
| Chroma | Optional persistent vector-search service or local store | No for a first trial; useful for persistent vector search |
| Business connector | A connection to an order system or another business service | Only for that business function |

AskFlow can keep accepting requests while some optional connections are unavailable. That does not establish that every configured feature works; verify each one you intend customers to use.

## A sensible setup order

1. Get a local installation running without external connections.
2. Sign in, upload a small text document, and ask a question about it.
3. Choose features and staff access.
4. Plan storage and backups before adding important records.
5. Add a model and business connections one at a time.
6. Test each complete customer journey.
7. Have the person responsible for hosting prepare the shared deployment.

Each chapter explains what to change, when it takes effect, how to check it, and what returning to the earlier setup involves. The reference distinguishes operational settings from reserved or partially integrated ones.

For developers and deployment specialists, the source references are [application settings](../../apps/api/app/core/config.py), [service-task settings](../../apps/api/app/services/agent/service/settings.py), [feature definitions](../../packages/contracts/features.yaml), and the [pilot deployment checklist](../../deploy/checklists/pilot-integration.md).
