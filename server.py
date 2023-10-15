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

from get_config import get_ip_port, close_server_option
from get_character import get_character, num_character, get_character_ids
from gpt_module import GPTModule
from transformers import GPT2Tokenizer
from handle_contents import load_contents_csv, check_tokents_for_dialog

NUM_WORKERS = 5

CONFIG_PATH = './config.json'
CHARACTER_PATH = './character_setting.json'

connected_clients = 0  # Track the number of connected clients
user_ids = list(get_character_ids(CHARACTER_PATH))
num_users = len(user_ids)

tokenizers = []
api_key_paths = []
gpt_modules = {}
keep_dialog = []
warmed_up_dialog = []

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
    json_data = {
        "id": id,
        "text": text,
        "time": {
            "start": start_time,
            "end": end_time,
            "elapsed_time": str(elapsed_time)
        }
    }

    return json_data



def reset_dialog():
    global keep_dialog
    keep_dialog = None
    keep_dialog = []
    for i in range(num_users):
        keep_dialog.append([])
    print('reset() has been done.')

def reset_warmed_up_dialog():
    global warmed_up_dialog
    warmed_up_dialog = None
    warmed_up_dialog = []
    for i in range(num_users):
        warmed_up_dialog.append([])
    print('reset() has been done.')


def warmup_dialog_without_gpt():
    for i in range(num_users):
        gpt_module = GPTModule(api_key_path = api_key_paths[i], character_id = user_ids[i], tokenizer = tokenizers[i], keep_dialog = warmed_up_dialog[i], warmup_mode = True)
        warmed_up_dialog[i] += gpt_module.get_q_and_a_by_character_and_post_text()
        # print(warmed_up_dialog[i])
        for d in warmed_up_dialog[i]:
            print(d)

def handle_received_date(received_data):
    message = ''
    try:
        json_data = json.loads(received_data)
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
        print(e)

    # It should be removed after testing
    if 'reset' in message:
        reset_dialog()
        message = ''

    return message
    
async def receive_gpt_result(gpt_module):
    json_format = True
    gpt_module.join()
    start_time, end_time, elapsed_time_sec = gpt_module.get_elapsed_time()
    return_val = None
    if json_format:
        json_result = pack_str_to_json(gpt_module.get_answer(), '0', start_time, end_time, elapsed_time_sec)
        return_val = json.dumps(json_result, ensure_ascii=False)  # Use ensure_ascii=False
    else:
        return_val = str('0') + ": " + gpt_module.get_answer()
        return_val += '\n{}~{}, 소요시간: {} 초'.format(start_time, end_time, elapsed_time_sec)

    return return_val

async def worker(task_queue):
    while True:
        websocket, work_id = await task_queue.get()
        result = await receive_gpt_result(gpt_modules[work_id])
        # gpt_modules[work_id] = None
        del gpt_modules[work_id]

        await websocket.send(result)
        task_queue.task_done()

connection_id = 0
# ws://127.0.0.1:12009/websocket
async def echo(task_queue, websocket, path):
    global gpt_modules, connected_clients, connection_id
    connected_clients += 1

    client_ip, client_port = websocket.remote_address
    print(f"New connection from {client_ip}:{client_port}")

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

            reset_dialog()
            
            for i in range(num_users):
                gpt_module_tmp = GPTModule(api_key_path = api_key_paths[i], character_id = user_ids[i], tokenizer = tokenizers[i], keep_dialog = keep_dialog[i], warmed_up_dialog = warmed_up_dialog[i])
                gpt_modules[str(connection_id)] = gpt_module_tmp

            for i in range(num_users):
                gpt_modules[str(connection_id)].set_text(message)
                gpt_modules[str(connection_id)].start()

            # the number of 
            # Enqueue the task for computation
            await task_queue.put((websocket, str(connection_id)))
            
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected")
    except Exception as ex:
        print('Unexpected error occurred.', str(ex))
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
        keep_dialog.append([])

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

        # start_server = websockets.serve(echo, ip, port)

        # # Start the worker to process tasks in the background
        # asyncio.create_task(worker())

        # asyncio.get_event_loop().run_until_complete(start_server)
        # print('--- The server is ready. ---')
        # asyncio.get_event_loop().run_forever()



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