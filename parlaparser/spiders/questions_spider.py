# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime


class QuestionsSpider(scrapy.Spider):
    name = 'questions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'parlaparser.pipelines.ParlaparserPipeline': 1
        }
    }

    start_urls = [
        'https://fotogalerija.dz-rs.si/datoteke/opendata/VPP.XML',
    ]

    def parse(self, response):
        for question in response.css('VPRASANJE'):
            card = question.css('KARTICA_VPRASANJA')
            data = {
                'date': card.css('KARTICA_DATUM::text').extract_first(),
                'title': card.css('KARTICA_NASLOV::text').extract_first(),
                'authors': card.css('KARTICA_VLAGATELJ::text').extract(),
                'parties': card.css('KARTICA_POSLANSKA_SKUPINA::text').extract(),
                'asigned': card.css('KARTICA_NASLOVLJENEC::text').extract_first(),
                'signature': card.css('UNID::text').extract_first(),
            }
            doc = question.css('PODDOKUMENTI')
            data['docs'] = []
            if doc:
                unids = doc.css('UNID::text').extract()
                for unid in unids:
                    docs_card = response.xpath("//DOKUMENT/KARTICA_DOKUMENTA/*[contains(text(), '" +unid+ "')]/../..")
                    if docs_card:
                        data['docs'].append({
                            'date': docs_card[0].css('KARTICA_DOKUMENTA KARTICA_DATUM::text').extract_first(),
                            'url': docs_card[0].css('PRIPONKA PRIPONKA_KLIC::text').extract_first(),
                            'title': docs_card[0].css('KARTICA_DOKUMENTA KARTICA_NASLOV::text').extract_first()
                        })

            yield data
