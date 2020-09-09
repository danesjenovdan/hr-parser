from .base_parser_37 import BaseParser37
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests

class SpeechParser(BaseParser37):
    def __init__(self, data, reference):
        """{"date": "20.04.2018.",
        "session_ref": ["Saziv: IX, sjednica: 8"],
        "content_list": ["Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254", "Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254"],
        "speaker": ["Brki\u0107, Milijan (HDZ)"],
        "order": 1,
        "content": "Prelazimo na sljede\u0107u to\u010dku dnevnog reda, Prijedlog Zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na RH, prvo \u010ditanje, P.Z. br. 254.\nPredlagatelj je zastupnik kolega Robert Podolnjak na temelju \u010dlanka 85. Ustava RH i \u010dlanka 172. Poslovnika Hrvatskog sabora.\nPrigodom rasprave o ovoj to\u010dki dnevnog reda primjenjuju se odredbe Poslovnika koji se odnose na prvo \u010ditanje zakona.\nRaspravu su proveli nadle\u017eni Odbor za zakonodavstvo, nadle\u017eni Odbor za obrazovanje, znanost i kulturu.\nVlada je dostavila svoje mi\u0161ljenje.\nPozivam po\u0161tovanog kolegu gospodina Roberta Podolnjaka da nam da dodatno obrazlo\u017eenje prijedloga Zakona.\nIzvolite."},
        """
        # call init of parent object
        speeches = data['speeches']
        super(SpeechParser, self).__init__(reference)

        self.speeches = []

        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
        }
        # get and set session
        session = data['session_ref'][0].split(':')[-1].strip()
        self.session_ref = data
        session = session + ". sjednica"
        self.session['name'] = session
        self.session_id, session_status = self.add_or_get_session(session, self.session)

        self.date = datetime.strptime(data['date'], API_DATE_FORMAT + '.')

        self.gov_id = data['agenda_id']

        self.agenda_ids = []
        methods = []
        for ai in data['agendas']:
            agenda_text = ai['text']
            ai_order = ai['order'] if ai['order'].isdigit() else None
            agenda_key = get_vote_key(agenda_text.strip(), self.date.isoformat())
            agenda_json = {
                "name": agenda_text.strip(),
                "date": self.date.isoformat(),
                "session": self.session_id,
                "order": self.gov_id,
                "gov_id": self.gov_id
            }
            agenda_id, agenda_method = self.get_agenda_item(agenda_key, agenda_json)
            self.agenda_ids.append(agenda_id)
            #print(agenda_method, agenda_text.strip())
            methods.append(agenda_method)

        # skip addins speeches if some agenda_item already exists
        if not 'get' in methods:
            #print("SETTING", self.session_id)
            for speech in speeches:

                self.speaker = speech['speaker']
                self.order = speech['order']
                self.content = speech['content']
                # SPEECH

                self.speech = {'session': self.session_id}

                self.parse_time()
                self.set_data()
            response = requests.post(API_URL + 'speechs/',
                                     json=self.speeches,
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
            if response.status_code == 400:
                print(response.content)
        elif agenda_method == 'fail':
            print('agenda item set failed')
        else:
            #print('this agenda item allready parsed')
            pass

    def parse_time(self):
        self.speech['valid_from'] = self.date.isoformat()
        self.speech['start_time'] = self.date.isoformat()
        self.speech['valid_to'] = datetime.max.isoformat()

    def set_data(self):
        self.speech['content'] = self.content
        self.speech['order'] = self.order

        self.speech['agenda_items'] = self.agenda_ids

        # get and set speaket
        speaker, pg = self.parse_edoc_person(self.speaker[0])
        speaker_id = self.get_or_add_person(speaker)

        party_id = self.get_membership_of_member_on_date(str(speaker_id), self.date)

        if not party_id:
            party_id = self.reference.others

        self.speech['party'] = party_id
        self.speech['speaker'] = speaker_id

        self.speeches.append(self.speech)
