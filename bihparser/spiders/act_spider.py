# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class ActSpider(scrapy.Spider):
    name = 'acts'
    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'http://parlament.ba/oLaw/GetOLawsBySubmissionDate?SearchTerm=&MandateId=6&DateFrom=&DateTo=',
        ]

    map_of_keys = {
        'Broj i datum Prijedloga zakona u PDPSBiH': 'epa_plus_pdps',
        'Status u PDPSBiH': 'status',
        'Nadležna komisija': 'mdt',
        'Status i faza postupka': 'faza',
        'Broj i datum Prijedloga zakona': 'epa',
        'Konačni status u PSBiH': 'status',
        'Red. br. i datum sjednice - tačka dnevnog reda	': 'date',
    }

    def parse(self, response):
        for link in response.css('.list-articles li a::attr(href)').extract():
            yield scrapy.Request(url=self.base_url + link, callback=self.legislation_parser)

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def legislation_parser(self, response):  
        title = response.css(".article header h1::text").extract_first()

        uid = response.url.split('lawId=')[1].split('&')[0]



        yield {'title': title,
               'mdt': mdt, #
               'ref_ses': ref_ses,
               'date': date, #
               'signature': uid, #
               #'voting': voting,
               #'ballots': ballots,
               #'result': result,
               #'pub_title': pub_title,
               #'pdf': pdf,
               'status': status,
               'epa': epa, #
               'uid': uid} #
        
        
