# import asyncio
# import websockets

# async def send_number(websocket, number):
#     await websocket.send(str(number))
#     response = await websocket.recv()
#     print(response)

# async def main():
#     async with websockets.connect("ws://localhost:8765") as websocket:
#         while True:
#             try:
#                 number = float(input("Enter a number to be squared (Ctrl+C to exit): "))
#                 await send_number(websocket, number)
#             except ValueError:
#                 print("Invalid input. Please enter a valid number.")
#             except KeyboardInterrupt:
#                 print("\nExiting...")
#                 break

# # Run the main coroutine
# asyncio.run(main())



import asyncio
import websockets

async def connect_to_server():
    uri = "ws://127.0.0.1:12009"  # Replace with your EC2 instance's Public DNS and WebSocket port

    async with websockets.connect(uri) as websocket:
        while True:
            message = input("Enter a message to send to the server (or 'exit' to quit): ")
            
            if message.lower() == "exit":
                break

            await websocket.send(message)
            response = await websocket.recv()
            print(f"Server response: {response}")

asyncio.get_event_loop().run_until_complete(connect_to_server())
