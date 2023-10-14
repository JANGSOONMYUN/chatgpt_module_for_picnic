import asyncio
import websockets

async def send_number(websocket, number):
    await websocket.send(str(number))
    response = await websocket.recv()
    print(response)

async def main():
    async with websockets.connect("ws://localhost:8765") as websocket:
        while True:
            try:
                number = float(input("Enter a number to be squared (Ctrl+C to exit): "))
                await send_number(websocket, number)
            except ValueError:
                print("Invalid input. Please enter a valid number.")
            except KeyboardInterrupt:
                print("\nExiting...")
                break

# Run the main coroutine
asyncio.run(main())
