from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime

class QuestionParser(BaseParser):
    def __init__(self, data, reference):
        # call init of parent object
        super(QuestionParser, self).__init__(reference)
        """
        {
            #"recipient": ["Plenkovi\u0107, Andrej / Predsjednik Vlade RH; "],
            #"field": ["Prestanak dru\u0161tava; "],
            #"link": ["../NewReports/GetReport.aspx?reportType=5&id=8561&pisaniOdgovor=False&opis=False"],
            #"date": ["11.4.2018."],
            #"author": ["Bulj, Miro (MOST)"],
            #"title": "Zastupni\u010dko pitanje ",
            #"typ": ["na 8. sjednici"],
            #"signature": [],
            X"ref": ["IX"]},

            send link
        """
        # copy item to object
        self.author = data['author'][0]
        self.title = data['title']
        self.ref = data['ref'][0]
        self.date = data['date'][0]
        self.typ = data['typ'][0]
        self.recipient = data['recipient'][0]
        self.field = data['field'][0]
        self.signature = data['edoc_url'].split('=')[1]
        self.edoc_url = data['edoc_url']
        if data['link']:
            self.url = data['link'][0]
        else:
            self.url = None
        #print(data['typ'])
        if data['answear']:
            self.answear = data['answear'][0]
            #print(data['answear'])
        else:
            self.answear = None

        # prepere dictionarys for setters
        self.question = {}
        self.link = {}
        self.date_f = None

        if self.is_question_saved():
            # TODO edit question if we need it make force_render mode
            #print("This question is allready parsed")
            pass
        else:
            # parse data
            self.parse_time()
            self.parse_data()

    def is_question_saved(self):
        return self.signature in self.reference.questions.keys()

    def get_question_id(self):
        return self.reference.questions[self.signature]


    def parse_time(self):
        self.date_f = datetime.strptime(self.date, "%d.%m.%Y.")
        self.question['date'] = self.date_f.isoformat()
        self.link['date'] = self.date_f.strftime("%Y-%m-%d")

    def parse_data(self):
        if self.url:
            self.link['url'] = "http://edoc.sabor.hr/Views/" + self.url
            self.link['name'] = self.title

        self.question['signature'] = self.signature

        self.question['title'] = self.field + ' | ' + self.title
        
        author_prs = []
        author_orgs = []
        authors = self.author.split(';')
        for author in authors:
            author_pr, author_org = self.parse_edoc_person(author)
            author_prs.append(author_pr)
            author_orgs.append(author_org)

        recipient_pr, recipient_org = self.parse_edoc_person(self.recipient)

        author_ids = []
        author_org_ids = []
        for author_pr in author_prs:
            author_id = self.get_or_add_person(author_pr)
            author_org_id = self.get_membership_of_member_on_date(str(author_id), self.date_f)
            author_ids.append(author_id)
            author_org_ids.append(author_org_id)


        recipient_id = self.get_or_add_person(recipient_pr)
        if recipient_org:
            recipient_party_id = self.add_organization(recipient_org.strip(), 'gov')
        else:
            recipient_party_id = None

        self.question['authors'] = author_ids
        self.question['author_orgs'] = author_org_ids
        self.question['recipient_person'] = [recipient_id]
        self.question['recipient_organization'] = [recipient_party_id]
        self.question['recipient_text'] = self.recipient

        # send question 
        question_id, method = self.add_or_get_question(self.question['signature'], self.question)

        
        # send link
        if method == 'set' and self.url:
            self.link['question'] = question_id
            self.add_link(self.link)


