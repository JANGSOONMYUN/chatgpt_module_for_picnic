import json
import re
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
        if i >= 8:
            break
        try:
            if int(n_str) > 5 or int(n_str) < 1:
                n_str = '1'
        except ValueError:
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

def get_character_by_percent(json_data, number_str):
    # print(number_str)
    # print(type(number_str))
    result_dict = {}
    result_str = ''
    tot_num = 0
    for i, n_str in enumerate(number_str):
        if i >= 8:
            break
        try:
            if int(n_str) > 5 or int(n_str) < 1:
                n_str = '1'
        except ValueError:
            n_str = '1'
        question = json_data[str(i)]['question']
        char_list = json_data[str(i)][n_str][1]

        for ci, c in enumerate(char_list):
            ch = c.split(',')[0]
            if ch in result_dict:
                result_dict[ch] += 1
            else:
                result_dict[ch] = 1
            tot_num += 1

    # 사이보그(50%), 영웅(10%), ...
    for k, v in result_dict.items():
        percent = int(v/tot_num*100)
        result_str += (k + f'({percent}%), ')

    result_str = result_str[:-2]
    return result_str

def remove_percent_str(message):
    if '%' in message:
        # Use regular expression to remove any percentage string
        message = re.sub(r'\(\d+%\)','', message)
        message = re.sub(r'\[\d+%\]','', message)
        message = message.replace('  ', ' ')
    return message


def find_matched_character(txt_from_gpt, english = True):
    selected = character_list[0]
    closest_idx = 1000
    for i, c in enumerate(character_list):
        c_kr = c[0]
        c_en = c[1]
        c_kr = c_kr.replace("'", '"')
        c_kr_wo_empty = c_kr.replace(' ', '')
        
        if f'"{c_kr}' in txt_from_gpt: # ex) "영웅"
            selected = c
            break
        if f'"{c_kr_wo_empty}' in txt_from_gpt: # ex) "영웅"
            selected = c
            break
        if f'"{c_en}' in txt_from_gpt: # ex) "HERO"
            selected = c
            break

        index = txt_from_gpt.find(c_kr)
        if index != -1 and closest_idx > index:
            closest_idx = index
            selected = c
            continue
        index = txt_from_gpt.find(c_kr_wo_empty)
        if index != -1 and closest_idx > index:
            closest_idx = index
            selected = c
            continue
            
        index = txt_from_gpt.find(c_en)
        if index != -1 and closest_idx > index:
            closest_idx = index
            selected = c


    print('find_matched_character:', selected)
    if english:
        return selected[1]
    else:
        return selected[0]


if __name__ == "__main__":
    input_string = "This is a sample string with [12%] inside. (12%)"
    result = remove_percent_str(input_string)
    print(result)