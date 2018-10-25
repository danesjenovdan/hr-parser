from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests

class SpeechParser(BaseParser):
    def __init__(self, list_data, reference):
        """{"date": "20.04.2018.",
        "session_ref": ["Saziv: IX, sjednica: 8"],
        "content_list": ["Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254", "Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254"],
        "speaker": ["Brki\u0107, Milijan (HDZ)"],
        "order": 1,
        "content": "Prelazimo na sljede\u0107u to\u010dku dnevnog reda, Prijedlog Zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na RH, prvo \u010ditanje, P.Z. br. 254.\nPredlagatelj je zastupnik kolega Robert Podolnjak na temelju \u010dlanka 85. Ustava RH i \u010dlanka 172. Poslovnika Hrvatskog sabora.\nPrigodom rasprave o ovoj to\u010dki dnevnog reda primjenjuju se odredbe Poslovnika koji se odnose na prvo \u010ditanje zakona.\nRaspravu su proveli nadle\u017eni Odbor za zakonodavstvo, nadle\u017eni Odbor za obrazovanje, znanost i kulturu.\nVlada je dostavila svoje mi\u0161ljenje.\nPozivam po\u0161tovanog kolegu gospodina Roberta Podolnjaka da nam da dodatno obrazlo\u017eenje prijedloga Zakona.\nIzvolite."},
        """
        # call init of parent object 
        list_data = list_data['speeches']
        super(SpeechParser, self).__init__(reference)

        self.speeches = []

        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
        }
        # get and set session
        session = list_data[0]['session_ref'][0].split(':')[-1].strip()
        self.session['name'] = session
        self.session_id, session_status = self.add_or_get_session(session, self.session)

        date = datetime.strptime(list_data[0]['date'], API_DATE_FORMAT + '.')

        agenda_text = ' '.join(list_data[0]['content_list'])
        agenda_key = get_vote_key(agenda_text.strip(), date.isoformat())

        self.agenda_order = list_data[0]['agenda_id']

        agenda_json = {
            "name": agenda_text.strip(),
            "date": date.isoformat(),
            "session": self.session_id,
            "order": self.agenda_order
        }
        self.agenda_id, agenda_method = self.get_agenda_item(agenda_key, agenda_json)

        print(agenda_method, agenda_text.strip())

        if agenda_method == 'set':
            print("SETTING", self.session_id)
            for data in list_data: 

                self.date = data['date']
                self.session_ref = data['session_ref']
                self.content_list = data['content_list']
                self.speaker = data['speaker']
                self.order = data['order']
                self.content = data['content']
                # SPEECH

                self.speech = {'session': self.session_id}

                self.parse_time()
                self.set_data()
            response = requests.post(API_URL + 'speechs/',
                                     json=self.speeches,  
                                     auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                    )
        elif agenda_method == 'fail':
            print('agenda item set failed')
        else:
            print('this agenda item allready parsed')
        
    def parse_time(self):
        self.date = datetime.strptime(self.date, API_DATE_FORMAT + '.')
        self.speech['valid_from'] = self.date.isoformat()
        self.speech['start_time'] = self.date.isoformat()
        self.speech['valid_to'] = datetime.max.isoformat()

    def set_data(self):
        self.speech['content'] = self.content
        self.speech['party'] = self.reference.commons_id
        self.speech['order'] = self.order

        self.speech['agenda_item'] = self.agenda_id

        # get and set speaket
        speaker, pg = self.parse_edoc_person(self.speaker[0])
        speaker_id = self.get_or_add_person(speaker)

        party_id = self.get_membership_of_member_on_date(str(speaker_id), self.date)

        if not party_id:
            party_id = self.reference.others

        self.speech['party'] = party_id
        self.speech['speaker'] = speaker_id

        self.speeches.append(self.speech)