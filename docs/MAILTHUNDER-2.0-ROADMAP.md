# MailThunder 2.0 — Email Automation & Integration Layer

## Goals

MailThunder should evolve from a SMTP/IMAP-oriented email utility into a provider-agnostic Python Email Automation & Integration Framework.

Goals:
- UI redesign around MailThunder Studio
- Complete PyPI metadata and description
- OAuth2 / XOAUTH2 authentication
- Reusable email templates
- Attachment size/type guards
- Microsoft Graph backend
- Generic mail triggers/events
- Project-level Mail Layer for automation projects
- Backward compatibility with existing SMTPWrapper / IMAPWrapper APIs

## Architecture

```
                    MailThunder
                         |
            +------------+------------+
            |            |            |
       Mail Composer  Providers    Triggers
            |            |            |
        Templates     SMTP/IMAP    Polling/Push
                      Graph        IMAP/Graph
            +------------+------------+
                         |
                   Mail Policies
              Attachment/Security
```

## Core Mail API

Applications should use a provider-agnostic API:

```python
from mailthunder import Mail

mail = Mail(provider="microsoft")

mail.send(
    to="test@example.com",
    template="test_report",
    context={"project": "APITestka", "passed": 100},
)
```

The application layer must not need to know whether the provider is SMTP, IMAP, or Microsoft Graph.

## Authentication

Introduce:

```
Authentication
├── PasswordAuth
├── AppPasswordAuth
├── OAuth2Auth
└── XOAUTH2Auth
```

Centralize token acquisition, refresh, expiry and provider scopes.

Provider mapping:
- Gmail: SMTP + XOAUTH2, IMAP + XOAUTH2
- Microsoft: Graph OAuth2
- Generic: SMTP / IMAP

## Templates

Introduce reusable subject/text/HTML templates, preferably using Jinja2-style syntax.

```python
mail.send(
    template="test_report",
    context={"project": "APITestka", "passed": 98, "failed": 2},
)
```

Template model:
- subject
- text
- html
- variables
- metadata

Support shared templates, project-local templates, context validation and structured rendering errors.

## Attachment Policy

Introduce `AttachmentPolicy` with:
- per-file size limit
- total size limit
- allowed extensions
- allowed MIME types
- attachment count limit

Validation pipeline:

Attachment -> existence -> size -> extension -> MIME -> policy -> provider

Structured exceptions:
- AttachmentTooLarge
- AttachmentTypeNotAllowed
- AttachmentNotFound
- AttachmentCountExceeded
- TotalAttachmentSizeExceeded

## Microsoft Graph Provider

Introduce a provider abstraction:

```
MailProvider
├── SMTPProvider
├── MicrosoftGraphProvider
└── IMAPProvider
```

Common operations:
- send
- get_messages
- get_message
- create_draft
- delete_message

Graph support should include OAuth2, send mail, drafts, message retrieval and attachments, with provider errors mapped into MailThunder exceptions.

## Mail Triggers

Introduce provider-independent mail events:

- message_received
- message_sent
- message_failed
- attachment_received
- attachment_rejected
- authentication_failed
- connection_failed

Example:

```python
mail.on(
    event="message_received",
    filter={"subject": "[TEST]"},
    handler=handle_message,
)
```

Filters should support sender, recipient, subject, body, attachments, attachment type, time and custom metadata.

Trigger backends:

```
MailTriggerBackend
├── IMAPPollingBackend
├── IMAPIdleBackend
├── GraphPollingBackend
└── GraphWebhookBackend
```

## Project Mail Layer

Automation projects such as APITestka, WebRunner and LoadDensity should consume MailThunder through a common project-level mail layer.

Example:

```
APITestka/
├── api/
├── assertions/
├── reports/
└── mail/
    ├── config.py
    ├── triggers.py
    └── templates/
```

The project API must remain independent of the underlying mail provider.

## Proposed Package Structure

```
mailthunder/
├── __init__.py
├── core/
│   ├── mail.py
│   ├── message.py
│   ├── account.py
│   └── events.py
├── auth/
│   ├── base.py
│   ├── password.py
│   ├── oauth2.py
│   └── xoauth2.py
├── providers/
│   ├── base.py
│   ├── smtp.py
│   ├── imap.py
│   └── microsoft_graph.py
├── templates/
│   ├── engine.py
│   ├── template.py
│   └── loader.py
├── attachments/
│   ├── policy.py
│   ├── validator.py
│   └── mime.py
├── triggers/
│   ├── trigger.py
│   ├── filter.py
│   ├── dispatcher.py
│   ├── imap.py
│   └── graph.py
├── security/
│   ├── secrets.py
│   └── policies.py
├── scripting/
├── cli/
└── exceptions.py
```

## UI — MailThunder Studio

Domains:
- Dashboard
- Accounts
- Templates
- Triggers
- Policies
- Projects
- Logs
- Settings

The UI must consume the Core API rather than directly binding to SMTP/Graph implementations.

## PyPI / Documentation

Improve:
- description
- readme
- license
- authors / maintainers
- keywords
- classifiers
- project URLs
- documentation / source / issue URLs
- changelog
- supported Python versions

Product positioning:

> MailThunder — A provider-agnostic email automation framework for Python.

Feature summary:
- SMTP / IMAP
- OAuth2 / XOAUTH2
- Microsoft Graph API
- HTML/text templates
- attachment validation
- email triggers
- JSON automation
- project-level mail integration
- configurable security policies

## Backward Compatibility

Existing `SMTPWrapper` and `IMAPWrapper` APIs must continue to work during migration.

Use:

Legacy API -> Compatibility Adapter -> New Mail Core

Do not perform a breaking rewrite in a single PR.

## Implementation Priority

Status: every item ticked below is implemented (`docs/updates` U-20261008-01 to U-20261008-14), in the
`je_mail_thunder` package rather than a new `mailthunder` one (decision: U-20261008-14). What is still open is
tracked in `progress.md`: the other repositories adopting the project mail layer (#18), a run against real
mailboxes (#24), shared and app-only Graph mailboxes (#25) and saving from MailThunder Studio (#26).

### P0 — Foundation
- [x] New Core Mail API
- [x] Provider interface
- [x] Authentication interface
- [x] OAuth2
- [x] XOAUTH2
- [x] AttachmentPolicy
- [x] PyPI metadata
- [x] README / documentation
- [x] Backward compatibility layer (the legacy API is unchanged, the wrappers share the core's attachment policy and file-name checks, and `legacy_message` / `mail_from_wrappers` bridge to the core)

### P1 — Email Platform
- [x] Template Engine
- [x] MicrosoftGraphProvider
- [x] Trigger interface
- [x] Trigger dispatcher
- [x] Structured mail events

### P2 — Automation Integration
- [x] IMAP polling trigger
- [x] IMAP IDLE trigger
- [x] Graph polling trigger
- [x] Graph webhook trigger
- [x] Project Mail Layer
- [ ] Integration with automation projects (their repositories: `progress.md` #18)

### P3 — UI
- [x] MailThunder Studio
- [x] Dashboard
- [x] Accounts
- [x] Templates
- [x] Triggers
- [x] Policies
- [x] Projects
- [x] Logs
- [x] Settings

### P4 — Advanced
- [x] Advanced webhook/event system
- [x] Provider health monitoring
- [x] Audit logging
- [x] Additional mail providers

## Suggested PR Breakdown

Implement this roadmap through focused, independently reviewable PRs:

1. Core architecture + provider interfaces
2. Authentication abstraction
3. OAuth2 / XOAUTH2
4. Attachment policies
5. Template engine
6. Microsoft Graph provider
7. Trigger/event architecture
8. IMAP / Graph trigger backends
9. Project Mail Layer
10. UI redesign
11. Documentation / PyPI
12. Integration tests + migration cleanup

## Acceptance Criteria

- [x] Existing MailThunder users can continue using the legacy API
- [x] SMTP remains supported
- [x] IMAP remains supported
- [x] OAuth2 is available
- [x] XOAUTH2 is available
- [x] Microsoft Graph can send/retrieve mail (against a scripted transport; not yet against Graph itself: `progress.md` #24)
- [x] Templates generate subject/text/HTML
- [x] Attachment validation occurs before sending (through `Mail`, and in the SMTP wrappers)
- [x] Mail events can be registered independently of provider
- [x] Trigger backends are pluggable
- [x] Automation projects can use MailThunder as their mail layer (`project_mail()`; none has adopted it yet: `progress.md` #18)
- [x] PyPI metadata reflects the new product direction
- [x] UI consumes the Core API
- [ ] Unit/integration tests cover new abstractions (unit tests: yes, 676 of them; integration against real mailboxes: `progress.md` #24)
- [x] Documentation includes migration guidance

## Product Direction

MailThunder should evolve from:

> Python SMTP/IMAP automation library

into:

> Python Email Automation & Integration Framework

Target ecosystem:

```
                     Automation Projects
                            |
              +-------------+-------------+
              |             |             |
          APITestka      WebRunner    LoadDensity
              |             |             |
              +-------------+-------------+
                            |
                       Project Mail Layer
                            |
                        MailThunder
                            |
             +--------------+--------------+
             |              |              |
            SMTP           IMAP       Microsoft Graph
             |              |              |
          OAuth2          OAuth2         OAuth2
```

The mail trigger system should become the common event interface for automation projects.
