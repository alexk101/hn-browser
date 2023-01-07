from bs4 import BeautifulSoup as sp
from typing import List, Dict, Tuple, Union, TypeAlias
import aiohttp
import asyncio
import json
from .schema import *
from . import interfaces as inter
from urllib.parse import urljoin
from datetime import datetime

AsyncAPIData: TypeAlias = Tuple[Union[Post, None], Union[List[Child], None]]


class MultiScraper:
    def __init__(
        self, links: Dict[datetime, str], silent: bool = False, verbose: bool = False
    ) -> None:
        self.links: Dict[datetime, str] = links
        self.silent: bool = silent
        self.verbose = verbose

        temp = asyncio.run(self.get_all())
        self.children: List[Child] = []
        self.posts: List[Post] = []
        for post, child in temp:
            if post is not None:
                self.posts.append(post)
            if child is not None:
                self.children += child

        if self.verbose and (not self.silent):
            print(f"Pages:")
            for page in self.posts:
                print(page)

            print(f"Children:")
            for child in self.children:
                print(child)

        self.save()

    async def get_image(self, url: str, session: aiohttp.ClientSession):
        try:
            async with session.get(url=url) as response:
                resp = await response.read()
                resp = resp.decode("utf-8")
                if len(resp):
                    if not self.silent:
                        print(
                            "Successfully got url {} with resp of length {}.".format(
                                url, len(resp)
                            )
                        )
                    soup = sp(resp, "html.parser")
                    images = soup.findAll("img")
                    if len(images):
                        img: str = images[0].attrs["src"]
                        if not img.startswith("data:image"):
                            img = urljoin(url, img)
                        return img
                    else:
                        return ""
                else:
                    print(f"Unable to get url {url}")
                    return ""
        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))
            return ""

    async def get_api_data(
        self, record: Tuple[datetime, str], session: aiohttp.ClientSession
    ) -> AsyncAPIData:
        time, url = record
        post = None
        children = None
        try:
            async with session.get(url=url) as response:
                resp = await response.read()
                resp = resp.decode("utf-8")
                if len(resp) and "Sorry" not in resp:
                    if not self.silent:
                        print(
                            "Successfully got url {} with resp of length {}.".format(
                                url, len(resp)
                            )
                        )
                    resp_dec: Dict = json.loads(resp)

                    # Response wrangling
                    resp_dec["author"] = resp_dec.pop("by")
                    resp_dec["time"] = datetime.fromtimestamp(resp_dec.pop("time"))
                    resp_dec["date_added"] = time

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
                    print(f"Unable to get url {url}")

        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))

        return post, children

    async def get_all(self) -> List[AsyncAPIData]:

        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"Querying HN API for data...")
            ret: List[AsyncAPIData] = await asyncio.gather(
                *[self.get_api_data(record, session) for record in self.links.items()]
            )
            print(f"Scraping links for images...")
            tasks = []
            for record in ret:
                if record[0] is not None:
                    tasks.append(self.get_image(record[0].url, session))
            images = await asyncio.gather(*tasks)
            for record, image in zip(ret, images):
                if record[0] is not None:
                    record[0].img = image
        if not self.silent:
            print(f"Finalized all. Got {len(ret)} new bookmarks.")
        return ret

    def save(self):
        if len(self.posts):
            print(f"Updating DB")

            # Add new bookmarks
            inter.DBMi.session.add_all(self.posts)

            # Add new children
            inter.DBMi.session.add_all(self.children)

            # Commit changes
            inter.DBMi.session.commit()

            print(f"Updated DB")
