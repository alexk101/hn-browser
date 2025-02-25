from bs4 import BeautifulSoup as sp
from typing import List, Dict, Tuple, TypeAlias, Optional
import json
from .schema import Child, Post, Error
from . import interfaces as inter
from urllib.parse import urljoin, quote_plus
from datetime import datetime
from sqlalchemy import update, insert
import logging
from enum import Enum
from requests import Response
import numpy as np
import trio
import asks
import re

class ErrorType(Enum):
    """
    Scraping Error Types
    """
    url = 'url'
    img = 'image'
    bing = 'bing image'
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

        posts = trio.run(self.get_all)

        self.children: List[Child] = []
        self.posts: List[Post] = []

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
        self, url: Optional[str], 
        session: asks.Session,
        output: List[Optional[str]],
        ind: int
    ):
        """
        Get the image from the url

        Args:
            url (Optional[str]): The url to get the image from
            session (asks.Session): The session to use to get the image
            output (List[Optional[str]]): The output list to store the image
            ind (int): The index of the url in the list
        """
        err = None
        img = None
        if url is not None:
            try:
                resp: Response = await session.get(url, timeout=10)
                content = resp.content.decode("utf-8")
                if resp.reason_phrase=='OK': # type: ignore
                    soup = sp(content, "html.parser")
                    images = soup.findAll("img")
                    if len(images):
                        if not self.silent:
                            mess = "Successfully got image from {} of length {}."
                            logging.info(mess.format(url, resp.__sizeof__()))
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
                logging.warning("Unable to get image from {} due to {}.".format(
                        url, 
                        e.__class__
                    )
                )
                err = Error(
                    url=url, type=ErrorType.img.value, 
                    time=datetime.now(), description=str(e.__class__)
                )
            if err is not None:
                inter.DBMi.session.execute(insert(Error), [err.to_dict()])
            output[ind] = img

    async def get_api_data(
        self, record: Tuple[datetime, str], 
        session: asks.Session,
        output: List[AsyncAPIData],
        ind: int
    ):
        """
        Get the api data from the url

        Args:
            record (Tuple[datetime, str]): The record to get the api data from
            session (asks.Session): The session to use to get the api data
            output (List[AsyncAPIData]): The output list to store the api data
            ind (int): The index of the record in the list
        """
        time, url = record
        post = None
        children = None
        err = None
        try:
            resp: Response = await session.get(url, timeout=10)
            content = resp.content.decode("utf-8", errors='ignore')
            if len(content) and "Sorry" not in content:
                if not self.silent:
                    logging.info(
                        "Successfully got url {} with resp of length {}.".format(
                            url, len(content)
                        )
                    )
                resp_dec: Dict = json.loads(content)

                # Response wrangling
                resp_dec["author"] = resp_dec.pop("by")
                resp_dec["time"] = datetime.fromtimestamp(resp_dec.pop("time"))
                resp_dec["date_added"] = time
                resp_dec['tags'] = []

                # Get HTML content if URL exists
                if "url" in resp_dec and resp_dec["url"]:
                    try:
                        html_resp = await session.get(resp_dec["url"], timeout=10)
                        if html_resp.reason_phrase == 'OK':
                            resp_dec['html'] = html_resp.content.decode("utf-8", errors='ignore')
                            if not self.silent:
                                logging.info(f"Successfully got HTML for {resp_dec['url']}")
                    except Exception as e:
                        logging.warning(f"Failed to get HTML for {resp_dec['url']}: {str(e)}")

                # Construct Objects
                if "kids" in resp_dec.keys():
                    children = [
                        Child(**{"id": resp_dec["id"], "child": child})
                        for child in resp_dec.pop("kids")
                    ]

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

        if err is not None:
            inter.DBMi.session.execute(insert(Error), [err.to_dict()])
        output[ind] = (post, children)

    async def get_all(self) -> List[AsyncAPIData]:
        """
        Get all the api data from the urls

        Returns:
            List[AsyncAPIData]: The list of api data
        """
        posts: List[AsyncAPIData] = [(None,None)] * len(self.links)
        async with trio.open_nursery() as n:
            for ind, record in enumerate(self.links.items()):
                n.start_soon(self.get_api_data, record, inter.SESS, posts, ind)

        print("Scraping links for images")
        images: List[Optional[str]] = [None] * len(posts)
        async with trio.open_nursery() as n:
            for ind, api_resp in enumerate(posts):
                if api_resp[0] is not None:
                    n.start_soon(self.get_image, api_resp[0].url, inter.SESS, images, ind)

        for record, image in zip(posts, images):
            if record[0] is not None:
                record[0].img = image
        if not self.silent:
            print(f"Finalized all. Got {len(posts)} new bookmarks.")

        inter.DBMi.session.commit()
        return posts

    def save(self):
        """
        Save the posts and children to the database
        """
        if len(self.posts):
            print("Saving DB")

            for ind, x in enumerate(self.posts):
                print(f"{ind}: {x.url}")

            # Add new bookmarks
            inter.DBMi.session.add_all(self.posts)

            # Add new children
            inter.DBMi.session.add_all(self.children)

            # Commit changes
            inter.DBMi.session.commit()

            print("Saved DB")


def update_posts(posts: List[Post]):
    """
    Update the posts in the database

    Args:
        posts (List[Post]): The posts to update
    """
    if len(posts):
        print("Updating DB")
        temp = [x.to_dict() for x in posts]
        print(f'temp: {temp}')
        inter.DBMi.session.execute(update(Post), temp)
        # Commit changes
        inter.DBMi.session.commit()
        print("Updated DB")


class BingImgSearch():
    """
    Bing Image Search
    """
    def __init__(self) -> None:
        self.base_url = 'https://www.bing.com/images/search?q={q}&first=1'
        self.queries = []
        self.titles = []

    def add_query(self, q: str):
        self.queries.append(self.base_url.format(q=quote_plus(q)))
        self.titles.append(q)

    async def query_img(
        self, url: str, 
        session: asks.Session, 
        output: List[Optional[str]],
        ind: int
    ) -> Optional[str]:

        err = None
        try:
            resp: Response = await session.get(url, timeout=10)
            if resp.reason_phrase=='OK': # type: ignore
                content = resp.content.decode()
                images = re.findall('murl&quot;:&quot;(.*?)&quot;', content)
                # print(f'found {len(images)} images')
                if images:
                    output[ind] = images[0]
                else:
                    logging.info("Bing found no images for {}".format(url))
            else:
                print(f"Unable to get url {url}. No response")
                err = Error(
                    url=url, type=ErrorType.resp.value, 
                    time=datetime.now(), description='no response'
                )
        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))
            err = Error(
                url=url, type=ErrorType.bing.value, 
                time=datetime.now(), description=str(e.__class__)
            )
        if err is not None:
            inter.DBMi.session.execute(insert(Error), [err.to_dict()])


    async def collect(self):    
        output = [None] * len(self.queries)
        async with trio.open_nursery() as n:
            for ind, path in enumerate(self.queries):
                n.start_soon(self.query_img, path, inter.SESS, output, ind)
        return output

    def get_urls(self):
        return trio.run(self.collect)

async def validate_all(imgs: List[Optional[str]]) -> np.ndarray:
    image_formats = (
        "image/png", 
        "image/jpeg", 
        "image/jpg", 
        'image/gif',
        'image/svg+xml'
    )

    async def validate(
        img_url: Optional[str], 
        session: asks.Session, 
        valid: np.ndarray,
        ind: int
    ):
        
        err = None
        if img_url is not None:
            try:
                r: Response = await session.head(img_url, timeout=10)
                if "content-type" not in r.headers:
                    # print(f'{img_url} no content')
                    pass
                else:
                    if r.headers["content-type"] not in image_formats:
                        logging.info(
                            "Invalid content type {} at {}".format(
                                    r.headers["content-type"],
                                    img_url
                                )
                            )
                    else:
                        valid[ind] = True
                        logging.info("Successfully got url {}".format(img_url))
            except Exception as e:
                err = Error(
                    url=img_url, type=ErrorType.img.value, 
                    time=datetime.now(), description=str(e.__class__)
                )
        if err is not None:
            inter.DBMi.session.execute(insert(Error), [err.to_dict()])

    output = np.zeros(len(imgs), dtype=bool)
    async with trio.open_nursery() as n:
        for ind, path in enumerate(imgs):
            n.start_soon(validate, path, inter.SESS, output, ind)
    inter.DBMi.session.commit()
    return output
