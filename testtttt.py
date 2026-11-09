# import aiohttp
# import asyncio
# import time


# async def grab_api_data():
#     async with aiohttp.ClientSession() as session:
#         async with session.get('https://api.example.com/data') as response:
#             api_data = await response.json()
#             return api_data


# def process_data(data):
#     # Process the data
#     print(data)


# async def fetch_and_process_data():
#     data = await grab_api_data()
#     process_data(data)


# def update_screen():
#     # Code to update the screen
#     print("Updating screen...")


# async def main():
#     # Schedule the fetch_and_process_data to run in a separate thread every hour
#     asyncio.create_task(asyncio.to_thread(fetch_and_process_data))
    
#     while True:
#         update_screen()
#         await asyncio.sleep(0.1)  # Adjust the sleep time as needed
#         # Check if it's time to fetch and process data
#         if int(time.time()) % 5 == 0:  # Every hour
#             asyncio.run(asyncio.to_thread(fetch_and_process_data))


# if __name__ == '__main__':
#     asyncio.run(main())


# import aiohttp
# import asyncio
# import time
# import json
# class pokemon:
#     def __init__(self,name):
#         self.name = name

#     async def grab_api_data(self):
#         async with aiohttp.ClientSession() as session:
#             async with session.get('https://pokeapi.co/api/v2/pokemon/empoleon') as response:
#                 api_data = await response.json()
#                 return api_data


#     def process_data(self,data):
#         # Process the data
#         print(data['name'])


#     async def fetch_and_process_data(self):
#         print(f"trying for a kid xd {self.name}")
#         data = await self.grab_api_data()
#         self.process_data(data)


# def update_screen():
#     # Code to update the screen
#     print("Updating screen...")


# async def main():
#     # Schedule the fetch_and_process_data to run every hour
#     with open("cachedArticles.json", 'r') as file:
#             print(json.load(file))
#     next_fetch_time = time.time()
#     poke = pokemon("qwerty")
#     poke2 = pokemon("12345")
#     while True:
#         update_screen()
#         await asyncio.sleep(0.1)  # Adjust the sleep time as needed
        
#         # Check if it's time to fetch and process data
#         if time.time() >= next_fetch_time:
#             asyncio.create_task(poke.fetch_and_process_data())
#             asyncio.create_task(poke2.fetch_and_process_data())
#             next_fetch_time = time.time() + 3  # Schedule next fetch in 1 hour


# if __name__ == '__main__':
#     asyncio.run(main())

import random

# Define the groups
groups = ['RED', 'BLUE', 'Cat WHITE', 'Strip BLUEKKK']

# Create a list of 8 slots with each group appearing exactly twice
slots = groups * 4

# Function to check if adjacent slots have the same group
def check_adjacent(slots):
    for i in range(1, len(slots)):
        if slots[i] == slots[i - 1]:
            return False
    return True

# Shuffle until the adjacent condition is met
while True:
    random.shuffle(slots)
    if check_adjacent(slots):
        break

# Assign the shuffled groups to the 8 slots
for i, group in enumerate(slots, start=1):
    print(f"Slot {i}: {group}")
