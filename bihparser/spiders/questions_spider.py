# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class QuestionsSpider(scrapy.Spider):
    name = 'questions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'http://parlament.ba/oQuestion/GetORQuestions?RDId=&MandateId=4&DateFrom=&DateTo=',
        ]
    base_url = 'http://parlament.ba'

    data_map = {
        'Poslanik': 'name',
        'Broj i datum dokumenta': 'date',
        'Pitanje postavljeno u pisanoj formi - subjekt i datum': 'asigned',
        'Tekst pitanja (identičan usvojenom zapisniku)': 'text',
    }

    def parse(self, response):
        for link in response.css('.list-articles li a::attr(href)').extract():
            yield scrapy.Request(url=self.base_url + link, callback=self.question_parser)

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def question_parser(self, response):
        table = response.css('.table-minus .table-docs')[0]
        json_data = {'ref': response.url.split('contentId=')[1].split('&')[0],
                     'links': [],
                     'url': response.url}
        try:
            links = response.css('.table-minus .table-docs')[1]
            for line in links.css('tr'):
                head = line.css('th::text').extract_first()
                data = line.css('td a::attr(href)').extract_first()
                json_data['links'].append({'name': head, 'url': data})
        except:
            pass
        for line in table.css('tr'):
            head = line.css('th::text').extract_first()
            data = line.css('td::text').extract_first()
            try:
                json_data[self.data_map[head]] = data
            except:
                print('Define KEY: ', head)
        print(json_data)
        yield json_data
