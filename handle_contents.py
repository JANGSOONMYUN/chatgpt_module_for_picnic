import sys
import json
import csv
from transformers import GPT2Tokenizer

def save_contents_as_json(prepared_msg_data, save_path):
    result_dict = {'messages': prepared_msg_data}
    try:
        # for i, cont_0, cont_1 in enumerate(zip(content_a_list, content_b_list)):
        #     if i < start_idx or i > end_idx:
        #         continue
        #     result_dict['messages'].append({'role': 'user', 'content': cont_0})
        #     result_dict['messages'].append({'role': 'assistant', 'content': cont_1})

        if len(result_dict['messages']) == 0:
            raise Exception('자료가 입력되지 않았습니다.')

        with open(save_path, "w", encoding="utf-8") as json_file:
            json.dump(result_dict, json_file, indent=4, ensure_ascii=False)
    except Exception as e:
        print('Input:', prepared_msg_data)
        print("An error occurred:", str(e))
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents.py] 파일을 확인해주세요.')
    except:
        print('Input:', prepared_msg_data)
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents.py] 파일을 확인해주세요.')

def get_dialogue_as_str(msgs):
    dialogue_str = ''
    for i, msg in enumerate(msgs):
        dialogue_str += '{}: '.format(msg['role'])
        dialogue_str += msg['content']
        dialogue_str += '\n'
    return dialogue_str

def check_tokens(text, max_num = 25000):
    tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
    tokens = tokenizer.encode(text, add_special_tokens=False)  # add_special_tokens=False to exclude special tokens like [CLS], [SEP]
    return len(tokens) < max_num, len(tokens)

def check_tokents_for_dialog(dialog_msgs, max_num = 25000):
    str_msg = get_dialogue_as_str(dialog_msgs)
    token_ok, token_size = check_tokens(str_msg, max_num)
    return token_ok, token_size

def load_contents_csv(csv_path):
    csv_dict_list = []
    try:
        with open(csv_path, 'r', encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                csv_dict_list.append(row)
                if 'role' not in row and 'content' not in row:
                    raise Exception('[ERROR]')
    except Exception as e:
        print("An error occurred:", str(e))
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents_*.csv] 파일을 확인해주세요.')
    except:
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents_*.csv] 파일을 확인해주세요.')
    return csv_dict_list

def load_contents(json_path):
    try:
        # Load JSON data from a file
        with open(json_path, 'r',  encoding="utf-8") as json_file:
            data_dict = json.load(json_file)
            return data_dict['messages']
    except Exception as e:
        print("An error occurred:", str(e))
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents_*.json] 파일을 확인해주세요.')
    except:
        print('[에러] 입력된 자료의 형태나 구조의 문제가 있을 수 있습니다. [contents_*.json] 파일을 확인해주세요.')

if __name__ == "__main__":
    # test
    load_contents_csv('contents_0.csv')