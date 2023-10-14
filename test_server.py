import asyncio
import websockets
from asyncio import Queue
import time
NUM_WORKERS = 5  # for example

async def compute_square(number):
    await asyncio.sleep(2)
    print(number)
    await asyncio.sleep(2)
    print(number)
    await asyncio.sleep(2)
    print(number)
    await asyncio.sleep(2)
    print(number)
    await asyncio.sleep(2)
    print(number)
    result = number * number
    return result


async def worker(task_queue):
    while True:
        websocket, number = await task_queue.get()
        result = await compute_square(number)
        await websocket.send(f"The square of {number} is {result:.2f}")
        task_queue.task_done()

async def handle_client(task_queue, websocket, path):
    # client_ip, client_port = websocket.remote_address
    print(websocket.remote_address)
    # print(f"New connection from {client_ip}:{client_port}")

    try:
        async for message in websocket:
            try:
                number = float(message)
                await task_queue.put((websocket, number))
            except ValueError:
                await websocket.send("Invalid input. Please send a valid number.")
    except websockets.ConnectionClosed:
        pass

async def main():
    task_queue = asyncio.Queue()  # Moved inside the main coroutine

    # Start multiple workers with the task_queue
    for _ in range(NUM_WORKERS):
        asyncio.create_task(worker(task_queue))

    # Start the websocket server with the task_queue
    server = await websockets.serve(lambda ws, path: handle_client(task_queue, ws, path), "localhost", 8765)
    await server.wait_closed()


# Run the main coroutine
asyncio.run(main())
