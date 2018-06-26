# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class PeopleSpider(scrapy.Spider):
    name = 'people'

    custom_settings = {
        'ITEM_PIPELINES': {
            'hrparser.pipelines.HrparserPipeline': 1
            #'hrparser.pipelines.ImagesPipeline': 2
        }
    }

    start_urls = [
        'http://www.sabor.hr/zastupnici-9',
        ]

    def parse(self, response):
        for i, mp in enumerate(response.css('table table table table table table a::attr(href)')):

            link = mp.extract()
            if link[0] == '#' or link[0] == '/':
                continue

            # dont parse too much
            if i == 3:
                break

            yield scrapy.Request(url='http://www.sabor.hr/' + link, callback=self.parser_person)



    def parser_person(self, response):
        main_rows = response.css("table.regionMainTable > tr")

        full_name = main_rows[0].css("table span::text")[0].extract()
        try:
            img_url = main_rows[0].css("img::attr(src)")[0].extract()
        except:
            img_url = None

        try:
            data =  main_rows[0].css("span p::text").extract()[2]
        except:
            data =  main_rows[0].css("span::text").extract()[2]
        birth_date, education = parse_birth_and_educ(data)

        if main_rows[1].css("table"):
            data = parser_other_data(main_rows[1])
        else:
            data = parser_other_data(main_rows[2])

        data.update({'type': 'mp','name': full_name, 'img': img_url, 'birth_date': birth_date, 'education': education})
        yield data



def parse_birth_and_educ(data):
    splited = data.split('.')
    birth_date = ('.'.join(splited[0:2])).split(' ')[2:5]
    education = splited[3:-1]
    return birth_date, education

def parser_other_data(table):
    data = {}
    value_loc = ["td::text", "td a::text"]
    for i in table.css("table span table"):
        key = i.css("td b::text").extract()[0].strip().replace(':', '')
        if key == 'Stranačka pripadnost':
            tmp = parse_party(i)
        elif key == 'Klub zastupnika':
            tmp = parse_deputy_club(i)
        elif key == 'Početak obnašanja zastupničkog mandata':
            tmp = parse_start_time(i)
        elif key == 'Dužnosti u Saboru':
            tmp = parse_wb_memberships(i)
        elif key == 'Izborna jedinica':
            tmp = parse_area(i)
        elif key == 'Prethodni mandati':
            tmp = parse_prev_mandates(i)
        data.update(tmp)
    return data

def parse_party(row):
    return {'party': row.css('td::text').extract()[0]}

def parse_deputy_club(row):
    return {'deputy': row.css('td a::text').extract()[0]}

def parse_start_time(row):
    return {'start_time': row.css('td::text').extract()[0]}

def parse_wb_memberships(row):
    av_roles = ['predsjednica', 'članica', 'predsjednik', 'član', 'potpredsjednik', 'potpredsjednica', 'zamjenica člana', 'zamjenik člana']

    roles = row.css('td::text').extract()
    wbs = row.css('td a::text').extract()

    i = 0
    j = 0
    out = []
    while i<len(roles):
        role = roles[i].replace('\xa0', ' ').replace('-', '').strip()
        if len(role.split(' ')) > 2:
            # cut role to role: wb
            found = False
            for c_role in av_roles:
                if role.startswith(c_role):
                    new_role = c_role
                    org = role[len(new_role):]
                    out.append({'org': org,  'role': new_role})
                    i += 1
                    found = True
                    break
            if not found:
                i += 1
                  
        else:
            out.append({'org': wbs[j].strip(),  'role': role})
            i += 1
            j += 1

    return {'wbs': out}

def parse_area(row):
    return {'area': row.css('td a::text').extract()[0]}

def parse_prev_mandates(row):
    return {'num_of_prev_mandates': len(row.css('td a::text').extract())}
    

# Prethodni mandati TODO
