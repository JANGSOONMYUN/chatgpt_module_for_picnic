import datetime
import pytz
# Set the time zone to Korean Standard Time (KST)
korean_timezone = pytz.timezone('Asia/Seoul')

def err_log(msg, file_path = 'log.txt'):
    current_time = datetime.datetime.now(korean_timezone)

    # Create an error message with the timestamp and exception details
    error_message = f"[{current_time}] {msg}"

    # Write the error message to a log file
    with open(file_path, "a") as log_file:
        log_file.write(error_message + "\n")
