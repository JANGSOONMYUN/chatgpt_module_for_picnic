import json
def get_character(json_path, user_id = "default"):
    # Specify the path to your JSON file
    file_path = json_path

    # Load the JSON data from the file
    with open(file_path, 'r',  encoding="utf-8") as file:
        data = json.load(file)
        
    return data[user_id]

def get_character_ids(json_path):
    # Load the JSON data from the file
    with open(json_path, 'r', encoding="utf-8") as file:
        data = json.load(file)
        # Deleting a key using the del statement
        if "default" in data:
            del data["default"]
        keys_list = data.keys()

    return keys_list

def num_character(json_path):
    # Load the JSON data from the file
    with open(json_path, 'r',  encoding="utf-8") as file:
        data = json.load(file)
        number_of_keys = len(data)
        return number_of_keys - 1