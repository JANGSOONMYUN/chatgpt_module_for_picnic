import os
import threading
import queue
import json
import copy
import time
from datetime import datetime

import openai
from transformers import GPT2Tokenizer
from get_config import get_api_key
from get_character import get_character
from handle_contents import load_contents, load_contents_csv

class GPTModule(threading.Thread):
    def __init__(self, api_key_path = './config.json', character_id = "default", tokenizer = None, keep_dialog = None, warmed_up_dialog = None, warmup_mode = False) -> None:
        threading.Thread.__init__(self)

        self.model = 'gpt-3.5-turbo-16k'

        self.tokenizer = tokenizer
        if self.tokenizer is None:
            self.tokenizer = self.load_tokenizer('gpt2')

        # Character
        self.character_id = character_id
        self.character_setting = get_character('character_setting.json', character_id)
        
        api_key_name = self.character_setting['api_key_name']
        openai.api_key = get_api_key(api_key_path, key_name = api_key_name)

        self.contents_path = self.character_setting['contents_path']
        self.personality = self.character_setting['personality']
        self.attitude = []
        self.other_options = self.character_setting['other_options']
        self.pre_text = self.character_setting['pre_text']
        self.post_text = self.character_setting['post_text']

        self.dialog_contains_pre_post_text = False
        if 'dialog_contains_pre_post_text' in self.character_setting:
            self.dialog_contains_pre_post_text = self.character_setting['dialog_contains_pre_post_text']


        # options
        self.keep_dialog = True
        self.dialog_data = []

        # test result showed maximum 33238
        self.max_num_token  = 30000

        # saving data
        self.user_text = ''
        self.answer_text = ''
        self.start_time = None
        self.end_time = None


        # init
        if keep_dialog is not None:
            self.keep_dialog = True
            self.dialog_data = keep_dialog
        else:
            self.keep_dialog = False

        # combine after contents
        self.warmed_up_dialog = warmed_up_dialog
        if warmup_mode:
            self.dialog_contains_pre_post_text = True
            
    # def set_keep_dialog_option(self, option = True):
    #     self.keep_dialog = option
    #     self.dialog_data = []

    def get_speaker_character(self):
        who_you_are = 'You are a'
        for p in self.personality + self.attitude:
            who_you_are += ' ' + p

        who_you_are += ' Korean assistant'
        if len(self.other_options) > 0:
            who_you_are += ' who'
        for i, opt in enumerate(self.other_options):
            if i > 0:
                who_you_are += ','
            who_you_are += ' ' + opt

        print('who_you_are:', who_you_are)
        speaker_setting = [{"role": "system", "content": who_you_are}]
        return speaker_setting
    
    def set_speaker_character(self, personality, attitude, other_options):
        # personality = ['introvert']
        # attitude = ['mild']
        # other_options = ['simple answering', 'simple questions']
        self.personality = personality
        self.attitude = attitude
        self.other_options = other_options
        return self.get_speaker_character()

    
    def ask_question(self, prev_msg, ask_option, who_you_are, model = 'gpt-3.5-turbo-16k'):
        system_setting = [{"role": "system", "content": who_you_are}]
        question = [
                    {"role": "user", "content": "According to the current conversation, ask me a short question in Korean."},
                ]
        full_msg = system_setting + prev_msg + question
        completion = openai.ChatCompletion.create(
            model=model,
            messages = full_msg
        )
        
        return completion.choices[0].message['content'], full_msg
    

    def load_tokenizer(self, model_name_or_path="gpt2"):
        tokenizer = GPT2Tokenizer.from_pretrained(model_name_or_path)
        return tokenizer

    def get_num_tokens(self, text):
        if self.tokenizer is None:
            self.tokenizer = self.load_tokenizer('gpt2')
        tokens = self.tokenizer.encode(text, add_special_tokens=False)  # add_special_tokens=False to exclude special tokens like [CLS], [SEP]
    #     print(tokens)
        return len(tokens)
        
 
    def drop_text(self, text_list, start_idx, end_idx):
        if start_idx < 0:
            start_idx = 0
        if end_idx >= len(text_list):
            del text_list[start_idx :]
        else:
            del text_list[start_idx : end_idx]
        return text_list

    def get_q_and_a_by_character_and_post_text(self):
        # prepare post text
        post_txt_combined = ''
        for i, post_txt in enumerate(self.post_text):
            if '.' in post_txt[-2:]:
                post_txt = post_txt[:-2] + post_txt[-2:].replace('.', '')

            if (i == (len(self.post_text) - 1)) and len(self.post_text) > 1:
                post_txt_combined += ' and '
            elif i > 0:
                post_txt_combined += ', '

            post_txt_combined += (post_txt)

        # Question
        who_you_are = self.set_speaker_character(personality = self.personality, attitude = [], other_options = self.other_options)
        who_you_are = who_you_are[0]['content']
        who_you_are += (' and you ' + post_txt_combined)

        # Answer
        who_I_am = 'Yes I am a'
        for p in self.personality:
            who_I_am += ' ' + p
        who_I_am += ' person'
        if len(self.other_options) > 0:
            who_I_am += ' who'
        for i, opt in enumerate(self.other_options):
            if i > 0:
                who_I_am += ','
            who_I_am += ' ' + opt
        
        who_I_am += ('\nAnd I will ' + post_txt_combined)

        user_msg = self.pack_string_to_msg_list(who_you_are, role = 'user', remove_white_space = False)
        assistant_msg = self.pack_string_to_msg_list(who_I_am, role = 'assistant', remove_white_space = False)

        return user_msg + assistant_msg
        

    def chat_completion(self, setting, messages, contents = None, remove_white_space = True):
        model = self.model 
        # Get the current time
        start_time = datetime.now().time()
        prepare_msg = copy.deepcopy(setting)
        dialog_data_idx = len(prepare_msg)
        if contents is not None:
            prepare_msg += contents
            dialog_data_idx = len(prepare_msg)
        if len(self.dialog_data) > 0:
            prepare_msg += self.dialog_data.copy()
        
        orig_messages = copy.deepcopy(messages)
        
        if self.warmed_up_dialog is not None:
            if len(self.warmed_up_dialog) > 0:
                prepare_msg += self.warmed_up_dialog
        
        pre_texts = ''
        for pre_text in self.pre_text:
            pre_texts += (pre_text + ' ')
        if len(self.pre_text) > 0:
            messages[0]['content'] = pre_texts + '\nquestion: ' + messages[0]['content']
        if len(self.post_text) > 0:
            messages[0]['content']
        for i, post_txt in enumerate(self.post_text):
            if i == 0:
                messages[0]['content'] += '\nTalking styles: '
            messages[0]['content'] += (post_txt + ' ')
            # if i == (len(self.post_text) - 1):
            #     messages[0]['content'] += ']'
        prepare_msg += messages
        

        str_msg = self.get_dialogue_as_str(prepare_msg)
        num_tokens = self.get_num_tokens(str_msg)
        print('current num_tokens[{}]: {}'.format(self.character_id, num_tokens))
        max_tries = 10
        orig_dialog_data_idx = dialog_data_idx
        while num_tokens > self.max_num_token:
            dialog_data_idx = orig_dialog_data_idx
            num_drops = 4
            # if the number of dialog is too small, the contents should be dropped.
            if dialog_data_idx == len(setting):
                num_drops = 1
            elif (len(prepare_msg) - dialog_data_idx) < (num_drops + 1):
                dialog_data_idx = 1
                num_drops = 1
                orig_dialog_data_idx -= num_drops
            else:
                # drop self.dialog_data
                self.drop_text(self.dialog_data, 0, num_drops)

            prepare_msg = self.drop_text(prepare_msg, dialog_data_idx, dialog_data_idx + num_drops)
            str_msg = self.get_dialogue_as_str(prepare_msg)
            num_tokens = self.get_num_tokens(str_msg)
            print('[{}] num_tokens after dropping some data: {}'.format(self.character_id, num_tokens) )
            max_tries -= 1
            if max_tries <= 0:
                print('[WARN] The tries of dropping dialog reached the maximum value. All the dialog will be removed.')
                self.dialog_data = []
                return None, None
        
        if prepare_msg[-1]['role'] != 'user':
            for d in prepare_msg:
                print(d)
        assert prepare_msg[-1]['role'] == 'user'

        completion = openai.ChatCompletion.create(
                        model=model,
                        messages = prepare_msg,
                        temperature=0.3,
                        # max_tokens=256,
                        # top_p=1,
                        # frequency_penalty=0,
                        # presence_penalty=0
                    )
        
        result_str = completion.choices[0].message['content']
        packed_result = self.pack_string_to_msg_list(result_str, 'assistant', remove_white_space)
        if self.keep_dialog:
            # print('-'*200)
            # print(len(self.dialog_data))
            
            dialog_w_opt = copy.deepcopy(self.dialog_data) + copy.deepcopy(messages) + copy.deepcopy(packed_result)
            dialog_wo_opt = copy.deepcopy(self.dialog_data) + copy.deepcopy(orig_messages) + copy.deepcopy(packed_result)
            if self.dialog_contains_pre_post_text:
                # with options
                self.dialog_data += (messages + packed_result)
            else:
                # without options
                self.dialog_data += (orig_messages + packed_result)
            # print(len(self.dialog_data))

            # Saving logs
            saving_dir = 'log/'
            if not os.path.exists(saving_dir):
                os.makedirs(saving_dir)
            with open(saving_dir + 'dialog_data_{}.json'.format(self.character_id), "w", encoding="utf-8") as json_file:
                json.dump(dialog_wo_opt, json_file, indent=4, ensure_ascii=False)
            with open(saving_dir + 'dialog_data_w_opts_{}.json'.format(self.character_id), "w", encoding="utf-8") as json_file:
                json.dump(dialog_w_opt, json_file, indent=4, ensure_ascii=False)
            with open(saving_dir + 'dialog_data_full_{}.json'.format(self.character_id), "w", encoding="utf-8") as json_file:
                json.dump(prepare_msg + packed_result, json_file, indent=4, ensure_ascii=False)


        end_time = datetime.now().time()

        start_time_str, end_time_str, elapsed_time_sec_str = self.convert_time_to_str(start_time, end_time)

        # Print the current time
        print("Started: {}, Ended: {}, Elapsed: {} sec".format(start_time_str, end_time_str, elapsed_time_sec_str))
        return result_str, packed_result

    def pack_string_to_msg_list(self, str_msg, role = 'user', remove_white_space = True):
        if remove_white_space:
            str_msg = str_msg.replace('  ', ' ')
            str_msg = str_msg.replace('\n', ' ')
        message = [
                    {"role": role, "content": str_msg},
                ]
        return message
    
    def get_dialogue_as_str(self, msgs):
        speaker_0 = 'user'
        speaker_1 = 'assistant'
        dialogue_str = ''
        for i, msg in enumerate(msgs):
            if msg['role'] == speaker_0:
                dialogue_str += 'A: '
            else:
                dialogue_str += 'B: '
            dialogue_str += msg['content']
            dialogue_str += '\n'
        return dialogue_str

    def switch_role(self, msg):
        for i, m in enumerate(msg):
            if m['role'] == 'user':
                msg[i]['role'] = 'assistant'
            elif m['role'] == 'assistant':
                msg[i]['role'] = 'user'
        return msg
    '''
        speaker: speaker's characteristic e.g., [{"role": "system", "content": "helpful assistant"}]
        listener: same data format to speaker but different content.
        msgs: messages for completion.
        msg_type: question or answer, or both.
    '''
    def talk_to_counterpart(self, speaker, listener, msgs, msg_type, model = 'gpt-3.5-turbo-16k'):
        # the listener MUST be assistant because assistant will answer the questions.
        # So, speaker is user here. 
        # (user and assistant are switched according to functions)
        completion = openai.ChatCompletion.create(
                    model = model,
                    messages = listener + msgs
        )
        
        answer_str = completion.choices[0].message['content']
        answer = self.pack_string_to_msg_list(answer_str, 'assistant', True)
        
        return msgs + answer
    

    def set_text(self, text):
        self.user_text = text
    
    def get_answer(self):
        return self.answer_text
    
    def convert_time_to_str(self, start_time, end_time):
        # Calculate the time difference
        time_difference = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time)
        elapsed_time_sec = time_difference.total_seconds()

        # Convert to strings with limited decimal places
        start_time_str = start_time.strftime("%H:%M:%S.%f")[:-3]
        end_time_str = end_time.strftime("%H:%M:%S.%f")[:-3]
        elapsed_time_sec_str = "{:.2f}".format(elapsed_time_sec)

        self.start_time = start_time_str
        self.end_time = end_time_str
        self.elapsed_time = elapsed_time_sec_str

        return start_time_str, end_time_str, elapsed_time_sec_str
    
    def get_elapsed_time(self):
        if self.start_time is None or self.end_time is None:
            return '0:0:0', '0:0:0', '0 sec'
        
        return self.start_time, self.end_time, self.elapsed_time

    # Threading for conversation
    def run(self):
        self.start_time = None
        self.end_time = None
        # Test
        personality = self.personality # ['introvert']
        attitude = [] #['mild']
        other_options = self.other_options  # ['speakes Korean for all the questions', 'answers simply', 'has artistic mind']
        speaker_character = self.set_speaker_character(personality, attitude, other_options)
        print(speaker_character)

        cont = load_contents_csv(self.contents_path)

        # question = 'Hi, who are you?'
        self.answer_text, _ = self.chat_completion(speaker_character, self.pack_string_to_msg_list(self.user_text), contents = cont)
        if self.answer_text is None:
            self.answer_text = '다시 입력해 주세요.'


# test
if __name__ == "__main__":
    gpt = GPTModule()

    # 
    personality = ['introvert']
    attitude = ['mild']
    other_options = ['speakes Korean for all the questions', 'answers simply', 'has artistic mind']
    speaker_character = gpt.set_speaker_character(personality, attitude, other_options)
    print(speaker_character)

    # cont = get_contents(0, 5)
    # cont = load_contents('contents_0.json')
    cont = load_contents_csv(self.contents_path)
    # print(cont)


    question = 'Hi, who are you?'
    received_msg, _ = gpt.chat_completion(speaker_character, gpt.pack_string_to_msg_list(question), contents = cont)
    print(received_msg)

    
    question = 'Who is your favorite artist?'
    received_msg, _ = gpt.chat_completion(speaker_character, gpt.pack_string_to_msg_list(question), contents = cont)
    print(received_msg)

    question = '빈센트 반고흐에 대해 알아?'
    received_msg, _ = gpt.chat_completion(speaker_character, gpt.pack_string_to_msg_list(question), contents = cont)
    print(received_msg)


    # # test for checking max number of tokens
    # while(True):
    #     question = '''빈센트 반고흐에 대해 알아? 빈센트 반고흐는 19세기 네덜란드의 화가로, 세계적으로 유명한 예술가입니다. 그는 후기 인상주의(star post-impressionism) 예술 스타일로 알려져 있으며, 선명한 색상과 강렬한 터치가 특징입니다. 그의 작품은 그의 감정과 내면의 고통을 표현하는 데 큰 역할을 했으며, 
    #                             특히 "별이 빛나는 밤"과 "해바라기" 등의 대표작으로 알려져 있습니다. 그러나 그의 삶은 고통과 어려움
    #                     으로 가득한 시기로 알려져 있으며, 결국 자살로 생을 마감하였습니다. 그러나 그의 작품은 세계적으로 인정받고 있으며, 많은 사람들에게 
    #                     영감과 감동을 전달하고 있습니다. 더 궁금한 것이 있으신가요? 빈센트 반고흐에 대해 알아? 빈센트 반고흐는 19세기 네덜란드의 화가로, 세계적으로 유명한 예술가입니다. 그는 후기 인상주의(star post-impressionism) 예술 스타일로 알려져 있으며, 선명한 색상과 강렬한 터치가 특징입니다. 그의 작품은 그의 감정과 내면의 고통을 표현하는 데 큰 역할을 했으며, 
    #                             특히 "별이 빛나는 밤"과 "해바라기" 등의 대표작으로 알려져 있습니다. 그러나 그의 삶은 고통과 어려움
    #                     으로 가득한 시기로 알려져 있으며, 결국 자살로 생을 마감하였습니다. 그러나 그의 작품은 세계적으로 인정받고 있으며, 많은 사람들에게 
    #                     영감과 감동을 전달하고 있습니다. 더 궁금한 것이 있으신가요? 빈센트 반고흐에 대해 알아? 빈센트 반고흐는 19세기 네덜란드의 화가로, 세계적으로 유명한 예술가입니다. 그는 후기 인상주의(star post-impressionism) 예술 스타일로 알려져 있으며, 선명한 색상과 강렬한 터치가 특징입니다. 그의 작품은 그의 감정과 내면의 고통을 표현하는 데 큰 역할을 했으며, 
    #                             특히 "별이 빛나는 밤"과 "해바라기" 등의 대표작으로 알려져 있습니다. 그러나 그의 삶은 고통과 어려움
    #                     으로 가득한 시기로 알려져 있으며, 결국 자살로 생을 마감하였습니다. 그러나 그의 작품은 세계적으로 인정받고 있으며, 많은 사람들에게 
    #                     영감과 감동을 전달하고 있습니다. 더 궁금한 것이 있으신가요? 
    #                     '''
    #     received_msg, _ = gpt.chat_completion(speaker_character, gpt.pack_string_to_msg_list(question), contents = cont)
    #     print(received_msg)