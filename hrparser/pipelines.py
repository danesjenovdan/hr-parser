# -*- coding: utf-8 -*-
from .settings import API_URL, API_AUTH
from hrparser.spiders.people_spider import PeopleSpider
from hrparser.spiders.speeches_spider import SpeechSpider
from hrparser.spiders.votes_spider import VotesSpider
from datetime import datetime

from requests.auth import HTTPBasicAuth
import requests

import scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem
import editdistance
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html travnja

COMMONS_ID = 199
API_DATE_FORMAT = '%d.%m.%Y'

class HrparserPipeline(object):
    value = 0
    commons_id = COMMONS_ID
    others = 344
    local_data = {}
    members = {}
    parties = {}
    links = {}
    areas = {}
    agenda_items = {}
    orgs = {}
    
    added_session = {}
    added_votes = {}
    added_links = {}

    sessions = {}
    motions = {}
    votes = {}
    votes_dates = {}

    mandate_start_time = datetime(day=14, month=10, year=2016)

    def __init__(self):
        print('pipeline getMembers')
        mps = getDataFromPagerApiDRF(API_URL + 'persons')
        for mp in mps:
            self.members[mp['name_parser']] = mp['id']

        print('pipeline parties')
        print(API_URL + 'organizations/')
        paries = getDataFromPagerApiDRF(API_URL + 'organizations/')
        for pg in paries:
            self.orgs[pg['name_parser']] = pg['id']
            if pg['classification'] == 'poslanska skupina':
                self.parties[pg['name_parser']] = pg['id']

        print(self.parties)

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
            self.sessions[session['name']] = session['id']

        print('pipeline get motions')
        motions = getDataFromPagerApiDRF(API_URL + 'motions')
        for motion in motions:
            self.motions[motion['gov_id']] = motion['id']

        print('pipeline get districts')
        links = getDataFromPagerApiDRF(API_URL + 'links')
        for link in links:
            self.links[get_vote_key(link['name'], link['date'])] = link['id']

        print('pipeline get agenda items')
        items = getDataFromPagerApiDRF(API_URL + 'agenda-items')
        for item in items:
            self.agenda_items[get_vote_key(item['name'], item['date'])] = item['id']

        print('PIPELINE is READY')

    def process_item(self, item, spider):
        #PEOPLE PARSER
        if type(spider) == PeopleSpider:
            print("PPEPPEL")
            if item['type'] =='mp':
                if item['name'] in self.members.keys():
                    print('pass')
                    pass
                else:
                    if 'area' in item.keys():
                        if item['area'] in self.areas.keys(): 
                            area_id = self.areas[item['area']]
                        else:
                            response = requests.post(API_URL + 'areas/',
                                                 json={"name": item['area'],
                                                       "calssification": "okraj"},
                                                 auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                                )
                            print(response.content)
                            area_id = response.json()['id']
                            self.areas[item['area']] = area_id
                    else:
                        area_id = None

                    try:
                        birth_date = parse_date(item['birth_date']).isoformat()
                    except:
                        birth_date = None
                    try:
                        start_time = parse_date(item['start_time']).isoformat()
                    except:
                        start_time = self.mandate_start_time.isoformat()

                    if 'num_of_prev_mandates' in item.keys():
                        num_mandates = int(item['num_of_prev_mandates']) + 1
                    else:
                        num_mandates = 1

                    edu = parse_edu(item['education'])

                    if area_id:
                        area = [area_id]
                    else:
                        area = []

                    person_data = {'name': fix_name(item['name']),
                                   'name_parser': item['name'],
                                   'districts': area,
                                   'mandates': num_mandates,
                                   'education': edu}
                    if birth_date:
                        person_data.update({'birth_date': birth_date,})

                    response = requests.post(API_URL + 'persons/',
                                             json=person_data,
                                             auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                            )
                    try:
                        person_id = response.json()['id']
                    except:
                        print("PEEEEPL FEJL:   ", response.json())
                        print({'name': fix_name(item['name']),
                               'name_parser': item['name'],
                               'districts': [area_id],
                               'birth_date': birth_date,
                               'mandates': num_mandates,
                               'education': edu})

                    # get or add party
                    party_id = self.add_organization(item['party'], "poslanska skupina")

                    membership_id = self.add_membership(person_id, party_id, 'clan', 'cl', start_time)

                    if 'wbs' in item.keys():
                        for wb in item['wbs']:
                            wb_id = self.add_organization(wb['org'], 'odbor')
                            self.add_membership(person_id, wb_id, wb['role'], wb['role'], self.mandate_start_time.isoformat())

        elif type(spider) == SpeechSpider:
            print("spic_spider")
            SpeechesPipeline(item, self)

        elif type(spider) == VotesSpider:
            if item['type'] == 'vote_ballots':
                BallotsPipeline(item, self)

        else:
            print("else")
            return item
    # GET OR ADD

    # TODO fix adding visitors or members in past of this reference
    def get_person(self, name):
        if name in self.members.keys():
            person_id = self.members[name]
        else:
            """
            response = requests.post(API_URL + 'persons/',
                                     json={"name": name,
                                           "start_time": date,
                                           "organization": self.commons_id,
                                           "organizations": [self.commons_id],
                                           "in_review": False,},
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
            """
            print("NEWWW PERSON  check it: ", name)
            try:
                person_id = response.json()['id']
                self.members[name] = person_id
            except Exception as e:
                print(e, response.json())
                return None
        return person_id

    def get_session(self, name, date):
        if name in self.sessions.keys():
            session_id = self.sessions[name]
        else:
            response = requests.post(API_URL + 'sessions/',
                                     json={"name": name,
                                           "start_time": date,
                                           "organization": self.commons_id,
                                           "organizations": [self.commons_id],
                                           "in_review": False,},
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
            try:
                session_id = response.json()['id']
                self.sessions[name] = session_id
            except Exception as e:
                print(e, response.json())
                return None
        return session_id


    def get_agenda_item(self, name, date, session_id):
        key = get_vote_key(name, date)
        if key in self.agenda_items.keys():
            item_id = self.agenda_items[key]
        else:
            response = requests.post(API_URL + 'agenda-items/',
                                     json={"name": name.strip(),
                                           "date": date,
                                           "session": session_id},
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
            try:
                item_id = response.json()['id']
                self.agenda_items[key] = item_id
            except Exception as e:
                print(e, response.json())
                return None
        return item_id


    def add_organization(self, name, classification):
        if name.strip() in self.parties.keys():
            party_id = self.parties[name.strip()]
        else:
            response = requests.post(API_URL + 'organizations/',
                                     json={"_name": name.strip(),
                                           "name": name.strip(),
                                           "name_parser": name.strip(),
                                           "_acronym": name[:100],
                                           "classification": classification},
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
            
            try:
                party_id = response.json()['id']
                self.parties[name.strip()] = party_id
            except Exception as e:
                print(e, response.json())
                return None

        return party_id

    def add_membership(self, person_id, party_id, role, label, start_time):
        response = requests.post(API_URL + 'memberships/',
                                 json={"person": person_id,
                                       "organization": party_id,
                                       "role": role,
                                       "label": label,
                                       "start_time": start_time},
                                 auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                )
        membership_id = response.json()['id']
        return membership_id

## CLASSES

class BasePipeline(object):
    def __init__(self, reference):
        self.reference = reference

    # TODO
    def api_request(self, endpoint, dict_key, value_key, json_data):
        if value_key in getattr(self.reference, dict_key).keys():
            obj_id = getattr(self.reference, dict_key)[value_key]
            return obj_id, 'get'
        else:
            response = requests.post(
                API_URL + endpoint,
                json=json_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            try:
                obj_id = response.json()['id']
                getattr(self.reference, dict_key)[value_key] = obj_id
            except Exception as e:
                print(endpoint, e, response.text)
                return None, 'fail'
        return obj_id, 'set'


    def get_agenda_item(self, value_key, json_data):
        return self.api_request('agenda-items/', 'agenda_items', value_key, json_data)


    def get_or_add_person(self, name, districts=None, mandates=None, education=None):
        person_id = self.get_person_id(name)
        if not person_id:
            person_data = {
                'name': fix_name(name),
                'name_parser': name_parser(name),
            }
            if districts:
                person_data['districts'] = districts
            if mandates:
                person_data['mandates'] = mandates
            if education:
                person_data['education'] = education
            print('Adding person', person_data)
            response = requests.post(
                API_URL + 'persons/',
                json=person_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            print("NEWWW PERSON  check it: ", name)
            try:
                person_id = response.json()['id']
                self.reference.members[name] = person_id
            except Exception as e:
                print(e, response.json())
                return None
        return person_id

    def get_person_id(self, name):
        for key in self.reference.members.keys():
            for parser_name in key.split(','):
                if editdistance.eval(name, parser_name) < 3:
                    return self.reference.members[key]
        return None

    def get_organization_id(self, name):
        for key in self.reference.parties.keys():
            for parser_name in key.split(','):
                if editdistance.eval(name, parser_name) < 3:
                    return self.reference.parties[key]
        return None

    def add_or_get_motion(self, value_key, json_data):
        return self.api_request('motions/', 'motions', value_key, json_data)


    def add_or_get_vote(self, value_key, json_data):
        return  self.api_request('votes/', 'votes', value_key, json_data)


    def add_ballot(self, voter, vote, option, party=None):
        json_data ={
            'option': option,
            'vote': vote,
            'voter': voter,
            'voterparty': self.reference.others
        }
        if party:
            json_data.update({"voterparty": party})
        response = requests.post(
            API_URL + 'ballots/',
            json=json_data,
            auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        )
        print(response.text)

    def add_ballots(self, json_data):
        print("SENDING BALLOTS")
        response = requests.post(
            API_URL + 'ballots/',
            json=json_data,
            auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        )

    def add_or_get_session(self, session_name, json_data):
        return  self.api_request('sessions/', 'sessions', session_name, json_data)

class SpeechesPipeline(BasePipeline):
    def __init__(self, data, reference):
        """{"date": "20.04.2018.",
        "session_ref": ["Saziv: IX, sjednica: 8"],
        "content_list": ["Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254", "Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254"],
        "speaker": ["Brki\u0107, Milijan (HDZ)"],
        "order": 1,
        "content": "Prelazimo na sljede\u0107u to\u010dku dnevnog reda, Prijedlog Zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na RH, prvo \u010ditanje, P.Z. br. 254.\nPredlagatelj je zastupnik kolega Robert Podolnjak na temelju \u010dlanka 85. Ustava RH i \u010dlanka 172. Poslovnika Hrvatskog sabora.\nPrigodom rasprave o ovoj to\u010dki dnevnog reda primjenjuju se odredbe Poslovnika koji se odnose na prvo \u010ditanje zakona.\nRaspravu su proveli nadle\u017eni Odbor za zakonodavstvo, nadle\u017eni Odbor za obrazovanje, znanost i kulturu.\nVlada je dostavila svoje mi\u0161ljenje.\nPozivam po\u0161tovanog kolegu gospodina Roberta Podolnjaka da nam da dodatno obrazlo\u017eenje prijedloga Zakona.\nIzvolite."},
        """
        # call init of parent object        
        super(SpeechesPipeline, self).__init__(reference)

        self.date = data['date']
        self.session_ref = data['session_ref']
        self.content_list = data['content_list']
        self.speaker = data['speaker']
        self.order = data['order']
        self.content = data['content']
        self.agenda_id = data['agenda_id']
        # SPEECH

        self.speech = {}
        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
        }

        self.parse_time()
        self.set_data()
        
    def parse_time(self):
        self.date = datetime.strptime(self.date, API_DATE_FORMAT + '.')
        self.speech['valid_from'] = self.date.isoformat()
        self.speech['start_time'] = self.date.isoformat()
        self.speech['valid_to'] = datetime.max.isoformat()

    def set_data(self):
        self.speech['content'] = self.content
        self.speech['party'] = self.reference.commons_id
        self.speech['order'] = self.order

        # get and set session
        session = self.session_ref[0].split(':')[-1].strip()
        self.session['name'] = session
        session_id, session_status = self.add_or_get_session(session, self.session)
        self.speech['session'] = session_id

        agenda_text = ' '.join(self.content_list)
        agenda_key = get_vote_key(agenda_text.strip(), self.date.isoformat())
        agenda_json = {
            "name": agenda_text.strip(),
            "date": self.date.isoformat(),
            "session": session_id,
            "order": self.agenda_id
        }
        agenda_id = self.get_agenda_item(agenda_key, agenda_json)

        self.speech['agenda_item'] = agenda_id[0]

        # get and set speaket
        speaker, pg = self.parse_speaker(self.speaker[0])
        speaker_id = self.get_or_add_person(speaker)
        if pg:
            party_id = self.get_organization_id(pg.strip())
        else:
            party_id = None
        self.speech['party'] = party_id
        self.speech['speaker'] = speaker_id

        response = requests.post(API_URL + 'speechs/',
                                 json=self.speech,  
                                 auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                )

    def parse_speaker(self, data):
        splited = data.split('(')
        print(splited)
        name = splited[0]
        if len(splited) > 1:
            pg = splited[1].split(')')[0]
            print(pg)
        else:
            pg = None
        name = ' '.join(reversed(list(map(str.strip, name.split(',')))))
        return name, pg


class BallotsPipeline(BasePipeline):
    """
    {"results": "Ukupno: 101. Za: 96. Suzdr\u017ean: 2. Protiv: 3.",
     "results_data": ["Rasprava je zaklju\u010dena 23. studenoga 2016.", "Zakon je donesen na  2. sjednici 25. studenoga 2016. (96 glasova \"za\", 3 \"protiv\", 2 \"suzdr\u017eana\").", "O ovoj to\u010dki dnevnog reda o\u010ditovali su se:\r\n"],
     "time": "25.11.2016. 12:02",
     "title": "KONA\u010cNI PRIJEDLOG ZAKONA O POTVR\u0110IVANJU PROTOKOLA UZ SJEVERNOATLANTSKI UGOVOR O PRISTUPANJU CRNE GORE, hitni postupak, prvo i drugo \u010ditanje, P.Z. br. 31",
     "type": "vote_ballots",
     "ballots": [{"voter": "Aleksi\u0107 Goran", "option": "+"}, {"voter": "Ambru\u0161ec Ljubica", "option": "+"}, {"voter": "Anu\u0161i\u0107 Ivan", "option": "+"}, {"voter": "Ba\u010di\u0107 Branko", "option": "+"}, {"voter": "Bali\u0107 Marijana", "option": "+"}, {"voter": "Bari\u0161i\u0107 Dra\u017een", "option": "+"}, {"voter": "Batini\u0107 Milorad", "option": "+"}, {"voter": "Bedekovi\u0107 Vesna", "option": "+"}, {"voter": "Beus Richembergh Goran", "option": "+"}, {"voter": "Bilek Vladimir", "option": "+"}, {"voter": "Boban Bla\u017eenko", "option": "+"}, {"voter": "Bori\u0107 Josip", "option": "+"}, {"voter": "Bo\u0161njakovi\u0107 Dra\u017een", "option": "+"}, {"voter": "Brki\u0107 Milijan", "option": "+"}, {"voter": "Bulj Miro", "option": "+"}, {"voter": "Bunjac Branimir", "option": "-"}, {"voter": "Buri\u0107 Majda", "option": "+"}, {"voter": "Culej Stevo", "option": "+"}, {"voter": "\u010ci\u010dak Mato", "option": "+"}, {"voter": "\u0106eli\u0107 Ivan", "option": "+"}, {"voter": "\u0106osi\u0107 Pero", "option": "+"}, {"voter": "Dodig Goran", "option": "+"}, {"voter": "\u0110aki\u0107 Josip", "option": "+"}, {"voter": "Esih Bruna", "option": "+"}, {"voter": "Felak Damir", "option": "+"}, {"voter": "Frankovi\u0107 Mato", "option": "+"}, {"voter": "Glasnovi\u0107 \u017deljko", "option": "o"}, {"voter": "Glasovac Sabina", "option": "+"}, {"voter": "Grmoja Nikola", "option": "+"}, {"voter": "Hajdukovi\u0107 Domagoj", "option": "+"}, {"voter": "Hasanbegovi\u0107 Zlatko", "option": "+"}, {"voter": "Horvat Darko", "option": "+"}, {"voter": "Hrg Branko", "option": "+"}, {"voter": "Jandrokovi\u0107 Gordan", "option": "+"}, {"voter": "Jankovics R\u00f3bert", "option": "+"}, {"voter": "Jeli\u0107 Damir", "option": "+"}, {"voter": "Jelkovac Marija", "option": "+"}, {"voter": "Josi\u0107 \u017deljka", "option": "+"}, {"voter": "Jovanovi\u0107 \u017deljko", "option": "+"}, {"voter": "Juri\u010dev-Martin\u010dev Branka", "option": "+"}, {"voter": "Kajtazi Veljko", "option": "+"}, {"voter": "Karli\u0107 Mladen", "option": "+"}, {"voter": "Kirin Ivan", "option": "+"}, {"voter": "Klari\u0107 Tomislav", "option": "+"}, {"voter": "Kliman Anton", "option": "+"}, {"voter": "Klisovi\u0107 Jo\u0161ko", "option": "+"}, {"voter": "Kosor Darinko", "option": "+"}, {"voter": "Kova\u010d Miro", "option": "+"}, {"voter": "Kristi\u0107 Maro", "option": "+"}, {"voter": "Kri\u017eani\u0107 Josip", "option": "+"}, {"voter": "Krstulovi\u0107 Opara Andro", "option": "+"}, {"voter": "Lackovi\u0107 \u017deljko", "option": "o"}, {"voter": "Lalovac Boris", "option": "+"}, {"voter": "Lekaj Prljaskaj Ermina", "option": "+"}, {"voter": "Lon\u010dar Davor", "option": "+"}, {"voter": "Lovrinovi\u0107 Ivan", "option": "+"}, {"voter": "Luci\u0107 Franjo", "option": "+"}, {"voter": "Luka\u010di\u0107 Ljubica", "option": "+"}, {"voter": "Maksim\u010duk Ljubica", "option": "+"}, {"voter": "Mati\u0107 Predrag", "option": "+"}, {"voter": "Mesi\u0107 Jasen", "option": "+"}, {"voter": "Mikuli\u0107 Andrija", "option": "+"}, {"voter": "Mili\u010devi\u0107 Davor", "option": "+"}, {"voter": "Milinovi\u0107 Darko", "option": "+"}, {"voter": "Milo\u0161evi\u0107 Boris", "option": "+"}, {"voter": "Milo\u0161evi\u0107 Domagoj Ivan", "option": "+"}, {"voter": "Mrak-Tarita\u0161 Anka", "option": "+"}, {"voter": "Nin\u010devi\u0107-Lesandri\u0107 Ivana", "option": "+"}, {"voter": "Pari\u0107 Darko", "option": "+"}, {"voter": "Peri\u0107 Grozdana", "option": "+"}, {"voter": "Petrijev\u010danin Vuksanovi\u0107 Irena", "option": "+"}, {"voter": "Petrov Bo\u017eo", "option": "+"}, {"voter": "Podolnjak Robert", "option": "+"}, {"voter": "Prgomet Drago", "option": "+"}, {"voter": "Puh Marija", "option": "+"}, {"voter": "Pusi\u0107 Vesna", "option": "+"}, {"voter": "Radin Furio", "option": "+"}, {"voter": "Ragu\u017e \u017deljko", "option": "+"}, {"voter": "Reiner \u017deljko", "option": "+"}, {"voter": "Romi\u0107 Davor", "option": "+"}, {"voter": "Ronko Zdravko", "option": "+"}, {"voter": "Ro\u0161\u010di\u0107 Dragica", "option": "+"}, {"voter": "Runti\u0107 Hrvoje", "option": "+"}, {"voter": "Sanader Ante", "option": "+"}, {"voter": "Sin\u010di\u0107 Ivan", "option": "-"}, {"voter": "Sladoljev Marko", "option": "+"}, {"voter": "Strenja-Lini\u0107 Ines", "option": "+"}, {"voter": "Stri\u010dak An\u0111elko", "option": "+"}, {"voter": "\u0160imi\u0107 Marko", "option": "+"}, {"voter": "\u0160imi\u0107 Miroslav", "option": "+"}, {"voter": "\u0160ipi\u0107 Ivan", "option": "+"}, {"voter": "\u0160kibola Marin", "option": "-"}, {"voter": "\u0160kori\u0107 Petar", "option": "+"}, {"voter": "Topolko Bernarda", "option": "+"}, {"voter": "Totgergeli Miro", "option": "+"}, {"voter": "Tu\u0111man Miroslav", "option": "+"}, {"voter": "Turina-\u0110uri\u0107 Nada", "option": "+"}, {"voter": "Tu\u0161ek \u017darko", "option": "+"}, {"voter": "Varda Ka\u017eimir", "option": "+"}, {"voter": "Vu\u010deti\u0107 Marko", "option": "+"}, {"voter": "Zekanovi\u0107 Hrvoje", "option": "+"}]},
    """
    def __init__(self, data, reference):
        # call init of parent object
        super(BallotsPipeline, self).__init__(reference)

        # copy item to object
        self.results = data['results']
        self.results_data = data['results_data']
        self.time = data['time']
        self.title = data['title']
        self.ballots = data['ballots']
        self.url = data['url']

        # prepere dictionarys for setters
        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
        }
        self.motion = {}
        self.vote = {}
        self.time_f = None

        # parse data
        self.parse_time()
        self.parse_title()

        if self.is_motion_saved():
            # TODO edit motion if we need it
            print("This motion is allready parsed")

            self.parse_results()
            motion_id = self.get_motion_id()
            vote_id = self.get_vote_id()

            print("patching motion", motion_id, 'and vote', vote_id)
            
            response = requests.patch(
                API_URL + 'motions/' + str(motion_id) + '/',
                json=self.motion,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            print(response.status_code)
            response = requests.patch(
                API_URL + 'votes/' + str(vote_id) + '/',
                json=self.vote,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            print(response.status_code)
            
        else:
            # add new motion
            self.set_fixed_data()
            self.parse_results()
            self.set_fixed_data()

            # run setters
            self.set_data()

    def is_motion_saved(self):
        return self.url in self.reference.motions.keys()

    def get_motion_id(self):
        return self.reference.motions[self.url]

    def get_vote_id(self):
        return self.reference.votes[get_vote_key(self.vote['name'], self.vote['start_time'])]

    def set_fixed_data(self):
        self.vote['organization'] = self.reference.others
        self.motion['party'] = self.reference.others
        #self.motion['tags'] = [' ']
        #self.vote['tags'] = [' '],

    def parse_results(self):
        def find_line_with_vote(data):
            voting_words = [
                'glas',
                'glasova',
                'glasa',
            ]
            i = 0
            found = None
            for i, line in enumerate(data):
                line = line.replace(',', '')
                splited_line = line.split(" ")
                for word in voting_words:
                    if word in splited_line:
                        found = i
            return found

        data = self.results_data

        line_id = find_line_with_vote(data)

        if line_id == None:
            raise ValueError("DONT FIND VOTING DATA: ", data)

        session_split = data[line_id].replace(',', '').split(" ")

        ses_idx = session_split.index('sjednici')
        session_name = session_split[ses_idx - 1].strip()
        if '.' in session_name:
            session_name = session_name.replace('.', '')
        self.session['name'] = session_name


        decision_words = [
            'donesen',
            'donesena',
            'doneseni',
            'donesene',
            'prihvaćeno',
            'prihvaćena',
            'prihvaćen',
            'donesene',
            'iskazano',
            'primljeno',
            'primljena',
            'iskazao',
            'potvrđen',
            'potvrđeno',
        ]
        result_idx = -1
        for word in decision_words:
            if word in session_split:
                result_idx = session_split.index(word)
                break

        if result_idx < 0:
            raise ValueError("DECISION FAIL: ", session_split)

        pre_result = session_split[result_idx - 1].strip()
        post_result = session_split[result_idx + 1].strip()

        if pre_result in ['je', 'su']:
            self.vote['result'] = 1
            self.motion['result'] = 1
        elif pre_result in ['nije']:
            self.vote['result'] = 0
            self.motion['result'] = 0

        elif post_result in ['je', 'su']:
            self.vote['result'] = 1
            self.motion['result'] = 1
        elif post_result in ['nije']:
            self.vote['result'] = 0
            self.motion['result'] = 0
        else:
            raise ValueError("VOTE RESULT IS SOMETHING ELSE: ", pre_result, post_result)
            print("VOTE RESULT IS SOMETHING ELSE: ")      


    def parse_time(self):
        self.time_f = datetime.strptime(self.time, "%d.%m.%Y. %H:%M")
        self.motion['date'] = self.time_f.isoformat()
        self.vote['start_time'] = self.time_f.isoformat()
        self.session['start_time'] = self.time_f.isoformat()

    def parse_title(self):
        self.motion['text'] = self.title
        self.motion['gov_id'] = self.url
        self.vote['name'] = self.title

    def parse_ballots(self, vote):
        print("PARSe Ballots")
        # {"voter": "Aleksi\u0107 Goran", "option": "+"}
        option_map = {
            'o': 'kvorum',
            '+': 'za',
            '-': 'proti'
        }
        data = []
        members_on_vote = []
        # get vote
        for ballot in self.ballots:
            member = self.get_or_add_person(ballot['voter'])
            option = option_map[ballot['option']]
            #self.add_ballot(member, vote, option)
            temp ={
            'option': option,
            'vote': vote,
            'voter': member,
            'voterparty': self.reference.others
            }
            data.append(temp)
            members_on_vote.append(member)

        date_f = dt= datetime.strptime(self.reference.votes_dates[vote], "%Y-%m-%dT%H:%M:%S")
        mps = requests.get(API_URL + 'getMPs/' + date_f.strftime(API_DATE_FORMAT)).json()
        for mp in mps:
            if mp['id'] not in members_on_vote:
                temp ={
                    'option': 'ni',
                    'vote': vote,
                    'voter': mp['id'],
                    'voterparty': self.reference.others
                }
                data.append(temp)
        self.add_ballots(data)

    def set_data(self):
        session_id, session_status = self.add_or_get_session(self.session['name'], self.session)
        self.motion['session'] = session_id
        self.vote['session'] = session_id
        motion_id, motion_status = self.add_or_get_motion(
            self.url,
            self.motion
        )
        self.vote['motion'] = motion_id
        vote_id, vote_status = self.add_or_get_vote(self.vote['name'], self.vote)

        if not vote_id in self.reference.votes_dates.keys():
            self.reference.votes_dates[vote_id] = self.time_f.isoformat()
        self.parse_ballots(vote_id)



## HELPER METHODS

def getDataFromPagerApi(url, per_page = None):
    data = []
    end = False
    page = 1
    while not end:
        response = requests.get(url + '?page=' + str(page) + ('&per_page='+str(per_page) if per_page else '')).json()
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
    while url:
        response = requests.get(url, auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])).json()
        data += response['results']
        url = response['next']
    return data


def get_vote_key(name, date):
    return (name + date).strip()


def fix_name(name_str):
    return ' '.join(map(str.capitalize, name_str.split(' ')))

def parse_month(month_str):
    months = ['sije', 'velj', 'ožuj', 'trav', 'svib', 'lip', 'srp', 'kolov', 'ruj', 'listop', 'studen', 'prosin']
    for i, month in enumerate(months):
        if month_str.lower().startswith(month):
            return i + 1
    return None

def parse_date(input_data):
    # "birth_date": ["28.", "sije\u010dnja", "1977"]
    # "14. listopada 2016."
    if type(input_data) == str:
        input_data = input_data.split(' ')

    day = int(float(input_data[0]))
    month = parse_month(input_data[1])
    year = int(float(input_data[2]))
    return datetime(day=day, month=month, year=year)

def parse_edu(data):
    # {"e": [" Zavr\u0161io Gimnaziju \"M", " A", " Reljkovi\u0107\" u Vinkovcima (SSS - kulturno-umjetni\u010dki smjer)"]},

    splited = ' '.join(data).split('(')
    if len(splited) > 1:
        out = splited[1].split(')')[0]
        print(out) 
        return out
    print("EDUJEHSN; ", data)
    return ''


def name_parser(name):
    words = name.split(' ')
    new_words = list(map(str.capitalize, words))
    print(new_words)
    new_parser_name = ' '.join(new_words)+','+' '.join(list(reversed(new_words)))

    return new_parser_name
