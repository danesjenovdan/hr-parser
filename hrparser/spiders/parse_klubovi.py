# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class PeopleClubSpider(scrapy.Spider):
    name = 'klubovi'

    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1
            #'hrparser.pipelines.ImagesPipeline': 2
        }
    }

    start_urls = [
        'https://sabor.hr/hr/zastupnici/klubovi-zastupnika',
        ]

    def parse(self, response):
        for i, link in enumerate(response.css('div.lista-sadrzaja > div.views-row a::attr(href)').extract()):
            link = link.strip()
            yield scrapy.Request(url='https://www.sabor.hr/' + link, callback=self.parser_klub, meta={'page': 0})

    def parser_klub(self, response):
        try:
            pages = int(max(response.css("ul.pager__items a::attr(href)").extract()).split('=')[1])
        except:
            pages = 0

        klub = response.css('.pre-title-second::text').extract_first()
        c_page = response.meta['page']
        containters =  response.css('div.views-element-container')
        for containter in containters:
            role = containter.css('h2.funkcija-naziv::text').extract_first()
            if role:
                role = role.strip()
                print(role)
                rows = containter.css('div.row')
                for row in rows:
                    items = row.css('div div span a')
                    for item in items:
                        person_page = item.css('::attr(href)').extract_first()
                        yield scrapy.Request(url='https://www.sabor.hr/' + person_page, callback=self.parser_person, meta={'role': role, 'klub': klub})
                        image = item.css('.image')
                        info = item.css('.info')
                        url = image.css('img::attr(src)').extract_first()
                        name = info.css('span.ime-prezime::text').extract_first()
                        stranka = info.css('span.akronim::text').extract_first()

                        print(name, url, stranka)
                print()
        if c_page != pages:
            next_page = response.url.split('?')[0] + '?page=' + str(c_page + 1)
            yield scrapy.Request(url=next_page, callback=self.parser_klub, meta={'page': c_page + 1})



    def parser_person(self, response):
        image = response.css('div.image-social div img::attr(src)').extract_first()
        name = response.css('div.view-id-zastupnici span.field-content h2::text').extract_first().strip()
        club_acronym = response.css('div.view-id-zastupnici span.field-content h2 span::text').extract_first().strip()
        zivotopis = response.css('div.zivotopis p::text').extract_first()
        area = response.css('div.view-display-id-izborna_jedinica a::text').extract_first().strip()
        start_date = response.css('div.views-field-field-pocetak-mandata-1 div.field-content::text').extract_first().strip()
        mandates = len(response.css('div.view-display-id-prethodni_mandati div.views-row')) + 1
        try:
            stranka = response.css('div.view-display-id-stranacka_pripadnost a::text').extract_first().strip()
        except:
            stranka = response.css('div.view-display-id-stranacka_pripadnost span::text').extract_first().strip()

        wbs = []
        wbs_div = response.css("div.view-display-id-duznosti>div.item-list li")
        for wb in wbs_div:
            role = wb.css(".views-field-field-funkcija .field-content::text").extract_first().strip()
            wb_1 = wb.css(".views-field-field-naziv-u-genitivu span a::text").extract_first()
            wb_2 = wb.css(".views-field-field-naziv-u-genitivu-1 span a::text").extract_first()
            wb_3 = wb.css(".views-field-field-naziv-u-genitivu-2 span a::text").extract_first()
            date_from_1 = wb.css(".views-field-field-od .field-content::text").extract_first()
            date_from_2 = wb.css(".views-field-field-datum-pocetka-1 .field-content::text").extract_first()

            # find non empty div. Because they have same field in diferent classes.
            try:
                m_wb = [w for w in [wb_1, wb_2, wb_3] if w][0]
            except:
                if 'Sabora' in role:
                    role = role.split(' ')[0]
                    m_wb = 'Sabor'
            try:
                date_from = [w for w in [date_from_1, date_from_2] if w][0]
            except:
                date_from = None

            wbs.append({
                'date_from': date_from.strip() if date_from else None,
                'role': role,
                'commitee': m_wb.strip()
            })

        yield {
            'role': response.meta['role'],
            'image': image,
            'name': name,
            'club': response.meta['klub'],
            'club_acronym': club_acronym,
            'zivotopis': zivotopis,
            'area': area,
            'start_date': start_date,
            'mandates': mandates,
            'stranka': stranka,
            'wbs': wbs
        }
