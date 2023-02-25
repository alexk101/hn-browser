from __future__ import annotations

from sqlalchemy import Column, ForeignKey, create_engine, Table
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import (
    sessionmaker,
    relationship,
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from appdirs import user_cache_dir
from pathlib import Path
from datetime import datetime

CACHE = f"sqlite:///{user_cache_dir('hn-browser')}/hackernews.db"

# declarative base class
class Base(DeclarativeBase):
    pass


association_table = Table(
    "post_tag_link",
    Base.metadata,
    Column("post_id", ForeignKey("hn_bookmarks.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class Post(Base):
    __tablename__ = "hn_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    date_added: Mapped[datetime]
    author: Mapped[str]
    descendants: Mapped[int]
    score: Mapped[int]
    time: Mapped[datetime]
    title: Mapped[str]
    type: Mapped[str]
    url: Mapped[str | None]
    text: Mapped[str | None]
    img: Mapped[str | None]
    tags: Mapped[list[Tag]] = relationship(secondary=association_table)


class Child(Base):
    __tablename__ = "hn_children"

    id: Mapped[int]
    child: Mapped[str] = mapped_column(primary_key=True)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]


class DBM:
    def __init__(self) -> None:
        if database_exists(CACHE):
            print(f"DB exists")
        else:
            Path(user_cache_dir("hn-browser")).mkdir(parents=True, exist_ok=True)
            print(f"Creating DB")
            print(CACHE)
            create_database(CACHE)

        self.engine = create_engine(CACHE, echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
