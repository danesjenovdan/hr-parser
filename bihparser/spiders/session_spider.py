# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class SessionSpider(scrapy.Spider):
    name = 'sessions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'http://parlament.ba/session/Read?ConvernerId=1',
        'http://parlament.ba/session/Read?ConvernerId=2',
        ]
    base_url = 'http://parlament.ba'
    def parse(self, response):
        session_of = response.css(".article header h1::text").extract_first()
        for link in response.css('.list-articles li a::attr(href)').extract():
            yield scrapy.Request(url=self.base_url + link, callback=self.session_parser, meta={'session_of': session_of})

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def session_parser(self, response):
        session_gov_id = response.url.split('id=')[1].split('&')[0]
        session_name = response.css('.article header h1::text').extract_first()
        start_date = ''.join([i.strip() for i in response.css('.schedule::text').extract()])
        start_time = response.css('.time::text').extract_first()

        print(session_name)

        data = {
            'session_of': response.meta['session_of'],
            'gov_id': session_gov_id,
            'name': session_name,
            'start_date': start_date,
            'start_time': start_time,
        }

        for li in response.css('.session-box .list-unstyled li a'):
            key = li.css('a::text').extract_first()
            link = li.css('a::attr(href)').extract_first()
            print('link', link)
            if key == 'Rezultati glasanja' and link:
                # parse votes
                file_name = str(session_gov_id) + '-votes.pdf'
                data['votes'] = file_name
                yield scrapy.Request(
                        url=self.base_url + link,
                        callback=self.save_pdf,
                        meta={'name': file_name}
                    )
            elif key == 'Stenogram' and link:
                # parse speeches
                file_name = str(session_gov_id) + '-speeches.pdf'
                data['speeches'] = file_name
                yield scrapy.Request(
                        url=self.base_url + link,
                        callback=self.save_pdf,
                        meta={'name': file_name}
                    )
        yield data

    def save_pdf(self, response):
        file_name = response.meta['name']
        self.logger.info('Saving PDF %s', file_name)
        with open('files/'+file_name, 'wb') as f:
            f.write(response.body)