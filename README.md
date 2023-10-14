# Requirements
- python >= 3.9
- pytorch for CPU only
### pip install
- openai
- transformers
- websockets
### Example
```
conda create -n openai python=3.9
conda activate openai
pip install openai
pip install transformers
pip install websockets
pip install pyinstaller
conda install pytorch cpuonly -c pytorch
```

# Configuration
- File name = [config.json]
- File contents = 
```
{
    "api_key": "sk-JEP5T......",
    "api_key_0": "sk-JEP5T......",
    ...,
    "port": 12009,
    "close_server_when_client_die": true
}
```
    - "api_key": API key of OpenAI; 현재 하나의 key 만 공통적으로 사용.
    - "port": port number
    - "close_server_when_client_die": 클라이언트 연결이 끊겼을 때 서버의 상태. (true: 서버 종료, false: 서버 유지)

## character setting
- File name = [character_setting.json]
- File contents
    - 인물 아이디: "default", "0", "1", ... 
    - 항목
        - "api_key_name": config.json 에 있는 api_key 의 이름 (예, "api_key", "api_key_0", "api_key_1", ...),
        - "contents_path": contents 파일의 경로 (예, "contents_0.csv", ...)
        - "personality": 인물의 성격 부여 (data type: string list)
        - "other_options": 인물의 동작 부여 (data type: string list, 문장이 동사(verb)로 시작해야 한다.)
        - "pre_text": 질문 앞에 오는 설정 (data type: string list)
        - "post_text": 질문 뒤에 오는 설정 (data type: string list)

# pyinstaller
pyinstaller --onefile server.py --copy-metadata transformers --copy-metadata tqdm  --copy-metadata regex --copy-metadata requests --copy-metadata packaging --copy-metadata filelock --copy-metadata tokenizers --copy-metadata numpy --copy-metadata huggingface-hub --copy-metadata safetensors --copy-metadata pyyaml