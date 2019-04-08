from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from .utils import fix_name
from pprint import pprint
import re


class QuestionParser(BaseParser):
    def __init__(self, data, reference):
        #print('\n'*5)
        #print('='*50, ' QuestionParser ', '='*50)
        #pprint(data)
        #print('='*50, ' ============== ', '='*50)

        # call init of parent object
        super(QuestionParser, self).__init__(reference)

        # copy item to object
        self.authors = data['authors']
        self.title = data['title']
        self.signature = data['signature'].strip()
        self.date = data['date']
        self.recipient = data['asigned']
        self.links = data['docs']
        self.parties = data['parties']
        self.session = data.get('session', None)

        # prepere dictionarys for setters
        self.question = {}
        self.date_f = None

        if self.is_question_saved():
            # TODO edit question if we need it make force_render mode
            print("This question is already parsed")

        else:
            # parse data
            self.parse_time()
            self.parse_data()

    def is_question_saved(self):
        return self.signature in self.reference.questions.keys()

    def get_question_id(self):
        return self.reference.questions[self.signature]

    def parse_time(self):

        self.date_f = datetime.strptime(self.date, "%Y-%m-%d")
        self.question['date'] = self.date_f.isoformat()

    def parse_data(self):
        self.question['signature'] = self.signature
        self.question['title'] = self.title

        if not self.authors:
            #print('************** self.author is empty')
            pass
        else:
            author_ids = []
            author_org_ids = []
            for author in self.authors:
                author_id = self.get_or_add_person(
                    fix_name(author),
                )
                author_ids.append(author_id)

            for party in self.parties:
                party_id = self.add_organization(party, 'party')
                author_org_ids.append(party_id)

            self.question['authors'] = author_ids
            self.question['author_orgs'] = author_org_ids
            self.question['recipient_text'] = self.recipient

            # TODO parse recipients
            #self.question['recipient_person'] = [recipient_id]
            #self.question['recipient_organization'] = [recipient_party_id]


            # send question
            question_id, method = self.add_or_get_question(self.question['signature'], self.question)

            # send link
            if method == 'set' and self.links:
                for link in self.links:
                    if link['url']:
                        if 'Besedilo' in link['title']:
                            link['question'] = question_id
                            link['note'] = link['title']
                            self.add_link(link)
