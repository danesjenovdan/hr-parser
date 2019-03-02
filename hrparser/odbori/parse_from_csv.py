from hrparser.settings import API_URL, API_AUTH, API_DATE_FORMAT
from hrparser.pipelines import getDataFromPagerApiDRF

from requests.auth import HTTPBasicAuth
from datetime import datetime

import requests
import editdistance
import re

# this manually parses the csv file since some fields are too long for the csv parser
def parse_csv(filename):
  with open(filename, encoding='utf-8') as csvfile:
    lines = csvfile.readlines()
    rows = []
    cols = []
    in_quote = False
    col_start = 0
    from_prev_line = ''
    for line in lines:
      for i, char in enumerate(line):
        if char == '"':
          in_quote = not in_quote
          continue
        if not in_quote and char == ';':
          cols.append(from_prev_line + line[col_start:i])
          from_prev_line = ''
          col_start = i + 1
          continue
        if char == '\n':
          if in_quote:
            from_prev_line += line[col_start:i] + '\n'
            col_start = 0
            continue
          else:
            rows.append(cols)
            cols = []
            in_quote = False
            col_start = 0
            from_prev_line = ''
  return rows


def unquote(string):
  if string == '""':
    return ''
  m = re.match(r'^"([^"]+)"$', string)
  if m and m.group(1):
    return m.group(1)
  m = re.match(r'^"(.+)"$', string, re.DOTALL)
  if m and m.group(1):
    s = m.group(1)
    s.replace('""', '"')
  return string


def main():
  csvfile = parse_csv('hrparser/odbori/dokumenti.csv')
  csvheader = list(map(unquote, csvfile[0]))
  print(csvheader)

  orgs = getDataFromPagerApiDRF(API_URL + 'organizations/')
  sessions = getDataFromPagerApiDRF(API_URL + 'sessions/')
  agenda_items = getDataFromPagerApiDRF(API_URL + 'agenda-items/')
  records = getDataFromPagerApiDRF(API_URL + 'records/')

  current_mandate_rows = [row for row in csvfile[1:] if row[0] == '9']
  row_len = len(current_mandate_rows)

  for i, row in enumerate(current_mandate_rows):
    print('\n', i, '/', row_len - 1)

    odbor = unquote(row[1])
    print('ODBOR:', odbor)
    odbor_id = next((org['id'] for org in orgs if editdistance.eval(odbor, org['_name']) < 4), 0)
    if not odbor_id:
      response = requests.post(API_URL + 'organizations/',
                               auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1]),
                               data={
                                 '_name': odbor,
                                 'name_parser': '|' + odbor + '|',
                                 '_acronym': odbor,
                                 'classification': 'committee',
                               }).json()
      print(response)
      orgs.append(response)
      odbor_id = response['id']

    session = unquote(row[2])
    print('SESSION:', session)
    session_name, date = re.match(r'(.*) - (\d{1,2}\.\d{1,2}\.\d{4})\.', session).groups()
    session_name = session_name.lower()
    date = datetime.strptime(date, API_DATE_FORMAT)
    session_id = next((s['id'] for s in sessions if session_name == s['name'] and odbor_id in s['organizations']), 0)
    if not session_id:
      response = requests.post(API_URL + 'sessions/',
                               auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1]),
                               data={
                                 'name': session_name,
                                 'organization': odbor_id,
                                 'organizations': [odbor_id],
                                 'start_time': date.isoformat(),
                               }).json()
      print(response)
      sessions.append(response)
      session_id = response['id']

    url = unquote(row[5])
    print('URL:', url)
    agenda_name = unquote(row[3])
    print('AGENDA_NAME:', agenda_name)
    agenda_item_id = next((a['id'] for a in agenda_items if agenda_name == a['name'] and session_id == a['session']), 0)
    if not agenda_item_id:
      response = requests.post(API_URL + 'agenda-items/',
                               auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1]),
                               data={
                                 'name': agenda_name,
                                 'session': session_id,
                                 'gov_id': url,
                               }).json()
      print(response)
      agenda_items.append(response)
      agenda_item_id = response['id']

    record_content = unquote(row[4])
    print('RECORD', record_content[:50])
    record_id = next((r['id'] for r in records if agenda_item_id == r['agenda_item']), 0)
    if not record_id:
      if record_content:
        response = requests.post(API_URL + 'records/',
                                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1]),
                                data={
                                  'content': record_content,
                                  'agenda_item': agenda_item_id,
                                  'session': session_id,
                                  'gov_id': url,
                                }).json()
        print(response)
        records.append(response)
        record_id = response['id']




if __name__ == "__main__":
  main()
