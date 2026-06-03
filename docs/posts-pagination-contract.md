# Posts Pagination Contract

The posts list endpoint uses page-number pagination.

- Endpoint: `GET /api/v1/posts`
- Success status: `200 OK`
- Error status: `422 Unprocessable Entity` for invalid query parameters
- Response envelope: `items`, `page`, `limit`, `total`

## Query Parameters

| Name | Type | Default | Constraints | Notes |
| --- | --- | --- | --- | --- |
| `page` | integer | `1` | `>= 1` | 1-based page number. Requests beyond the available result set still return `200` with an empty `items` array. |
| `limit` | integer | `20` | `1..100` | Maximum number of posts returned in a single page. |
| `status` | enum | none | `draft` or `published` | Filters by publication state. |
| `author_id` | UUID | none | valid UUID | Filters by owning author. |
| `search` | string | none | length `1..255` | Case-insensitive substring match across `title` and `body`. Leading and trailing whitespace is ignored before the query runs. |
| `sort_by` | enum | `created_at` | `created_at`, `updated_at`, `published_at`, `title` | Primary field used to order results. |
| `sort_order` | enum | `desc` | `asc` or `desc` | Sort direction. |

## Response Shape

```json
{
  "items": [
    {
      "id": "de305d54-75b4-431b-adb2-eb6b9e546014",
      "title": "Introducing Posts API v1",
      "body": "This release adds CRUD operations for posts.",
      "status": "published",
      "author_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
      "published_at": "2026-05-28T12:00:00Z",
      "created_at": "2026-05-28T11:45:00Z",
      "updated_at": "2026-05-28T12:00:00Z"
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 57
}
```

- `items`: posts for the requested page after filtering and sorting.
- `page`: the requested 1-based page number.
- `limit`: the requested page size.
- `total`: the total number of matching posts before pagination is applied.

## Sorting Behavior

Results are sorted by the requested `sort_by` field and `sort_order`. When multiple posts have the same primary sort value, the API applies the post `id` as a deterministic secondary tie-breaker in the same direction as `sort_order`.

## Pagination Caveat

This endpoint uses offset pagination (`offset = (page - 1) * limit`). When matching posts are inserted, updated, or deleted between requests, items can shift between pages. Clients should treat `page`, `limit`, and `total` as a snapshot of the query at request time rather than a stable cursor.
