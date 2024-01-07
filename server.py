import os
import json
import gc
import threading
import queue
import time
from datetime import datetime

import asyncio
import websockets
from asyncio import Queue

from log.err_log import err_log
from get_config import get_ip_port, close_server_option
from get_character import get_character, num_character, get_character_ids
from gpt_module import GPTModule
from transformers import GPT2Tokenizer
from handle_contents import load_contents_csv, check_tokents_for_dialog
from questionnaire import load_question, get_character_set, get_character_by_percent, find_matched_character, remove_percent_str

NUM_WORKERS = 5


question_data = load_question()

CONFIG_PATH = './config.json'
CHARACTER_PATH = './character_setting.json'

connected_clients = 0  # Track the number of connected clients
user_ids = list(get_character_ids(CHARACTER_PATH))
num_users = len(user_ids)

tokenizers = []
api_key_paths = []
gpt_modules = {}
keep_dialog = {}
warmed_up_dialog = {}

def print_remaining_workers():
    wks = []
    for k, v in gpt_modules.items():
        wks.append(k)
    print('Remainings:', wks)

async def disconnect_callback():
    print_remaining_workers()

def check_time():
    # Get the current time
    current_time = datetime.now().time()
    # Print the current time
    print("Start time:", current_time)

def load_tokenizer(model_name_or_path="gpt2"):
    tokenizer = GPT2Tokenizer.from_pretrained(model_name_or_path)
    return tokenizer

def check_contents_tokens_by_character(id, json_path = './character_setting.json'):
    character = get_character(json_path, id)
    contents_path = character['contents_path']
    contents = load_contents_csv(contents_path)
    token_ok, token_size = check_tokents_for_dialog(contents, 25000)
    if token_ok:
        print('ID-{} 의 contents token 크기는 {} 입니다.'.format(id, token_size))
    else:
        print('[에러] Token 크기가 초과되었습니다. 자료를 축소해주세요 ({}). 현재 자료의 Token: {}. 최대 허용 Token: {}'.format(contents_path, token_size, 25000))
    return token_ok

def pack_str_to_json(text, id, end_time = '0:0:0', start_time = '0:0:0', elapsed_time = '0'):
    '''
    {
        “id”: “0”,
        “text”: “text text text text”,
        “time”: { “start”: “20:59:40”,
            “end”: “20:59:53”,
            “elapsed_time”: “13.28”
    }
    '''

    text = remove_percent_str(text)

    json_data = {
        "id": id,
        "text": text,
        "character": find_matched_character(text, True),
        "time": {
            "start": start_time,
            "end": end_time,
            "elapsed_time": str(elapsed_time)
        }
    }

    return json_data



def reset_dialog(worker_id = None):
    global keep_dialog
    if worker_id is None:
        for k, v in keep_dialog.items():
            del keep_dialog[k]
            keep_dialog[k] = []
        worker_id = 'all'
    else:
        if worker_id in keep_dialog:
            del keep_dialog[worker_id]
        keep_dialog[worker_id] = []

    print(f'reset() for worker:{worker_id} has been done.')

def reset_warmed_up_dialog(worker_id = None):
    global warmed_up_dialog
    if worker_id is None:
        for k, v in warmed_up_dialog.items():
            del warmed_up_dialog[k]
            warmed_up_dialog[k] = []
        worker_id = 'all'
    else:
        if worker_id in warmed_up_dialog:
            del warmed_up_dialog[worker_id]
        warmed_up_dialog[worker_id] = []

    print(f'reset_warmed_up_dialog() for worker:{worker_id} has been done.')


def warmup_dialog_without_gpt(worker_id = None):
    if worker_id is None:
        for k, v in gpt_module.items():
            reset_warmed_up_dialog(k)
            gpt_module = GPTModule(api_key_path = api_key_paths[0], character_id = user_ids[0], tokenizer = tokenizers[0], 
                                   keep_dialog = warmed_up_dialog[k], warmup_mode = True)
            warmed_up_dialog[k] += gpt_module.get_q_and_a_by_character_and_post_text()
            # print(warmed_up_dialog[i])
        for k, v in warmed_up_dialog.items():
            print(v)

def handle_received_date(received_data):
    message = ''
    try:
        json_data = json.loads(received_data)
        
        if isinstance(json_data, int) or isinstance(json_data, str):
            message = str(json_data)
        else:
            # dict
            if "action" in json_data:
                if json_data["action"] == "reset":
                    # Do reset dialog
                    reset_dialog()
            if 'text' in json_data:
                message = json_data['text']
        
    except json.JSONDecodeError:    
        # print("Non-JSON received:", received_data)
        message = str(received_data)
    except Exception as e:
        print('in handle_received_date(), ', e)

    try:
        integer_value = int(message)
        # message = get_character_set(question_data, message)
        message = get_character_by_percent(question_data, message)
    except ValueError:
        # print('Input value is not integer:', message)
        pass

    # It should be removed after testing
    if 'reset' in message:
        reset_dialog()
        message = ''

    return message
    
async def receive_gpt_result(gpt_module):
    print_remaining_workers()
    json_format = True

    # gpt_module.join()

    # Use an async loop to check if the thread is alive
    while gpt_module.is_alive():
        await asyncio.sleep(0.1)  # Sleep for a short duration before checking again
    

    start_time, end_time, elapsed_time_sec = gpt_module.get_elapsed_time()
    return_val = None
    if json_format:
        json_result = pack_str_to_json(gpt_module.get_answer(), '0', start_time, end_time, elapsed_time_sec)
        return_val = json.dumps(json_result, ensure_ascii=False)  # Use ensure_ascii=False
    else:
        return_val = str('0') + ": " + gpt_module.get_answer()
        return_val += '\n{}~{}, 소요시간: {} 초'.format(start_time, end_time, elapsed_time_sec)

    return return_val

async def delete_callback(work_id):
    print("WebSocket connection closed!")


async def worker(task_queue):
    while True:
        try:
            websocket, work_id = await task_queue.get()
            result = await receive_gpt_result(gpt_modules[work_id])
            # gpt_modules[work_id] = None
            
            await websocket.send(result)
            task_queue.task_done()
        except websockets.exceptions.ConnectionClosed:
            print(f'Current connection has been closed. Worker: {work_id}')
            err_log(f'Current connection has been closed. Worker: {work_id}', './log/server_log.txt')

        finally:
            # Delete memory
            if work_id in gpt_modules:
                del gpt_modules[work_id]
            if work_id in keep_dialog:
                del keep_dialog[work_id]
            if work_id in warmed_up_dialog:
                del warmed_up_dialog[work_id]


connection_id = 0
# ws://127.0.0.1:12009/websocket
async def echo(task_queue, websocket, path):
    global gpt_modules, connected_clients, connection_id
    connected_clients += 1
    connection_id += 1
    connection_id_str = str(connection_id)

    client_ip, client_port = websocket.remote_address
    print(f"New connection from {client_ip}:{client_port}, worker_id: {connection_id_str}")

    json_format = True
    
    try:
        async for received_data in websocket:
            message = handle_received_date(received_data)

            if len(message) <= 0:
                # print('no received data')
                continue

            # await websocket.send('질문: ' + message)
            print(f"Received message from {client_ip}:{client_port}: {message}")
            print(user_ids)

            if connection_id_str not in keep_dialog:
                keep_dialog[connection_id_str] = []
            if connection_id_str not in warmed_up_dialog:
                warmed_up_dialog[connection_id_str] = []

            reset_dialog(connection_id_str)
            
            gpt_modules[connection_id_str] = GPTModule(api_key_path = api_key_paths[0], character_id = user_ids[0], tokenizer = tokenizers[0], 
                                                    keep_dialog = keep_dialog[connection_id_str], warmed_up_dialog = warmed_up_dialog[connection_id_str])
            gpt_modules[connection_id_str].set_text(message)
            gpt_modules[connection_id_str].start()

            # the number of 
            # Enqueue the task for computation
            await task_queue.put((websocket, connection_id_str))
            
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected")
        print_remaining_workers()
    except Exception as ex:
        print('Unexpected error occurred.', str(ex))
        err_log(f'Unexpected error occurred: {str(ex)}', './log/server_log.txt')
    finally:
        connected_clients -= 1
        if connected_clients == 0:
            if not close_server_option(CONFIG_PATH):
                return
            print('The server has been closed.')
            asyncio.get_event_loop().stop()  # Close the event loop when all clients disconnect

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


async def main():
    clear_terminal()
    print('{} users are detected.'.format(len(user_ids)))
    user_input = 1
    
    is_token_ok = True
    for i in range(num_users):
        tokenizers.append(load_tokenizer('gpt2'))
        api_key_paths.append(CONFIG_PATH)

        # check tokens of contents
        if not check_contents_tokens_by_character(user_ids[i]):
            is_token_ok = False
    if is_token_ok:
        # warm up dialog
        reset_warmed_up_dialog()
        # clear_terminal()
        # for n in range(user_input):
        #     print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        #     print('>>>>>>>>>>>>>>>>>>>>>>>>> warming up... please wait for a while >>>>>>>>>>>>>>>>>>>>>>>>>')
        #     print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n')
        #     warmup_dialog_without_gpt()
        #     # warmup_dialog()
        #     # clear_terminal()
        # if user_input > 0:
        #     print('<<<<<<<<<<<<<<<<<<<<<<<<< warming up process has been done. <<<<<<<<<<<<<<<<<<<<<<<<<')
        # 127.0.0.1:12009
        ip, port = get_ip_port(CONFIG_PATH)

        # Create a Queue to manage tasks
        task_queue = asyncio.Queue()

        # Start multiple workers with the task_queue
        for _ in range(NUM_WORKERS):
            asyncio.create_task(worker(task_queue))

        # Start the websocket server with the task_queue
        server = await websockets.serve(lambda ws, path: echo(task_queue, ws, path), ip, port)
        await server.wait_closed()

import sys
if __name__ == "__main__":
    # Run the main coroutine
    asyncio.run(main())
    
    # os.system('pause')