## Tweet Request Observability

This note defines the log and counter contract for Asana `1215356956196742`.

### Lifecycle events

- `tweet_request.created`
- `tweet_request.clarification_loop`
- `tweet_request.readiness_evaluated`
- `tweet_request.drop_decision`
- `tweet_request.compliance_blocked`
- `tweet_request.status_transition`

### Counter events

All counters are emitted through `event=tweet_request.metric`.

- `metric_name=tweet_request.created`
- `metric_name=tweet_request.clarification_loop`
- `metric_name=tweet_request.readiness_evaluated`
- `metric_name=tweet_request.not_writable`
- `metric_name=tweet_request.drop_decision`
- `metric_name=tweet_request.compliance_blocked`

### Required query fields

- `request_id`
- `event`
- `metric_name`
- `readiness_state`
- `is_writable`
- `drop_reason`
- `blocked_transition`
- `blocker_summary`
- `blocker_codes`
- `from_status`
- `to_status`
- `transition_reason`

### Example questions

- Why are tweet requests failing to become writable?
  Filter `event=tweet_request.readiness_evaluated` and `is_writable=false`, then group by `blocker_summary`, `blocker_codes`, and `readiness_state`.

- Which transitions were blocked by compliance review?
  Filter `event=tweet_request.compliance_blocked` or `event=tweet_request.status_transition` with `audit_log=true`, then group by `blocked_transition` or `to_status`.

- How often are requests being dropped?
  Filter `event=tweet_request.metric` and `metric_name=tweet_request.drop_decision`, then group by `drop_reason`.
