from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests

class SpeechParser(BaseParser):
    def __init__(self, data, reference):
        """{"date": "20.04.2018.",
        "session_ref": ["Saziv: IX, sjednica: 8"],
        "content_list": ["Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254", "Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254"],
        "speaker": ["Brki\u0107, Milijan (HDZ)"],
        "order": 1,
        "content": "Prelazimo na sljede\u0107u to\u010dku dnevnog reda, Prijedlog Zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na RH, prvo \u010ditanje, P.Z. br. 254.\nPredlagatelj je zastupnik kolega Robert Podolnjak na temelju \u010dlanka 85. Ustava RH i \u010dlanka 172. Poslovnika Hrvatskog sabora.\nPrigodom rasprave o ovoj to\u010dki dnevnog reda primjenjuju se odredbe Poslovnika koji se odnose na prvo \u010ditanje zakona.\nRaspravu su proveli nadle\u017eni Odbor za zakonodavstvo, nadle\u017eni Odbor za obrazovanje, znanost i kulturu.\nVlada je dostavila svoje mi\u0161ljenje.\nPozivam po\u0161tovanog kolegu gospodina Roberta Podolnjaka da nam da dodatno obrazlo\u017eenje prijedloga Zakona.\nIzvolite."},
        """
        # call init of parent object        
        super(SpeechParser, self).__init__(reference)

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

        #if agenda_key not in self.reference.agenda_items.keys():
        agenda_json = {
            "name": agenda_text.strip(),
            "date": self.date.isoformat(),
            "session": session_id,
            "order": self.agenda_id
        }
        agenda_id = self.get_agenda_item(agenda_key, agenda_json)

        self.speech['agenda_item'] = agenda_id[0]

        # get and set speaket
        speaker, pg = self.parse_edoc_person(self.speaker[0])
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
        #else:
        #    print("Speech is allready parsed")