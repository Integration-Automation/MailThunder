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

### P0 — Foundation
- [ ] New Core Mail API
- [ ] Provider interface
- [ ] Authentication interface
- [ ] OAuth2
- [ ] XOAUTH2
- [ ] AttachmentPolicy
- [ ] PyPI metadata
- [ ] README / documentation
- [ ] Backward compatibility layer

### P1 — Email Platform
- [ ] Template Engine
- [ ] MicrosoftGraphProvider
- [ ] Trigger interface
- [ ] Trigger dispatcher
- [ ] Structured mail events

### P2 — Automation Integration
- [ ] IMAP polling trigger
- [ ] IMAP IDLE trigger
- [ ] Graph polling trigger
- [ ] Graph webhook trigger
- [ ] Project Mail Layer
- [ ] Integration with automation projects

### P3 — UI
- [ ] MailThunder Studio
- [ ] Dashboard
- [ ] Accounts
- [ ] Templates
- [ ] Triggers
- [ ] Policies
- [ ] Projects
- [ ] Logs
- [ ] Settings

### P4 — Advanced
- [ ] Advanced webhook/event system
- [ ] Provider health monitoring
- [ ] Audit logging
- [ ] Additional mail providers

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

- [ ] Existing MailThunder users can continue using the legacy API
- [ ] SMTP remains supported
- [ ] IMAP remains supported
- [ ] OAuth2 is available
- [ ] XOAUTH2 is available
- [ ] Microsoft Graph can send/retrieve mail
- [ ] Templates generate subject/text/HTML
- [ ] Attachment validation occurs before sending
- [ ] Mail events can be registered independently of provider
- [ ] Trigger backends are pluggable
- [ ] Automation projects can use MailThunder as their mail layer
- [ ] PyPI metadata reflects the new product direction
- [ ] UI consumes the Core API
- [ ] Unit/integration tests cover new abstractions
- [ ] Documentation includes migration guidance

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
