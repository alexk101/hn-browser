from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

python_hn_post = {
    'id': 0,
    'date_added': datetime.now(), 
    'by': '', 
    'descendants': 0,
    'score': 0,
    'time': 0, 
    'title': '',
    'type': '',
    'url': '',
    'text': ''
}

hn_post = [
    Column('id', Integer, primary_key = True),
    Column('date_added', DateTime), 
    Column('by', String), 
    Column('descendants', Integer),
    Column('score', Integer),
    Column('time', DateTime),
    Column('title', String),
    Column('type', String),
    Column('url', String),
    Column('text', String)
]

kids = [
    Column('id', Integer),
    Column('child', String, primary_key=True)
]

