# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class AmandmanSpider(scrapy.Spider):
    name = 'amandman'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }   

    start_urls = [
        'http://www.sabor.hr/arhiva-dnevnih-redova-9',
        ]

    def parse(self, response):
        print('parse')
        for i, link in enumerate(list(reversed(response.css("td.liste2 a::attr(href)").extract()))+['sjednica-sabora']):

            # dont parse too much
            if i == 10:
                break

            yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_session)



    def parser_session(self, response):
        print('parse session')
        rows = response.css("td.webservice > span > table > tr.tocka-red")
        for row in rows:
            if row.css("td.zakljucena"):
                # This row is ended
                link = row.css("a::attr(href)").extract()[0]
                yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_motion)



    def parser_motion(self, response):
        print('parse_motion')
        texts = response.css("td.ArticleLinks>a>span::text").extract()

        title = response.css("td.ArticleHeading span::text").extract()
        if not title:
            title = response.css("td.ArticleHeading span p::text").extract()
        title = '\n'.join(title)

        yield {'title': title,
               'texts': [i for i in texts if 'AMANDMAN' in i.split("_")]}
