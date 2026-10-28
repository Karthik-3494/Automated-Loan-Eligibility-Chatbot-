import request_id_generator

def log(message, request_id=None):
    if request_id:
        file_path = f"logs/{request_id}.log"
        with open(file_path, 'w') as file:
            file.write(message + "\n")
    else:
        file_path = f"logs/general.log"
        with open(file_path, 'a') as file:
            file.write(message + "\n")
