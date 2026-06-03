# Tweet Intake Operator Runbook

## Purpose

Use this runbook when triaging or submitting tweet requests for writing. The goal is to pick the right format, set the count fields correctly, and avoid handing downstream writers an ambiguous request.

## Quick Format Selection

| Use this format when | Set `format` to | Count rule |
| --- | --- | --- |
| You want standalone non-paid tweets | `organic` | `tweet_count` = number of tweet slots, `variants_per_tweet` = alternates per slot |
| You want promoted or ad copy that needs review | `paid` | `tweet_count` = number of paid tweet slots, `variants_per_tweet` = alternates per slot |
| You want one ordered multi-post sequence | `thread` | `tweet_count` = number of posts in the thread, `variants_per_tweet` must stay `1` |
| You want replies to an existing tweet | `reply` | `tweet_count` = number of reply slots, `variants_per_tweet` = alternates per slot |

## Operator Checklist

Before marking a request ready, confirm all of the following:

1. `format` matches the actual deliverable type.
2. `tweet_count` reflects slots in scope, not total output rows after variants.
3. `variants_per_tweet` is set to `1` for any thread request.
4. The audience, intended action, and source context are specific enough to write from.
5. Paid requests include explicit review and compliance ownership.
6. Reply requests include both the parent tweet ID and the author handle.

## How To Count Deliverables

### Organic

- Treat each requested tweet as independent.
- Total outputs = `tweet_count * variants_per_tweet`.
- Example: `tweet_count = 3`, `variants_per_tweet = 2` means six organic options grouped as three slots.

### Paid

- Count paid concepts the same way as organic tweets.
- Do not bypass review metadata just because the copy is short.
- Example: `tweet_count = 2`, `variants_per_tweet = 2` means four promoted-copy options grouped as two slots.

### Thread

- `tweet_count` is the number of posts in one thread.
- Keep `variants_per_tweet = 1`.
- If the requester wants two different full threads, create two separate requests instead of one request with variants.

### Reply

- Scope one reply request to one parent tweet.
- `tweet_count` is the number of distinct reply options for that same parent.
- Example: `tweet_count = 2`, `variants_per_tweet = 3` means six reply options grouped as two reply slots for the same source tweet.

## Ready Examples

### Organic Ready

```json
{
  "format": "organic",
  "tweet_count": 2,
  "variants_per_tweet": 2,
  "product_or_campaign": "Acme Analytics launch",
  "audience": "B2B SaaS founders",
  "intended_action": "Book a demo",
  "context": {
    "brief": "Launch-day tweet copy."
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

Status: `ready_for_writing`

### Paid Ready

```json
{
  "format": "paid",
  "tweet_count": 1,
  "variants_per_tweet": 3,
  "product_or_campaign": "Acme Analytics Q3 campaign",
  "audience": "Revenue operations leads",
  "intended_action": "Download the buyer guide",
  "context": {
    "brief": "Promoted social copy."
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

Status: `ready_for_writing`

### Thread Ready

```json
{
  "format": "thread",
  "tweet_count": 4,
  "variants_per_tweet": 1,
  "product_or_campaign": "Acme Analytics launch",
  "audience": "Existing customers",
  "intended_action": "Read the release notes",
  "context": {
    "brief": "Four-post launch thread."
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

Status: `ready_for_writing`

### Reply Ready

```json
{
  "format": "reply",
  "tweet_count": 2,
  "variants_per_tweet": 2,
  "product_or_campaign": "Acme Support",
  "audience": "Existing customer",
  "intended_action": "Acknowledge and redirect to support",
  "reply_to_tweet_id": "1796543210123456789",
  "reply_to_author_handle": "@customer_handle",
  "context": {
    "brief": "Respond to a customer complaint."
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

Status: `ready_for_writing`

## Common Blockers

| Problem | Result | Fix |
| --- | --- | --- |
| `thread` request with `variants_per_tweet > 1` | `needs_clarification` | Split alternate threads into separate requests |
| `reply` request without parent tweet metadata | `needs_clarification` | Add `reply_to_tweet_id` and `reply_to_author_handle` |
| `paid` request without review ownership | `blocked_review` | Add `review.approval_required` and `review.compliance_owner` |
| Missing audience, intended action, or context | `draft` or `needs_clarification` | Fill the missing common fields before handoff |

## Status Handling

- Move a request to `ready_for_writing` only when common fields and format-specific fields are complete.
- Use `needs_clarification` for invalid or ambiguous payloads.
- Use `blocked_review` when the payload is structurally valid but missing required approval/compliance data.
- Use `dropped` only when the requester or operator intentionally abandons the work.
