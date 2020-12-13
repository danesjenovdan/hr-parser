from .base_parser import BaseParser
from .utils import get_vote_key, fix_name

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT, H_PEOPLE, H_LORDS

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import pdftotext
import copy
import re
import time

import logging
logger = logging.getLogger('session logger')

UPDATE_VOTES = False

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
        logger.info('.:SESSION PARSER:.')
        self.speeches = []

        if item['session_of'] == 'Dom naroda':
            org = self.reference.people_id
        elif item['session_of'] == 'Predstavnički dom':
            org = self.reference.commons_id
        else:
            logger.info("WTF session")
            return
        self.session = {
            "organization": org,
            "organizations": [org],
            "in_review": False,
            "gov_id": item['gov_id'],
            "name": item['name'],
        }
        self.update = UPDATE_VOTES
        # get and set session

        logger.debug('session state 1')

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
            logger.debug('ima speeches')
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
            logger.debug(response.content)
            logger.debug(response.status_code)
        if 'votes' in item.keys():
            logger.debug('ima votes')
            if item['session_of'] == 'Dom naroda':
                votes_parser = VotesParserPeople(item['votes'])
                org_id = H_PEOPLE
            elif item['session_of'] == 'Predstavnički dom':
                votes_parser = VotesParser(item['votes'])
                org_id = H_LORDS

            for order, parsed_vote in enumerate(votes_parser.votes):
                logger.debug(parsed_vote.keys())
                if 'name' in parsed_vote.keys():
                    name = parsed_vote['name']
                else:
                    name = parsed_vote['agenda_item_name']

                vote_key = get_vote_key(org_id, parsed_vote['start_time'].isoformat())
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
                        'organization': org_id
                        #'motion':
                    }
                    logger.debug('Adding motion::::........')
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
                elif self.update:
                    logger.debug('UPDATE VOTE')
                    vote_data = {
                        'name': name
                    }
                    vote_id, vote_status = self.update_vote(vote_key, vote_data, id=vote_id)

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
        return epas

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
            #logger.debug(line)
            line = line.strip()
            if self.state == 'start':
                if line in ['PREDSJEDAVAJUĆI', 'PREDSJEDATELJICA', 'PREDSJEDATELJ']:
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
        self.curr_title = ''

        self.parse()

        #logger.debug(self.votes)

    def merge_name(self, name, agenda, typ):
        return ' - '.join([i for i in [name, agenda, typ] if i])

    def parse(self):
        current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}

        # helpers for find agenda
        self.num_of_lines = 0
        self.found_keyword = False

        for line in self.content:
            logger.debug(line)
            #logger.debug(self.state, self.num_of_lines, self.found_keyword)
            line = line.strip()
            if re.split("\s\s+", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN NIJE PRISUTAN', 'UKUPNO']:
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                current_vote['name'] = ' '.join(current_vote['name'])
                current_vote['name'] = self.merge_name(current_vote['name'], ' '.join(current_vote['agenda_item_name']), current_vote.get('type', ''))
                logger.debug(current_vote['name'])
                if current_vote['ballots']:
                    self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}
                continue

            if self.state == 'start':
                if line.startswith('Redni broj glasanja'):
                    self.state = 'parse'
                    continue

            elif self.state == 'agenda':
                current_vote['agenda_item_name'].append(self.parse_multiline(line, self.curr_title, 'voteing-about'))
                if not self.num_of_lines:
                    self.state = 'voteing-about'

            elif self.state == 'voteing-about':
                current_vote['name'].append(self.parse_multiline(line, 'Glasanje o:', 'parse'))


            if self.state == 'parse':
                if line.startswith('Redni broj tačke'):
                    current_vote['agenda_number'] = line.split(':')[1].strip()
                    self.state = 'agenda'
                    self.curr_title = 'Redni broj tačke'
                    self.num_of_lines = 0
                    self.found_keyword = False
                    continue
                # workaround for stupit wtf case
                if line.startswith('5HGQLEURMWDþNH'):
                    current_vote['agenda_number'] = line.replace('5HGQLEURMWDþNH', '').strip()
                    self.state = 'agenda'
                    self.curr_title = '5HGQLEURMWDþNH'
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
                    else:
                        current_vote['type'] = line.split(':')[1].strip()
                if line.startswith('Prisutan'):
                    continue
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
                    #logger.debug(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})\.', line))
                    if line.split(' ')[0].endswith('.') and not bool(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})', line)):
                        #logger.debug("in", bool(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})\.', line)))
                        current_vote['ballots'].append(self.parse_ballot(line))
                if line.startswith('Tačka dnevnog reda:'):
                    self.state = 'agenda'
                    self.curr_title = 'Tačka dnevnog reda:'
                    current_vote['agenda_item_name'].append(line.replace('Tačka dnevnog reda:', '').strip())
                if line.startswith('7DþNDGQHYQRJUHGD'):
                    self.state = 'agenda'
                    self.curr_title = '7DþNDGQHYQRJUHGD'
                    current_vote['agenda_item_name'].append(line.replace('7DþNDGQHYQRJUHGD', '').strip())

    def parse_ballot(self, line):
        #logger.debug(repr(line))
        #logger.debug(line)
        try:
            temp1, name, temp2, option = re.split("\s\s+", line)
        except:
            logger.debug('FAIL!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            logger.debug(line)
            raise Exception
        return {'name': name, 'option': self.VOTE_MAP[option]}

    def parse_multiline(self, line, keyword, next_state):
        if line.startswith(keyword):
            # If is single line return end, else return switch for invert counter
            if self.num_of_lines:
                self.found_keyword = True
            else:
                self.state = next_state
            return line.replace(keyword, '').strip()
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

        logger.debug(self.votes)

    def merge_name(self, name, agenda, typ):
        return ' - '.join([i for i in [name, agenda, typ] if i])

    def parse(self):
        current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': [], 'agenda-name': []}

        # helpers for find agenda
        self.num_of_lines = 0
        self.found_keyword = False

        for line in self.content:
            line = line.strip()
            if re.split("\s\s*", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN', 'NIJE', 'PRISUTAN', 'UKUPNO']:
                #logger.debug(line)
                #logger.debug(re.split("\s\s*", line.strip()))
                #logger.debug(re.split("\s\s+", line.strip()))
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                if current_vote['agenda_item_name'].endswith(";") or current_vote['agenda_item_name'].endswith(":"):
                    current_vote['agenda_item_name'] = current_vote['agenda_item_name'][0:-1]
                current_vote['name'] = ' '.join(current_vote['name'])
                if current_vote['name'].endswith(";") or current_vote['name'].endswith(":"):
                    current_vote['name'] = current_vote['name'][0:-1]
                #current_vote['name'] = ' '.join(current_vote['name'])

                current_vote['name'] = self.merge_name(current_vote['name'], ' '.join(current_vote['agenda-name']), current_vote.get('type', ''))
                logger.debug(current_vote['name'])

                if current_vote['ballots']:
                    self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': [], 'agenda-name': []}
                continue

            if self.state == 'start':
                logger.debug('start')
                if line.startswith('Rezultati glasanja'):
                    self.state = 'date'
                    continue

            elif self.state == 'date':
                logger.debug('date')
                current_vote['start_time'] = datetime.strptime(line, API_DATE_FORMAT + ' %H:%M:%S')
                self.state = 'agenda'
                continue

            elif self.state == 'agenda':
                logger.debug('agenda')
                if line.startswith('Dom:') or line.startswith('Sjednica:') or line.startswith('Način glasanja:') or line.startswith('1DþLQJODVDQMD'):
                    continue
                if line.startswith('Redni broj:'):
                    line = line.replace("Redni broj:", "").strip()
                    current_vote['agenda_item_name'].append(line)
                if line.startswith('Redni broj glasanja: '):
                    line = line.replace("Redni broj glasanja: ", "").strip()
                    current_vote['agenda_item_name'].append(line)
                if line.startswith('Redni broj'):
                    line = line.replace("Redni broj", "").strip()
                    current_vote['agenda_item_name'].append(line)
                elif line.startswith('Glasanje o:'):
                    self.state = 'voteing-about'
                elif line.startswith('Naziv tačke:'):
                    self.state = 'agenda-name'
                else:
                    current_vote['agenda_item_name'].append(line.strip())

            if self.state == 'agenda-name':
                logger.debug('agenda-name')
                if line.startswith('Glasanje o:'):
                    self.state = 'voteing-about'
                else:
                    current_vote['agenda-name'].append(line.replace('Naziv tačke:', '').strip())

            if self.state == 'voteing-about':
                logger.debug('voting-about')
                if line.startswith('Tip glasanja:'):
                    if 'poništeno' in line:
                        logger.debug('ponisteno')
                        # skip this vote because it's repeted
                        current_vote = {'count': {}, 'ballots': [], 'agenda_item_name': [], 'agenda-name': [], 'name': []}
                        self.state = 'start'
                        continue
                    current_vote['type'] = line.replace('Tip glasanja:', '').strip()
                    self.state = 'parse'
                    continue
                current_vote['name'].append(line.replace('Glasanje o:', '').strip())

            if self.state == 'parse':
                logger.debug('parse')
                logger.debug(line)
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
