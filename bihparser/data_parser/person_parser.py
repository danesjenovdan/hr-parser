from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from .utils import parse_date, fix_name
from datetime import datetime

class PersonParser(BaseParser):
    def __init__(self, item, reference):
        # call init of parent object
        super(PersonParser, self).__init__(reference)
        self.name = item['name'] 
        self.area = item['area']
        #self.education = item['education']
        self.party = item['party']
        self.wbs = item['wbs']
        print(self.name)
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
            self.get_person_data(item)

    def get_person_data(self, item):
        area_id, method = self.add_or_get_area(item['area'], self.area_data)
        if area_id:
            area = [area_id]
        else:
            area = []

        person_id = self.get_or_add_person(
            fix_name(self.name),
            districts=area,
            #mandates=self.num_of_prev_mandates,
            #education=edu,
            #birth_date=self.birth_date
        )

        party_id = self.add_organization(self.party, "party")

        membership_id = self.add_membership(person_id, party_id, 'member', 'cl', self.start_time)

        if 'wbs' in item.keys():
            for typ, names in self.wbs.items():
                for name in names:
                    wb_id = self.add_organization(name, typ)
                    self.add_membership(
                        person_id,
                        wb_id,
                        'member',
                        'member',
                        self.reference.mandate_start_time.isoformat()
                    )
