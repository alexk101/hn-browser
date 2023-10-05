from bs4 import BeautifulSoup as sp
from typing import List, Dict, Tuple, TypeAlias, Optional
import aiohttp
import asyncio
import json
from .schema import Child, Post, Error
from . import interfaces as inter
from urllib.parse import urljoin, quote_plus
from datetime import datetime
from sqlalchemy import update
import logging
from enum import Enum
import re

class ErrorType(Enum):
    """
    Scraping Error Types
    """
    url = 'url'
    img = 'image'
    resp = 'no response'

AsyncAPIData: TypeAlias = Tuple[
    Optional[Post], 
    Optional[List[Child]]
]


class MultiScraper:
    def __init__(
        self, links: Dict[datetime, str], silent: bool = False, verbose: bool = False
    ) -> None:
        self.links: Dict[datetime, str] = links
        self.silent: bool = silent
        self.verbose = verbose

        temp = asyncio.run(self.get_all())
        posts = temp[0]
        errors = temp[1]

        self.children: List[Child] = []
        self.posts: List[Post] = []
        self.errors: List[Error] = errors

        for (post, child) in posts:
            if post is not None:
                self.posts.append(post)
            if child is not None:
                self.children += child


        if self.verbose and (not self.silent):
            logging.debug("Pages:")
            for page in self.posts:
                logging.debug(page)

            logging.debug("Children:")
            for child in self.children:
                logging.debug(child)

    async def get_image(
        self, url: Optional[str], session: aiohttp.ClientSession
    ) -> Tuple[Optional[str], Optional[Error]]:
        err = None
        img = None
        if url is not None:
            try:
                async with session.get(url=url) as response:
                    resp = await response.read()
                    resp = resp.decode("utf-8")
                    if len(resp):
                        soup = sp(resp, "html.parser")
                        images = soup.findAll("img")
                        if len(images):
                            if not self.silent:
                                logging.info(
                                    "Successfully got image from {} with resp of length {}.".format(
                                        url, len(resp)
                                    )
                                )
                            img = images[0].attrs["src"]
                            if not img.startswith("data:image"):
                                img = urljoin(url, img)
                        else:
                            if not self.silent:
                                logging.info("No images found at {}".format(url))
                    else:
                        logging.warning(f"Unable to get image from {url}. No response.")
                        err = Error(
                            url=url, type=ErrorType.resp.value, 
                            time=datetime.now(), description='no response'
                        )
            except Exception as e:
                logging.warning("Unable to get image from {} due to {}.".format(url, e.__class__))
                err = Error(
                    url=url, type=ErrorType.img.value, 
                    time=datetime.now(), description=str(e.__class__)
                )
        return img, err

    async def get_api_data(
        self, record: Tuple[datetime, str], session: aiohttp.ClientSession
    ) -> Tuple[AsyncAPIData, Optional[Error]]:
        time, url = record
        post = None
        children = None
        err = None
        try:
            async with session.get(url=url) as response:
                response.headers
                resp = await response.read()
                resp = resp.decode("utf-8", errors='ignore')
                if len(resp) and "Sorry" not in resp:
                    if not self.silent:
                        logging.info(
                            "Successfully got url {} with resp of length {}.".format(
                                url, len(resp)
                            )
                        )
                    resp_dec: Dict = json.loads(resp)

                    # Response wrangling
                    resp_dec["author"] = resp_dec.pop("by")
                    resp_dec["time"] = datetime.fromtimestamp(resp_dec.pop("time"))
                    resp_dec["date_added"] = time
                    resp_dec['tags'] = []

                    # Construct Objects
                    if "kids" in resp_dec.keys():
                        children = [
                            Child(**{"id": resp_dec["id"], "child": child})
                            for child in resp_dec.pop("kids")
                        ]

                    # FIXME
                    # Validation
                    post = Post(**resp_dec)
                    if (not self.silent) and self.verbose:
                        print(post)
                else:
                    print(f"Unable to get url {url}. No response")
                    err = Error(
                        url=url, type=ErrorType.resp.value, 
                        time=datetime.now(), description='no response'
                    )
        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))
            err = Error(
                url=url, type=ErrorType.url.value, 
                time=datetime.now(), description=str(e.__class__)
            )

        return (post, children), err

    async def get_all(self) -> Tuple[List[AsyncAPIData],List[Error]]:

        timeout = aiohttp.ClientTimeout(total=20)
        conn = aiohttp.TCPConnector(limit=50)

        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
            print("Querying HN API for data")
            resp: List[Tuple[AsyncAPIData, Optional[Error]]] = await asyncio.gather(
                *[self.get_api_data(record, session) for record in self.links.items()]
            )
            posts = [x[0] for x in resp]
            errors: List[Error] = list(filter(
                lambda x: x is not None, [x[1] for x in resp]
            )) # type: ignore

            tasks = []
            for record in posts:
                if record[0] is not None:
                    tasks.append(self.get_image(record[0].url, session))
            print("Scraping links for images")
            
            if tasks:
                img_resp: List[Tuple[str, Optional[Error]]] = await asyncio.gather(*tasks)
                images = [x[0] for x in img_resp]
                img_errs: List[Error] = filter(
                    lambda x: x is not None, [x[1] for x in img_resp]
                ) # type: ignore
                errors += list(img_errs)

                for record, image in zip(posts, images):
                    if record[0] is not None:
                        record[0].img = image
        if not self.silent:
            print(f"Finalized all. Got {len(resp)} new bookmarks.")
        return posts, errors

    def save(self):
        if len(self.posts):
            print("Saving DB")

            for ind, x in enumerate(self.posts):
                print(f"{ind}: {x.url}")

            # Add new bookmarks
            inter.DBMi.session.add_all(self.posts)

            # Add new children
            inter.DBMi.session.add_all(self.children)

            # Add errors
            inter.DBMi.session.add_all(self.errors)

            # Commit changes
            inter.DBMi.session.commit()

            print("Saved DB")


def update_posts(posts: List[Post]):
    if len(posts):
        print("Updating DB")
        temp = [x.to_dict() for x in posts]
        # for x in temp:
        #     if '_sa_instance_state' in x.keys():
        #         del x['_sa_instance_state']
        print(f'temp: {temp}')
        inter.DBMi.session.execute(update(Post), temp)
        # Commit changes
        inter.DBMi.session.commit()
        print("Updated DB")


class BingImgSearch():
    def __init__(self) -> None:
        self.base_url = 'https://www.bing.com/images/search?q={q}'
        self.queries = []
        self.titles = []

    def add_query(self, q: str):
        self.queries.append(self.base_url.format(q=quote_plus(q)))
        self.titles.append(q)

    async def query_img(
        self, url: str, session: aiohttp.ClientSession
    ) -> Optional[str]:

        image = None

        try:
            async with session.get(url=url) as response:
                resp = await response.read()
                resp = resp.decode("utf-8", errors='ignore')
                if len(resp):
                    images = re.findall('murl&quot;:&quot;(.*?)&quot;', resp)
                    # print(f'found {len(images)} images')
                    if images:
                        image = images[0]
                    else:
                        logging.info("Bing found no images for{}".format(url))
                else:
                    print(f"Unable to get url {url}. No response")
                    err = Error(
                        url=url, type=ErrorType.resp.value, 
                        time=datetime.now(), description='no response'
                    )
        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))
            err = Error(
                url=url, type=ErrorType.img.value, 
                time=datetime.now(), description=str(e.__class__)
            )

        return image

    async def collect(self):
        timeout = aiohttp.ClientTimeout(total=20)
        conn = aiohttp.TCPConnector(limit=50)

        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
            print("Querying Bing for image data")
            resp: List[Optional[str]] = await asyncio.gather(
                *[self.query_img(url, session) for url in self.queries]
            )
        return resp

    def get_urls(self):
        return asyncio.run(self.collect())

async def validate_all(imgs: List[Optional[str]]) -> List[Optional[str]]:
    image_formats = (
        "image/png", 
        "image/jpeg", 
        "image/jpg", 
        'image/gif',
        'image/svg+xml'
    )

    async def validate(
        img_url: Optional[str], session: aiohttp.ClientSession
    ) -> Optional[bool]:
        valid = False
        if img_url is not None:
            try:
                async with session.head(url=img_url) as r:
                    if "Content-Type" not in r.headers:
                        print(f'{img_url} no content')
                    else:
                        if r.headers["Content-Type"] not in image_formats:
                            print(f'{r.headers["Content-Type"]}: {img_url}')
                        else:
                            valid = True
            except Exception as e:
                print("Unable to get url {} due to {}.".format(img_url, e.__class__))
                print("Unable to get url due to {}.".format(e.__class__))
                err = Error(
                    url=img_url, type=ErrorType.img.value, 
                    time=datetime.now(), description=str(e.__class__)
                )
        return valid

    timeout = aiohttp.ClientTimeout(total=40)
    conn = aiohttp.TCPConnector(
        limit=20, 
        enable_cleanup_closed=True,
    )
    client = aiohttp.ClientSession(
        timeout=timeout, 
        connector=conn, 
        connector_owner=True
    )

    async with client as session:
        print("Validating image data")
        resp: List[Optional[str]] = await asyncio.gather(
            *[validate(url, session) for url in imgs]
        )
    return resp