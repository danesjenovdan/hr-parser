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
            reading = (''.join(i.css("td")[4].css("::text").extract())).strip(' \\t\\n\\r')
            url = 'http://edoc.sabor.hr/' + row[4][2:-2]
            #print(url)
            yield scrapy.Request(url=url, callback=self.parse_acts, meta={'reading': reading})


    def parse_acts(self, response):
        reading = response.meta['reading'].strip()
        tab = '0'
        if reading == '2.':
            tab = '1'
        tab_id = "#ctl00_ContentPlaceHolder_ctrlAktView_pnlCitanje" + tab +"_ctl01"

        if reading:
            for content_tab in response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlButtons span"):
                text = content_tab.css("::text").extract_first().strip()
                if reading + ' čitanje' == text:
                    tab_id = "#ctl00_ContentPlaceHolder_ctrlAktView_" + content_tab.css("::attr(name)").extract_first() + "_ctl01"
                    break



        #print(response.meta, tab_id)

        title = response.css(tab_id + "_lnkNazivAktaUProceduri *::text").extract()
        mdt = response.css(tab_id + "_lblPredlagatelj *::text").extract()
        ref_ses = response.css(tab_id + "_lnkSazivSjednica *::text").extract()
        dates = response.css(tab_id + "_lblRasprava *::text").extract()
        date_vote = response.css(tab_id + "_lblDatum *::text").extract()
        signature = response.css(tab_id + "_lblSignatura *::text").extract()

        agenda_no = response.css(tab_id + "_lblTockaDnevnogReda *::text").extract()
        voting = response.css(tab_id + "_lblNacinIzglasavanja *::text").extract()
        ballots = response.css(tab_id + "_lblZaProtivSuzdrano *::text").extract()
        result = response.css(tab_id + "_lblZaProtivSuzdrano *::text").extract()

        #text if is poveučen
        remark = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlNapomena1_ctl01_lblNapomena::text").extract()

        pub_title = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_pnlObjava1_ctl01_lblNazivObjavljenogAkta *::text").extract()

        pdf = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_lnk_PohraniPdf::attr(href)").extract()

        status = response.css(tab_id + "_lblStatus *::text").extract()

        epa = response.css("#ctl00_ContentPlaceHolder_ctrlAktView_glava_lblBrojPrijedloga::text").extract()
        uid = response.url.split("id=")[1]

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
               'status': status,
               'epa': epa,
               'uid': uid,
               'remark': remark}
