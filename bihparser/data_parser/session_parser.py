from .base_parser import BaseParser
from .utils import get_vote_key, fix_name

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import pdftotext
import copy
import re
import time

class SessionParser(BaseParser):
    def __init__(self, item, reference):
        """
            'gov_id': session_gov_id,
            'name': session_name,
            'start_date': start_date,
            'start_time': start_time,
            'speeches'
            'votes'
            'session_of'
        """
        # call init of parent object
        super(SessionParser, self).__init__(reference)
        print('.:SESSION PARSER:.')
        self.speeches = []

        if item['session_of'] == 'Dom naroda':
            org = self.reference.people_id
        elif item['session_of'] == 'Predstavnički dom':
            org = self.reference.commons_id
        else:
            print("WTF session")
            return
        self.session = {
            "organization": org,
            "organizations": [org],
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

        if 'speeches' in item.keys() and self.session_id not in reference.sessions_with_speeches:
            #TODO skip parsing speeches already parsed
            content_parser = ContentParser(item['speeches'])

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
        if 'votes' in item.keys():
            if item['session_of'] == 'Dom naroda':
                votes_parser = VotesParserPeople(item['votes'])
            elif item['session_of'] == 'Predstavnički dom':
                votes_parser = VotesParser(item['votes'])

            for order, parsed_vote in enumerate(votes_parser.votes):
                if 'name' in parsed_vote.keys():
                    name = parsed_vote['name']
                else:
                    name = parsed_vote['agenda_item_name']
                vote_key = get_vote_key(name, parsed_vote['start_time'].isoformat())
                if vote_key in self.reference.votes.keys():
                    vote_id = self.reference.votes[vote_key]
                else:
                    vote_id = None
                epa = self.find_epa(parsed_vote['agenda_item_name'])
                if not vote_id:
                    motion_data = {
                        'session': self.session_id,
                        'text': name,
                        'date': parsed_vote['start_time'].isoformat(),
                        'epa': epa,
                        'party': self.reference.commons_id,
                    }
                    vote_data = {
                        'session': self.session_id,
                        'name': name,
                        'start_time': parsed_vote['start_time'].isoformat(),
                        'epa': epa,
                        #'motion':
                    }
                    print('Adding motion::::........')
                    motion_id, motion_status = self.add_or_get_motion(
                        vote_key,
                        motion_data
                    )
                    vote_data['motion'] = motion_id
                    vote_id, vote_status = self.add_or_get_vote(vote_key, vote_data)
                    ballots = []

                    for ballot in parsed_vote['ballots']:
                        voter_id = self.get_or_add_person(
                            fix_name(ballot['name']),
                        )

                        party_id = self.get_membership_of_member_on_date(str(voter_id), parsed_vote['start_time'])
                        if not party_id:
                            party_id = self.reference.others
                        temp_ballot = {'vote': vote_id,
                                       'option': ballot['option'],
                                       'voter': voter_id,
                                       'voterparty': party_id}
                        ballots.append(temp_ballot)
                    self.add_ballots(ballots)

    def find_epa(self, line):
        epas = None
        for m in re.finditer('broj:', line):
            m.start()
            epa_str = line[m.end():].strip()
            if '- ' in epa_str:
                epa_str = epa_str.replace('- ', '-')
            epa = epa_str.split(' ')
            if epas:
                epas = epas + '|' +epa[0]
            else:
                epas = epa[0]

class get_PDF(object):
    def __init__(self, url, file_name):
        response = requests.get(url)
        with open('files/'+file_name, 'wb') as f:
            f.write(response.content)

        with open('files/'+file_name, "rb") as f:
            self.pdf = pdftotext.PDF(f)

class ContentParser(get_PDF):
    def __init__(self, obj):
        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)
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



class VotesParser(get_PDF):
    def __init__(self, obj):
        self.VOTE_MAP = {'Protiv': 'against', 'Za': 'for', 'Nije glasao': 'abstain', 'Suzdržan': 'abstain', 'Nije prisutan': 'absent'}

        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)

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
            #print(line)
            #print(self.state, self.num_of_lines, self.found_keyword)
            line = line.strip()
            if re.split("\s\s+", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN NIJE PRISUTAN', 'UKUPNO']:
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                current_vote['name'] = ' '.join(current_vote['name'])
                if current_vote['ballots']:
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
        #print(repr(line))
        temp1, name, temp2, option = re.split("\s\s+", line)
        return {'name': name, 'option': self.VOTE_MAP[option]}

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


class VotesParserPeople(get_PDF):
    def __init__(self, obj):
        self.VOTE_MAP = {'PROTIV': 'against', 'ZA': 'for', 'NIJE PRISUTAN': 'abstain', 'SUZDRŽAN': 'abstain'}

        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)

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
            line = line.strip()
            if re.split("\s\s+", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN', 'NIJE PRISUTAN', 'UKUPNO']:
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                if current_vote['agenda_item_name'].endswith(";"):
                    current_vote['agenda_item_name'] = current_vote['agenda_item_name'][0:-1]
                current_vote['name'] = ' '.join(current_vote['name'])
                if current_vote['name'].endswith(";"):
                    current_vote['name'] = current_vote['name'][0:-1]
                if current_vote['ballots']:
                    self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}
                continue

            if self.state == 'start':
                if line.startswith('Rezultati glasanja'):
                    self.state = 'date'
                    continue

            elif self.state == 'date':
                current_vote['start_time'] = datetime.strptime(line, API_DATE_FORMAT + ' %H:%M:%S')
                self.state = 'agenda'
                continue

            elif self.state == 'agenda':
                if line.startswith('Dom:') or line.startswith('Sjednica:') or line.startswith('Način glasanja:'):
                    continue
                if line.startswith('Redni broj:'):
                    line = line.replace("Redni broj:", "").strip()
                    current_vote['agenda_item_name'].append(line)
                elif line.startswith('Glasanje o:'):
                    self.state = 'voteing-about'
                else:
                    current_vote['agenda_item_name'].append(line.strip())


            if self.state == 'voteing-about':
                if line.startswith('Tip glasanja:'):
                    if 'poništeno' in line:
                        # skip this vote because it's repeted
                        current_vote = {'count': {}, 'ballots': [], 'agenda_item_name': [], 'name': []}
                        self.state = 'start'
                        continue
                    current_vote['type'] = line.replace('Tip glasanja:', '').strip()
                    self.state = 'parse'
                    continue
                current_vote['name'].append(line.replace('Glasanje o:', '').strip())

            if self.state == 'parse':
                if line.startswith('Prisutno'):
                    current_vote['count']['absent'] = 15 - int(line[-5:].strip())
                elif line.startswith('ZA'):
                    current_vote['count']['for'] = int(line[-5:].strip())
                elif line.startswith('PROTIV'):
                    current_vote['count']['against'] = int(line[-5:].strip())
                elif line.startswith('SUZDRŽAN'):
                    current_vote['count']['abstain'] = int(line[-5:].strip())
                elif line.startswith('Ukupno'):
                    pass
                else:
                    # parse ballot
                    current_vote['ballots'].append(self.parse_ballot(line))

    def parse_ballot(self, line):
        name, temp2, option = re.split("\s\s+", line)
        return {'name': name, 'option': self.VOTE_MAP[option]}