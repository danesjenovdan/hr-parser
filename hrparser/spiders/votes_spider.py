# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class VotesSpider(scrapy.Spider):
    name = 'votes'

    custom_settings = {
        'ITEM_PIPELINES': {
            'ukparser.pipelines.HrparserPipeline': 1
        }
    }   

    start_urls = [
        'http://www.sabor.hr/arhiva-dnevnih-redova-9',
        ]

    def parse(self, response):
        print('parse')
        for i, link in enumerate(list(reversed(response.css("td.liste2 a::attr(href)").extract()))+['sjednica-sabora']):

            # dont parse too much
            if i == 10:
                break

            yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_session)



    def parser_session(self, response):
        print('parse session')
        rows = response.css("td.webservice > span > table > tr.tocka-red")
        for row in rows:
            if row.css("td.zakljucena"):
                # This row is ended
                link = row.css("a::attr(href)").extract()[0]
                yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_motion)



    def parser_motion(self, response):
        print('parse_motion')
        ballots_link = []
        links = response.css('td.ArticleText a::attr(href)').extract()
        for link in links:
            if 'lasovanje.aspx' in link:
                href = link.split('\'')
                if len(href) > 1:
                    for link in href:
                        if 'lasovanje.aspx' in link:
                            ballots_link.append(link)
                else:
                    ballots_link.append(href[0])

        ballots_link = list(set(ballots_link))

        #TODO

        title = response.css("td.ArticleHeading span::text").extract()
        if not title:
            title = response.css("td.ArticleHeading span p::text").extract()
        title = '\n'.join(title)
        result_and_data = response.css("td.ArticleText span::text").extract()

        links = []
        for i in response.css("td.ArticleLinks a"):
            links.append({'url': i.css("::attr(href)").extract()[0],
                          'name': i.css("::text").extract()[0]})

        data = {'title': title,
                'results_data': result_and_data,
                'type': 'vote',
                'url': response.url}

        if ballots_link:
            for link in ballots_link:
                yield scrapy.Request(url=link, meta={'data': data}, callback=self.parse_ballots)
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
        data.update({'title': title,
                     'time': time,
                     'results': result,
                     'ballots': ballots,
                     'url': response.url,
                     'type': 'vote_ballots'})
        yield data
