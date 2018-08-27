# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class VotesSpider(scrapy.Spider):
    name = 'votes'

    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1,
        }
    }   

    start_urls = [
        'http://www.sabor.hr/arhiva-dnevnih-redova-9',
    ]

    skip_urls = [
        'http://www.sabor.hr/prijedlog-polugodisnjeg-izvjestaja-o-izvrsenju0004',
        'http://www.sabor.hr/prijedlog-odluke-o-izboru-tri-suca-ustavnog-suda-r'
    ]

    def parse(self, response):
        #print('parse')
        for i, link in enumerate(list(reversed(response.css("td.liste2 a::attr(href)").extract()))+['sjednica-sabora']):

            # dont parse too much
            #if i == 1:
            #    break

            yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_session)



    def parser_session(self, response):
        #print('parse session')
        rows = response.css("td.webservice > span > table > tr.tocka-red")
        for row in rows:
            if row.css("td.zakljucena"):
                # This row is ended
                link = row.css("a::attr(href)").extract()[0]
                url = 'http://www.sabor.hr/' + link
                if url in self.skip_urls:
                    continue
                yield scrapy.Request(url=url, callback=self.parser_motion, meta={'parent': response.url})



    def parser_motion(self, response):
        #print('parse_motion')
        ballots_link = []
        is_nested = False
        links = response.css('td.ArticleText a')
        for raw_link in links:
            link = raw_link.css('::attr(href)').extract_first()
            if 'lasovanje.aspx' in link:
                href = link.split('\'')
                if len(href) > 1:
                    for link in href:
                        if 'lasovanje.aspx' in link:
                            ballots_link.append(link)
                else:
                    ballots_link.append(href[0])
            elif 'lgs.axd?t' in link:
                #print("nested")
                alt = raw_link.css("::attr(alt)").extract_first()
                if alt:
                    if alt.isupper():
                        is_nested = True
                        url = 'http://www.sabor.hr/' + link
                        if url in self.skip_urls:
                            continue
                        yield scrapy.Request(url=url, callback=self.parser_motion, meta={'parent': response.url})

        if is_nested:
            return

        ballots_link = list(set(ballots_link))

        docs = []
        raw_docs = response.css("td.ArticleLinks")
        for doc in raw_docs:
            docs.append({'url': doc.css("a::attr(href)").extract()[0],
                         'text': doc.css("a span::text").extract()[0]})

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
                'url': response.url,
                'docs': docs,
                'parent': response.meta['parent']}

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
