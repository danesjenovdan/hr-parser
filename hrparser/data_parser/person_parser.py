from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from .utils import parse_date
from datetime import datetime

class PersonParser(BaseParser):
    def __init__(self, data, reference):
        # call init of parent object
        super(PersonParser, self).__init__(reference)
        self.name = item['name'] 
        self.area = item['area']
        self.education = item['education']
        self.party = item['party']
        self.wbs = item['wbs']

        if 'num_of_prev_mandates' in item.keys():
            self.num_of_prev_mandates = int(item['num_of_prev_mandates']) + 1
        else:
            self.num_of_prev_mandates = 1

        try:
            self.birth_date = parse_date(item['birth_date']).isoformat()
        except:
            self.birth_date = None

        try:
            self.start_time = parse_date(item['start_time']).isoformat()
        except:
            self.start_time = self.reference.mandate_start_time.isoformat()

        # prepere dictionarys for setters
        self.person = {}
        self.area_data = {
            "name": item['area'],
            "calssification": "district"
        }

        if self.get_person_id(self.name):
            print('pass')
            pass
        else:
            self.get_person_data()

    def get_person_data(self):
        edu = parse_edu(self.education)
        area_id, method = add_or_get_area(item['area'], self.area_data)
        if area_id:
            area = [area_id]
        else:
            area = []

        person_id = self.get_or_add_person(
            fix_name(self.name),
            districts=area,
            mandates=self.num_of_prev_mandates,
            education=edu,
            birth_date=self.birth_date
        )

        party_id = self.add_organization(self.party, "party")

        membership_id = self.add_membership(person_id, party_id, 'member', 'cl', start_time)

        if 'wbs' in item.keys():
            for wb in self.wbs:
                wb_id = self.add_organization(wb['org'], 'committee')
                self.add_membership(
                    person_id,
                    wb_id,
                    wb['role'],
                    wb['role'],
                    self.reference.mandate_start_time.isoformat()
                )
