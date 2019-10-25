from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests


options_map = {
    'donesen': 'enacted',
    'dostavljeno radi informiranja': 'submitted',
    'odbijen': 'rejected',
    'povučen': 'retracted',
    'prihvaćen': 'adopted',
    'prima se na znanje': 'received',
    'u proceduri': 'in_procedure',
}


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
            #"remark": ["Dana 02. listopada 2019. predlagatelj je povukao Prijedlog odluke iz procedure."],
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
            if data['remark']:
                special_date = data['remark'][0].split(' ')[1:4]
                day = re.sub('[^A-Za-z0-9]+', '', special_date[0])
                month = self.get_month_by_name(special_date[1])
                year = re.sub('[^A-Za-z0-9]+', '', special_date[2])
                self.date = datetime(day=int(day), month=int(month), year=int(year))
            else:
                self.date = None

        self.mdt = data['mdt'][0]
        self.session_name = data['ref_ses'][0].split('-')[1]
        if '.' in self.session_name:
            self.session_name = self.session_name.replace('.', '')

        # break if not session name
        if not self.session_name:
            return
        self.results = data['result'][0]
        self.pdf = data['pdf'][0]
        self.status = data['status'][0]
        self.epa = data['epa'][0] if data['epa'] else None
        self.uid = data['uid']
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
            self.add_act(self.uid, self.act)
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
        self.act['epa'] = self.epa
        self.act['uid'] = self.uid
        self.act['classification'] = 'zakon' if self.epa else 'akt'

        #if 'Vlada HR' in self.mdt:
        #    self.mdt = self.mdt.replace('HR')

        mdt_fk = self.add_organization(self.mdt.strip(), '', create_if_not_exist=False)
        self.act['mdt_fk'] = mdt_fk
        self.act['procedure_phase'] = self.status
        """
        statuses = {
            'odbijen': 'end_of_hearing',
            'prihvaćen': 'under_consideration',
            'donesen': 'end_of_hearing',
            'prima se na znanje': 'end_of_hearing',
            }
        """

        try:
            self.act['status'] = options_map[self.status]
        except:
            self.act['status'] = 'under_consideration'

        self.act['procedure_phase'] = self.status
        """
        options = {
            'odbijen': 'rejected',
            'prihvaćen': None,
            'donesen': 'accepted',
            'prima se na znanje': 'accepted',
            }
        """
        try:
            self.act['result'] = options_map[self.status]
        except:
            self.act['result'] = ''

        if self.act['result'] in ['accepted', 'rejected']:
            self.act['procedure_ended'] = True

        self.act['date'] = self.date.isoformat()
        self.act['procedure'] = self.voting

    def act_status(self):
        if self.uid.strip() in self.reference.acts.keys():
            act = self.reference.acts[self.uid]
            if act['ended']:
                return 'ended'
            else:
                return 'in process'
        else:
            return 'unknown'


    def add_act(self, uid, json_data):
        act_id, method = self.api_request('law/', 'acts', uid, json_data)
        if 'procedure_ended' in json_data.keys():
            ended = True
        else:
            ended = False
        self.reference.acts[uid] = {"id": act_id, "ended": ended}

    def get_month_by_name(name):
        month_names = [
            'siječanja',
            'veljače',
            'ožujka',
            'travnja',
            'svibnja',
            'lipnja',
            'srpnja',
            'kolovoza',
            'rujna',
            'listopada',
            'studenoga',
            'prosinca'
        ]
        return month_names.index(name) + 1
