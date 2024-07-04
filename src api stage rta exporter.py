import requests
import pandas as pd
import os

# Define the base URL for the Speedrun.com API
base_url = "https://www.speedrun.com/api/v1"

# Function to get game ID by game name
def get_game_id(game_name):
    response = requests.get(f"{base_url}/games", params={"name": game_name})
    if response.status_code == 200:
        games = response.json()['data']
        for game in games:
            if game['names']['international'].lower() == game_name.lower():
                return game['id']
    return None

# Function to get user ID by username
def get_user_id(username):
    response = requests.get(f"{base_url}/users/{username}")
    if response.status_code == 200:
        user_details = response.json()['data']
        return user_details['id']
    else:
        return None

# Function to get category name by category ID
def get_category_name(category_id):
    response = requests.get(f"{base_url}/categories/{category_id}")
    if response.status_code == 200:
        category_details = response.json()['data']
        return category_details['name']
    else:
        return "Unknown Category"

# Function to get level name by level ID
def get_level_name(level_id):
    response = requests.get(f"{base_url}/levels/{level_id}")
    if response.status_code == 200:
        level_details = response.json()['data']
        return level_details['name']
    else:
        return "Unknown Level"

# Function to get runs by user ID with pagination
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

# Function to convert time in seconds to minutes:seconds.milliseconds format
def convert_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.3f}"

# Main function to get level runs for a user and export to Excel
def get_level_runs(username):
    # Define the desired order of levels
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
        "Rainbow Ride",
        "Tick Tock Clock"
    ]

    # Get the game ID
    game_name = "Super Mario 64"
    game_id = get_game_id(game_name)
    if not game_id:
        print("Failed to retrieve game ID.")
        return

    # Get the user ID
    user_id = get_user_id(username)
    if not user_id:
        print("Failed to retrieve user ID.")
        return

    print(f"Fetching level runs for user: {username}")

    # Get all runs for the user with pagination
    all_runs = get_runs_by_user(user_id)
    if not all_runs:
        print("Failed to retrieve runs or no runs found.")
        return

    # Filter runs to include only those for the specified game and accepted runs
    level_runs = [run for run in all_runs if run['game'] == game_id and run['level'] and run['status']['status'] == 'verified']
    fastest_runs = {}

    # Find the fastest run for each level and category
    for run in level_runs:
        time = run['times']['primary_t']
        category_id = run['category']
        level_id = run['level']
        key = (level_id, category_id)

        if key not in fastest_runs or time < fastest_runs[key]['times']['primary_t']:
            fastest_runs[key] = run

    # Prepare data for export
    data = []
    for level_name in level_order:
        for key, run in fastest_runs.items():
            level_id, category_id = key
            if get_level_name(level_id) == level_name:
                time_seconds = run['times']['primary_t']
                time_formatted = convert_time(time_seconds)
                category_name = get_category_name(category_id)
                date = run['date']
                data.append([username, level_name, category_name, time_formatted, date])

    # Create a DataFrame and export to Excel
    df = pd.DataFrame(data, columns=["Username", "Level", "Category", "Time", "Date"])

    # Ensure the 'exports' directory exists
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    # Export the DataFrame to an Excel file in the 'exports' directory
    file_path = os.path.join(export_dir, f"{username}_level_runs.xlsx")
    df.to_excel(file_path, index=False)
    print(f"Exported data to {file_path}")

goats = ["vadien", "xwicko", "piegolds", "oatslice", "montyvr", "raisn", "fgsm", "nahottv", "sanj", "twig64", "pegitheloca", "ghdevil666", "packerzilla", "lfoxy"]

#get_level_runs("fgsm")

for runner in goats:
    get_level_runs(runner)
