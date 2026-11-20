"""Modelos Pydantic de la API."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]
Sentiment = Literal["positivo", "neutral", "negativo"]


class Post(BaseModel):
    post_id: str
    title: str
    content: Optional[str] = None
    author: str
    subreddit: str
    url: Optional[str] = None
    score: Optional[int] = 0
    num_comments: Optional[int] = 0
    threat_category: str
    sentiment: str
    compound: Optional[float] = 0
    created_utc: Optional[datetime] = None
    collected_at: Optional[datetime] = None


class PostPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Post]


class NewPost(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    content: str = Field(default="", max_length=10000)
    source: str = Field(default="manual", max_length=100, description="Fuente/subreddit de origen")
    url: Optional[str] = Field(default=None, max_length=2000)


class PostUpdate(BaseModel):
    threat_category: Optional[Category] = None
    sentiment: Optional[Sentiment] = None


class SyncResult(BaseModel):
    ok: bool
    mode: str
    detail: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    total_posts: Optional[int] = None
    by_category: dict[str, int] = {}
