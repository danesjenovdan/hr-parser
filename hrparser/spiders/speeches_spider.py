# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class SpeechSpider(scrapy.Spider):
    name = 'speeches'

    start_urls = [
        'http://edoc.sabor.hr/Fonogrami.aspx',
        ]

    def parse(self, response):       
        num_pages = int(response.css("table.OptionsTable td span::text").extract()[2].strip().split(" ")[1])

        # limiter
        #num_pages = 10

        for i in range(1, num_pages + 1):
            form_data = self.validate(response)
            
            # This is how edoc aspx backend works. callback param need to know how much digits has number
            special_aspx = len(str(i-1)) + 12
            callback_param = 'c0:KV|2;[];GB|' + str(special_aspx) + ';8|GOTOPAGE' + str(len(str(i-1))) + '|' + str(i-1) + ';'
            
            form_data.update({
                'ctl00$ContentPlaceHolder$gvFonogrami$PagerBarB$GotoBox': str(i),
                '__CALLBACKID': 'ctl00$ContentPlaceHolder$gvFonogrami',
                '__CALLBACKPARAM': callback_param,
                #'ctl00$ContentPlaceHolder$navFilter': '{&quot;selectedItemIndexPath&quot;:&quot;&quot;,&quot;groupsExpanding&quot;:&quot;0;0;0&quot;}',
                #'ctl00$ContentPlaceHolder$rbtnTraziPo': '0',
            })
            yield scrapy.FormRequest(url='http://edoc.sabor.hr/Fonogrami.aspx',
                                     formdata=form_data,
                                     meta={'page': str(i), 'calback': callback_param},
                                     callback=self.parse_agenda,
                                     method='POST')


    def validate(self, response):
        viewstate = response.css("#__VIEWSTATE::attr(value)").extract()[0]
        viewstategen = response.css("#__VIEWSTATEGENERATOR::attr(value)").extract()[0]
        eventvalidation = response.css("#__EVENTVALIDATION::attr(value)").extract()[0]
        return {'__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategen,
            }


    def parse_agenda(self, response):
        # print("AGENDA")
        items = response.css("#ctl00_ContentPlaceHolder_gvFonogrami_DXMainTable>tr")[1:]
        #logging.error(items)
        if items == 0:
            logging.error("FAIL " + response.meta["page"] + " " + response.meta["calback"])
        else:
            logging.error("OK " + response.meta["page"] + " " + response.meta["calback"])
        for i in items:
            row = i.css("td>a::attr(href)").extract()
            url = 'http://edoc.sabor.hr' + row[4][2:-2]
            #print(url)
            yield scrapy.Request(url=url, callback=self.parse_speeches)


    def parse_speeches(self, response):
        session_ref = response.css("#ctl00_ContentPlaceHolder_lblSazivSjednicaDatum::text").extract()
        content_list = response.css(".contentList li::text").extract()
        date_of_session = response.css(".dateString::text").extract()[0].strip()
        order = 0
        try:
            agenda_id = response.url.split('=')[1]
        except:
            agenda_id = 0
        for i in response.css(".singleContentContainer"):
            speaker = i.css(".speaker h2::text").extract()
            if not speaker:
                continue
            content = '\n'.join(map(str.strip, i.css(".singleContent dd::text").extract()))
            order += 1
            yield {'order': order,
                   'date': date_of_session,
                   'content_list': content_list,
                   'session_ref': session_ref,
                   'speaker': speaker,
                   'content': content,
                   'agenda_id': agenda_id}

        