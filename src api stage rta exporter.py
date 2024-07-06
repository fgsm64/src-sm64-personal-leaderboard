import requests
import pandas as pd
import os
import xlsxwriter
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

start = time.process_time()

# Define the base URL for the Speedrun.com API
base_url = "https://www.speedrun.com/api/v1"

@lru_cache(maxsize=1000)
def get_game_id(game_name):
    response = requests.get(f"{base_url}/games", params={"name": game_name})
    if response.status_code == 200:
        games = response.json()['data']
        for game in games:
            if game['names']['international'].lower() == game_name.lower():
                return game['id']
    return None

@lru_cache(maxsize=1000)
def get_user_id(username):
    response = requests.get(f"{base_url}/users/{username}")
    if response.status_code == 200:
        user_details = response.json()['data']
        return user_details['id']
    else:
        return None

@lru_cache(maxsize=1000)
def get_category_name(category_id):
    response = requests.get(f"{base_url}/categories/{category_id}")
    if response.status_code == 200:
        category_details = response.json()['data']
        return category_details['name']
    else:
        return "Unknown Category"

@lru_cache(maxsize=1000)
def get_level_name(level_id):
    response = requests.get(f"{base_url}/levels/{level_id}")
    if response.status_code == 200:
        level_details = response.json()['data']
        return level_details['name']
    else:
        return "Unknown Level"

def get_runs_by_user(user_id):
    runs = []
    url = f"{base_url}/runs"
    params = {"user": user_id, "max": 200}  # Set max results per page
    while url:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            runs.extend(data['data'])
            # Check if there is a next page
            pagination = data.get('pagination')
            if pagination and pagination.get('links'):
                next_link = next((link['uri'] for link in pagination['links'] if link['rel'] == 'next'), None)
                url = next_link
                params = {}  # Reset params for next page
            else:
                break
        else:
            break
    return runs

def convert_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.3f}"

def get_level_runs(username):
    level_order = [
        "Bob-omb Battlefield",
        "Whomp's Fortress",
        "Jolly Roger Bay",
        "Cool, Cool Mountain",
        "Big Boo's Haunt",
        "Hazy Maze Cave",
        "Lethal Lava Land",
        "Shifting Sand Land",
        "Dire, Dire Docks",
        "Snowman's Land",
        "Wet-Dry World",
        "Tall, Tall Mountain",
        "Tiny-Huge Island",
        "Tick Tock Clock",
        "Rainbow Ride"
    ]

    acronyms = [
        "BOB",
        "WF",
        "JRB",
        "CCM",
        "BBH",
        "HMC",
        "LLL",
        "SSL",
        "DDD",
        "SL",
        "WDW",
        "TTM",
        "THI",
        "TTC",
        "RR"
    ]

    level_name_to_acronym = dict(zip(level_order, acronyms))

    game_name = "Super Mario 64"
    game_id = get_game_id(game_name)
    if not game_id:
        print("Failed to retrieve game ID.")
        return {}

    user_id = get_user_id(username)
    if not user_id:
        print("Failed to retrieve user ID.")
        return {}

    print(f"Fetching level runs for user: {username}")

    all_runs = get_runs_by_user(user_id)
    if not all_runs:
        print("Failed to retrieve runs or no runs found.")
        return {}

    level_runs = [run for run in all_runs if run['game'] == game_id and run['level'] and run['status']['status'] == 'verified']
    fastest_runs = {}

    for run in level_runs:
        time = run['times']['primary_t']
        category_id = run['category']
        level_id = run['level']
        key = (level_id, category_id)

        if key not in fastest_runs or time < fastest_runs[key]['times']['primary_t']:
            fastest_runs[key] = run

    user_data = {"Username": username}
    detailed_data = {acronym: [] for acronym in acronyms}
    for level_name in level_order:
        user_data[level_name_to_acronym[level_name]] = ""
        for key, run in fastest_runs.items():
            level_id, category_id = key
            if get_level_name(level_id) == level_name:
                time_seconds = run['times']['primary_t']
                time_formatted = convert_time(time_seconds)
                user_data[level_name_to_acronym[level_name]] = time_formatted
                detailed_data[level_name_to_acronym[level_name]].append((username, time_formatted))
                break
    return user_data, detailed_data

def fetch_user_data(username):
    try:
        return get_level_runs(username)
    except Exception as e:
        print(f"Error fetching data for {username}: {e}")
        return None, None

def export_all_users_to_excel(usernames):
    # Use the current directory
    export_dir = os.path.dirname(os.path.abspath(__file__))
    
    all_data = []
    detailed_data_all = {acronym: [] for acronym in [
        "BOB", "WF", "JRB", "CCM", "BBH", "HMC", "LLL", "SSL", "DDD", "SL", "WDW", "TTM", "THI", "TTC", "RR"
    ]}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_username = {executor.submit(fetch_user_data, username): username for username in usernames}
        for future in as_completed(future_to_username):
            username = future_to_username[future]
            user_data, detailed_data = future.result()
            if user_data:
                all_data.append(user_data)
                for level_acronym, details in detailed_data.items():
                    detailed_data_all[level_acronym].extend(details)

    df_overall = pd.DataFrame(all_data)

    file_path = os.path.join(export_dir, "all_users_level_runs.xlsx")
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df_overall.to_excel(writer, sheet_name="Overall Level Times", index=False)

        for level_acronym in detailed_data_all:
            df_level = pd.DataFrame(detailed_data_all[level_acronym], columns=["Username", "Time"])
            df_level = df_level.sort_values(by="Time")
            df_level.insert(0, "Rank", range(1, len(df_level) + 1))
            df_level.to_excel(writer, sheet_name=level_acronym, index=False)
            worksheet = writer.sheets[level_acronym]
            worksheet.write(0, 0, level_acronym)

    print(f"Exported data to {file_path}")


goats = ["vadien", "xwicko", "piegolds", "oatslice", "montyvr", "raisn", "fgsm", "nahottv", "sanj", "twig64", "pegitheloca", "ghdevil666", "packerzilla", "lfoxy"]
export_all_users_to_excel(goats)

print(time.process_time() - start)