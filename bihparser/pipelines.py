# -*- coding: utf-8 -*-
from .settings import API_URL, API_AUTH, API_DATE_FORMAT

from bihparser.spiders.people_spider import PeopleSpider
from bihparser.spiders.questions_spider import QuestionsSpider
from bihparser.spiders.act_spider import ActSpider
from bihparser.spiders.club_spider import ClubSpider
from bihparser.spiders.session_spider import SessionSpider

from datetime import datetime

from requests.auth import HTTPBasicAuth
import requests

import scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

from .data_parser.question_parser import QuestionParser
from .data_parser.person_parser import PersonParser
from .data_parser.act_parser import ActParser
from .data_parser.club_parser import ClubParser
from .data_parser.session_parser import SessionParser
from .data_parser.utils import get_vote_key, fix_name, get_person_id

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html travnja

COMMONS_ID = 1
PEOPLE_ID = 51

class BihImagesPipeline(ImagesPipeline):
    members = {}
    def __init__(self, *args, **kwargs):
        super(BihImagesPipeline, self).__init__(*args, **kwargs)
        print('imgs pipeline getMembers')
        mps = getDataFromPagerApiDRF(API_URL + 'persons')
        for mp in mps:
            self.members[mp['name_parser']] = mp['id']

        print(self.members)

    def file_path(self, request, response=None, info=None):
        print("fajl path")
        print(fix_name(request.meta['name']), 'file-path')
        image_guid = str(get_person_id(self.members, fix_name(request.meta['name']))) + '.jpeg'
        print(image_guid)
        #log.msg(image_guid, level=log.DEBUG)
        return image_guid

    def get_media_requests(self, item, info):
        print("get media")
        if 'img' in item.keys():
            print('http://www.sabor.hr/' + item['img'])
            yield scrapy.Request('http://www.sabor.hr/' + item['img'], meta=item)
        else:
            return

    def item_completed(self, results, item, info):
        print("item compelte")
        print(results)
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem("Item contains no images")
        item['image_paths'] = image_paths
        return item


class BihParserPipeline(object):
    value = 0
    commons_id = COMMONS_ID
    people_id = PEOPLE_ID
    others = 2
    local_data = {}
    members = {}
    parties = {}
    links = {}
    areas = {}
    agenda_items = {}
    orgs = {}
    klubovi = {}

    added_session = {}
    added_votes = {}
    added_links = {}

    sessions = {}
    sessions_by_name = {}
    motions = {}
    votes = {}
    votes_dates = {}
    questions = {}
    acts = {}

    sessions_with_speeches = []

    memberships = {}

    mandate_start_time = datetime(day=1, month=12, year=2018)

    def __init__(self):
        print('pipeline getMembers')
        mps = getDataFromPagerApiDRF(API_URL + 'persons')
        for mp in mps:
            self.members[mp['name_parser']] = mp['id']

        print('pipeline parties')
        #print(API_URL + 'organizations/')
        paries = getDataFromPagerApiDRF(API_URL + 'organizations/')
        for pg in paries:
            self.orgs[pg['name_parser']] = pg['id']
            if pg['classification'] == 'party' or pg['classification'] == 'gov' :
                self.parties[pg['name_parser']] = pg['id']

            if pg['classification'] == 'pg':
                self.klubovi[pg['id']] = pg['_name']

        #print(self.parties)

        print('pipeline getVotes')
        votes = getDataFromPagerApiDRF(API_URL + 'votes/')
        for vote in votes:
            self.votes[get_vote_key(vote['name'], vote['start_time'])] = vote['id']
            self.votes_dates[vote['id']] = vote['start_time']

        print('pipeline get districts')
        areas = getDataFromPagerApiDRF(API_URL + 'areas')
        for area in areas:
            self.areas[area['name']] = area['id']

        print('pipeline get sessions')
        sessions = getDataFromPagerApiDRF(API_URL + 'sessions')
        for session in sessions:
            self.sessions[session['gov_id']] = session['id']
            self.sessions_by_name[session['name']] = session['id']
            if requests.get(API_URL + 'speechs?session='+str(session['id'])).json()['results']:
                self.sessions_with_speeches.append(session['id'])

        #print('\n', self.sessions, '\n ')

        print('pipeline get motions')
        motions = getDataFromPagerApiDRF(API_URL + 'motions')
        for motion in motions:
            self.motions[motion['gov_id']] = motion['id']

        """ # i think that this is unnecesery
        print('pipeline get districts')
        links = getDataFromPagerApiDRF(API_URL + 'links')
        for link in links:
            self.links[get_vote_key(link['name'], link['date'])] = link['id']
        """

        print('pipeline get agenda items')
        items = getDataFromPagerApiDRF(API_URL + 'agenda-items')
        for item in items:
            self.agenda_items[get_vote_key(item['name'], item['date'])] = item['id']

        print('pipeline get agenda items')
        items = getDataFromPagerApiDRF(API_URL + 'questions')
        for item in items:
            self.questions[item['signature']] = item['id']

        print('pipeline get acts items')
        items = getDataFromPagerApiDRF(API_URL + 'law')
        for item in items:
            self.acts[item['uid']] = {'id': item['id'], 'ended': item['procedure_ended']}

        print('pipeline get memberships')
        items = {}
        for mem in getDataFromPagerApiDRF(API_URL + 'memberships/?role=voter'):
            if str(mem['person']) in items.keys():
                items[str(mem['person'])].append(mem)
            else:
                items[str(mem['person'])] = [mem]

        self.memberships = items
       #print('Memberships', self.memberships)

        print('PIPELINE is READY')

    def process_item(self, item, spider):
        #return item
        if type(spider) == PeopleSpider:
            PersonParser(item, self)
        elif type(spider) == ClubSpider:
            print("club_spider")
            ClubParser(item, self)
        elif type(spider) == QuestionsSpider:
            QuestionParser(item, self)
        elif type(spider) == ActSpider:
            ActParser(item, self)
        elif type(spider) == SessionSpider:
            SessionParser(item, self)
        else:

            return item


def getDataFromPagerApiDRF(url):
    print(url)
    data = []
    end = False
    page = 1
    if '?' in url:
        url = url+'&limit=300'
    else:
        url = url+'?limit=300'
    while url:
        response = requests.get(url, auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])).json()
        #print(response)
        data += response['results']
        url = response['next']
    return data
