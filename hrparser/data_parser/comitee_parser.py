# uncompyle6 version 3.7.3
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.8.2 (default, Jul 16 2020, 14:00:26) 
# [GCC 9.3.0]
# Embedded file name: /home/tomaz/dev/DJND/hrparser/hrparser/data_parser/comitee_parser.py
# Compiled at: 2020-02-27 15:43:22
# Size of source mod 2**32: 14374 bytes
from .base_parser_37 import BaseParser37
from .utils import get_vote_key
from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from datetime import datetime, timedelta
import requests, re, json
PARSE_JUST_NEW_VOTES = False
options_map = {'donesen':'enacted',
 'dostavljeno radi informiranja':'submitted',
 'odbijen':'rejected',
 'povučen':'retracted',
 'prihvaćen':'adopted',
 'prima se na znanje':'received',
 'u proceduri':'in_procedure'}

class ComiteeParser(BaseParser37):
    zakljucak_reg = '\\s*z\\s*a\\s*k\\s*l\\s*j\\s*u\\s*č\\s*a\\s*k\\s*'
    order_number = '^[0-9]{1,2}([,.])'
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

    def __init__(self, data, reference):
        super(ComiteeParser, self).__init__(reference)
        self.data = data
        print(data)
        if 'wb_title' in self.data.keys():
            print('\033[93m 111111111111111 \033[0m')
            if self.data['wb_title'].startswith('Nastavak'):
                print('\n NASTAVAK \n')
                return
        if self.data['type'] == 'session_vote_texts':
            print("\033[93m session votes text \033[0m")
            self.parse_org_and_session_name()
            self.parse_results()
            self.parse_session_notes()
        else:
            print("\033[93m 22222222222 \033[0m")
            if self.data['type'] == 'calendar_session':
                print('calendar_session')
                self.parse_org_and_session_name()
                self.parse_agenda_items()
            else:
                print("\033[93m \n MEMS \n \033[0m")
                if self.data['type'] == 'wb_membership':
                    self.parse_membership()
                else:
                    print('WTF')

    def parse_membership(self):
        membership = {}
        membership['organization'] = self.org_id = self.add_organization((self.data['wb_title'].strip()), classification='committee', orgs='orgs')
        membership['member'] = self.get_or_add_person(self.data['name'].strip().replace(',', ''))
        membership['role'] = self.data['role']
        self.add_membership(membership['member'], membership['organization'], membership['role'], '', self.reference.mandate_start_time.isoformat())
        self.add_membership(membership['member'], membership['organization'], 'voter', '', self.reference.mandate_start_time.isoformat())

    def parse_org_and_session_name(self):
        if self.data['type'] == 'calendar_session':
            if 'Odbora' in self.data['session_name']:
                self.data['session_name'] = self.data['session_name'].split('Odbora')[0].strip()
            else:
                if 'Mandatno-imunitetnog' in self.data['session_name']:
                    self.data['session_name'] = self.data['session_name'].split('Mandatno-imunitetnog')[0].strip()
        session_name = self.data['session_name']
        self.org_id = self.add_organization((self.data['wb_title'].strip()), classification='committee', orgs='orgs')
        session = {'name':session_name, 
         'organization':self.org_id, 
         'organizations':[
          self.org_id], 
         'start_time':self.get_date(), 
         'in_review':False}
        self.session_id, method = self.add_or_get_session(session_name, session)

    def get_date(self):
        if self.data['datetime_utc']:
            return self.data['datetime_utc']
        try:
            date = datetime.strptime(self.data['date'], '%d.%m.%Y.').isoformat()
        except:
            date = None

        return date

    def parse_agenda_items(self):
        if 'agenda_items' in self.data.keys():
            i = 1
            for item in self.data['agenda_items']:
                striped_text = item.strip()
                if re.search(self.order_number, striped_text):
                    striped_text = ''.join(striped_text.split('.')[1:])
                    if striped_text:
                        if striped_text[(-1)] == ';':
                            striped_text = striped_text[:-1]
                        self.get_agenda_item(str(self.session_id) + '--' + striped_text, {'name':striped_text, 
                         'session':self.session_id, 
                         'order':i, 
                         'date':self.data['datetime_utc']})
                        i += 1

    def parse_results(self):
        print('parse results')
        find_brackets = '\\((.*?)\\)'
        find_results = '\\(?(?P<number>\\d+)\\)? „?(?P<type_before>\\w*)“?? ?glas\\w* ?„?(?P<type_after>„?\\w*)“?'
        find_results = '\\(?(?P<number>\\d+)\\)? (glas\\w*)? ?[„\\"]?(\\b(za|protiv|suzdržan|suzdržana|suzdržanim|suzdržanih|susdržan|sudržan|suzdržani|suzdran)\\b)[“\\"]?'
        find_results = '\\(?(?P<number>\\d+)\\)? (glas\\w* )?[„\\"]? ?(za|protiv|su[zs]?dr[zž]?an\\w*)[“\\"]?'
        self.counters = {}
        self.result = None
        self.all_in = False
        match = None
        if self.data['item_text']:
            for paragraph in self.data['item_text']:
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
                        option = self.options[option.lower()]
                        self.counters.update({option: votes})
                        option = None
                        votes = None

                if match:
                    self.result = self.find_result(paragraph)
                    if self.counters:
                        if 'jednoglasno' in paragraph.lower():
                            self.all_in = True
                    if self.counters:
                        break
                match = None
                if 'jednoglasno podupire donošenje' in paragraph or 'jednoglasno je odlučio predložiti' in paragraph:
                    self.all_in = True
                    self.result = '1'

            print(self.counters, 'result:', self.result, 'all_in: ', self.all_in)

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
         'podržao',
         'prihvati',
         'predložiti',
         'većinom glasova']
        for word in negative_words:
            if word in text:
                return '0'

        for word in positive_words:
            if word in text:
                return '1'

    def parse_session_notes(self):
        print("parse votes")
        """
        {
            "type": "session_vote_texts",
            "session_name": "54., zatvorena, sjednica Odbora za vanjsku politiku",
            "item_title": "Izvješće Odbora za prostorno uređenje i graditeljstvo s rasprave o Konačnom prijedlogu zakona o izmjenama i dopuni Zakona o izvršavanju Državnog proračuna Republike Hrvatske za 2016. godinu, P.Z. br. 33",
            "item_text": ["Odbor za prostorno uređenje i graditeljstvo Hrvatskoga sabora, na prvoj sjednici održanoj 23. studenoga 2016. godine, raspravljao je o Konačnom prijedlogu zakona o izmjenama i dopuni Zakona o izvršavanju Državnog proračuna Republike Hrvatske za 2016. godinu koji je predsjedniku Hrvatskoga sabora dostavila Vlada Republike Hrvatske, aktom od 21. studenoga 2016. godine.", "Odbor za prostorno uređenje i graditeljstvo, na temelju članka 179. Poslovnika Hrvatskoga sabora, raspravio je navedeni akt kao zainteresirano radno tijelo.", "Uvodno obrazloženje osnovnih odrednica ovog Konačnog prijedloga zakona o izmjenama i dopuni Zakona o izvršavanju Državnog proračuna Republike Hrvatske za 2016. godinu iznijeli su predstavnici Ministarstva financija. ", "Istaknuli su da se ovim Konačnim prijedlogom zakona mijenja iznos proračunske zalihe sa 200 milijuna kuna\xa0 na 230 milijuna, smanjuje\xa0 iznos zaduživanja na inozemnom i domaćem tržištu novca i kapitala, povećavaju tekuće otplate glavnice duga, te povećava ukupna visina zaduženja i tekuće otplate za izvanproračunske korisnike državnog proračuna.", "Predstavnici ministarstva obrazložili su drugačiji način dodjele pomoći iz državnog proračuna jedinicama lokalne i područne (regionalne) samouprave sa statusom potpomognutog područja i to obrnuto proporcionalno njihovom indeksu razvijenosti. ", "Za jedinice lokalne samouprave sa statusom brdsko planinskih područja čija vrijednost indeksa razvijenosti prelazi 75% prosjeka Republike Hrvatske ovaj Konačni prijedlog zakona\xa0 propisuje da se izračunati iznos pomoći umanjuje za iznos razlike prihoda od poreza na dohodak koji te jedinice ostvaruju sukladno Zakonu o izmjenama Zakona o financiranju jedinica lokalne i područne (regionalne) samouprave te prihoda koje bi ostvarile temeljem osnovne raspodjele prihoda od poreza na dohodak propisane navedenim Zakonom. Pomoć koja se ovim izmjenama dodjeljuje jedinicama lokalne i područne (regionalne) samouprave iz razdjela Ministarstva financija iznosit će 694,8 milijuna kuna, što znači povećanje od 20 milijuna kuna.", "U raspravi se od strane članova Odbora s postavilo pitanje koji su to još kriteriji, osim indeksa razvijenosti, na temelju kojih se, ovim Konačnim prijedlogom zakona, mijenja način dodjele pomoći iz državnog proračuna jedinicama lokalne i područne (regionalne) samouprave.", "Ova je mjera u raspravi ocijenjena kao palijativna mjera pomoći lokalnim jedinicama koje imaju manjak sredstava u svojim proračunima.", "Postavljeno je i pitanje dostatnosti predviđenih sredstava za ovako propisan način dodjele pomoći jedinicama lokalne i područne (regionalne) samouprave, s obzirom da se isto potencijalno može odnositi na veliki broj lokalnih jedinica.", "Nakon provedene rasprave, Konačni prijedlog zakona o izmjenama i dopuni Zakona o izvršavanju Državnog proračuna Republike Hrvatske za 2016. godinu\xa0 nije dobio potrebnu većinu glasova nazočnih članova Odbora (5 glasova za, 4 glasa protiv, 1 glas suzdržan).", "                          ", "Za izvjestiteljicu na sjednici Hrvatskoga sabora Odbor je odredio predsjednicu Odbora, Anku Mrak-Taritaš.", "                               ", "PREDSJEDNICA ODBORA", "Anka Mrak-Taritaš"],
        }"""
        motion = {}
        vote = {}
        if not self.data['item_title']:
            return
        epa = self.find_epa_in_name(self.data['item_title'])
        if self.all_in:
            if self.counters:
                voters_count = len(self.reference.commitees_members[self.org_id])
                attended = sum(self.counters.values())
                absent = voters_count - attended
                self.counters['absent'] = absent
                for option in self.options.values():
                    if option not in self.counters.keys():
                        self.counters[option] = 0

        motion['party'] = self.reference.others
        motion['epa'] = epa
        motion['result'] = self.result if epa else '1'
        motion['date'] = self.get_date()
        motion['text'] = self.data['item_title'].strip()
        motion['gov_id'] = self.data['url']
        motion['session'] = self.session_id
        vote['session'] = self.session_id
        vote['name'] = self.data['item_title'].strip()
        self.data['datetime_utc'] = None
        vote['start_time'] = self.get_date()
        vote['counter'] = json.dumps(self.counters)
        vote['organization'] = self.reference.others
        motion_id, motion_status = self.add_or_get_motion(self.data['url'].split('//')[1], motion)
        vote['motion'] = motion_id
        vote_id, vote_status = self.add_or_get_vote(motion_id, vote)
        if vote_id not in self.reference.votes_dates.keys():
            self.reference.votes_dates[vote_id] = self.get_date()
# okay decompiling comitee_parser.cpython-37.pyc
