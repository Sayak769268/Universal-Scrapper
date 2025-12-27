from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any, Dict, Union
from datetime import datetime

class ScrapeRequest(BaseModel):
    url: HttpUrl

class MetaData(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    canonical: Optional[str] = None

class Link(BaseModel):
    text: str
    href: str

class Image(BaseModel):
    src: str
    alt: str

class SectionContent(BaseModel):
    headings: List[str] = Field(default_factory=list)
    text: str = ""
    links: List[Link] = Field(default_factory=list)
    images: List[Image] = Field(default_factory=list)
    lists: List[List[str]] = Field(default_factory=list)
    tables: List[Any] = Field(default_factory=list)

class Section(BaseModel):
    id: str
    type: str # hero | section | nav | footer | list | grid | faq | pricing | unknown
    label: str
    sourceUrl: str
    content: SectionContent
    rawHtml: str
    truncated: bool

class Interactions(BaseModel):
    clicks: List[str] = Field(default_factory=list)
    scrolls: int = 0
    pages: List[str] = Field(default_factory=list)

class Error(BaseModel):
    message: str
    phase: str

class ScrapeResult(BaseModel):
    url: str
    scrapedAt: str
    meta: MetaData
    sections: List[Section]
    interactions: Interactions
    errors: List[Error] = Field(default_factory=list)

class ScrapeResponse(BaseModel):
    result: ScrapeResult
