# Video Post v1 Decision Note

Status: accepted for follow-on implementation in this repo

Date: 2026-06-02

## Decision summary

This repo does not contain an upload, scan, transcode, CDN, or moderation pipeline today. Video posts v1 therefore will not attempt to reuse an existing local media stack. The chosen path is a narrow new processing flow owned by this FastAPI service, backed by the existing PostgreSQL/Alembic stack, with explicit queues and buckets introduced for video only.

## v1 client surfaces in scope

In scope:

- first-party mobile create-post flow
- first-party mobile feed and profile playback

Out of scope:

- web, desktop, and admin authoring
- stories, reels, direct messages, and ads
- multi-video posts, editing the binary after publish, and third-party API clients

## Chosen backend path

Existing repo services to extend:

- API service: this FastAPI app (`src/app/main.py`) with new `/api/v1/posts` routes
- persistence: existing PostgreSQL + SQLAlchemy + Alembic stack

There is no reusable media pipeline in this repo. Follow-on tasks should add one narrow video-post path with these canonical integration points:

- endpoints:
  - `POST /api/v1/posts`
  - `POST /api/v1/posts/{post_id}/video-uploads`
  - `POST /api/v1/posts/{post_id}/video-uploads/{upload_id}/complete`
  - `GET /api/v1/posts/{post_id}`
  - `DELETE /api/v1/posts/{post_id}`
- queues:
  - `video_post_scan`
  - `video_post_transcode`
  - `video_post_moderation`
  - `video_post_delete`
- storage buckets:
  - `video-post-uploads`
  - `video-post-quarantine`
  - `video-post-public`

`video-post-public` is the only playback origin. The API must not expose a playback URL until all required jobs have passed and the processed asset has been promoted into that bucket.

## Server-enforced limits

The server is the source of truth even if clients pre-validate.

- allowed MIME type: `video/mp4`
- allowed video codec: H.264/AVC only
- allowed audio codec: AAC-LC only
- max file size: 250 MiB
- max duration: 120 seconds
- max caption length: 2200 Unicode characters

Reject MOV, HEVC/H.265, VP9, AV1, and any upload without both a valid MP4 container and H.264 video stream.

## Post lifecycle

Create the post row before upload begins so moderation, retries, and deletes have a durable identifier.

Statuses:

- `draft`: post row exists, no accepted upload yet
- `uploading`: upload session issued and original object may be arriving
- `processing`: upload finalized and required jobs enqueued
- `ready`: scan, moderation, and transcode all succeeded; playback allowed
- `failed`: terminal validation, scan, moderation, or processing failure
- `deleted`: soft-deleted in the database and purge requested

Allowed transitions:

- `draft -> uploading`
- `draft -> deleted`
- `uploading -> processing`
- `uploading -> failed`
- `uploading -> deleted`
- `processing -> ready`
- `processing -> failed`
- `processing -> deleted`
- `failed -> uploading`
- `failed -> deleted`
- `ready -> deleted`

Playback is allowed only in `ready`.

## Required hooks before playback

These hooks are mandatory for v1:

- malware scan: run on the original object from `video-post-uploads`; send failures to `video-post-quarantine`
- transcode: normalize to the single supported playback format before publish
- moderation: block promotion until automated moderation marks the asset safe or explicitly reviewable
- retention: purge superseded originals from `video-post-uploads` after successful processing; keep public derivatives until delete
- deletion: on user or admin delete, move the row to `deleted`, revoke playback, and enqueue object purge from all three buckets through `video_post_delete`

## Repo source of truth

Use this note as the single source of truth for later `/posts` work. It is linked from `README.md` and from the API v1 router comment in `src/app/api/v1/router.py`.
