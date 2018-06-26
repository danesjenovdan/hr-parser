from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests

class ActParser(BaseParser):
    def __init__(self, data, reference):
        """
        {
            #"ref_ses": ["IX-2"],
            #"signature": ["IX-73/2016"],
            #"ballots": ["81/8/22"],
            #"pub_title": ["Odluka o davanju suglasnosti na Polugodi\u0161nji izvje\u0161taj o izvr\u0161enju Financijskog plana Dr\u017eavne agencije za osiguranje \u0161tednih uloga i sanaciju banaka za prvo polugodi\u0161te 2016. godine"],
            #"mdt": ["Vlada RH"],
            #"title": ["Polugodi\u0161nji izvje\u0161taj o izvr\u0161enju Financijskog plana Dr\u017eavne agencije za osiguranje \u0161tednih uloga i sanaciju banaka u prvom polugodi\u0161tu 2016. godine"],
            "voting": ["ve\u0107inom glasova"],
            #"pdf": ["../NewReports/GetReport.aspx?reportType=1&id=2020972&loggedInUser=False"],
            #"agenda_no": ["4."],
            #"date_vote": ["\r\n                        \r\n                        ", "25.11.2016.", "\r\n                        ", "\r\n                        ", "\r\n\t\t\t\t\t\r\n                            \r\n                            ", "\r\n                        \r\n\t\t\t\t", "\r\n                    "],
            #"result": ["81/8/22"],
            #"status": ["donesen i objavljen"],
            "dates": ["24.11.2016.; 25.11.2016."]},
        """
        # call init of parent object        
        super(ActParser, self).__init__(reference)


        self.title = data['title'][0]
        #self.pub_title = data['pub_title'][0]
        self.signature = data['signature'][0]
        #self.agenda_no = data['agenda_no'][0]

        print(self.signature)

        #self.text_date = ''.join(data['date_vote']).replace(',', '').strip()
        dates = filter(None, map(str.strip, data['date_vote']))
        try:
            self.date = max([datetime.strptime(date, API_DATE_FORMAT + '.')  for date in dates])
        except:
            self.date = datetime(day=1, month=1, year=2000)
        #self.date = datetime.strptime(self.text_date, API_DATE_FORMAT + '.')
        self.mdt = data['mdt'][0]
        self.session_name = data['ref_ses'][0].split('-')[1]
        if '.' in self.session_name:
            self.session_name = self.session_name.replace('.', '')
        self.results = data['result'][0]
        self.pdf = data['pdf'][0]
        self.status = data['status'][0]
        try:
            self.voting = data['voting'][0]
        except:
            self.voting = ''

        self.session = {
            "organization": self.reference.commons_id,
            "organizations": [self.reference.commons_id],
            "in_review": False,
            "name": self.session_name
        }

        self.act = {}

        act_api_status = self.act_status()
        if act_api_status == 'unknown':
            self.parse_data()
            #print(self.act)
            self.add_act(self.signature, self.act)
        elif act_api_status == 'in process':
            # TODO compare and edit
            self.parse_data()
        else:
            #print('law is finished')
            self.parse_data()
            pass

    def parse_data(self):
        session_id, session_status = self.add_or_get_session(self.session_name, self.session)

        self.act['session'] = session_id
        self.act['text'] = self.title
        self.act['mdt'] = self.mdt
        self.act['status'] = self.status
        self.act['epa'] = self.signature

        #if 'Vlada HR' in self.mdt:
        #    self.mdt = self.mdt.replace('HR')

        mdt_fk = self.add_organization(self.mdt.strip(), '', create_if_not_exist=False)
        self.act['mdt_fk'] = mdt_fk
        self.act['procedure_phase'] = self.status

        self.act['classification'] = 'akt'

        options = {
            'odbijen': '0',
            'prihvaćen': '1',
            'donesen': '1',
            'prima se na znanje': '2',
            }

        try:
            self.act['result'] = options[self.status]
        except:
            self.act['result'] = ''

        if self.act['result'] in ['0', '1']:
            self.act['procedure_ended'] = True

        self.act['date'] = self.date.isoformat()
        self.act['procedure'] = self.voting

    def act_status(self):
        if self.signature.strip() in self.reference.acts.keys():
            act = self.reference.acts[self.signature]
            if act['ended']:
                return 'ended'
            else:
                return 'in process'
        else:
            return 'unknown'


    def add_act(self, signature, json_data):
        act_id, method = self.api_request('law/', 'acts', signature, json_data)
        if 'procedure_ended' in json_data.keys():
            ended = True
        else:
            ended = False
        self.reference.acts[signature] = {"id": act_id, "ended": ended}





