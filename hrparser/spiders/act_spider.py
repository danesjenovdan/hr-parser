# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class ActSpider(scrapy.Spider):
    name = 'acts'
    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1
        }
    }

    start_urls = [
        'http://edoc.sabor.hr/Akti.aspx',
        ]

    def parse(self, response):       
        num_pages = int(response.css("table.OptionsTable td span::text").extract()[2].strip().split(" ")[1])

        # limiter
        #num_pages = 10

        for i in range(1, num_pages + 1):
            print("PAGE: ", i)
            form_data = self.validate(response)
            
            # This is how edoc aspx backend works. callback param need to know how much digits has number
            special_aspx = len(str(i-1)) + 12
            callback_param = 'c0:KV|101;["2022639","2022640","2022641","2022642","2022643","2022644","2022645","2022635","2022632","2022630"];GB|' + str(special_aspx) + ';8|GOTOPAGE' + str(len(str(i-1))) + '|' + str(i-1) + ';'
            
            form_data.update({
                'ctl00$ContentPlaceHolder$gvAkti$PagerBarB$GotoBox': str(i),
                '__CALLBACKID': 'ctl00$ContentPlaceHolder$gvAkti',
                '__CALLBACKPARAM': callback_param,
            })
            yield scrapy.FormRequest(url='http://edoc.sabor.hr/Akti.aspx',
                                     formdata=form_data,
                                     meta={'page': str(i), 'calback': callback_param},
                                     callback=self.parse_list,
                                     method='POST')


    def validate(self, response):
        viewstate = response.css("#__VIEWSTATE::attr(value)").extract()[0]
        viewstategen = response.css("#__VIEWSTATEGENERATOR::attr(value)").extract()[0]
        eventvalidation = response.css("#__EVENTVALIDATION::attr(value)").extract()[0]
        return {'__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategen,
            }




    def parse_list(self, response):
        # print("AGENDA")
        items = response.css("#ctl00_ContentPlaceHolder_gvAkti_DXMainTable>tr")[1:]
        #logging.error(items)
        if len(items) == 0:
            logging.error("FAIL " + response.meta["page"] + " " + response.meta["calback"])
        for i in items:
            row = i.css("td>a::attr(href)").extract()
            url = 'http://edoc.sabor.hr/' + row[4][2:-2]
            #print(url)
            yield scrapy.Request(url=url, callback=self.parse_acts)


    def parse_acts(self, response):
        title = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lnkNazivAktaUProceduri *::text").extract()
        mdt = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblPredlagatelj *::text").extract()
        ref_ses = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lnkSazivSjednica *::text").extract()
        dates = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblRasprava *::text").extract()
        date_vote = response.css(".datumGlasovanja *::text").extract()
        signature = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblSignatura *::text").extract()

        agenda_no = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblTockaDnevnogReda *::text").extract()
        voting = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblNacinIzglasavanja *::text").extract()
        ballots = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblZaProtivSuzdrano *::text").extract()
        result = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblZaProtivSuzdrano *::text").extract()

        pub_title = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlObjava1_ctl01_lblNazivObjavljenogAkta *::text").extract()

        pdf = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_lnk_PohraniPdf::attr(href)").extract()

        status = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje0_ctl01_lblStatus *::text").extract()

        yield {'title': title,
               'mdt': mdt,
               'ref_ses': ref_ses,
               'dates': dates,
               'date_vote': date_vote,
               'signature': signature,
               'agenda_no': agenda_no,
               'voting': voting,
               'ballots': ballots,
               'result': result,
               'pub_title': pub_title,
               'pdf': pdf,
               'status': status}
        
        
