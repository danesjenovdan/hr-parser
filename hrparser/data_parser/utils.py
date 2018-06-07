from datetime import datetime

def get_vote_key(name, date):
    return (name + date).strip()

def fix_name(name_str):
    return ' '.join(map(str.capitalize, name_str.split(' ')))

def name_parser(name):
    words = name.split(' ')
    new_words = list(map(str.capitalize, words))
    print(new_words)
    new_parser_name = ' '.join(new_words)+','+' '.join(list(reversed(new_words)))

    return new_parser_name

def parse_date(input_data):
    # "birth_date": ["28.", "sije\u010dnja", "1977"]
    # "14. listopada 2016."
    if type(input_data) == str:
        input_data = input_data.split(' ')

    day = int(float(input_data[0]))
    month = parse_month(input_data[1])
    year = int(float(input_data[2]))
    return datetime(day=day, month=month, year=year)

def parse_month(month_str):
    months = ['sije', 'velj', 'ožuj', 'trav', 'svib', 'lip', 'srp', 'kolov', 'ruj', 'listop', 'studen', 'prosin']
    for i, month in enumerate(months):
        if month_str.lower().startswith(month):
            return i + 1
    return None