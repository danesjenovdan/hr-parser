# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class PeopleSpider(scrapy.Spider):
    name = 'klubovi'

    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1
            #'hrparser.pipelines.ImagesPipeline': 2
        }
    }

    start_urls = [
        'http://www.sabor.hr/klubovi-9',
        ]

    def parse(self, response):
        for i, mp in enumerate(response.css('table table table table.regionMainTable table table a::attr(href)')):

            link = mp.extract()
            if link[0] == '#' or link[0] == '/':
                continue

            yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_klub)



    def parser_klub(self, response):
        content = response.css(".regionMainTable")

        data = {'name': content.css(".Caption span::text").extract_first()}

        role_groups = content.css("table .liste2 table .liste2")
        data['groups'] = []
        for group in role_groups:
            role = group.css("b::text").extract_first().strip()
            items = group.css("a::text").extract()
            data['groups'].append({'role': role, 'members': items})

        yield data
