from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from .utils import parse_date
from datetime import datetime
import re

date_regex = r'\d{2}.\d{2}.\d{4}.'
special_date_regex = r'\d{1,2}. ([a-zA-Zčšžćđ]+\s)*[a-zA-Zčšžćđ]+ \d{4}.'

roles = {
    '\u010clanovi': 'member',
    'Potpredsjednica': 'vice president',
    'Potpredsjednici': 'vice president',
    'Potpredsjednik': 'vice president',
    'Predsjednik': 'president',
    'Predsjednica': 'president'
}

class PersonParser(BaseParser):
    def __init__(self, data, reference):
        # call init of parent object
        {
            "role": "Predsjednica",
            "image": "/sites/default/files/uploads/sabor/2020-07-29/153004/Jeckov_Dragana.jpeg",
            "name": "Dragana Jeckov",
            "club_acronym": "(SDSS)",
            "zivotopis": "Ro\u0111ena je 8. srpnja 1976. u Vinkovcima. Zavr\u0161ila Fakultet za obrazovanje diplomiranih pravnika i diplomiranih ekonomista za rukovode\u0107e kadrove na Privrednoj akademiji u Novome Sadu, Srbija (VSS - diplomirana pravnica).",
            "area": "XII. izborna jedinica",
            "start_date": "22.07.2020.",
            "mandates": 2,
            "stranka": "Samostalna demokratska srpska stranka"
        }
        super(PersonParser, self).__init__(reference)
        self.name = data['name'] 
        self.area = data['area']
        self.zivotopis = data['zivotopis']
        self.party = data['stranka']
        self.club_acronym = data['club_acronym']
        self.club = data['club']
        self.role = data['role']
        self.wbs = data['wbs'] if 'wbs' in data.keys() else []

        if 'mandates' in data.keys():
            self.num_of_prev_mandates = int(data['mandates'])
        else:
            self.num_of_prev_mandates = 1

        matches = re.search(special_date_regex, self.zivotopis.replace('\xa0', ' '))
        date_string = matches[0]

        try:
            self.birth_date = parse_date(date_string).isoformat()
        except:
            self.birth_date = None

        try:
            self.start_time = datetime.strptime(data['start_date'], '%d.%m.%Y')
        except:
            self.start_time = self.reference.mandate_start_time.isoformat()

        # prepere dictionarys for setters
        self.person = {}
        self.area_data = {
            "name": data['area'],
            "calssification": "district"
        }

        if self.get_person_id(self.name):
            print('pass')
            pass
        else:
            self.get_person_data()

    def get_person_data(self):
        #edu = parse_edu(self.education)
        area_id, method = self.add_or_get_area(self.area_data['name'], self.area_data)
        if area_id:
            area = [area_id]
        else:
            area = []

        person_id = self.get_or_add_person(
            self.name,
            districts=area,
            mandates=self.num_of_prev_mandates,
            #education=edu,
            #birth_date=self.birth_date
        )

        party_id = self.add_organization(self.party, "party")

        membership_id = self.add_membership(person_id, party_id, roles.get(self.role, 'member'), 'cl', self.start_time)

        club_id = self.add_organization(self.club, "party")

        membership_id = self.add_membership(person_id, 1, 'voter', 'v', self.start_time, on_behalf_of=club_id)

        for wb in self.wbs:
            wb_id = self.add_organization(wb['commitee'], 'commitee')
            # TODO
            if wb['date_from']:
                matches = re.search(date_regex, wb['date_from'])
                date_string = matches[0]

                start_time = datetime.strptime(date_string, '%d.%m.%Y.').isoformat()
            else:
                start_time = self.reference.mandate_start_time.isoformat()

            if wb['commitee'] != 'Sabor':
                membership_id = self.add_membership(person_id, wb_id, 'member', 'cl', start_time)
                voter_id = self.add_membership(person_id, wb_id, 'voter', 'cl', start_time, on_behalf_of=club_id)

