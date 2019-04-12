from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime

import requests
import re
import json
class BallotsParser(BaseParser):
    """
    {"results": "Ukupno: 101. Za: 96. Suzdr\u017ean: 2. Protiv: 3.",
     "results_data": ["Rasprava je zaklju\u010dena 23. studenoga 2016.", "Zakon je donesen na  2. sjednici 25. studenoga 2016. (96 glasova \"za\", 3 \"protiv\", 2 \"suzdr\u017eana\").", "O ovoj to\u010dki dnevnog reda o\u010ditovali su se:\r\n"],
     "time": "25.11.2016. 12:02",
     "title": "KONA\u010cNI PRIJEDLOG ZAKONA O POTVR\u0110IVANJU PROTOKOLA UZ SJEVERNOATLANTSKI UGOVOR O PRISTUPANJU CRNE GORE, hitni postupak, prvo i drugo \u010ditanje, P.Z. br. 31",
     "type": "vote_ballots",
     "ballots": [{"voter": "Aleksi\u0107 Goran", "option": "+"}, {"voter": "Ambru\u0161ec Ljubica", "option": "+"}, {"voter": "Anu\u0161i\u0107 Ivan", "option": "+"}, {"voter": "Ba\u010di\u0107 Branko", "option": "+"}, {"voter": "Bali\u0107 Marijana", "option": "+"}, {"voter": "Bari\u0161i\u0107 Dra\u017een", "option": "+"}, {"voter": "Batini\u0107 Milorad", "option": "+"}, {"voter": "Bedekovi\u0107 Vesna", "option": "+"}, {"voter": "Beus Richembergh Goran", "option": "+"}, {"voter": "Bilek Vladimir", "option": "+"}, {"voter": "Boban Bla\u017eenko", "option": "+"}, {"voter": "Bori\u0107 Josip", "option": "+"}, {"voter": "Bo\u0161njakovi\u0107 Dra\u017een", "option": "+"}, {"voter": "Brki\u0107 Milijan", "option": "+"}, {"voter": "Bulj Miro", "option": "+"}, {"voter": "Bunjac Branimir", "option": "-"}, {"voter": "Buri\u0107 Majda", "option": "+"}, {"voter": "Culej Stevo", "option": "+"}, {"voter": "\u010ci\u010dak Mato", "option": "+"}, {"voter": "\u0106eli\u0107 Ivan", "option": "+"}, {"voter": "\u0106osi\u0107 Pero", "option": "+"}, {"voter": "Dodig Goran", "option": "+"}, {"voter": "\u0110aki\u0107 Josip", "option": "+"}, {"voter": "Esih Bruna", "option": "+"}, {"voter": "Felak Damir", "option": "+"}, {"voter": "Frankovi\u0107 Mato", "option": "+"}, {"voter": "Glasnovi\u0107 \u017deljko", "option": "o"}, {"voter": "Glasovac Sabina", "option": "+"}, {"voter": "Grmoja Nikola", "option": "+"}, {"voter": "Hajdukovi\u0107 Domagoj", "option": "+"}, {"voter": "Hasanbegovi\u0107 Zlatko", "option": "+"}, {"voter": "Horvat Darko", "option": "+"}, {"voter": "Hrg Branko", "option": "+"}, {"voter": "Jandrokovi\u0107 Gordan", "option": "+"}, {"voter": "Jankovics R\u00f3bert", "option": "+"}, {"voter": "Jeli\u0107 Damir", "option": "+"}, {"voter": "Jelkovac Marija", "option": "+"}, {"voter": "Josi\u0107 \u017deljka", "option": "+"}, {"voter": "Jovanovi\u0107 \u017deljko", "option": "+"}, {"voter": "Juri\u010dev-Martin\u010dev Branka", "option": "+"}, {"voter": "Kajtazi Veljko", "option": "+"}, {"voter": "Karli\u0107 Mladen", "option": "+"}, {"voter": "Kirin Ivan", "option": "+"}, {"voter": "Klari\u0107 Tomislav", "option": "+"}, {"voter": "Kliman Anton", "option": "+"}, {"voter": "Klisovi\u0107 Jo\u0161ko", "option": "+"}, {"voter": "Kosor Darinko", "option": "+"}, {"voter": "Kova\u010d Miro", "option": "+"}, {"voter": "Kristi\u0107 Maro", "option": "+"}, {"voter": "Kri\u017eani\u0107 Josip", "option": "+"}, {"voter": "Krstulovi\u0107 Opara Andro", "option": "+"}, {"voter": "Lackovi\u0107 \u017deljko", "option": "o"}, {"voter": "Lalovac Boris", "option": "+"}, {"voter": "Lekaj Prljaskaj Ermina", "option": "+"}, {"voter": "Lon\u010dar Davor", "option": "+"}, {"voter": "Lovrinovi\u0107 Ivan", "option": "+"}, {"voter": "Luci\u0107 Franjo", "option": "+"}, {"voter": "Luka\u010di\u0107 Ljubica", "option": "+"}, {"voter": "Maksim\u010duk Ljubica", "option": "+"}, {"voter": "Mati\u0107 Predrag", "option": "+"}, {"voter": "Mesi\u0107 Jasen", "option": "+"}, {"voter": "Mikuli\u0107 Andrija", "option": "+"}, {"voter": "Mili\u010devi\u0107 Davor", "option": "+"}, {"voter": "Milinovi\u0107 Darko", "option": "+"}, {"voter": "Milo\u0161evi\u0107 Boris", "option": "+"}, {"voter": "Milo\u0161evi\u0107 Domagoj Ivan", "option": "+"}, {"voter": "Mrak-Tarita\u0161 Anka", "option": "+"}, {"voter": "Nin\u010devi\u0107-Lesandri\u0107 Ivana", "option": "+"}, {"voter": "Pari\u0107 Darko", "option": "+"}, {"voter": "Peri\u0107 Grozdana", "option": "+"}, {"voter": "Petrijev\u010danin Vuksanovi\u0107 Irena", "option": "+"}, {"voter": "Petrov Bo\u017eo", "option": "+"}, {"voter": "Podolnjak Robert", "option": "+"}, {"voter": "Prgomet Drago", "option": "+"}, {"voter": "Puh Marija", "option": "+"}, {"voter": "Pusi\u0107 Vesna", "option": "+"}, {"voter": "Radin Furio", "option": "+"}, {"voter": "Ragu\u017e \u017deljko", "option": "+"}, {"voter": "Reiner \u017deljko", "option": "+"}, {"voter": "Romi\u0107 Davor", "option": "+"}, {"voter": "Ronko Zdravko", "option": "+"}, {"voter": "Ro\u0161\u010di\u0107 Dragica", "option": "+"}, {"voter": "Runti\u0107 Hrvoje", "option": "+"}, {"voter": "Sanader Ante", "option": "+"}, {"voter": "Sin\u010di\u0107 Ivan", "option": "-"}, {"voter": "Sladoljev Marko", "option": "+"}, {"voter": "Strenja-Lini\u0107 Ines", "option": "+"}, {"voter": "Stri\u010dak An\u0111elko", "option": "+"}, {"voter": "\u0160imi\u0107 Marko", "option": "+"}, {"voter": "\u0160imi\u0107 Miroslav", "option": "+"}, {"voter": "\u0160ipi\u0107 Ivan", "option": "+"}, {"voter": "\u0160kibola Marin", "option": "-"}, {"voter": "\u0160kori\u0107 Petar", "option": "+"}, {"voter": "Topolko Bernarda", "option": "+"}, {"voter": "Totgergeli Miro", "option": "+"}, {"voter": "Tu\u0111man Miroslav", "option": "+"}, {"voter": "Turina-\u0110uri\u0107 Nada", "option": "+"}, {"voter": "Tu\u0161ek \u017darko", "option": "+"}, {"voter": "Varda Ka\u017eimir", "option": "+"}, {"voter": "Vu\u010deti\u0107 Marko", "option": "+"}, {"voter": "Zekanovi\u0107 Hrvoje", "option": "+"}]},
    {
     "type": "vote",
     "title": "PRIJEDLOG ODLUKE O IZBORU TRI SUCA USTAVNOG SUDA REPUBLIKE HRVATSKE - predlagatelj: Odbor za Ustav, Poslovnik i politi\u010dki sustav",
     "results_data": ["Rasprava je zaklju\u010dena 13. srpnja 2017.", "Na 5. sjednici 11. listopada 2017. za suce Ustavnog suda RH izabrani su: dr. sc. Miroslav \u0160eparovi\u0107 (118 glasova \"za\", 7 \"protiv\"); dr. sc. Mato Arlovi\u0107 (116 glasova \"za\", 9 \"protiv\"); dr. sc. Goran Selanec (118 glasova \"za\", 7 \"protiv\").", "O ovoj to\u010dki dnevnog reda o\u010ditovali su se:\r\n"],
     "parent": "http://www.sabor.hr/4-sjednica-hrvatskoga-sabora0001",
     "url": "http://www.sabor.hr/prijedlog-odluke-o-izboru-tri-suca-ustavnog-suda-r",
     "docs": [{"text": "PO IZBOR TRI SUCA USUD-a RH 2017.pdf",
               "url": "/fgs.axd?id=49907"},
              {"text": "AMANDMAN-Odbor za Ustav_izbor tri suca.pdf",
               "url": "/fgs.axd?id=50347"}]},

{"results_data": ["Rasprava je zaklju\u010dena 25. studenoga 2016.", "\nOdluka je donesena na 2. sjednici 25. studenoga 2016. (", ")."],
"results": "Ukupno: 94. Za: 77. Suzdr\u017ean: 8. Protiv: 9.",
"parent": "http://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax",
"type": "vote_ballots", "date": "25.11.2016.",
"ballots": [{"option": "-", "voter": "Aleksi\u0107 Goran"}, {"option": "+", "voter": "Ambru\u0161ec Ljubica"}, {"option": "+", "voter": "Anu\u0161i\u0107 Ivan"}, {"option": "+", "voter": "Ba\u010di\u0107 Branko"}, {"option": "+", "voter": "Bali\u0107 Marijana"}, {"option": "+", "voter": "Bari\u0161i\u0107 Dra\u017een"}, {"option": "+", "voter": "Batini\u0107 Milorad"}, {"option": "+", "voter": "Bauk Arsen"}, {"option": "o", "voter": "Bedekovi\u0107 Vesna"}, {"option": "+", "voter": "Beus Richembergh Goran"}, {"option": "+", "voter": "Bilek Vladimir"}, {"option": "+", "voter": "Bori\u0107 Josip"}, {"option": "+", "voter": "Bo\u0161njakovi\u0107 Dra\u017een"}, {"option": "+", "voter": "Brki\u0107 Milijan"}, {"option": "-", "voter": "Bulj Miro"}, {"option": "o", "voter": "Bunjac Branimir"}, {"option": "+", "voter": "Buri\u0107 Majda"}, {"option": "+", "voter": "Culej Stevo"}, {"option": "+", "voter": "\u010ci\u010dak Mato"}, {"option": "+", "voter": "\u0106osi\u0107 Pero"}, {"option": "-", "voter": "Dodig Goran"}, {"option": "+", "voter": "Dragovan Igor"}, {"option": "+", "voter": "\u0110aki\u0107 Josip"}, {"option": "+", "voter": "\u0110uji\u0107 Sa\u0161a"}, {"option": "+", "voter": "Felak Damir"}, {"option": "+", "voter": "Frankovi\u0107 Mato"}, {"option": "-", "voter": "Glasnovi\u0107 \u017deljko"}, {"option": "+", "voter": "Glasovac Sabina"}, {"option": "+", "voter": "Glava\u0161evi\u0107 Bojan"}, {"option": "+", "voter": "Hajdukovi\u0107 Domagoj"}, {"option": "+", "voter": "Horvat Darko"}, {"option": "+", "voter": "Horvat Mile"}, {"option": "+", "voter": "Hrg Branko"}, {"option": "+", "voter": "Jandrokovi\u0107 Gordan"}, {"option": "+", "voter": "Jankovics R\u00f3bert"}, {"option": "+", "voter": "Jeli\u0107 Damir"}, {"option": "+", "voter": "Jelkovac Marija"}, {"option": "+", "voter": "Josi\u0107 \u017deljka"}, {"option": "+", "voter": "Jovanovi\u0107 \u017deljko"}, {"option": "+", "voter": "Juri\u010dev-Martin\u010dev Branka"}, {"option": "+", "voter": "Kajtazi Veljko"}, {"option": "o", "voter": "Karli\u0107 Mladen"}, {"option": "+", "voter": "Kirin Ivan"}, {"option": "o", "voter": "Klari\u0107 Tomislav"}, {"option": "o", "voter": "Kliman Anton"}, {"option": "o", "voter": "Kosor Darinko"}, {"option": "+", "voter": "Kova\u010d Miro"}, {"option": "+", "voter": "Kristi\u0107 Maro"}, {"option": "o", "voter": "Kri\u017eani\u0107 Josip"}, {"option": "+", "voter": "Krstulovi\u0107 Opara Andro"}, {"option": "-", "voter": "Lackovi\u0107 \u017deljko"}, {"option": "+", "voter": "Lalovac Boris"}, {"option": "+", "voter": "Lekaj Prljaskaj Ermina"}, {"option": "+", "voter": "Luci\u0107 Franjo"}, {"option": "+", "voter": "Luka\u010di\u0107 Ljubica"}, {"option": "+", "voter": "Maksim\u010duk Ljubica"}, {"option": "-", "voter": "Mati\u0107 Predrag"}, {"option": "+", "voter": "Mesi\u0107 Jasen"}, {"option": "+", "voter": "Mikuli\u0107 Andrija"}, {"option": "+", "voter": "Mili\u010devi\u0107 Davor"}, {"option": "+", "voter": "Milinovi\u0107 Darko"}, {"option": "+", "voter": "Milo\u0161evi\u0107 Boris"}, {"option": "+", "voter": "Milo\u0161evi\u0107 Domagoj Ivan"}, {"option": "+", "voter": "Mrak-Tarita\u0161 Anka"}, {"option": "+", "voter": "Nin\u010devi\u0107-Lesandri\u0107 Ivana"}, {"option": "+", "voter": "Pari\u0107 Darko"}, {"option": "+", "voter": "Peri\u0107 Grozdana"}, {"option": "-", "voter": "Petin Ana-Marija"}, {"option": "+", "voter": "Petrijev\u010danin Vuksanovi\u0107 Irena"}, {"option": "+", "voter": "Podolnjak Robert"}, {"option": "+", "voter": "Prgomet Drago"}, {"option": "+", "voter": "Puh Marija"}, {"option": "+", "voter": "Pusi\u0107 Vesna"}, {"option": "+", "voter": "Radin Furio"}, {"option": "+", "voter": "Reiner \u017deljko"}, {"option": "+", "voter": "Romi\u0107 Davor"}, {"option": "+", "voter": "Ronko Zdravko"}, {"option": "+", "voter": "Ro\u0161\u010di\u0107 Dragica"}, {"option": "-", "voter": "Runti\u0107 Hrvoje"}, {"option": "+", "voter": "Sanader Ante"}, {"option": "+", "voter": "Saucha Tomislav"}, {"option": "+", "voter": "Sladoljev Marko"}, {"option": "+", "voter": "Strenja-Lini\u0107 Ines"}, {"option": "-", "voter": "Stri\u010dak An\u0111elko"}, {"option": "+", "voter": "\u0160imi\u0107 Marko"}, {"option": "+", "voter": "\u0160imi\u0107 Miroslav"}, {"option": "+", "voter": "Topolko Bernarda"}, {"option": "+", "voter": "Totgergeli Miro"}, {"option": "+", "voter": "Tu\u0111man Miroslav"}, {"option": "+", "voter": "Turina-\u0110uri\u0107 Nada"}, {"option": "+", "voter": "Tu\u0161ek \u017darko"}, {"option": "+", "voter": "Varda Ka\u017eimir"}, {"option": "+", "voter": "Vu\u010deti\u0107 Marko"}, {"option": "o", "voter": "Zekanovi\u0107 Hrvoje"}],
"title": "Izvje\u0161\u0107e Mandatno-imunitetnog povjerenstva o zahtjevu za davanje odobrenja za vo\u0111enje kaznenog postupka protiv STEVE CULEJA, zastupnika u Hrvatskom saboru",
"session_name": "2. sjednica Hrvatskoga sabora",
"docs": [{"url": "/sites/default/files/uploads/sabor/2019-01-18/081050/MIP_STEVO_CULEJ.pdf",
          "text": "MIP_STEVO_CULEJ.pdf"}],
"url": "http://itv.sabor.hr/video/glasovanje.aspx?ID=7995",
"time": "25.11.2016. 13:36"},

    """
    def __init__(self, data, reference):
        # call init of parent object
        super(BallotsParser, self).__init__(reference)

        self.source_data = data

        self.results_data = data['results_data']
        self.title = data['title']

        self.url = data['url']
        self.docs = data['docs']

        # prepere dictionarys for setters
        self.session_name = data['session_name'].split('.')[0]
        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
            "name": self.session_name
        }
        self.motion = {}
        self.vote = {}
        self.time_f = None

        # parse common data
        self.parse_title()
        self.set_fixed_data()

        self.ballots = None


        if data['type'] == 'vote':
            # parse vote without ballots

            if self.is_motion_saved():
                # vote allready exists
                # check if vote has ballots
                if get_vote_key(self.vote['name'], self.vote['start_time']) in self.reference.votes_without_ballots.keys():
                    if self.ballots:
                        vote_id = self.reference.votes_without_ballots[get_vote_key(self.vote['name'], self.vote['start_time'])]
                        self.parse_ballots(vote_id)

            else:
                #if len(self.results_data) > 2:
                #    # skip this shit
                #    raise ValueError("this edge case is stupid", self.url)
                # parse votes for////
                # ["Rasprava je zaklju\u010dena 27. listopada 2017.","Odluka je donesena na 5. sjednici 27. listopada 2017. (81 glas \"za\", 4 \"protiv\", 4 \"suzdr\u017eana\")"]
                self.parse_results()

                self.parse_time_from_result_data()
                self.parse_non_balots_balots(data)

                # run setters
                self.set_data()
                self.set_docs()
        else:
            # parse votes with ballots
            self.time = data['time']

            self.results = data['results']

            self.ballots = data['ballots']


            # parse data
            self.parse_time()


            if self.is_motion_saved():
                # TODO edit motion if we need it make force_render mode
                print("This motion is allready parsed")
                """
                self.parse_results()
                motion_id = self.get_motion_id()
                vote_id = self.get_vote_id()

                #print("patching motion", motion_id, 'and vote', vote_id)
                response = requests.patch(
                    API_URL + 'motions/' + str(motion_id) + '/',
                    json=self.motion,
                    auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                )
                #print(response.status_code)
                response = requests.patch(
                    API_URL + 'votes/' + str(vote_id) + '/',
                    json=self.vote,
                    auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                )
                #print(response.status_code)
                """
                # TODO Delete this. Is here just for reparse ballots.

                #self.parse_results()
                #self.set_docs()
            else:
                # add new motion
                self.parse_results()


                # run setters
                self.set_data()
                self.set_docs()

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

    def get_line_id(self, line_ids):
        if line_ids:
            if self.source_data['type'] == 'vote_ballots':
                offset = len(line_ids)-self.source_data['m_items']
                return (line_ids[self.source_data['c_item'] + offset] - 1)
            else:
                return line_ids[-1]
        else:
            return None

    def parse_results(self):
        def find_line_with_vote(data):
            founded = []
            voting_words = [
                'glas',
                'glasova',
                'glasa',
            ]
            i = 0
            found = None
            for i, line in enumerate(data):
                line = line.replace(',', '').replace(u'\xa0', ' ')
                splited_line = line.split(" ")
                for word in voting_words:
                    if word in splited_line:
                        found = i
                        founded.append(i)
            return founded

        data = self.results_data

        line_ids = find_line_with_vote(data)

        if line_ids == None:
            raise ValueError("DONT FIND VOTING DATA: ", data)

        line_id = self.get_line_id(line_ids)

        session_split = data[line_id].replace(',', '').split(" ")

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
            'odbijena',
            'povučen'
        ]
        result_idx = -1
        d_word = ''
        for word in decision_words:
            if word in session_split:
                d_word = word
                result_idx = session_split.index(word)
                break

        if result_idx < 0:
            print('###############')
            print('#############################################')
            print("DECISION FAIL: ", session_split, line_id, line_ids)
            print('#############################################')
            print('###############')
            self.vote['result'] = None
            self.vote['result'] = None
            return

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
                    #print("VOTE RESULT IS SOMETHING ELSE: ")


    def parse_time(self):
        self.time_f = datetime.strptime(self.time, "%d.%m.%Y. %H:%M")
        self.motion['date'] = self.time_f.isoformat()
        self.vote['start_time'] = self.time_f.isoformat()
        self.session['start_time'] = self.time_f.isoformat()

    def parse_title(self):
        self.motion['text'] = self.title.lower()
        self.motion['gov_id'] = self.url
        self.vote['name'] = self.title.lower()

        epa = find_epa_in_name(self.title)
        if epa:
            self.vote['epa'] = epa
            self.motion['epa'] = epa


    def parse_ballots(self, vote):
        #print("PARSe Ballots")
        # {"voter": "Aleksi\u0107 Goran", "option": "+"}
        option_map = {
            'o': 'abstain',
            '+': 'for',
            '-': 'against'
        }
        data = []
        members_on_vote = []
        # get vote
        for ballot in self.ballots:
            member = self.get_or_add_person(ballot['voter'])
            option = option_map[ballot['option']]
            #self.add_ballot(member, vote, option)

            voter_party_id = self.get_membership_of_member_on_date(str(member), self.time_f)
            if not voter_party_id:
                voter_party_id = self.reference.others

            temp ={
            'option': option,
            'vote': vote,
            'voter': member,
            'voterparty': voter_party_id
            }
            data.append(temp)
            members_on_vote.append(member)

        date_f = dt= datetime.strptime(self.reference.votes_dates[vote], "%Y-%m-%dT%H:%M:%S")
        mps = requests.get(API_URL + 'getMPs/' + date_f.strftime(API_DATE_FORMAT + 'T%H:%M')).json()
        for mp in mps:
            if mp['id'] not in members_on_vote:
                temp ={
                    'option': 'absent',
                    'vote': vote,
                    'voter': mp['id'],
                    'voterparty': self.reference.others
                }
                data.append(temp)
        #print("tuk je ballotov", len(data))
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
        vote_key = get_vote_key(self.vote['name'], self.vote['start_time'])
        vote_id, vote_status = self.add_or_get_vote(vote_key, self.vote)

        if not vote_id in self.reference.votes_dates.keys():
            self.reference.votes_dates[vote_id] = self.time_f.isoformat()

        if self.ballots:
            self.parse_ballots(vote_id)

    def set_docs(self):
        motion_id, motion_status = self.add_or_get_motion(
            self.url,
            self.motion
        )
        for doc in self.docs:
            data = {'url': 'http://www.sabor.hr'+doc['url'],
                    'name': doc['text'],
                    'motion': motion_id}
            self.add_link(data)

    def parse_time_from_result_data(self):
        time = datetime.strptime(self.source_data['date'], API_DATE_FORMAT+'.')
        self.time_f = time
        self.motion['date'] = time.isoformat()
        self.vote['start_time'] = time.isoformat()
        self.session['start_time'] = time.isoformat()


    def parse_non_balots_balots(self, data):
        # for votes where vote by hand :)
        opt_map = {
            "suzdr\u017eana": "abstain",
            "za": "for",
            "protiv": "against",
        }
        r=re.compile(r'\(.*\)')
        text = self.results_data
        #print(len(text))
        if len(text)>1 and '(' in text[1]:
            data = r.search(text[1]).group(0)
        else:
            data = r.search(text[0]).group(0)
        data = data.replace('(','').replace(')','').replace(u'\xa0', ' ')
        splited = data.split(' ')
        j_data = {}
        if 'jednoglasno' in data:
            i=3
            if splited[3] in ['glas', 'glasova']:
                i=4
            option = replace_nonalphanum(splited[i])
            votes = splited[1]

            j_data = {opt_map[option]: votes}

        else:
            #parse others
            # (81 glas \"za\", 4 \"protiv\", 4 \"suzdr\u017eana\")
            votes = 0
            option = ''
            for token in splited:
                token = replace_nonalphanum(token)
                if token.isalpha():
                    if token in opt_map.keys():
                        option = token
                        j_data[opt_map[option]] = votes
                if token.isdigit():
                    votes = int(token)

        self.vote['counter'] = json.dumps(j_data)

def replace_nonalphanum(word):
    word = re.sub(r'\W+', '', word)
    return word


def find_epa_in_name(name):
    search_epa = re.compile(r'(\d+)')
    if 'P.Z.' in name:
        new_text = name.split('P.Z.')[1]
        a = search_epa.search(new_text.strip())
        if a:
            #print(a.group(0))
            return a.group(0)
    return None
