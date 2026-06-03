# Tweet Intake Contract

## Purpose

This document is the canonical developer-facing contract for tweet intake requests. It defines how callers must encode tweet format, how `tweet_count` and `variants_per_tweet` are interpreted for each supported format, and which combinations are considered ready for writing.

## Shared Payload Shape

All tweet requests use the same top-level payload. Format-specific rules add required fields or tighter validation on top of this base shape.

```json
{
  "product_or_campaign": "Acme Analytics launch",
  "audience": "B2B SaaS founders",
  "intended_action": "Book a demo",
  "format": "organic",
  "tweet_count": 2,
  "variants_per_tweet": 3,
  "tone": "clear and confident",
  "cta": "Book a demo",
  "deadline": "2026-06-10",
  "success_metric": "Demo bookings",
  "context": {
    "brief": "Launch-day social copy for the new analytics dashboard.",
    "source_materials": [
      "launch-brief-v3",
      "messaging-house"
    ]
  },
  "review": {
    "approval_required": false,
    "approver": null,
    "compliance_owner": null
  },
  "compliance": {
    "regulated_claims": false,
    "brand_safety_notes": null
  }
}
```

## Required Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `product_or_campaign` | string | yes | Human-readable name for the product, launch, or campaign. |
| `audience` | string | yes | Intended reader segment for the tweet output. |
| `intended_action` | string | yes | Desired response, for example `Book a demo` or `Read the announcement`. |
| `format` | enum | yes | One of `organic`, `paid`, `thread`, or `reply`. |
| `tweet_count` | integer | yes | Positive integer whose meaning depends on `format`. |
| `variants_per_tweet` | integer | yes | Positive integer whose meaning depends on `format`. |
| `tone` | string | no | Style guidance for the writer. |
| `cta` | string | no | Explicit call to action, if needed. |
| `deadline` | string | no | ISO date or timestamp expected by the intake surface. |
| `success_metric` | string | no | Goal used to judge whether the request is fit for purpose. |
| `context` | object | yes | Must include at least one usable brief, source document, or messaging reference. |
| `review` | object | yes | Review and approval metadata. |
| `compliance` | object | yes | Compliance and risk metadata, even when the values are `false` or `null`. |

## Format Scope Matrix

The `format` field changes the scope of the request. That scope determines how the count fields must be interpreted.

| Format | Request scope | `tweet_count` means | `variants_per_tweet` means | Additional required fields |
| --- | --- | --- | --- | --- |
| `organic` | Independent standalone tweets | Number of separate organic tweet slots requested in one batch | Number of alternate phrasings required for each tweet slot | None |
| `paid` | Independent paid/promoted tweet concepts | Number of separate paid tweet slots requested in one batch | Number of alternate phrasings required for each paid tweet slot | `review.approval_required`, `review.compliance_owner` |
| `thread` | One ordered thread | Number of tweets in the single thread | Must be `1`; the system does not support branching thread variants inside one request | None |
| `reply` | Independent replies to the same source tweet | Number of reply candidates requested for the same parent tweet | Number of alternate phrasings required for each reply slot | `reply_to_tweet_id`, `reply_to_author_handle` |

## Validation Semantics

### Base Validation

- `format` is required and must match one of the supported enum values exactly.
- `tweet_count` must be an integer greater than or equal to `1`.
- `variants_per_tweet` must be an integer greater than or equal to `1`.
- `context.brief` or `context.source_materials` must be present so the request is writable.
- Missing common required fields keep the request in `draft` or move it to `needs_clarification`.

### Format-Specific Validation

#### Organic

- `tweet_count` is the number of independent organic tweets to write.
- `variants_per_tweet` multiplies each requested tweet slot.
- Expected deliverables = `tweet_count * variants_per_tweet`.
- Example: `tweet_count = 2` and `variants_per_tweet = 3` requests `6` organic tweet candidates arranged as `2` slots with `3` variants each.

#### Paid

- `tweet_count` is the number of distinct paid tweet concepts to write.
- `variants_per_tweet` multiplies each paid concept slot.
- Expected deliverables = `tweet_count * variants_per_tweet`.
- Paid requests are not `ready_for_writing` until `review.approval_required` is explicitly set and `review.compliance_owner` is populated.
- If regulated claims are present, missing review metadata moves the request to `blocked_review`, not `ready_for_writing`.

#### Thread

- `tweet_count` is the number of posts in one ordered thread.
- `tweet_count` must be greater than or equal to `2`; a thread with `1` tweet must be submitted as `organic` or `paid`.
- `variants_per_tweet` must be `1`.
- If a caller needs multiple alternate thread versions, submit multiple thread requests instead of increasing `variants_per_tweet`.
- A thread request with `variants_per_tweet > 1` should fail validation and move to `needs_clarification`.

#### Reply

- `tweet_count` is the number of distinct reply candidates requested for one parent tweet.
- `variants_per_tweet` multiplies each reply slot.
- Expected deliverables = `tweet_count * variants_per_tweet`.
- `reply_to_tweet_id` and `reply_to_author_handle` are required because reply writing is scoped to a specific parent conversation.
- A reply request without parent-tweet metadata should fail validation and remain `needs_clarification`.

## Readiness States

| Status | Meaning |
| --- | --- |
| `draft` | The request exists but is missing core intake data. |
| `needs_clarification` | The payload is structurally present but ambiguous, invalid, or missing format-specific requirements. |
| `ready_for_writing` | The request satisfies common and format-specific validation and can be handed to writing/generation. |
| `blocked_review` | The request is otherwise valid but is waiting on required review or compliance approval metadata. |
| `dropped` | The request was intentionally abandoned and should not re-enter writing without a new intake event. |

## Ready Examples By Format

### Organic

```json
{
  "product_or_campaign": "Acme Analytics launch",
  "audience": "B2B SaaS founders",
  "intended_action": "Book a demo",
  "format": "organic",
  "tweet_count": 2,
  "variants_per_tweet": 2,
  "tone": "clear and confident",
  "cta": "Book a demo",
  "context": {
    "brief": "Launch-day tweet copy.",
    "source_materials": [
      "launch-brief-v3"
    ]
  },
  "review": {
    "approval_required": false,
    "approver": null,
    "compliance_owner": null
  },
  "compliance": {
    "regulated_claims": false,
    "brand_safety_notes": null
  }
}
```

Expected status: `ready_for_writing`

### Paid

```json
{
  "product_or_campaign": "Acme Analytics Q3 campaign",
  "audience": "Revenue operations leads",
  "intended_action": "Download the buyer guide",
  "format": "paid",
  "tweet_count": 1,
  "variants_per_tweet": 3,
  "tone": "direct and benefit-led",
  "cta": "Download the buyer guide",
  "context": {
    "brief": "Promoted social copy for the Q3 demand-gen campaign.",
    "source_materials": [
      "buyer-guide-summary"
    ]
  },
  "review": {
    "approval_required": true,
    "approver": "paid-social-lead",
    "compliance_owner": "legal-marketing"
  },
  "compliance": {
    "regulated_claims": true,
    "brand_safety_notes": "Do not promise outcomes."
  }
}
```

Expected status: `ready_for_writing`

### Thread

```json
{
  "product_or_campaign": "Acme Analytics launch",
  "audience": "Existing customers",
  "intended_action": "Read the full release notes",
  "format": "thread",
  "tweet_count": 4,
  "variants_per_tweet": 1,
  "tone": "helpful and explanatory",
  "cta": "Read the full release notes",
  "context": {
    "brief": "Four-post launch thread covering the problem, feature, proof, and CTA.",
    "source_materials": [
      "release-notes-v2"
    ]
  },
  "review": {
    "approval_required": false,
    "approver": null,
    "compliance_owner": null
  },
  "compliance": {
    "regulated_claims": false,
    "brand_safety_notes": null
  }
}
```

Expected status: `ready_for_writing`

### Reply

```json
{
  "product_or_campaign": "Acme Support",
  "audience": "Existing customer",
  "intended_action": "Acknowledge the report and direct the user to support",
  "format": "reply",
  "tweet_count": 2,
  "variants_per_tweet": 2,
  "tone": "empathetic and concise",
  "cta": "Please DM your ticket number",
  "reply_to_tweet_id": "1796543210123456789",
  "reply_to_author_handle": "@customer_handle",
  "context": {
    "brief": "Respond to a customer complaint about dashboard latency.",
    "source_materials": [
      "support-playbook-latency"
    ]
  },
  "review": {
    "approval_required": false,
    "approver": null,
    "compliance_owner": null
  },
  "compliance": {
    "regulated_claims": false,
    "brand_safety_notes": "Avoid discussing account details publicly."
  }
}
```

Expected status: `ready_for_writing`

## Invalid Examples

### Invalid Thread Variant Request

```json
{
  "format": "thread",
  "tweet_count": 4,
  "variants_per_tweet": 2
}
```

Expected status: `needs_clarification`

Reason: one intake request can only describe one coherent thread. Branching thread variants must be split into separate requests.

### Invalid Reply Request

```json
{
  "format": "reply",
  "tweet_count": 1,
  "variants_per_tweet": 1
}
```

Expected status: `needs_clarification`

Reason: reply requests are incomplete without `reply_to_tweet_id` and `reply_to_author_handle`.
