import json
character_list = [
    ["영웅", "HERO"],
    ["반딧불이", "FIREFLY"],
    ["전설", "LEGEND"],
    ["마법사", "WIZARD"],
    ["친구", "FRIEND"],
    ["사이보그", "CYBORG"],
    ["주인공", "PROTAGONIST"],
    ["수호자", "GUARDIAN"],
    ["관찰자", "OBSERVER"],
    ["명인", "MASTER"],
    ["이웃", "NEIGHBOR"],
    ["웃는 사람", "LAUGHER"],
    ["춤추는 사람", "DANCER"],
    ["노래하는 사람", "SINGER"],
    ["꿈꾸는 사람", "DREAMER"],
    ["생각하는 사람", "THINKER"],
    ["모험가", "ADVENTURER"],
    ["이상가", "IDEALIST"],
    ["투사", "CHAMPION"],
    ["귀여운 사람", "CUTIE"]
]


def load_question(json_path = 'questionnaire.json'):
    # Load the JSON data from the file
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return data

def get_character_set(json_data, number_str):
    # print(number_str)
    # print(type(number_str))
    result_str = ''
    for i, n_str in enumerate(number_str):
        if int(n_str) > 5 or int(n_str) < 1:
            n_str = '1'
        question = json_data[str(i)]['question']
        char_list = json_data[str(i)][n_str][1]

        result_str += str(i + 1) + ') '
        for ci, c in enumerate(char_list):
            result_str += c.split(',')[0]
            if ci < len(char_list) - 1:
                result_str += ', '
            else:
                result_str += '\n'
    return result_str

def find_matched_character(txt_from_gpt, english = True):
    selected = character_list[0]
    for i, c in enumerate(character_list):
        c_kr = c[0]
        c_en = c[1]

        if c_kr in txt_from_gpt:
            selected = c
            continue
        elif c_kr.replace(' ', '') in txt_from_gpt:
            selected = c
            continue
        elif c_en in txt_from_gpt:
            selected = c
            continue

    print('find_matched_character:', selected)
    if english:
        return selected[1]
    else:
        return selected[0]
