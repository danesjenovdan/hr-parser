from .base_parser import BaseParser
from .utils import get_vote_key, fix_name

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import pdftotext
import copy
import re

VOTE_MAP = {'Protiv': 'against', 'Za': 'for', 'Nije glasao': 'abstain', 'Suzdržan': 'abstain', 'Nije prisutan': 'absent'}

class SessionParser(BaseParser):
    def __init__(self, item, reference):
        """
            'gov_id': session_gov_id,
            'name': session_name,
            'start_date': start_date,
            'start_time': start_time,
            'speeches'
            'votes'
        """
        # call init of parent object 
        super(SessionParser, self).__init__(reference)
        print('.:SESSION PARSER:.')
        self.speeches = []

        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
            "gov_id": item['gov_id'],
            "name": item['name'],
        }
        # get and set session

        start_time = datetime.strptime(item['start_date'].strip() + ' ' + item['start_time'].strip(), API_DATE_FORMAT + ' %H:%M')
        self.session['start_time'] = start_time.isoformat()

        self.session_id, session_status = self.add_or_get_session(item['gov_id'], self.session)

        self.speech = {
            'session': self.session_id,
            'valid_from': start_time.isoformat(),
            'start_time': start_time.isoformat(),
            'valid_to': datetime.max.isoformat()
        }

        if 'speeches' in item.keys():
            #TODO skip parsing speeches already parsed
            content_parser = ContentParser("files/"+item['speeches'])
            #print(content_parser.speeches)
            print(start_time)

            for order, parsed_speech in enumerate(content_parser.speeches):

                speaker_id = self.get_or_add_person(
                    fix_name(parsed_speech['speaker']),
                )

                party_id = self.get_membership_of_member_on_date(str(speaker_id), start_time)

                if not party_id:
                    party_id = self.reference.others

                speech = copy.deepcopy(self.speech)

                speech['content'] = parsed_speech['content']
                speech['order'] = order
                speech['party'] = party_id
                speech['speaker'] = speaker_id

                self.speeches.append(speech)
            response = requests.post(API_URL + 'speechs/',
                                     json=self.speeches,  
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )



class ContentParser(object):
    def __init__(self, file_name):
        with open(file_name, "rb") as f:
            pdf = pdftotext.PDF(f)
        content = "".join(pdf)
        self.content = content.split('\n')
        self.state = 'start'
        self.speeches = []

        self.parse()

    def parse(self):
        current_speaker = ''
        current_content = []
        for line in self.content:
            #print(line)
            line = line.strip()
            if self.state == 'start':
                if line in ['PREDSJEDAVAJUĆI', 'PREDSJEDATELJICA']:
                    self.state = 'parse'
                    continue
            elif self.state == 'parse':
                # skip line if line is not speakers content 
                if not line or line[0]=='/' or '___(?)' in line or line.isdigit() or 'Sjednica završena' in line:
                    continue
                # line is of new speaker name
                if line.isupper():
                    if current_content:
                        self.speeches.append({
                            'speaker': current_speaker,
                            'content': ' '.join(current_content),
                        })
                        current_content = []
                    current_speaker = line
                # parse content
                else:
                    current_content.append(line)
        self.speeches.append({
            'speaker': current_speaker,
            'content': ' '.join(current_content),
        })
        


class VotesParser(object):
    def __init__(self, file_name):
        with open(file_name, "rb") as f:
            pdf = pdftotext.PDF(f)
        content = "".join(pdf)
        self.content = content.split('\n')
        self.state = 'start'
        self.votes = []

        self.parse()

    def parse(self):
        current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}

        # helpers for find agenda
        self.num_of_lines = 0
        self.found_keyword = False
        
        for line in self.content:
            print(line)
            print(self.state, self.num_of_lines, self.found_keyword)
            line = line.strip()

            if line.strip().startswith('ZA  PROTIV'):
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                current_vote['name'] = ' '.join(current_vote['name'])
                self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}
                continue

            if self.state == 'start':
                if line.startswith('Redni broj glasanja'):
                    self.state = 'parse'
                    continue

            elif self.state == 'agenda':
                current_vote['agenda_item_name'].append(self.parse_multiline(line, 'Tačka dnevnog reda', 'voteing-about'))
                if not self.num_of_lines:
                    self.state = 'voteing-about'

            elif self.state == 'voteing-about':
                current_vote['name'].append(self.parse_multiline(line, 'Glasanje o', 'parse'))
                

            if self.state == 'parse':
                if line.startswith('Redni broj tačke'):
                    current_vote['agenda_number'] = line.split(':')[1].strip()
                    self.state = 'agenda'
                    self.num_of_lines = 0
                    self.found_keyword = False
                    continue
                if line.startswith('Datum i vrijeme glasanja'):
                    current_vote['start_time'] = datetime.strptime(line.split(':', 1)[1].strip(), API_DATE_FORMAT + '. %H:%M')
                #if line.startswith('Glasanje o'):
                #    current_vote['name'] = line.split(':')[1].strip()
                if line.startswith('Tip glasanja'):
                    if 'Poništeno' in line:
                        # skip this vote because it's repeted
                        current_vote = {'count': {}, 'ballots': [], 'agenda_item_name': [], 'name': []}
                        self.state = 'start'
                if line.startswith('Nije prisutan'):
                    current_vote['count']['absent'] = int(line[-5:].strip())
                if line.startswith('ZA'):
                    current_vote['count']['for'] = int(line[-5:].strip())
                if line.startswith('PROTIV'):
                    current_vote['count']['against'] = int(line[-5:].strip())
                if line.startswith('SUZDRŽAN'):
                    current_vote['count']['abstain'] = int(line[-5:].strip())
                if line[0].isdigit():
                    # parse ballot
                    if line.split(' ')[0].endswith('.'):
                        current_vote['ballots'].append(self.parse_ballot(line))
                if line.startswith('Tačka dnevnog reda:'):
                    self.state = 'agenda'
                    current_vote['agenda_item_name'].append(line.split(':', 1)[1].strip())

    def parse_ballot(self, line):
        print(repr(line))
        temp1, name, temp2, option = re.split("\s\s+", line)
        return {'name': name, 'option': VOTE_MAP[option]}

    def parse_multiline(self, line, keyword, next_state):
        if line.startswith(keyword):
            # If is single line return end, else return switch for invert counter
            if self.num_of_lines:
                self.found_keyword = True
            else:
                self.state = next_state
            return line.split(':')[1].strip()
        else:
            if self.found_keyword:
                self.num_of_lines-=1
            else:
                self.num_of_lines+=1
            if not self.num_of_lines:
                self.state = next_state
                self.found_keyword = False
            return line.strip()
