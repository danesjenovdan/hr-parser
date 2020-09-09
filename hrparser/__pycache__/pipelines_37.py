# uncompyle6 version 3.7.3
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.8.2 (default, Jul 16 2020, 14:00:26) 
# [GCC 9.3.0]
# Embedded file name: /home/tomaz/dev/DJND/hrparser/hrparser/pipelines.py
# Compiled at: 2020-03-20 10:55:03
# Size of source mod 2**32: 13413 bytes
from .settings import API_URL, API_AUTH, API_DATE_FORMAT
from hrparser.spiders.people_spider import PeopleSpider
from hrparser.spiders.speeches_spider import SpeechSpider
from hrparser.spiders.votes_spider import VotesSpider
from hrparser.spiders.questions_spider import QuestionsSpider
from hrparser.spiders.act_spider import ActSpider
from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests, scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem
from data_parser.vote_parser import BallotsParser
from data_parser.speech_parser import SpeechParser
from data_parser.question_parser import QuestionParser
from data_parser.person_parser import PersonParser
from data_parser.act_parser import ActParser
from data_parser.utils import get_vote_key, fix_name, get_person_id
COMMONS_ID = 199
import scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

class ImagesPipeline(ImagesPipeline):
    members = {}

    def __init__(self, *args, **kwargs):
        (super(ImagesPipeline, self).__init__)(*args, **kwargs)
        print('imgs pipeline getMembers')
        mps = getDataFromPagerApiDRF(API_URL + 'persons')
        for mp in mps:
            self.members[mp['name_parser']] = mp['id']

        print(self.members)

    def file_path(self, request, response=None, info=None):
        print('fajl path')
        print(fix_name(request.meta['name']), 'file-path')
        image_guid = str(get_person_id(self.members, fix_name(request.meta['name']))) + '.jpeg'
        print(image_guid)
        return image_guid

    def get_media_requests(self, item, info):
        print('get media')
        if 'img' in item.keys():
            print('http://www.sabor.hr/' + item['img'])
            yield scrapy.Request(('http://www.sabor.hr/' + item['img']), meta=item)
        else:
            return

    def item_completed(self, results, item, info):
        print('item compelte')
        print(results)
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem('Item contains no images')
        item['image_paths'] = image_paths
        return item


class HrparserPipeline(object):
    value = 0
    commons_id = COMMONS_ID
    others = 344
    local_data = {}
    members = {}
    parties = {}
    commitees = {}
    links = {}
    areas = {}
    agenda_items = {}
    orgs = {}
    klubovi = {}
    commitees_members = {}
    added_session = {}
    added_votes = {}
    added_links = {}
    votes_without_ballots = {}
    sessions = {}
    motions = {}
    votes = {}
    votes_dates = {}
    questions = {}
    acts = {}
    laws = {}
    memberships = {}
    mandate_start_time = datetime(day=14, month=10, year=2016)

    def __init__(self):
        print('pipeline getMembers')
        mps = getDataFromPagerApiDRF(API_URL + 'persons/')
        for mp in mps:
            self.members[mp['name_parser']] = mp['id']

        print('pipeline parties')
        print(API_URL + 'organizations/')
        paries = getDataFromPagerApiDRF(API_URL + 'organizations/')
        for pg in paries:
            self.orgs[pg['name_parser']] = pg['id']
            if not pg['classification'] == 'party':
                if pg['classification'] == 'gov':
                    self.parties[pg['name_parser']] = pg['id']
                if pg['classification'] == 'pg':
                    self.klubovi[pg['id']] = pg['_name']
                if pg['classification'] == 'committee':
                    self.commitees[pg['id']] = pg['_name']

        print(self.parties)
        print('pipeline getVotes')
        votes = getDataFromPagerApiDRF(API_URL + 'votes/')
        for vote in votes:
            self.votes[vote['motion']] = vote['id']
            self.votes_dates[vote['id']] = vote['start_time']
            if not vote['results']:
                self.votes_without_ballots[vote['motion']] = vote['id']

        print('pipeline get districts')
        areas = getDataFromPagerApiDRF(API_URL + 'areas')
        for area in areas:
            self.areas[area['name']] = area['id']

        print('pipeline get sessions')
        sessions = getDataFromPagerApiDRF(API_URL + 'sessions')
        for session in sessions:
            self.sessions[session['name'] + '_' + str(session['organization'])] = session['id']

        print('pipeline get motions')
        motions = getDataFromPagerApiDRF(API_URL + 'motions')
        for motion in motions:
            if '//' in motion['gov_id']:
                self.motions[motion['gov_id'].split('//')[1]] = motion['id']
            else:
                self.motions[motion['gov_id']] = motion['id']

        print('pipeline get districts')
        links = getDataFromPagerApiDRF(API_URL + 'links')
        for link in links:
            self.links[link['url']] = link['id']

        print('pipeline get agenda items')
        items = getDataFromPagerApiDRF(API_URL + 'agenda-items')
        for item in items:
            self.agenda_items[get_vote_key(str(item['session']) + '--' + item['name'], item['date'])] = item['id']

        print('pipeline get agenda items')
        items = getDataFromPagerApiDRF(API_URL + 'questions')
        for item in items:
            self.questions[item['signature']] = item['id']

        print('pipeline get acts items')
        items = getDataFromPagerApiDRF(API_URL + 'law')
        for item in items:
            if item['classification'] == 'act':
                self.acts[item['text'].lower()] = {'id':item['id'], 
                 'ended':item['procedure_ended'],  'procedure':item['procedure']}
            else:
                self.laws[item['epa']] = {'id':item['id'], 
                 'ended':item['procedure_ended'],  'procedure':item['procedure']}

        print('pipeline get acts items')
        items = requests.get(API_URL + 'getParliamentMembershipsOfMembers').json()
        self.memberships = items
        print('pipeline get commiteees memberships')
        for commitee in self.commitees.keys():
            items = getDataFromPagerApiDRF(API_URL + 'memberships/?role=voter&organization=' + str(commitee))
            self.commitees_members[commitee] = [item['person'] for item in items]

        print('PIPELINE is READY')

    def process_item(self, item, spider):
        if type(spider) == PeopleSpider:
            print('PPEPPEL')
            if item['type'] == 'mp':
                PersonParser(item, self)
        elif type(spider) == SpeechSpider:
            print('spic_spider')
            SpeechParser(item, self)
        else:
            if type(spider) == VotesSpider:
                BallotsParser(item, self)
            else:
                if type(spider) == QuestionsSpider:
                    QuestionParser(item, self)
                else:
                    if type(spider) == ActSpider:
                        ActParser(item, self)
                    else:
                        return item

    def get_person(self, name):
        if name in self.members.keys():
            person_id = self.members[name]
        else:
            print('NEWWW PERSON  check it: ', name)
            try:
                person_id = response.json()['id']
                self.members[name] = person_id
            except Exception as e:
                try:
                    print(e, response.json())
                    return
                finally:
                    e = None
                    del e

            return person_id

    def get_session(self, name, date):
        if name in self.sessions.keys():
            session_id = self.sessions[name]
        else:
            response = requests.post((API_URL + 'sessions/'), json={'name':name, 
             'start_time':date, 
             'organization':self.commons_id, 
             'organizations':[
              self.commons_id], 
             'in_review':False},
              auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
            try:
                session_id = response.json()['id']
                self.sessions[name] = session_id
            except Exception as e:
                try:
                    print(e, response.json())
                    return
                finally:
                    e = None
                    del e

            return session_id

    def get_agenda_item(self, name, date, session_id):
        key = get_vote_key(name, date)
        if key in self.agenda_items.keys():
            item_id = self.agenda_items[key]
        else:
            response = requests.post((API_URL + 'agenda-items/'), json={'name':name.strip(), 
             'date':date, 
             'session':session_id},
              auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
            try:
                item_id = response.json()['id']
                self.agenda_items[key] = item_id
            except Exception as e:
                try:
                    print(e, response.json())
                    return
                finally:
                    e = None
                    del e

            return item_id

    def add_organization(self, name, classification):
        if name.strip() in self.parties.keys():
            party_id = self.parties[name.strip()]
        else:
            response = requests.post((API_URL + 'organizations/'), json={'_name':name.strip(), 
             'name':name.strip(), 
             'name_parser':name.strip(), 
             '_acronym':name[:100], 
             'classification':classification},
              auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
            try:
                party_id = response.json()['id']
                self.parties[name.strip()] = party_id
            except Exception as e:
                try:
                    print(e, response.json())
                    return
                finally:
                    e = None
                    del e

            return party_id

    def add_membership(self, person_id, party_id, role, label, start_time):
        response = requests.post((API_URL + 'memberships/'), json={'person':person_id, 
         'organization':party_id, 
         'role':role, 
         'label':label, 
         'start_time':start_time},
          auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
        membership_id = response.json()['id']
        return membership_id


def getDataFromPagerApi(url, per_page=None):
    data = []
    end = False
    page = 1
    while not end:
        response = requests.get(url + '?page=' + str(page) + ('&per_page=' + str(per_page) if per_page else '')).json()
        data += response['data']
        if page >= response['pages']:
            break
        page += 1

    return data


def getDataFromPagerApiDRF(url):
    print(url)
    data = []
    end = False
    page = 1
    if '?' in url:
        url = url + '&limit=300'
    else:
        url = url + '?limit=300'
    while url:
        response = requests.get(url, auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1]))).json()
        data += response['results']
        url = response['next']

    return data
# okay decompiling pipelines.cpython-37.pyc
