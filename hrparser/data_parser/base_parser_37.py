# uncompyle6 version 3.7.3
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.8.2 (default, Jul 16 2020, 14:00:26) 
# [GCC 9.3.0]
# Embedded file name: /home/tomaz/dev/DJND/hrparser/hrparser/data_parser/base_parser.py
# Compiled at: 2020-02-13 17:04:50
# Size of source mod 2**32: 11448 bytes
from .utils import fix_name, name_parser
from ..settings import API_URL, API_AUTH
from requests.auth import HTTPBasicAuth
import requests, editdistance, re
from datetime import datetime

class BaseParser37(object):

    def __init__(self, reference):
        self.reference = reference

    # File "/home/tomaz/dev/DJND/hrparser/hrparser/data_parser/base_parser_37.py", line 167, in add_or_update_act
    #     act_id, method = self.api_request('law/', 'acts', name, json_data)
    # File "/home/tomaz/dev/DJND/hrparser/hrparser/data_parser/base_parser_37.py", line 26, in api_request
    #     response = getattr(requests, method)(API_URL + endpoint,

    def api_request(self, endpoint, dict_key, value_key, json_data, method='post'):
        print(endpoint, dict_key, value_key, json_data, method)
        print(value_key in getattr(self.reference, dict_key).keys())
        if value_key in getattr(self.reference, dict_key).keys():
            if method != 'patch':
                obj_id = getattr(self.reference, dict_key)[value_key]
                return (obj_id, 'get')
        response = getattr(requests, method)(API_URL + endpoint,
            json=json_data,
            auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        )
        # response = requests.post(
        #     API_URL + endpoint,
        #     json=json_data,
        #     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        # )
        try:
            obj_id = response.json()['id']
            getattr(self.reference, dict_key)[value_key] = obj_id
        except Exception as e:
            try:
                print(response.content)
                print(endpoint, e, response.text, 'request was not delivered request was not delivered request was not delivered request was not delivered')
                return (None, 'fail')
            finally:
                e = None
                del e

        return (
         obj_id, 'set')

    def get_agenda_item(self, value_key, json_data):
        return self.api_request('agenda-items/', 'agenda_items', value_key, json_data)

    # def get_or_add_person(self, name, districts=None, mandates=None, education=None, birth_date=None):
    #     person_id = self.get_person_id(name)
    #     person_data = person_id or {'name':fix_name(name), 
    #      'name_parser':name_parser(name)}
    #     if districts:
    #         person_data['districts'] = districts
    #     if mandates:
    #         person_data['mandates'] = mandates
    #     if education:
    #         person_data['education'] = education
    #     if birth_date:
    #         person_data['birth_date'] = birth_date
    #     response = requests.post((API_URL + 'persons/'),
    #       json=person_data,
    #       auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
    #     print('NEWWW PERSON  check it: ', name)
    #     try:
    #         person_id = response.json()['id']
    #         self.reference.members[name] = person_id
    #     except Exception as e:
    #         try:
    #             print(e, response.json())
    #             return
    #         finally:
    #             e = None
    #             del e

    #     return person_id

    def get_or_add_person(self, name, districts=None, mandates=None, education=None, birth_date=None):
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
            if birth_date:
                person_data['birth_date'] = birth_date
            #print('Adding person', person_data)
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
                if editdistance.eval(name, parser_name) < 1:
                    return self.reference.members[key]

    def add_or_get_motion(self, value_key, json_data):
        return self.api_request('motions/', 'motions', value_key, json_data)

    def add_or_get_area(self, value_key, json_data):
        return self.api_request('areas/', 'areas', value_key, json_data)

    def add_or_get_vote(self, value_key, json_data):
        return self.api_request('votes/', 'votes', value_key, json_data)

    def add_or_get_question(self, value_key, json_data):
        return self.api_request('questions/', 'questions', value_key, json_data)

    def update_question(self, signature, json_data):
        self.api_request(f'questions/{self.reference.questions[signature]["id"]}/', 'questions', signature, json_data, method='patch')

    def add_link(self, json_data):
        return self.api_request('links/', 'links', json_data['url'], json_data)

    def add_ballot(self, voter, vote, option, party=None):
        json_data = {'option':option, 
         'vote':vote, 
         'voter':voter, 
         'voterparty':self.reference.others}
        if party:
            json_data.update({'voterparty': party})
        response = requests.post((API_URL + 'ballots/'),
          json=json_data,
          auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))

    def add_ballots(self, json_data):
        print('SENDING BALLOTS')
        response = requests.post((API_URL + 'ballots/'),
          json=json_data,
          auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))

    def update_motion(self, uid, json_data):
        self.api_request(('motions/%s/' % str(self.reference.motions[uid])), 'motions', uid, json_data, method='patch')

    def add_or_update_law(self, uid, json_data):
        if uid in self.reference.laws.keys():
            print('UPDATE law')
            json_data.pop('text', None)
            if not self.reference.laws[uid]['ended']:
                act_id, method = self.api_request(('law/%s/' % str(self.reference.laws[uid]['id'])), 'laws', uid, json_data, method='patch')
                if 'procedure_ended' in json_data.keys():
                    ended = True
                else:
                    ended = False
                self.reference.laws[uid] = {'id':act_id, 
                 'ended':ended}
                return act_id
            return self.reference.laws[uid]['id']
        else:
            print('CREATE law')
            act_id, method = self.api_request('law/', 'laws', uid, json_data)
            if 'procedure_ended' in json_data.keys():
                ended = True
            else:
                ended = False
            self.reference.laws[uid] = {
                'id':act_id, 
                'ended':ended}
            return act_id

    def add_or_update_act(self, name, json_data):
        if name in self.reference.acts.keys():
            if not self.reference.acts[name]['ended']:
                print('UPDATE act')
                json_data.pop('text', None)
                act_id, method = self.api_request(('law/%s/' % str(self.reference.acts[name]['id'])), 'acts', name, json_data, method='patch')
                if 'procedure_ended' in json_data.keys():
                    ended = True
                else:
                    ended = False
                self.reference.acts[name] = {
                    'id':act_id,
                    'ended':ended
                }
                return act_id
            return self.reference.acts[name]['id']
        else:
            print('Create act')
            act_id, method = self.api_request('law/', 'acts', name, json_data)
            if 'procedure_ended' in json_data.keys():
                ended = True
            else:
                ended = False
        self.reference.acts[name] = {'id':act_id, 
         'ended':ended}
        return act_id

    def add_or_get_session(self, session_name, json_data):
        if session_name:
            print("\n")
            print("______________SESSION_________________:", session_name + '_' + str(json_data['organization']))
            print("\n")
            return self.api_request('sessions/', 'sessions', session_name + '_' + str(json_data['organization']), json_data)
        return

    def parse_edoc_person(self, data):
        splited = data.split('(')
        name = splited[0]
        if len(splited) > 1:
            pg = splited[1].split(')')[0]
        else:
            splited = data.split('/')
            if len(splited) > 1:
                name = splited[0]
                pg = splited[1].strip()
                if ';' in pg:
                    pg = pg.replace(';', '')
                if 'Vlade' in pg:
                    pg = 'gov'
            else:
                pg = None
        name = ' '.join(reversed(list(map(str.strip, name.split(',')))))
        return (name, pg)

    def get_organization_id(self, name, orgs='parties'):
        p = False
        for key in getattr(self.reference, orgs).keys():
            if not key:
                continue
            for parser_name in key.split('|'):
                if editdistance.eval(name, parser_name) < 1:
                    return getattr(self.reference, orgs)[key]

    def add_organization(self, name, classification, create_if_not_exist=True, orgs='parties'):
        party_id = self.get_organization_id(name, orgs=orgs)
        if not party_id:
            if create_if_not_exist:
                orgs_pipeline = getattr(self.reference, orgs)
                print('ADDING ORG ' + name)
                response = requests.post((API_URL + 'organizations/'), json={'_name':name.strip(), 
                 'name':name.strip(), 
                 'name_parser':name.strip(), 
                 '_acronym':name[:100], 
                 'classification':classification},
                  auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
                try:
                    party_id = response.json()['id']
                    orgs_pipeline[name.strip()] = party_id
                except Exception as e:
                    try:
                        print(e, response.json())
                        return
                    finally:
                        e = None
                        del e

            else:
                return
        return party_id

    def add_membership(self, person_id, party_id, role, label, start_time, on_behalf_of=None):
        response = requests.post((API_URL + 'memberships/'), json={'person':person_id, 
         'organization':party_id, 
         'on_behalf_of':on_behalf_of, 
         'role':role, 
         'label':label, 
         'start_time':start_time},
          auth=(HTTPBasicAuth(API_AUTH[0], API_AUTH[1])))
        membership_id = response.json()['id']
        return membership_id

    def get_membership_of_member_on_date(self, person_id, search_date):
        memberships = self.reference.memberships
        if person_id in memberships.keys():
            mems = memberships[person_id]
            for mem in mems:
                start_time = datetime.strptime(mem['start_time'], '%Y-%m-%dT%H:%M:%S')
                if start_time <= search_date:
                    if mem['end_time']:
                        end_time = datetime.strptime(mem['end_time'], '%Y-%m-%dT%H:%M:%S')
                        if end_time >= search_date:
                            return mem['on_behalf_of_id']
                    else:
                        return mem['on_behalf_of_id']

    def find_epa_in_name(self, name):
        search_epa = re.compile('(\\d+)')
        name = name.lower()
        if 'p.z.' in name:
            new_text = name.split('p.z.')[1]
            a = search_epa.search(new_text.strip())
            if a:
                return a.group(0)
        if 'p. z.' in name:
            new_text = name.split('p. z.')[1]
            a = search_epa.search(new_text.strip())
            if a:
                return a.group(0)
# okay decompiling base_parser.cpython-37.pyc
