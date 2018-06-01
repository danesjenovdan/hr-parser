

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
