import requests
from bs4 import BeautifulSoup as sp
from linkpreview import link_preview as lp
from linkpreview import LinkPreview
from typing import Union
from urllib.parse import urlparse

class Scraper:
    def __init__(self, link: str) -> None:
        self.hn_link: str = urlparse(link)._replace(fragment='').geturl()
        self.hn_html: sp = sp(requests.get(self.hn_link).text, 'html.parser')
        self.hn_title: str = ''
        self.content_link: str = ''
        self.preview: Union[None, LinkPreview] = None

        hn_scrape = self.hn_html.find('span', attrs={"class":"titleline"})
        if hn_scrape:
            self.hn_title = list(hn_scrape.children)[0].text # type: ignore
            temp = str(hn_scrape.find('a').get('href')) # type: ignore
            self.content_link = urlparse(temp)._replace(fragment='').geturl()
            self.preview = lp(self.content_link)
            # try:
            #     self.preview = lp(self.content_link)
            # except:
            #     print(f'Failed to generate preview for: {self.content_link}')

    def __str__(self) -> str:
        output= ''
        output += f'hn_link: {self.hn_link}\n'
        output += f'hn_title: {self.hn_title}\n'
        output += f'content_link: {self.content_link}\n'
        return output
        
    def __repr__(self) -> str:
        output= ''
        output += f'hn_link: {self.hn_link}\n'
        output += f'hn_title: {self.hn_title}\n'
        output += f'content_link: {self.content_link}\n'
        return output