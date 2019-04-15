# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime
import json
import requests

class VotesSpider(scrapy.Spider):
    name = 'votes'

    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1,
        }
    }   
    BASE_URL = 'http://www.sabor.hr'
    start_urls = [
        'http://www.sabor.hr/hr/sjednice/pregled-dnevnih-redova',
    ]
    THIS_SAZIV_ID = 170

    skip_urls = [
        'http://www.sabor.hr/prijedlog-polugodisnjeg-izvjestaja-o-izvrsenju0004',
        'http://www.sabor.hr/prijedlog-odluke-o-izboru-tri-suca-ustavnog-suda-r'
    ]

    def parse(self, response):
        data = {
            'view_name': 'sabor_data',
            'view_display_id': 'dnevni_redovi',
            'field_saziv_target_id': '170',
        }
        print(data)
        url = 'https://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax'
        for select in response.css('[name="plenarna_id"] option')[:2]:
            value=select.css("::attr(value)").extract_first()
            if value:
                print('-'*100)
                print(select.css('::text').extract_first(), value)
                print('-'*100)
                data['plenarna_id'] = str(value)
                yield scrapy.FormRequest(url, callback=self.parser_session, method='POST', formdata=data)


    def parser_session(self, response):
        j_data = json.loads(response.css('textarea::text').extract_first())
        my_response = scrapy.selector.Selector(text=j_data[4]['data'].strip())
        session_name = my_response.css('.group h2::text').extract_first()
        for line in my_response.css(".content li"):
            if line.css('.dnevni-red-stavka::attr(data-status)').extract_first()=='8': # if voteing is ended
                url = line.css('a::attr(href)').extract_first()
                print(url)
                yield scrapy.Request(url=self.BASE_URL + url, callback=self.parser_motion, meta={'parent': response.url, 'session_name': session_name})


    def parser_motion(self, response):
        child_motion_urls = response.css('.popis-sadrzaja .item-list li a::attr(href)').extract()
        for child_motion_url in child_motion_urls:
            yield scrapy.Request(url=self.BASE_URL + child_motion_url, callback=self.parser_motion, meta=response.meta)
        if child_motion_urls:
            return
        title = response.css(".views-row h1::text").extract_first()
        result_and_data = response.css(".field-content p *::text").extract()
        vote_date = response.css(".views-field-field-vrijeme-izglasavanja .field-content::text").extract_first()
        tid = response.url.split('tid=')[1]

        ballots_link = []
        motion_data = None
        # if is link Rezultati glasovanja than call ajax for ballots url
        try:
            motion_data = requests.get('http://sabor.hr/hr/videosnimka-rasprave/'+tid+'/', verify=False).json()
        except:
            pass
        if motion_data and 'glasovanje_link' in motion_data.keys() and motion_data['glasovanje_link']:
            tilte = motion_data['naziv']
            gov_id = motion_data['glasovanje_id']
            ballots_link = [motion_data['glasovanje_link']]
        else:
            ballots_link = response.css('.views-field-field-status-tekstualni a::attr(href)').extract()

        docs = []
        raw_docs = response.css(".view-display-id-vezane_informacije .field-content")
        for doc in raw_docs:
            docs.append({'url': doc.css("a::attr(href)").extract()[0],
                         'text': doc.css("a::text").extract()[0]})

        data = {'title': title,
                'results_data': result_and_data,
                'type': 'vote',
                'date': vote_date,
                'url': response.url,
                'docs': docs,
                'parent': response.meta['parent'],
                'session_name': response.meta['session_name']}

        if ballots_link:
            for i, link in enumerate(ballots_link):
                data['parent'] = response.url
                yield scrapy.Request(url=link, meta={'data': data, 'c_item': i, 'm_items': len(ballots_link)}, callback=self.parse_ballots)
        else:
            yield data

    def parse_ballots(self, response):
        title = response.css("span#LNazivTocke::text").extract()[0]
        time = response.css("span#LDateAndTime::text").extract()[0]
        result = response.css("span#LRezultat::text").extract()[0]
        voters = response.css("div#Panel1 > table > tr")[2:]

        ballots = []
        for vote in voters:
            name = vote.css("td::text")[0].extract()
            option = vote.css("td::text")[1].extract()
            ballots.append({'voter': name, 'option': option})
        data = response.meta['data']
        if title[-1] == ';':
            title = title[:-1]
        data.update({'title': title,
                     'time': time,
                     'results': result,
                     'ballots': ballots,
                     'url': response.url,
                     'type': 'vote_ballots',
                     'c_item': response.meta['c_item'],
                     'm_items': response.meta['m_items']})
        yield data
