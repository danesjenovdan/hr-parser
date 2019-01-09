# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class PeopleSpider(scrapy.Spider):
    name = 'people'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
            #'bihparser.pipelines.BihImagesPipeline': 2
        }
    }

    start_urls = [
        'http://parlament.ba/representative/list',
        ]
    base_url = 'http://parlament.ba'

    def parse(self, response):
        for i, mp in enumerate(response.css('.table-reps tbody tr')):
            link = mp.css('td')[1].css('a::attr(href)').extract_first()
            print(link)
            #if link[0] == '#' or link[0] == '/':
            #    continue

            yield scrapy.Request(url=self.base_url + link, callback=self.parser_person)
        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)



    def parser_person(self, response):
        full_name = ' '.join(list(reversed(list(map(str.strip, response.css('.article h1::text').extract_first().split(',')))))).strip()
        try:
            img_url = self.base_url + response.css('.contact-image img::attr(src)').extract_first()
        except:
            img_url = None

        data = parser_other_data(response)

        data.update(parse_body(response))

        data.update({'type': 'mp','name': full_name, 'img': img_url})
        print('yeald'+full_name)
        yield data



def parser_other_data(table):
    data = {}
    value_loc = ["td::text", "td a::text"]
    for i in table.css(".table-verthead tr"):
        key = i.css("th::text").extract_first()
        tmp = {}
        if key == 'Stranka':
            tmp = parse_party(i)
        elif key == 'Izborna jedinica / Entitet':
            tmp = parse_area(i)
        elif key == 'E-mail':
            tmp = parse_email(i)
        data.update(tmp)
    return data

def parse_party(row):
    return {'party': row.css('td span::text').extract_first()}

def parse_area(row):
    return {'area': row.css('td span a::text').extract_first()}

def parse_email(row):
    try:
        return {'area': row.css('td span a::attr(href)').extract_first().split(':')[1]}
    except:
        return {}

def parse_body(response):
    data = {'wbs': {'comission': []}}
    body = response.css('.body')
    for col in body.css('.collapsible'):
        key = col.css('.btn-collapshead::text').extract_first().strip()
        if key == 'PRETHODNI MANDATI':
            pass
        if key == 'KOMISIJE':
            for comitee in col.css('.list-arrows li'):
                data['wbs']['comission'].append(comitee.css('a::text').extract_first())
    return data
