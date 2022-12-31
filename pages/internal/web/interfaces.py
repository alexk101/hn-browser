from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy_utils import database_exists, create_database
from appdirs import user_cache_dir
from pathlib import Path
from .schema import *

CACHE = f"sqlite:///{user_cache_dir('hn-browser')}/hackernews.db"

class DBM:
    def __init__(self) -> None:
        if database_exists(CACHE):
            print(f'DB exists')
        else:
            Path(user_cache_dir('hn-browser')).mkdir(parents=True, exist_ok=True)
            print(f'Creating DB')
            print(CACHE)
            create_database(CACHE)

        self.engine = create_engine(CACHE, echo = False)
        meta = MetaData()

        self.hn = Table(
            'hn_bookmarks', meta, 
            *hn_post
        )
        
        self.hn_child = Table(
            'hn_children', meta, 
            *kids
        )

        meta.create_all(self.engine)

DBMi = DBM()