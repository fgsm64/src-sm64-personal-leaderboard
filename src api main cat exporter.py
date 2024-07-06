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
print("gaming")

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
            if pagination and pagination['links']:
                next_link = next((link['uri'] for link in pagination['links'] if link['rel'] == 'next'), None)
                url = next_link if next_link else None
            else:
                break
        else:
            break
    return runs

def fetch_user_data(username):
    try:
        user_id = get_user_id(username)
        if not user_id:
            return None, None
        
        game_id = get_game_id("Super Mario 64")
        if not game_id:
            return None, None
        
        user_runs = get_runs_by_user(user_id)
        if not user_runs:
            return None, None

        user_data = {"Username": username}
        detailed_data = {category: [] for category in ["0 Star", "1 Star", "16 Star", "70 Star", "120 Star"]}
        fastest_times = {category: float('inf') for category in ["0 Star", "1 Star", "16 Star", "70 Star", "120 Star"]}

        for run in user_runs:
            run_category = get_category_name(run['category'])
            if run['game'] == game_id and run_category in detailed_data and run['status']['status'] == 'verified':
                run_time = run['times']['primary_t']
                if run_time < fastest_times[run_category]:
                    fastest_times[run_category] = run_time

        for category, time in fastest_times.items():
            if time < float('inf'):
                formatted_time = format_time(time)
                user_data[category] = formatted_time
                detailed_data[category].append((username, time))
        
        return user_data, detailed_data
    except Exception as e:
        print(f"Error fetching data for {username}: {e}")
        return None, None

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    formatted_time = ""
    if hours > 0:
        formatted_time += f"{hours}:{minutes:02}:{seconds:02}"
    elif minutes > 0:
        formatted_time += f"{minutes}:{seconds:02}"
    else:
        formatted_time += f"{seconds}"
    
    return formatted_time

def export_all_users_to_excel(usernames):
    # Use the current directory
    export_dir = os.path.dirname(os.path.abspath(__file__))
    
    all_data = []
    detailed_data_all = {category: [] for category in ["0 Star", "1 Star", "16 Star", "70 Star", "120 Star"]}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_username = {executor.submit(fetch_user_data, username): username for username in usernames}
        for future in as_completed(future_to_username):
            username = future_to_username[future]
            user_data, detailed_data = future.result()
            if user_data:
                all_data.append(user_data)
                for category, details in detailed_data.items():
                    detailed_data_all[category].extend(details)

    # Sort the data by categories in ascending order
    sorted_categories = ["0 Star", "1 Star", "16 Star", "70 Star", "120 Star"]
    df_overall = pd.DataFrame(all_data, columns=["Username"] + sorted_categories)

    file_path = os.path.join(export_dir, "all_users_main_categories.xlsx")
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df_overall.to_excel(writer, sheet_name="Overall Main Categories", index=False)

        for category in sorted_categories:
            df_category = pd.DataFrame(detailed_data_all[category], columns=["Username", "Time"])
            df_category = df_category.sort_values(by="Time")
            df_category["Time"] = df_category["Time"].apply(format_time)
            df_category.insert(0, "Rank", range(1, len(df_category) + 1))
            df_category.to_excel(writer, sheet_name=category, index=False)
            worksheet = writer.sheets[category]
            worksheet.write(0, 0, category)

    print(f"Exported data to {file_path}")

goats = ["vadien", "xwicko", "piegolds", "oatslice", "montyvr", "raisn", "fgsm", "nahottv", "sanj", "twig64", "pegitheloca", "ghdevil666", "packerzilla", "lfoxy"]
export_all_users_to_excel(goats)

print(time.process_time() - start)
