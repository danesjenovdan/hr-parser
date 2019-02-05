from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from .utils import fix_name
from pprint import pprint
import re


class QuestionParser(BaseParser):
    base_url = 'http://parlament.ba'

    def __init__(self, data, reference):
        print('\n'*5)
        print('='*50, ' QuestionParser ', '='*50)
        pprint(data)
        print('='*50, ' ============== ', '='*50)

        # call init of parent object
        super(QuestionParser, self).__init__(reference)

        # copy item to object
        self.author = data['name']
        self.title = data['text']
        self.signature = data['ref']
        self.date = data['date']
        self.recipient = data['asigned']
        self.links = data['links']
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
        sp = self.date.split(',')
        date = sp[1].strip()
        self.date_f = datetime.strptime(date, "%d.%m.%Y.")
        self.question['date'] = self.date_f.isoformat()

    def parse_data(self):
        self.question['signature'] = self.signature
        self.question['title'] = self.title

        if not self.author.strip():
            print('************** self.author is empty')
        else:
            author_ids = []
            author_org_ids = []
            author_id = self.get_or_add_person(
                fix_name(self.author),
            )

            party_id = self.get_membership_of_member_on_date(str(author_id), self.date_f)

            author_ids.append(author_id)
            if party_id:
                author_org_ids.append(party_id)

            # for now is recipient_id None
            # recipient_id = None
            #recipient_id = self.get_or_add_person(recipient_pr)
            #if recipient_org:
            #    recipient_party_id = self.add_organization(recipient_org.strip(), 'gov')
            #else:
            #    recipient_party_id = None

            if self.session:
                session_name = self.session.split(',')
                session_id = self.reference.sessions_by_name.get(session_name[0].strip())
                if session_id:
                    self.question['session'] = session_id

            self.question['authors'] = author_ids
            self.question['author_orgs'] = author_org_ids
            self.question['recipient_text'] = self.recipient.strip()
            #self.question['recipient_person'] = [recipient_id]
            #self.question['recipient_organization'] = [recipient_party_id]

            print('*'*60)
            pprint(self.question)
            print('*'*60)

            # send question
            question_id, method = self.add_or_get_question(self.question['signature'], self.question)

            # send link
            if method == 'set' and self.links:
                for link in self.links:
                    if link['url']:
                        link['question'] = question_id
                        link['url'] = self.base_url + link['url']
                        self.add_link(link)
