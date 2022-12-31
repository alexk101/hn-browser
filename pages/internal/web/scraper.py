from bs4 import BeautifulSoup as sp
from typing import List, Dict, Tuple
import aiohttp
import asyncio
import json
from .schema import *
from . import interfaces as inter


class MultiScraper:
    def __init__(self, links: Dict[datetime, str], silent: bool=True, verbose: bool=False) -> None:
        self.links: Dict[datetime, str] = links
        self.silent: bool= silent

        temp = asyncio.run(self.get_all())
        self.children: List[Dict] = []
        for record in temp:
            if 'kids' in record.keys():
                self.children += [{'id': record['id'], 'child': child} for child in record.pop('kids')]

        self.pages: List[Dict] = temp
        self.verbose = verbose

        if self.verbose and not self.silent:
            print(f'Pages:')
            for page in self.pages:
                print(page)

            print(f'Children:')
            for child in self.children:
                print(child)

        self.save()


    async def get(self, record: Tuple[datetime, str], session: aiohttp.ClientSession):
        output = python_hn_post.copy()
        time, url = record
        try:
            async with session.get(url=url) as response:
                resp = await response.read()
                resp = resp.decode('utf-8')
                if 'Sorry' not in resp:
                    if not self.silent:
                        print("Successfully got url {} with resp of length {}.".format(url, len(resp)))
                    output.update(json.loads(resp))
                    output['time'] = datetime.fromtimestamp(output['time'])
                    output['date_added'] = time
                    if not self.silent and self.verbose:
                        print(output)
                else:
                    print('Exceeded rate limit.')

        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))

        return output


    async def get_all(self) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            ret = await asyncio.gather(*[self.get(record, session) for record in self.links.items()])
        if not self.silent:
            print(f"Finalized all. Got {len(ret)} outputs.")
        return ret


    def save(self):
        if len(self.pages):
            conn = inter.DBMi.engine.connect()
            conn.execute(inter.DBMi.hn.insert(self.pages))
            conn.execute(inter.DBMi.hn_child.insert(self.children))
            print(f'Updated DB')
            conn.close()
