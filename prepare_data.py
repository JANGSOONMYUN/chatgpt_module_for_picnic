import sys
import os
import json
import copy

# # Get the parent directory path of the current script
# parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# # Add the parent directory path to sys.path
# sys.path.append(parent_dir)

from gpt_module import GPTModule
from handle_contents import load_contents_csv, check_tokents_for_dialog
from get_character import get_character, num_character, get_character_ids

CHARACTER_PATH = 'character_setting.json'
user_ids = list(get_character_ids(CHARACTER_PATH))
num_users = len(user_ids)

def convert_data_for_dialog_format(id):
    character = get_character(CHARACTER_PATH, id)
    contents_path = character['contents_path']
    contents = load_contents_csv(contents_path)
    
    # print(contents)
    return contents


def save_json(json_data, save_path):
    with open(save_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)

def convert_prompt_completion_format(contents):
    new_contents = []
    for a_dict in contents:
        if a_dict['role'] == 'user':
            new_dict = {}
            new_dict['prompt'] = a_dict['content']
        elif a_dict['role'] == 'assistant':
            if 'prompt' not in new_dict:
                new_dict = {}
                new_dict['prompt'] =  'Any information.'
            new_dict['completion'] =  a_dict['content']
            new_contents.append(new_dict)
    return new_contents

def convert_gpt3_format(contents):
    new_contents = []
    new_dict_list = []
    for a_dict in contents:
        # print(a_dict)

        if a_dict['role'] == 'user':
            new_dict_list = []
            new_dict = {}

        if a_dict['role'] == 'user' or a_dict['role'] == 'assistant':
            new_dict_list.append(a_dict)

        if a_dict['role'] == 'assistant':
            new_dict['messages'] = new_dict_list
            new_contents.append(new_dict)
    return new_contents

for id in user_ids:
    convert_data_for_dialog_format(id)

api_key_paths = []

combined_to_one_json = {'messages': []}
combined_to_list = []
for i in range(num_users):
    id = user_ids[i]
    print('-'*200)
    api_key_paths.append('config.json')
    gpt_module = GPTModule(api_key_path = api_key_paths[i], character_id = user_ids[i])

    character = gpt_module.get_speaker_character()
    # print(character)

    contents = convert_data_for_dialog_format(id)

    wrapped_data = {}
    wrapped_data['messages'] = character + contents

    combined_to_list.append(wrapped_data)
    combined_to_one_json['messages'] += (character + contents)

    # print(combined_result)

    gpt_module = None

prompt_completion_format = convert_prompt_completion_format(combined_to_one_json['messages'])

# save_json(combined_to_list, './fine_tune_data/fine_tune_data_list.json')
save_json(combined_to_one_json, './fine_tune_data/fine_tune_data.json')
save_json(prompt_completion_format, './fine_tune_data/prompt_completion_data.json')

# Specify the file path where you want to save the data
file_path = "./fine_tune_data/fine_tune_data_list.jsonl"

# Save the conversations to the file
with open(file_path, "w", encoding="utf-8") as json_file:
    for conversation in combined_to_list:
        json.dump(conversation, json_file)
        # json.dump(conversation, json_file, indent=4, ensure_ascii=False)
        json_file.write('\n')
# openai tools fine_tunes.prepare_data -f fine_tune_data.json


#######################################################################################
#######################################################################################
#######################################################################################

gpt3_format = convert_gpt3_format(combined_to_one_json['messages'])
print(gpt3_format)
# Specify the file path where you want to save the data
file_path = "./fine_tune_data/gpt3_format.jsonl"

# Save the conversations to the file
with open(file_path, "w", encoding="utf-8") as json_file:
    for conversation in gpt3_format:
        json.dump(conversation, json_file)
        # json.dump(conversation, json_file, indent=4, ensure_ascii=False)
        json_file.write('\n')
# openai tools fine_tunes.prepare_data -f fine_tune_data.json