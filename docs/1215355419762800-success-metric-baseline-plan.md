# Task 1215355419762800: primary success metric and baseline plan

Status: provisional success metric and baseline plan for Issue `1215354560850994`

Date: 2026-06-03

## Purpose

This note specifies the primary success metric and first baseline plan for Issue `1215354560850994`. It builds on the earlier problem-statement framing and evidence-ranking work. Because the current issue bundle still lacks authoritative user research, support evidence, and production usage data, the metric must stay close to the user's core job and must not treat raw request volume as success.

## Inputs used

- Parent PDLC artifact in Asana task `1215354560850994`
- Child task `1215355533542054` triage output for primary user segment and workflow
- Task note `docs/1215355506805570-problem-statement.md`
- Task note `docs/1215355507138772-validation-evidence.md`
- Branch `codex/1215320036039132-chat-telemetry-foundation` (`60bdb96`)
- Branch `codex/1215320036113597-user-scoped-retrieval-service` (`046b32d`)
- Branch `codex/1215324006007161-expose-authenticated-chat-api` (`303d71a`)
- Branch `codex/1215313150792721-thin-chat-ui-entry-point` (`b0cf04d`)

## Metric selection rule

The primary metric should satisfy all of the following:

1. Measure whether the signed-in user gets a grounded answer from accessible posts.
2. Be computable from the current telemetry design without logging free-text prompts or answers.
3. Avoid rewarding request volume, feature exposure, or traffic spikes that do not improve the user outcome.
4. Stay valid while the current product area and user segment remain working hypotheses rather than validated facts.

## Primary success metric

Primary metric: grounded answer rate for authenticated post-question requests.

Definition: the share of authenticated `/api/v1/chat` requests that finish with a grounded answer sourced from the signed-in user's accessible posts instead of an insufficient-evidence fallback or a hard failure.

Formula:

```text
grounded_answer_rate =
count(distinct request_id where
  chat.request.status = "success"
  and chat.retrieval.retrieval_result_count >= 1
  and chat.retrieval.retrieval_used_count >= 1
  and chat.response.insufficient_evidence = false
  and chat.response.citation_count >= 1
)
/
count(distinct request_id for authenticated `/api/v1/chat` requests)
```

This metric is the best current proxy for user value because it requires the workflow to retrieve usable evidence, produce a response, and avoid the explicit insufficient-evidence fallback. It is stronger than request volume or raw completion rate, and it matches the issue's working hypothesis: a signed-in user is trying to get an answer from posts they already authored or can access.

## Supporting indicators, not the primary metric

| Metric | Role | Why it is not the main success metric |
| --- | --- | --- |
| `chat.retrieval_miss` rate | Diagnostic | Shows whether evidence lookup failed, but not whether the user ultimately got a grounded answer. |
| `chat.insufficient_evidence_fallback` rate | Diagnostic | Important failure mode, but it only measures fallback frequency. |
| Citation coverage | Quality check | Measures grounding depth, but not whether the overall request succeeded. |
| `chat.model_failure` rate | Reliability guardrail | Protects against provider regressions, but it is not a user-value metric by itself. |
| `chat.request` latency | Experience guardrail | Speed matters, but a fast ungrounded answer is still a failure. |

## Baseline status today

No authoritative usage baseline exists yet. The repository contains telemetry groundwork, retrieval wiring, and an authenticated chat surface, but no production dashboard, query output, or exported snapshot was attached to this issue. The current numeric baseline is therefore unavailable and must be created from first-party telemetry rather than estimated from stakeholder intent.

## Baseline plan

### 1. Lock the event contract before collection

- Emit `chat.request`, `chat.retrieval`, `chat.response`, and `chat.metric` with the same stable `request_id`.
- Include the route and authenticated-scope marker on every event used in the baseline query.
- Keep free-text prompts, answers, and retrieved content out of telemetry; rely on counts, flags, and status fields only.

### 2. Capture the first usable baseline window

- Start the baseline once the authenticated posts-chat workflow has real internal, beta, or production traffic.
- Capture the first 14 full days of authenticated traffic after the event contract is stable.
- If the window yields fewer than 200 completed requests, extend the window to 28 days before locking the baseline.

### 3. Compute the baseline from joined events

- Join `chat.request`, `chat.retrieval`, and `chat.response` by `request_id`.
- Calculate daily and weekly grounded answer rate for authenticated `/api/v1/chat` traffic.
- Break out supporting indicators alongside the primary metric: retrieval-miss rate, insufficient-evidence fallback rate, model-failure rate, citation coverage, and p95 request latency.

### 4. Apply data-quality gates

- Require >=95% request-response join coverage before publishing the baseline as authoritative.
- Exclude internal smoke tests, scripted load tests, and replay traffic from the baseline dataset.
- Mark the baseline invalid if logging outages or schema drift make the numerator or denominator incomplete.

### 5. Publish the baseline pack

- Record the baseline window dates, completed-request count, grounded answer rate, and all supporting indicators in one reviewable note or dashboard snapshot.
- Use that snapshot as the fixed comparison point for follow-on iteration work; do not recalculate the original baseline after instrumentation changes without calling out the break in comparability.

## Guardrails

- Do not substitute request volume, sign-ins, or total chat sessions for the success metric.
- Do not claim this metric validates demand; it only measures how often the current workflow produces a grounded answer once used.
- Revisit the metric if higher-authority research or support evidence shows that the user job to be done is different from the current working hypothesis.
