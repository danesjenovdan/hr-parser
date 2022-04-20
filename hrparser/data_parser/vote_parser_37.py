from hrparser.data_parser.base_parser_37 import BaseParser37
from hrparser.data_parser.utils import get_vote_key
from hrparser.settings import API_URL, API_AUTH, API_DATE_FORMAT
from datetime import datetime, timedelta
import requests, re, json, pdftotext

PARSE_JUST_NEW_VOTES = False
FORCE_SET_DOCS = False

options_map = {
    'donesen':'enacted',
    'dostavljeno radi informiranja':'submitted',
    'odbijen':'rejected',
    'povučen':'retracted',
    'prihvaćen':'adopted',
    'prima se na znanje':'received',
    'u proceduri':'in_procedure'
}

options = {'za':'for',
 'protiv':'against',
 'suzdržan':'abstain',
 'suzdržana':'abstain',
 'suzdržanim':'abstain',
 'suzdržanih':'abstain',
 'susdržan':'abstain',
 'sudržan':'abstain',
 'suzdržani':'abstain',
 'suzdran':'abstain'}

all_options = [
    'for',
    'against',
    'abstain',
    'absent'
]

class BallotsParser37(BaseParser37):
    options = {
        'za':'for',
        'protiv':'against',
        'suzdržan':'abstain',
        'suzdržana':'abstain',
        'suzdržanim':'abstain',
        'suzdržanih':'abstain',
        'susdržan':'abstain',
        'sudržan':'abstain',
        'suzdržani':'abstain',
        'suzdran':'abstain'
    }
    def __init__(self, data, reference):
        super(BallotsParser37, self).__init__(reference)
        self.source_data = data
        self.title = data['title']
        self.url = data['url']
        self.docs = data['docs']
        print('PARSE____', self.title)
        print(self.docs)
        self.session_name = data['session_name'].split('.')[0] + '. sjednica'
        self.session = {'organization':self.reference.commons_id,
            'organizations':[
            self.reference.commons_id],
            'in_review':False,
            'name':self.session_name
        }
        self.motion = {}
        self.vote = {}
        self.act = {
            'status':'in_procedure',
            'result':'in_procedure'}
        self.time_f = None
        self.result_hirarhy = [
            'in_procedure',
            'rejected',
            'adopted',
            'enacted'
        ]
        self.act_result_options = ('rejected', 'adopted', 'adopted')
        self.parse_title()
        self.set_fixed_data()
        self.ballots = None
        self.act_id = None
        if data['type'] == 'vote':
            if self.is_motion_saved():
                if PARSE_JUST_NEW_VOTES:
                    pass
                else:
                    print("VOTESSSSSSSSSS")
                    self.parse_results_from_content()
                    try:
                        self.parse_time_from_result_data()
                        if FORCE_SET_DOCS:
                            print("set_docs")
                            self.set_docs()
                    except:
                        print("FAILLLLSSSS")
                        return
                    print("WOOHOOO")
            else:
                self.parse_results_from_content()
                try:
                    self.parse_time_from_result_data()
                except Exception as e:
                    print("FAILLLLSSSS", e)
                    return
                self.set_data()
                self.set_docs()

        if data['type'] == 'vote_ballots':
            self.time = data['time']
            self.ballots = data['ballots']
            self.parse_time()
            print("")
            if self.is_motion_saved():
                if PARSE_JUST_NEW_VOTES:
                    print('This motion is allready parsed')
                elif self.is_motion_saved_without_ballots():
                    self.parse_results()
                    motion_id = self.reference.motions[self.source_data['id']]
                    vote_id = self.reference.votes_without_ballots[motion_id]
                    self.parse_ballots(vote_id)
                else:
                    self.parse_results()
                    self.set_data()
                    self.set_docs()
            else:
                session_id, session_status = self.add_or_get_session(self.session['name'], self.session)
                print("session_id", session_id)
                self.act['session'] = session_id
                self.act['procedure_ended'] = False
                self.act['status'] = 'in_procedure'
                self.act['result'] = 'in_procedure'
                if 'date_to_procedure' in self.source_data.keys():
                    d_time = datetime.strptime(self.source_data['date_to_procedure'], '%Y-%m-%dT%H:%M:%SZ')
                elif 'time' in self.source_data.keys():
                    d_time = datetime.strptime(self.source_data['time'], '%d.%m.%Y. %H:%M')
                else:
                    raise Exception("No time")
                self.act['date'] = d_time.isoformat()
                print("law type:", self.act['classification'])
                if self.act['classification'] == 'act':
                    self.act_id = self.add_or_update_act(self.act['text'], self.act)
                else:
                    note = None
                    for doc in self.docs:
                        if doc['text'].lower().startswith('pz') or doc['text'].lower().startswith('pze'):
                            note = ContentParser(doc).parse()

                    if note:
                        self.act['note'] = ' '.join(note)
                    self.act_id = self.add_or_update_law(self.act['epa'], self.act)
                self.parse_results()
                self.set_data()
                self.set_docs()

        if data['type'] == 'legislation':
            session_id, session_status = self.add_or_get_session(self.session['name'], self.session)
            self.act['session'] = session_id
            self.act['procedure_ended'] = False
            self.act['status'] = 'in_procedure'
            self.act['result'] = 'in_procedure'
            d_time = datetime.strptime(self.source_data['date_to_procedure'], '%Y-%m-%dT%H:%M:%SZ')
            self.act['date'] = d_time.isoformat()
            if self.act['classification'] == 'act':
                self.act_id = self.add_or_update_act(self.act['text'], self.act)
            else:
                note = None
                for doc in self.docs:
                    if doc['text'].lower().startswith('pz') or doc['text'].lower().startswith('pze'):
                        note = ContentParser(doc).parse()

                if note:
                    self.act['note'] = ' '.join(note)
                self.act_id = self.add_or_update_law(self.act['epa'], self.act)

    def is_motion_saved(self):
        print('IS SAVED:  ', self.source_data['id'] in self.reference.motions.keys())
        return self.source_data['id'] in self.reference.motions.keys()

    def is_motion_saved_without_ballots(self):
        return self.source_data['id'] in self.reference.votes_without_ballots.keys()

    def get_motion_id(self):
        return self.reference.motions[self.source_data['id']]

    def get_vote_id(self):
        return self.reference.votes[get_vote_key(self.vote['name'], self.vote['start_time'])]

    def set_fixed_data(self):
        self.vote['organization'] = self.reference.others
        self.motion['party'] = self.reference.others

    def get_line_id(self, line_ids):
        if line_ids:
            if self.source_data['type'] == 'vote_ballots':
                offset = len(line_ids) - self.source_data['m_items']
                return line_ids[(self.source_data['c_item'] + offset)]
            return line_ids[(-1)]
        else:
            return

    def parse_results_from_content(self):
        find_results = r'\(?(?P<number>\d+)\)?\s?(glas\w* )?[„\"]? ?(za|protiv|su[zs]?dr[zž]?an\w*)[“\"]?'
        self.counters = {}
        self.result = None
        match = None
        if self.source_data['results_data']:
            for paragraph in self.source_data['results_data']:
                matches = re.finditer(find_results, paragraph, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    votes = int(match.group(1))
                    option = match.group(3)
                    if votes:
                        if option:
                            if option in ('preferencijalna', 'odlučio', 'jedno', 'većinom',
                                          'zastupnika'):
                                print(paragraph)
                                break
                        option = options[option.lower()]
                        self.counters.update({option: votes})
                        option = None
                        votes = None

                if match:
                    self.result = self.find_result(paragraph)
                    if self.counters:
                        break
                #match = None

            if self.counters:
                self.counters.update(absent=(151 - sum(self.counters.values())))
                for opt in all_options:
                    if opt not in self.counters:
                        self.counters.update({opt: 0})

                self.vote['counter'] = json.dumps(self.counters)
            self.vote['result'] = self.result
            self.motion['result'] = self.result
            if self.result:
                if self.act['procedure'] in ['drugo čitanje', 'hitni postupak']:
                    self.act['result'] = self.act_result_options[int(self.result)]
                else:
                    self.act['result'] = self.act_result_options[0 if int(self.result) == 0 else 2]
            print(self.counters, 'result:', self.result)

    def find_result(self, text):
        negative_words = [
         'ne prihvaća',
         'nije podržao',
         'da ne prihvati',
         'ne podupire donošenje',
         'nije mogao utvrditi',
         'nije donesen',
         'nije dobio']
        positive_words = [
         'odlučio predložiti',
         'da donese',
         'donošenje',
         'je prihvaćeno'
         'podržao',
         'prihvati',
         'je donesen',
         'je donesenpredložiti',
         'većinom glasova',
         'je donesena',
         'da se prihvaća']
        for word in negative_words:
            if word in text:
                return '0'

        for word in positive_words:
            if word in text:
                return '1'

    def parse_results(self):
        if self.source_data['for_count'] > self.source_data['against_count']:
            self.vote['result'] = 1
            self.motion['result'] = 1
            self.act['result'] = self.act_result_options[1]
        else:
            self.vote['result'] = 0
            self.motion['result'] = 0
            self.act['result'] = self.act_result_options[0]
        self.act['procedure_phase'] = self.act['result']
        self.act['status'] = self.act['result']

    def parse_time(self):
        self.time_f = datetime.strptime(self.time, '%d.%m.%Y. %H:%M')
        self.motion['date'] = self.time_f.isoformat()
        self.vote['start_time'] = self.time_f.isoformat()
        self.session['start_time'] = self.time_f.isoformat()
        self.act['date'] = self.time_f.isoformat()

    def parse_title(self):
        text = self.title.lower()
        if text[-1] == ';':
            text = text[:-1]
        else:
            self.motion['text'] = text
            self.motion['gov_id'] = self.source_data['id']
            self.vote['name'] = text
            epa = self.find_epa_in_name(self.title)
            if epa:
                self.vote['epa'] = epa
                self.motion['epa'] = epa
                self.act['epa'] = epa
                self.act['classification'] = 'zakon'
                if ', hitni postupak' in text:
                    text = text.split(', hitni postupak')[0]
                    self.act_result_options = ('rejected', 'enacted', 'adopted')
                    self.act['procedure'] = 'hitni postupak'
                    self.act['procedure_ended'] = True
                else:
                    if ', drugo čitanje' in text:
                        text = text.split(', drugo čitanje')[0]
                        self.act_result_options = ('rejected', 'enacted')
                        self.act['procedure'] = 'drugo čitanje'
                        self.act['procedure_ended'] = True
                    else:
                        if ', prvo čitanje' in text:
                            text = text.split(', prvo čitanje')[0]
                            self.act_result_options = ('rejected', 'adopted', 'adopted')
                            self.act['procedure'] = 'prvo čitanje'
                self.act['text'] = text
            else:
                self.act['classification'] = 'act'
                self.act['epa'] = 'act' + self.url.split('=')[(-1)]
                self.vote['epa'] = self.act['epa']
                self.motion['epa'] = self.act['epa']
                if '- podnositelj' in text:
                    self.act['text'] = text.split('- podnositelj')[0].strip()
                else:
                    if '- predlagatelj' in text:
                        self.act['text'] = text.split('- predlagatelj')[0].strip()
                    else:
                        self.act['text'] = text.strip()
                self.act['procedure_ended'] = True
                self.act['procedure'] = 'act'
            self.act_result_options = ('rejected', 'enacted', 'adopted')
            #self.act['procedure_ended'] = True

    def parse_ballots(self, vote):
        option_map = {'abstained':'abstain',
         'for':'for',
         'against':'against'}
        data = []
        members_on_vote = []
        for ballot in self.ballots:
            member = self.get_or_add_person(ballot['voter'])
            option = option_map[ballot['option']]
            voter_party_id = self.get_membership_of_member_on_date(str(member), self.time_f)
            if not voter_party_id:
                voter_party_id = self.reference.others
            temp = {'option':option,
             'vote':vote,
             'voter':member,
             'voterparty':voter_party_id}
            data.append(temp)
            members_on_vote.append(member)

        date_f = dt = datetime.strptime(self.reference.votes_dates[vote], '%Y-%m-%dT%H:%M:%S')
        mps = requests.get(API_URL + 'getMPs/' + date_f.strftime(API_DATE_FORMAT + 'T%H:%M')).json()
        for mp in mps:
            if mp['id'] not in members_on_vote:
                temp = {'option':'absent',  'vote':vote,
                 'voter':mp['id'],
                 'voterparty':self.reference.others}
                data.append(temp)

        self.add_ballots(data)

    def set_data(self):
        session_id, session_status = self.add_or_get_session(self.session['name'], self.session)
        self.motion['session'] = session_id
        self.vote['session'] = session_id
        self.act['session'] = session_id
        if self.act['classification'] == 'act':
            self.act_id = self.add_or_update_act(self.act['text'], self.act)
        else:
            print('TO JE ACT__________________', self.act)
            note = None
            for doc in self.docs:
                if doc['text'].lower().startswith('pz') or doc['text'].lower().startswith('pze'):
                    note = ContentParser(doc).parse()

            if note:
                self.act['note'] = ' '.join(note)
            self.act_id = self.add_or_update_law(self.act['epa'], self.act)

        # UNDO
        motion_id, motion_status = self.add_or_get_motion(self.source_data['id'], self.motion)


        self.vote['motion'] = motion_id
        vote_id, vote_status = self.add_or_get_vote(motion_id, self.vote)
        if vote_id not in self.reference.votes_dates.keys():
            self.reference.votes_dates[vote_id] = self.time_f.isoformat()
        if self.ballots:
            self.parse_ballots(vote_id)

    def set_docs(self):
        if not self.is_motion_saved or FORCE_SET_DOCS:
            motion_id, motion_status = self.add_or_get_motion(self.source_data['id'], self.motion)
            for doc in self.docs:
                data = {'url': doc['url'],
                    'name':doc['text'],
                    'motion':motion_id
                }
                print(self.add_link(data))

    def parse_time_from_result_data(self):
        time = datetime.strptime(self.source_data['date'], API_DATE_FORMAT + '.')
        self.time_f = time
        self.motion['date'] = time.isoformat()
        self.vote['start_time'] = time.isoformat()
        self.act['date'] = time.isoformat()
        self.session['start_time'] = time.isoformat()

    def parse_non_balots_balots(self, data):
        opt_map = {'suzdržana':'abstain',
         'za':'for',
         'protiv':'against'}
        r = re.compile('\\(.*\\)')
        text = self.results_data
        if len(text) > 1:
            if '(' in text[1]:
                data = r.searchtext[1].group(0)
            else:
                data = r.searchtext[0].group(0)
        else:
            data = data.replace('(', '').replace(')','').replace('\xa0',' ')
            splited = data.split(' ')
            j_data = {}
            if 'jednoglasno' in data:
                i = 3
                if splited[3] in ('glas', 'glasova'):
                    i = 4
                option = replace_nonalphanum(splited[i])
                votes = splited[1]
                j_data = {opt_map[option]: votes}
            else:
                votes = 0
                option = ''
                for token in splited:
                    token = replace_nonalphanum(token)
                    if token.isalpha:
                        if token in opt_map.keys():
                            option = token
                            j_data[opt_map[option]] = votes
                        if token.isdigit:
                            votes = int(token)

        self.vote['counter'] = json.dumps(j_data)

    #def find_epa_in_name(self, name):
    #    search_epa = re.compile(r'(\d+)')
    #    if 'P.Z.' in name:
    #        new_text = name.split('P.Z.')[1]
    #        a = search_epa.search(new_text.strip())
    #        if a:
    #            #print(a.group(0))
    #            return a.group(0)
    #    return None


def replace_nonalphanum(word):
    word = re.sub('\\W+', '', word)
    return word


class Get_PDF(object):

    def __init__(self, url, file_name):
        response = requests.get((url), verify=False)
        with open('files/' + file_name, 'wb') as (f):
            f.write(response.content)
        with open('files/' + file_name, 'rb') as (f):
            self.pdf = pdftotext.PDF(f)


class ContentParser(Get_PDF):
    reg_roman = '(?=\\b[MCDXLVI]{1,6}\\b)M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'

    def __init__(self, obj):
        super().__init__(obj['url'], obj['text'])
        content = ''.join(self.pdf)
        self.content = content.split('\n')

    def parse(self):
        read = False
        out_data = []
        for line in self.content:
            if re.match(self.reg_roman, line.strip()):
                if 'OCJENA STANJA I OSNOVNA PITANJA' in line.upper():
                    read = True
                else:
                    read = False
            elif line.strip() == line.strip().upper():
                continue
            if read:
                out_data.append(line)

        print(out_data)
        return out_data


class ContentParserFILE(object):
    reg_roman = '(?=\\b[MCDXLVI]{1,6}\\b)M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'
    END_WORDS = [
     'Osnovna pitanja koja se uređuju predloženim Zakonom',
     'Posljedice koje će donošenjem zakona proisteći',
     'Pitanja koja se trebaju urediti Zakonom',
     'Posljedice koje će proisteći donošenjem Zakona',
     'Osnovna pitanja koja se trebaju urediti Zakonom',
     'Razlozi zbog kojih se Zakon donosi',
     'Osnovna pitanja koja se trebaju urediti ovim Zakonom',
     'Posljedice koje će proisteći donošenjem ovoga Zakona']
    SKIP_START_LINES = [
     'Ocjena stanja i pitanja koja se rješavaju ovim Zakonom',
     'Ocjena stanja']

    def __init__(self, file_name):
        with open(file_name, 'rb') as f:
            self.pdf = pdftotext.PDF(f)
        content = ''.join(self.pdf)
        self.content = content.split('\n')

    def parse(self):
        read = False
        out_data = []
        for line in self.content:
            if re.match(self.reg_roman, line.strip()):
                if 'OCJENA STANJA I OSNOVNA PITANJA' in line.upper():
                    read = True
                else:
                    if read == True:
                        if line.strip() == line.strip().upper():
                            break
                    read = False
            else:
                if 'Ocjena stanja' in line and len(line.strip().replace('Ocjena stanja', '').strip()) < 3:
                    continue
                else:
                    if self.check_end_inner(line):
                        break
                if line.strip() == line.strip().upper():
                    continue
            if read:
                out_data.append(line)

        print(out_data)
        return out_data

    def check_end_inner(self, line):
        for word in self.END_WORDS:
            print(len(line.strip().replace(word, '').strip()))
            if word in line and len(line.strip().replace(word, '').strip()) < 3:
                return True

        return False
