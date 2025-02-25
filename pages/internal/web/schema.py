from __future__ import annotations

from sqlalchemy import Column, ForeignKey, create_engine, Table
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import (
    sessionmaker,
    relationship,
    DeclarativeBase,
    Mapped,
    mapped_column,
    MappedAsDataclass
)
from appdirs import user_cache_dir
from pathlib import Path
from datetime import datetime
import logging

CACHE = f"sqlite:///{user_cache_dir('hn-browser')}/hackernews.db"

# declarative base class
class Base(DeclarativeBase, MappedAsDataclass):
    def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_


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
    tags: Mapped[list[Tag]] = relationship(secondary=association_table)
    url: Mapped[str | None] = mapped_column(default=None)
    text: Mapped[str | None] = mapped_column(default=None)
    img: Mapped[str | None] = mapped_column(default=None)
    html: Mapped[str | None] = mapped_column(default=None)
    


class Child(Base):
    __tablename__ = "hn_children"

    id: Mapped[int]
    child: Mapped[str] = mapped_column(primary_key=True)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]

class Error(Base):
    __tablename__ = "post_errors"

    url: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(primary_key=True)
    description: Mapped[str]

class DBM:
    def __init__(self) -> None:
        # Check if DB exists. Create if not
        if database_exists(CACHE):
            print("DB exists")
            print(CACHE)
        else:
            Path(user_cache_dir("hn-browser")).mkdir(parents=True, exist_ok=True)
            print("Creating DB")
            create_database(CACHE)

        # Check if odbc config exists. Create if not
        db_config_out = Path.home() / '.odbc.ini'
        db_config_src = (Path(__file__)/'..'/'..'/'..'/'..'/'.odbc.ini').resolve()
        if not db_config_out.exists():
            with open(db_config_src, 'r') as fp:
                db_path = Path(user_cache_dir("hn-browser")) / 'hackernews.db'
                conf = ''.join(fp.readlines()).format(db_dir=str(db_path))
            with open(db_config_out, 'w') as fp:
                fp.write(conf)

        logging.info(f'DB location: {CACHE}')

        self.engine = create_engine(CACHE, echo=False) # type: ignore
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
