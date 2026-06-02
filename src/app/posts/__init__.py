"""Posts domain package."""

from app.posts.models import Post
from app.posts.repository import PostRepository

__all__ = ["Post", "PostRepository"]
