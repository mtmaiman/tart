# Standard library
import logging
import argparse
import json
import sys
import re

# Imported libraries
import requests


USAGE = f'''
tart.py -Command "Arguments"\n\n
A lightweigth python CLI for tracking task, hideout, and barter progression, including item collection, for Escape From Tarkov. Please read below for usage notes and command details.\n\n
Notes:\n\n
> Surround command arguments with whitespace in quotations \' or \"'
> Command arguments expect the entity normalized names or GUIDs. Please use search functions to find these if you are unsure
'''
DEV_MODE = True
ITEM_HEADER = '{:<25} {:<60} {:<30} {:<25}\n'.format('Item Short Name', 'Item Normalized Name', 'Item GUID', 'Have (FIR) Need (FIR)')
MAP_HEADER = '{:<30} {:<20}\n'.format('Map Normalized Name', 'Map GUID')
TRADER_HEADER = '{:<30} {:<20}\n'.format('Trader Normalized Name', 'Trader GUID')
INVENTORY_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Have (FIR) Need (FIR)', 'Item', 'Have (FIR) Need (FIR)', 'Item', 'Have (FIR) Need (FIR)')
INVENTORY_HAVE_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Have (FIR)', 'Item', 'Have (FIR)', 'Item', 'Have (FIR)')
INVENTORY_NEEDED_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Need (FIR)', 'Item', 'Need (FIR)', 'Item', 'Need (FIR)')
TASK_HEADER = '{:<40} {:<20} {:<20} {:<20} {:<20}\n'.format('Task Title', 'Task Giver', 'Task Status', 'Tracked', 'Kappa?')
HIDEOUT_HEADER = '{:<40} {:<20} {:<20}\n'.format('Station Name', 'Station Status', 'Tracked')
BARTER_HEADER = '{:<40} {:<20} {:<20} {:<20}\n'.format('Barter GUID', 'Trader', 'Level', 'Tracked')
UNTRACKED_HEADER = '{:<40} {:<20} {:<20}\n'.format('Entity Name', 'Type', 'Tracked')
BUFFER = '-------------------------------------------------------------------------------------------------------------------------------------\n'


###################################################
#                                                 #
# WORKER FUNCTIONS                                #
#                                                 #
###################################################


def parser(command):
    if (DEV_MODE):
        logging.info('RUNNING IN DEBUG MODE. All changes will affect only the debug database file!')
        tracker_file = './bin/debug_tracker.json'
    else:
        tracker_file = './bin/tracker.json'

    parser = argparse.ArgumentParser(prog = 'tart.py', usage = USAGE)

    # Inventory
    parser.add_argument('-Inventory', '-inventory', '-i', action = "store_true", help = 'Lists all items in the player\'s inventory')
    parser.add_argument('-InventoryTasks', '-inventorytasks', '-it', action = "store_true", help = 'Lists all items in the player\'s inventory pertaining to tasks')
    parser.add_argument('-InventoryStations', '-inventorystations', '-is', action = "store_true", help = 'Lists all items in the player\'s inventory pertaining to hideout stations')
    parser.add_argument('-InventoryBarters', '-inventorybarters', '-ib', action = "store_true", help = 'Lists all items in the player\'s inventory pertaining to barters')
    parser.add_argument('-Have', '-have', action = "store_true", help = 'Lists all items the player currently has')
    parser.add_argument('-Need', '-need', action = "store_true", help = 'Lists all remaining items that the player needs for tasks, hideout stations, and tracked barters')

    # List entities
    parser.add_argument('-Tasks', '-tasks', '-t', type = str, help = '"{str}" Lists tracked and available tasks by [All, Map, Trader]', nargs = 1, default = False)
    parser.add_argument('-Stations', '-stations', '-Hideout', '-hideout', '-st', action = "store_true", help = 'Lists tracked and available hideout stations')
    parser.add_argument('-Barters', '-barters', '-b', type = str, help = '"{str}" Lists tracked barters by [All, Trader]', nargs = 1, default = False)
    parser.add_argument('-Untracked', '-untracked', '-u', action = "store_true", help = 'Lists all untracked hideout stations and Kappa required tasks')

    # List consts
    parser.add_argument('-Maps', '-maps', '-m', action = "store_true", help = 'Lists available maps')
    parser.add_argument('-Traders', '-traders', '-tr', action = "store_true", help = 'Lists available traders')

    # Reset
    parser.add_argument('-ResetTasks', '-resettasks', action = "store_true", help = 'Resets all task progress')
    parser.add_argument('-ResetStations', '-resetstations', '-ResetHideout', '-resethideout', action = "store_true", help = 'Resets all hideout station progress')
    parser.add_argument('-ResetBarters', '-resetbarters', action = "store_true", help = 'Resets all barter progress and tracking')
    parser.add_argument('-RestartBarter', '-restartbarter', type = str, help = '"{str}" Restarts the barter of given GUID and adds the required items to needed inventory again (Use after completing a barter and wishing to do it again', nargs = 1, default = False)
    parser.add_argument('-ResetInventory', '-resetinventory', action = "store_true", help = 'Removes all items from the player\'s inventory')
    parser.add_argument('-ResetAll', '-resetall', action = "store_true", help = 'Resets all progress and clears the player\'s inventory')
    parser.add_argument('-Refresh', '-refresh', action = "store_true", help = 'Pulls updated game data from api.tarkov.dev. (WARNING: This will also reset all progression and clear the player\'s inventory!)')

    # Searching
    parser.add_argument('-Search', '-search', '-s', type = str, help = '"{str}" Searches for this normalized name', nargs = 1, default = False)
    parser.add_argument('-GUID', '-guid', '-g', type = str, help = '"{str}" Searches for this GUID', nargs = 1, default = False)
    parser.add_argument('-FuzzySearch', '-fuzzysearch', '-f', type = str, help = '"{str}" Searches for any entity containing this text. (WARNING: This may take a while!)', nargs = 1, default = False)
    parser.add_argument('-Requires', '-requires', '-r', type = str, help = '"{str}" Lists all entites which require this item', nargs = 1, default = False)
    parser.add_argument('-IgnoreBarters', '-ignorebarters', '-nob', action = "store_true", help = 'Ignores barters from searches')

    # Tracking
    parser.add_argument('-Track', '-track', type = str, help = '"{str}" Begins tracking the specified task, hideout station, or barter and adds required items to the needed inventory', nargs = '+', default = False)
    parser.add_argument('-Untrack', '-untrack', type = str, help = '"{str}" Stops tracking the specified task, hideout station, or barter and removes required items from the needed inventory', nargs = '+', default = False)

    # Completing
    parser.add_argument('-Complete', '-complete', type = str, help = '"{str}" Marks the specified task, hideout station, or barter as complete', nargs = '+', default = False)
    parser.add_argument('-Force', '-force', action = "store_true", help = 'Forces the entity to complete regardless if enough items are found in the player\'s inventory')
    parser.add_argument('-RecursiveForce', '-recursiveforce', action = "store_true", help = 'Forces the entity and all prerequisite entities to recursively complete regardless if enough items are found in the player\'s inventory')

    # Items
    parser.add_argument('-AddItemFIR', '-additemfir', '-fir', type = str, help = '"{str}" Adds the specified item in shortname notation to the player\'s inventory with Found In Raid (FIR) status', nargs = '+', default = False)
    parser.add_argument('-AddItemNIR', '-additemnir', '-nir', type = str, help = '"{str}" Adds the specified item in shortname notation to the player\'s inventory without Found In Raid (FIR) status', nargs = '+', default = False)
    parser.add_argument('-Count', '-count', '-c', type = int, help = '{int} The amount of an item to add to the player\'s inventory. This is required with either -AddItem commands', default = False)

    # Level
    parser.add_argument('-Level', '-level', action = "store_true", help = 'Displays the player\'s current level')
    parser.add_argument('-LevelUp', '-levelup', '-up', action = "store_true", help = 'Increments the player\'s level by one (1)')
    parser.add_argument('-SetLevel', '-setlevel', type = int, help = '{int} Sets the player to the specified level', default = False)

    parsed = parser.parse_args(command)

    # Inventory
    if (parsed.Inventory):
        list_inventory(tracker_file)
    if (parsed.InventoryTasks):
        list_inventory_tasks(tracker_file)
    if (parsed.InventoryStations):
        list_inventory_stations(tracker_file)
    if (parsed.InventoryBarters):
        list_inventory_barters(tracker_file)
    if (parsed.Have):
        list_owned_items(tracker_file)
    if (parsed.Need):
        list_needed_items(tracker_file)

    # List entities
    if (parsed.Tasks):
        list_tasks(tracker_file, normalize(''.join(parsed.Tasks)))
    if (parsed.Stations):
        list_stations(tracker_file)
    if (parsed.Barters):
        list_barters(tracker_file, normalize(''.join(parsed.Barters)))
    if (parsed.Untracked):
        list_untracked(tracker_file)

    # List consts
    if (parsed.Maps):
        list_maps(tracker_file)
    if (parsed.Traders):
        list_traders(tracker_file)
    
    # Reset
    if (parsed.ResetTasks):
        logging.warning('This will reset all progress on tasks! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            reset_tasks(tracker_file)
        else:
            logging.info('Aborted task reset.')
    if (parsed.ResetStations):
        logging.warning('This will reset all progress on hideout stations! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            reset_stations(tracker_file)
        else:
            logging.info('Aborted hideout reset.')
    if (parsed.ResetBarters):
        logging.warning('This will reset all progress on barters! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            reset_barters(tracker_file)
        else:
            logging.info('Aborted barter reset.')
    if (parsed.RestartBarter):
        restart_barter(tracker_file, parsed.RestartBarter)
    if (parsed.ResetInventory):
        logging.warning('This will clear all items from the player\'s inventory! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            reset_inventory(tracker_file)
        else:
            logging.info('Aborted item reset.')
    if (parsed.ResetAll):
        logging.warning('This will reset all progress and clear the player\'s inventory! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            reset_tasks(tracker_file)
            reset_stations(tracker_file)
            reset_barters(tracker_file)
            reset_inventory(tracker_file)
        else:
            logging.info('Aborted reset.')
    if (parsed.Refresh):
        logging.warning('This will refresh all application data with the latest from api.tarkov.dev! Are you sure you wish to proceed? (Y/N)')

        if (input('> ').lower() == 'y'):
            refresh(tracker_file)
        else:
            logging.info('Aborted refresh.')

    # Searching
    if (parsed.Search):
        search(tracker_file, super_normalize(''.join(parsed.Search)), parsed.IgnoreBarters)
    if (parsed.GUID):
        guid(tracker_file, normalize(''.join(parsed.GUID)), parsed.IgnoreBarters)
    if (parsed.FuzzySearch):
        fuzzy_search(tracker_file, normalize(''.join(parsed.FuzzySearch)), parsed.IgnoreBarters)
    if (parsed.Requires):
        requires(tracker_file, normalize(''.join(parsed.Requires)), parsed.IgnoreBarters)

    # Tracking
    if (parsed.Track):
        track(tracker_file, normalize(''.join(parsed.Track)))
    if (parsed.Untrack):
        untrack(tracker_file, normalize(''.join(parsed.Untrack)))

    # Completing
    if (parsed.Complete):
        complete(tracker_file, normalize(''.join(parsed.Complete)), parsed.Force, parsed.RecursiveForce)

    # Items
    if (parsed.AddItemFIR and parsed.Count):
        add_item_fir(tracker_file, normalize(''.join(parsed.AddItemFIR)), parsed.Count)
    if (parsed.AddItemNIR and parsed.Count):
        add_item_nir(tracker_file, normalize(''.join(parsed.AddItemNIR)), parsed.Count)
    
    # Level
    if (parsed.Level):
        check_level(tracker_file)
    if (parsed.LevelUp):
        level_up(tracker_file)
    if (parsed.SetLevel):
        set_level(tracker_file, parsed.SetLevel)
    
    return

# Database editing
def open_database(file_path):
    try:
        with open(file_path, 'r', encoding = 'utf-8') as open_file:
            file = json.load(open_file)
    except FileNotFoundError:
        logging.error('I couldn\'t find the tracker database file in the bin. Try doing a full refresh with -Refresh')
        exit(1)
    return file

def write_database(file_path, data):
    with open(file_path, 'w', encoding = 'utf-8') as open_file:
        open_file.write(json.dumps(data))
    return

# GUID to name or object
def guid_to_item(database, guid):
    for item in database['all_items']:
        if (item['id'] == guid):
            return item['shortName']
    
    return False

def guid_to_item_object(database, guid):
    for item in database['all_items']:
        if (item['id'] == guid):
            return item
    
    return False

def guid_to_task(database, guid):
    for task in database['tasks']:
        if (task['id'] == guid):
            return task['name']
        
    return False

def guid_to_station(database, guid):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                return level['normalizedName']
    
    return False

def guid_to_map(database, guid):
    for map in database['maps']:
        if (map['id'] == guid):
            return map['normalizedName']
    
    return False

def guid_to_trader(database, guid):
    for trader in database['traders']:
        if (trader['id'] == guid):
            return trader['normalizedName']
    
    return False

def guid_name_lookup(database, guid):
    normalized_name = guid_to_trader(database, guid)
    found = 'trader'

    if (not normalized_name):
        normalized_name = guid_to_map(database, guid)
        found = 'map'

        if (not normalized_name):
            normalized_name = guid_to_item(database, guid)
            found = 'item'

            if (not normalized_name):
                normalized_name = guid_to_task(database, guid)
                found = 'task'

                if (not normalized_name):
                    normalized_name = guid_to_station(database, guid)
                    found = 'station'

                    if (not normalized_name):
                        return False, None
    
    return normalized_name, found

# Name to GUID
def item_to_guid(database, item_name):
    for item in database['all_items']:
        if (item['shortName'].lower() == item_name or item['normalizedName'] == item_name):
            return item['id']
    
    return False

def task_to_guid(database, task_name):
    for task in database['tasks']:
        if (task['normalizedName'] == task_name):
            return task['id']
    
    return False

def station_to_guid(database, station_name):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['normalizedName'] == station_name):
                return level['id']
    
    return False

def map_to_guid(database, map_name):
    for map in database['maps']:
        if (map['normalizedName'] == map_name):
            return map['id']
    
    return False

def trader_to_guid(database, trader_name):
    for trader in database['traders']:
        if (trader['normalizedName'] == trader_name):
            return trader['id']
    
    return False

def name_guid_lookup(database, name):
    guid = trader_to_guid(database, name)
    found = 'trader'

    if (not guid):
        guid = map_to_guid(database, name)
        found = 'map'

        if (not guid):
            guid = item_to_guid(database, name)
            found = 'item'

            if (not guid):
                guid = task_to_guid(database, name)
                found = 'task'

                if (not guid):
                    guid = station_to_guid(database, name)
                    found = 'station'

                    if (not guid):
                        return False, None

    return guid, found

# Inventory functions
def get_fir_count_by_guid(database, guid):
    for this_guid in database['inventory'].keys():
        if (this_guid == guid):
            return database['inventory'][this_guid]['have_fir']
    
    return False

def get_nir_count_by_guid(database, guid):
    for this_guid in database['inventory'].keys():
        if (this_guid == guid):
            return database['inventory'][this_guid]['have_nir']
    
    return False

# String functions
def is_guid(text):
    if (len(text) == 24 and text[0].isdigit()):
        return True
    if (len(text) > 24 and text[0].isdigit() and text[24] == '-'):
        return True
    
    return False

def normalize(text):
    normalized = text.lower().replace('-',' ')
    normalized = re.sub(' +', ' ', normalized)
    normalized = normalized.replace(' ','-')
    return normalized

def super_normalize(text):
    super_normalized = text.lower().replace('-',' ')
    super_normalized = super_normalized.replace('the', '')
    super_normalized = re.sub(' +', ' ', super_normalized)
    super_normalized = super_normalized.replace(' ','')
    return super_normalized

# Verify functions
def verify_task(database, task, task_table):
    if (task['status'] == 'complete'):
        return False
    
    if (not task['tracked']):
        return False
    
    if (database['player_level'] < task['minPlayerLevel']):
        return False
    
    for prereq in task['taskRequirements']:
        if (task_table[prereq['id']] == 'incomplete'):
            return False
    
    return True

def verify_hideout_level(station, level):
    max_level = 0

    if (not level['tracked']):
        return False
    
    if (level['status'] == 'complete'):
        return False

    for prereq in level['stationLevelRequirements']:
        if (prereq['level'] > max_level):
            max_level = prereq['level']

    for prereq_level in station['levels']:
        if (prereq_level['level'] <= max_level and prereq_level['status'] == 'incomplete'):
            return False
        
    return True

def verify_barter(barter):
    if (barter['status'] == 'complete' or not barter['tracked']):
        return False
    
    return True

# Get functions
def get_items_needed_for_tasks(database):
    items = {}

    for task in database['tasks']:
        for objective in task['objectives']:
            if (task['tracked']):
                if (objective['type'] == 'giveItem'):
                    guid = objective['item']['id']

                    if (guid not in items.keys()):
                        items[guid] = {
                            'need_fir': 0,
                            'need_nir': 0,
                            'have_fir': 0,
                            'have_nir': 0
                        }

                    if (objective['foundInRaid']):
                        items[guid]['need_fir'] = items[guid]['need_fir'] + objective['count']
                    else:
                        items[guid]['need_nir'] = items[guid]['need_nir'] + objective['count']

    for guid in database['inventory'].keys():
        if (guid in items.keys()):
            items[guid]['have_fir'] = database['inventory'][guid]['have_fir']
            items[guid]['have_nir'] = database['inventory'][guid]['have_nir']

    return items

def get_items_needed_for_stations(database):
    items = {}

    for station in database['hideout']:
        for level in station['levels']:
            if (level['tracked']):
                for item in level['itemRequirements']:
                    guid = item['item']['id']

                    if (guid not in items.keys()):
                        items[guid] = {
                        'need_fir': 0,
                        'need_nir': 0,
                        'have_fir': 0,
                        'have_nir': 0
                    }

                    items[guid]['need_nir'] = items[guid]['need_nir'] + item['count']
    
    for guid in database['inventory'].keys():
        if (guid in items.keys()):
            items[guid]['have_fir'] = database['inventory'][guid]['have_fir']
            items[guid]['have_nir'] = database['inventory'][guid]['have_nir']

    return items

def get_items_needed_for_barters(database):
    items = {}

    for barter in database['barters']:
        if (barter['tracked']):
            for item in barter['requiredItems']:
                guid = item['item']['id']

                if (guid not in items.keys()):
                    items[guid] = {
                        'need_fir': 0,
                        'need_nir': 0,
                        'have_fir': 0,
                        'have_nir': 0
                    }

                items[guid]['need_nir'] = items[guid]['need_nir'] + item['count']
    
    for guid in database['inventory'].keys():
        if (guid in items.keys()):
            items[guid]['have_fir'] = database['inventory'][guid]['have_fir']
            items[guid]['have_nir'] = database['inventory'][guid]['have_nir']

    return items

def get_items_owned(database):
    items = {}

    for guid in database['inventory'].keys():
        if (guid not in items.keys()):
            items[guid] = {
                'have_fir': 0,
                'have_nir': 0
            }
        
        items[guid]['have_fir'] = database['inventory'][guid]['have_fir']
        items[guid]['have_nir'] = database['inventory'][guid]['have_nir']

    for guid in list(items.keys()):
        if (items[guid]['have_fir'] == 0 and items[guid]['have_nir'] == 0):
            del items[guid]

    return items

def get_items_needed(database):
    items = {}

    for guid in database['inventory'].keys():
        if (guid not in items.keys()):
            items[guid] = {
                'need_fir': 0,
                'need_nir': 0
            }

        items[guid]['need_fir'] = database['inventory'][guid]['need_fir'] - database['inventory'][guid]['have_fir']
        items[guid]['need_nir'] = database['inventory'][guid]['need_nir'] - database['inventory'][guid]['have_nir']

    for guid in list(items.keys()):
        if (items[guid]['need_fir'] < 1 and items[guid]['need_nir'] < 1):
            del items[guid]

    return items

def get_tasks_by_map(database, guid):
    tasks = []
    task_table = {}

    for task in database['tasks']:
        task_table[task['id']] = task['status']

    for task in database['tasks']:
        if (not verify_task(database, task, task_table)):
            continue

        for objective in task['objectives']:
            if (len(objective['maps']) == 0):
                tasks.append(task)
                break

            for map in objective['maps']:
                if (map['id'] == guid):
                    tasks.append(task)
                    break

    return tasks

def get_tasks_by_trader(database, guid):
    tasks = []
    task_table = {}

    for task in database['tasks']:
        task_table[task['id']] = task['status']

    for task in database['tasks']:
        if (task['trader']['id'] == guid and verify_task(database, task, task_table)):
            tasks.append(task)

    return tasks

def get_available_tasks(database):
    tasks = []
    task_table = {}

    for task in database['tasks']:
        task_table[task['id']] = task['status']

    for task in database['tasks']:
        if (verify_task(database, task, task_table)):
            tasks.append(task)

    return tasks

def get_hideout_stations(database):
    hideout_stations = []

    for station in database['hideout']:
        for level in station['levels']:
            if (verify_hideout_level(station, level)):
                hideout_stations.append(level)
    
    return hideout_stations

def get_barters(database):
    barters = []

    for barter in database['barters']:
        if (verify_barter(barter)):
            barters.append(barter)

    return barters

def get_barters_by_trader(database, guid):
    barters = []

    for barter in database['barters']:
        if (verify_barter(barter) and barter['trader']['id'] == guid):
            barters.append(barter)

    return barters

def get_untracked(database):
    untracked = []

    for task in database['tasks']:
        if (not task['tracked'] and task['kappaRequired']):
            untracked.append({
                'type': 'task',
                'entity': task
            })

    for station in database['hideout']:
        for level in station['levels']:
            if (not level['tracked']):
                untracked.append({
                    'type': 'hideout',
                    'entity': level
                })
    
    return untracked

# Track functions
def track_task(database, guid):
    for task in database['tasks']:
        if (task['id'] == guid):
            if (task['tracked']):
                logging.info(f'Task {task["name"]} is already tracked. Skipping')
                return False
            
            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    count = objective['count']

                    if (objective['foundInRaid']):
                        database['inventory'][item_guid]['need_fir'] = database['inventory'][item_guid]['need_fir'] + count
                        logging.info(f'Added {count} {guid_to_item(database, item_guid)} to needed (FIR) inventory')
                    else:
                        database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] + count
                        logging.info(f'Added {count} {guid_to_item(database, item_guid)} to needed inventory')

            task['tracked'] = True
            logging.info(f'Tracked task {task["name"]}')
                
    return database

def track_station(database, guid):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (level['tracked']):
                    logging.info(f'Hideout station {level["normalizedName"]} is already tracked. Skipping')
                    return False
                
                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    count = requirement['count']
                    database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] + count
                    logging.info(f'Added {count} {guid_to_item(database, item_guid)} to needed inventory')

                level['tracked'] = True
                logging.info(f'Tracked hideout station {level["normalizedName"]}')
                
    return database

def track_barter(database, guid):
    for barter in database['barters']:
        if (barter['id'] == guid):
            if (barter['tracked']):
                logging.info(f'Barter {barter["id"]} is already tracked. Skipping')
                return False
            
            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                count = requirement['count']
                database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] + count
                logging.info(f'Added {count} {guid_to_item(database, item_guid)} to needed inventory')

            barter['tracked'] = True
            logging.info(f'Tracked barter {barter["id"]}')
                
    return database

def untrack_task(database, guid):
    for task in database['tasks']:
        if (task['id'] == guid):
            if (not task['tracked']):
                logging.info(f'Task {task["name"]} is already untracked. Skipping')
                return False
            
            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    count = objective['count']

                    if (objective['foundInRaid']):
                        database['inventory'][item_guid]['need_fir'] = database['inventory'][item_guid]['need_fir'] - count
                        logging.info(f'Removed {count} {guid_to_item(database, item_guid)} from needed (FIR) inventory')
                    else:
                        database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                        logging.info(f'Removed {count} {guid_to_item(database, item_guid)} from needed inventory')

            task['tracked'] = False
            logging.info(f'Untracked task {task["name"]}')
                
    return database

def untrack_station(database, guid):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (not level['tracked']):
                    logging.info(f'Hideout station {level["normalizedName"]} is already untracked. Skipping')
                    return False
                
                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    count = requirement['count']
                    database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                    logging.info(f'Removed {count} {guid_to_item(database, item_guid)} from needed inventory')

                level['tracked'] = False
                logging.info(f'Untracked hideout station {level["normalizedName"]}')
                
    return database

def untrack_barter(database, guid):
    for barter in database['barters']:
        if (barter['id'] == guid):
            if (not barter['tracked']):
                logging.info(f'Barter {barter["id"]} is already untracked. Skipping')
                return False
            
            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                count = requirement['count']
                database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                logging.info(f'Removed {count} {guid_to_item(database, item_guid)} from needed inventory')

            barter['tracked'] = False
            logging.info(f'Untracked barter {barter["id"]}')
                
    return database

# Complete functions
def complete_task(database, guid, force):
    for task in database['tasks']:
        if (task['id'] == guid):
            if (task['status'] == 'complete'):
                logging.info(f'Task {task["name"]} is already complete. Skipping')
                return False

            if (not force):
                task_table = {}

                for seen_task in database['tasks']:
                    task_table[seen_task['id']] = seen_task['status']

                if (not verify_task(database, task, task_table)):
                    logging.error(f'Task {task["name"]} cannot be completed due to a verification error')
                    return False

                for objective in task['objectives']:
                    if (objective['type'] == 'giveItem'):
                        item_guid = objective['item']['id']

                        if (objective['foundInRaid']):
                            have_fir = get_fir_count_by_guid(database, item_guid)
                            need_fir = objective['count']
                            diff_fir = need_fir - have_fir

                            if (diff_fir > 0):
                                logging.error(f'{diff_fir} more {guid_to_item(database, item_guid)} required to complete this task. Use the -Force flag to override')
                                return False
                            else:
                                continue
                        else:
                            have_nir = get_nir_count_by_guid(database, item_guid)
                            need_nir = objective['count']
                            diff_nir = need_nir - have_nir

                            if (diff_nir > 0):
                                logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this task. Use the -Force flag to override')
                                return False
                            else:
                                continue

            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']

                    if (objective['foundInRaid']):
                        have_fir = get_fir_count_by_guid(database, item_guid)
                        need_fir = objective['count']
                        diff_fir = need_fir - have_fir

                        if (diff_fir > 0):
                            database['inventory'][item_guid]['have_fir'] = database['inventory'][item_guid]['have_fir'] + diff_fir
                            logging.info(f'Added {diff_fir} {guid_to_item(database, item_guid)} to the player\'s inventory as Found In Raid (FIR) to complete {task["name"]}')
                        
                        database['inventory'][item_guid]['consumed_fir'] = database['inventory'][item_guid]['consumed_fir'] + need_fir
                    else:
                        have_nir = get_nir_count_by_guid(database, item_guid)
                        need_nir = objective['count']
                        diff_nir = need_nir - have_nir

                        if (diff_nir > 0):
                            database['inventory'][item_guid]['have_nir'] = database['inventory'][item_guid]['have_nir'] + diff_nir
                            logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the player\'s inventory to complete {task["name"]}')
                        
                        database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + need_nir
            
            task['status'] = 'complete'
            logging.info(f'Set status of {task["name"]} to complete')
            break
    else:
        logging.error(f'Failed to find a matching task with GUID {guid}')

    return database

def complete_recursive_task(database, guid, force):
    database = complete_task(database, guid, force)

    for task in database['tasks']:
        if (task['id'] == guid):
            for prereq in task['taskRequirements']:
                database = complete_recursive_task(database, prereq['task']['id'], force)

    return database

def complete_station(database, guid, force):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (level['status'] == 'complete'):
                    logging.info(f'Hideout station {level["normalizedName"]} is already complete. Skipping')
                    return False

                if (not force):
                    if (not verify_hideout_level(station, level)):
                        logging.error(f'Hideout station {level["normalizedName"]} cannot be completed due to a verification error')
                        return False

                    for requirement in level['itemRequirements']:
                        item_guid = requirement['item']['id']
                        have_nir = get_nir_count_by_guid(database, item_guid)
                        need_nir = requirement['count']
                        diff_nir = need_nir - have_nir

                        if (diff_nir > 0):
                            logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this hideout station. Use the -Force flag to override')
                            return False
                        else:
                            continue

                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    have_nir = get_nir_count_by_guid(database, item_guid)
                    need_nir = requirement['count']
                    diff_nir = need_nir - have_nir

                    if (diff_nir > 0):
                        database['inventory'][item_guid]['have_nir'] = database['inventory'][item_guid]['have_nir'] + diff_nir
                        logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the player\'s inventory to complete {level["normalizedName"]}')
                    
                    database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + need_nir
                
                level['status'] = 'complete'
                logging.info(f'Set status of {level["normalizedName"]} to complete')
                break
        else:
            continue
        break
    else:
        logging.error(f'Failed to find a matching hideout station with guid {guid}')

    return database

def complete_barter(database, guid, force):
    for barter in database['barters']:
        if (barter['id'] == guid):
            if (barter['status'] == 'complete'):
                logging.info(f'Barter {barter["id"]} is already complete. Skipping')
                return False
            
            if (not barter['tracked']):
                logging.error(f'Please start tracking barter {barter["id"]} to complete it')
                return False

            if (not force):
                if (not verify_barter(barter)):
                    logging.error(f'Barter {barter["id"]} cannot be completed due to a verification error')
                    return False

                for requirement in barter['requiredItems']:
                    item_guid = requirement['item']['id']
                    have_nir = get_nir_count_by_guid(database, item_guid)
                    need_nir = requirement['count']
                    diff_nir = need_nir - have_nir

                    if (diff_nir > 0):
                        logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this barter. Use the -Force flag to override')
                        return False
                    else:
                        continue

            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                have_nir = get_nir_count_by_guid(database, item_guid)
                need_nir = requirement['count']
                diff_nir = need_nir - have_nir

                if (diff_nir > 0):
                    database['inventory'][item_guid]['have_nir'] = database['inventory'][item_guid]['have_nir'] + diff_nir
                    logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the player\'s inventory to complete {barter["id"]}')
                
                database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + need_nir
            
            barter['status'] = 'complete'
            logging.info(f'Set status of {barter["id"]} to complete')
            break
    else:
        logging.error(f'Failed to find a matching barter with GUID {guid}')

    return database

# Print functions
def print_bool(bool_value):
    if (bool_value):
        return 'true'
    else:
        return 'false'

def print_inventory(database, items):
    display = INVENTORY_HEADER + BUFFER
    items_in_this_row = 0

    for guid in items.keys():
        if (items[guid]["have_nir"] != 0 or items[guid]["have_fir"] != 0 or items[guid]["need_nir"] != 0 or items[guid]["need_fir"]):
            item_string = f'{items[guid]["have_nir"]} ({items[guid]["have_fir"]}) {items[guid]["need_nir"]} ({items[guid]["need_fir"]})'
            display = display + '{:<20} {:<25} '.format(guid_to_item(database, guid), item_string)
            items_in_this_row = items_in_this_row + 1
            
            if (items_in_this_row == 3):
                display = display.strip(' ') + '\n'
                items_in_this_row = 0
    
    display = display + '\n\n'
    print(display)
    return

def print_inventory_have(database, items):
    display = INVENTORY_HAVE_HEADER + BUFFER
    items_in_this_row = 0

    for guid in items.keys():
        item_string = f'{items[guid]["have_nir"]} ({items[guid]["have_fir"]})'
        display = display + '{:<20} {:<25} '.format(guid_to_item(database, guid), item_string)
        items_in_this_row = items_in_this_row + 1
        
        if (items_in_this_row == 3):
            display = display.strip(' ') + '\n'
            items_in_this_row = 0
    
    display = display + '\n\n'
    print(display)
    return

def print_inventory_needed(database, items):
    display = INVENTORY_NEEDED_HEADER + BUFFER
    items_in_this_row = 0

    for guid in items.keys():
        item_string = f'{items[guid]["need_nir"]} ({items[guid]["need_fir"]})'
        display = display + '{:<20} {:<25} '.format(guid_to_item(database, guid), item_string)
        items_in_this_row = items_in_this_row + 1
        
        if (items_in_this_row == 3):
            display = display.strip(' ') + '\n'
            items_in_this_row = 0
    
    display = display + '\n\n'
    print(display)
    return

def print_tasks(database, tasks):
    display = TASK_HEADER + BUFFER
    
    for task in tasks:
        display = display + '{:<40} {:<20} {:<20} {:<20} {:<20}\n'.format(task['name'], guid_to_trader(database, task['trader']['id']), task['status'], print_bool(task['tracked']), print_bool(task['kappaRequired']))

        for objective in task['objectives']:
            objective_string = '-->'

            if (objective['optional']):
                objective_string = objective_string + ' (OPT)'

            objective_string = objective_string + ' ' + objective['description']

            if ('count' in objective):
                objective_string = objective_string + f' ({objective["count"]})'

            if ('foundInRaid' in objective and objective['foundInRaid']):
                objective_string = objective_string + f' (FIR)'

            if ('skillLevel' in objective):
                objective_string = objective_string + f'({objective["skillLevel"]["level"]})'

            if ('exitStatus' in objective):
                objective_string = objective_string + f' // Exit with status {objective["exitStatus"]}'

            objective_string = objective_string + '\n'
            display = display + objective_string

        if (len(task['neededKeys']) > 0):
            for key_object in task['neededKeys']:
                for key in key_object['keys']:
                    key_string = '-->'
                    key_guid = key['id']
                    database = open_database(database)

                    for item in database['all_items']:
                        if (item['id'] == key_guid):
                            key_string = key_string + f' Acquire {item["shortName"]} key'
                    
                    key_string = key_string + '\n'
                    display = display + key_string
    
        display = display + '\n\n'

    print(display)
    return True

def print_hideout_stations(database, stations):
    display = HIDEOUT_HEADER + BUFFER

    for level in stations:
        display = display + '{:<40} {:<20} {:<20}\n'.format(level['normalizedName'], level['status'], print_bool(level['tracked']))

        for item in level['itemRequirements']:
            short_name = guid_to_item(database, item['item']['id'])
            count = item['count']
            display = display + f'--> Requires {count} {short_name}\n'
        
        display = display + '\n\n'

    print(display)
    return True

def print_barters(database, barters):
    display = BARTER_HEADER + BUFFER

    for barter in barters:
        display = display + '{:<40} {:<20} {:<20} {:<20}\n'.format(barter['id'], guid_to_trader(database, barter['trader']['id']), barter['level'], print_bool(barter['tracked']))

        for item in barter['requiredItems']:
            short_name = guid_to_item(database, item['item']['id'])
            count = item['count']
            display = display + f'--> Give {count} {short_name}\n'

        for item in barter['rewardItems']:
            short_name = guid_to_item(database, item['item']['id'])
            count = item['count']
            display = display + f'--> Receive {count} {short_name}\n'

        if (barter['taskUnlock'] is not None):
            display = display + f'--> Requires task {guid_to_task(database, barter["taskUnlock"]["id"])}\n'

        display = display + '\n\n'

    print(display)
    return True

def print_untracked(untracked):
    display = UNTRACKED_HEADER + BUFFER

    for untracked_object in untracked:
        if (untracked_object['type'] == 'task'):
            display = display + '{:<40} {:<20} {:<20}\n'.format(untracked_object['entity']['name'], 'task', print_bool(untracked_object['entity']['tracked']))
        else:
            display = display + '{:<40} {:<20} {:<20}\n'.format(untracked_object['entity']['normalizedName'], 'hideout station', print_bool(untracked_object['entity']['tracked']))
        
    print(display)
    return True

def print_items(items):
    display = ITEM_HEADER + BUFFER

    for item in items:
        item_display = f'{item["have_nir"]} ({item["have_fir"]}) {item["need_nir"]} ({item["need_fir"]})'
        display = display + '{:<25} {:<60} {:<30} {:<25}\n'.format(item['shortName'], item['normalizedName'], item['id'], item_display)

    display = display + '\n\n'
    print(display)
    return True

def print_maps(maps):
    display = MAP_HEADER + BUFFER

    for map in maps:
        display = display + '{:<30} {:<20}\n'.format(map['normalizedName'], map['id'])

    display = display + '\n\n'
    print(display)
    return True

def print_traders(traders):
    display = TRADER_HEADER + BUFFER

    for trader in traders:
        display = display + '{:<30} {:<20}\n'.format(trader['normalizedName'], trader['id'])

    display = display + '\n\n'
    print(display)
    return True

def print_search(database, tasks, stations, barters, items, traders, maps):
    if (len(tasks) > 0):
        print_tasks(database, tasks)
    
    if (len(stations) > 0):
        print_hideout_stations(database, stations)

    if (len(barters) > 0):
        print_barters(database, barters)

    if (len(items) > 0):
        print_items(items)

    if (len(traders) > 0):
        print_traders(traders)

    if (len(maps) > 0):
        print_maps(maps)

    return True


###################################################
#                                                 #
# INTERACTIVE FUNCTIONS                           #
#                                                 #
###################################################


# Inventory
def list_inventory(tracker_file):
    database = open_database(tracker_file)
    inventory = database['inventory']
    print_inventory(database, inventory)
    return True

def list_inventory_tasks(tracker_file):
    database = open_database(tracker_file)
    task_items = get_items_needed_for_tasks(database)

    if (not bool(task_items)):
        logging.info('Could not find any items needed for tasks')
    else:
        print_inventory(database, task_items)

    return True

def list_inventory_stations(tracker_file):
    database = open_database(tracker_file)
    station_items = get_items_needed_for_stations(database)

    if (not bool(station_items)):
        logging.info('Could not find any items needed for hideout stations')
    else:
        print_inventory(database, station_items)

    return True

def list_inventory_barters(tracker_file):
    database = open_database(tracker_file)
    barter_items = get_items_needed_for_barters(database)

    if (not bool(barter_items)):
        logging.info('Could not find any items needed for barters')
    else:
        print_inventory(database, barter_items)

    return True

def list_owned_items(tracker_file):
    database = open_database(tracker_file)
    owned_items = get_items_owned(database)
    
    if (not bool(owned_items)):
        logging.info('Your inventory is empty!')
    else:
        print_inventory_have(database, owned_items)

    return

def list_needed_items(tracker_file):
    database = open_database(tracker_file)
    needed_items = get_items_needed(database)
    
    if (not bool(needed_items)):
        logging.info('Congratulations, you have no items remaining to collect!')
    else:
        print_inventory_needed(database, needed_items)

    return

# List entities
def list_tasks(tracker_file, argument):
    database = open_database(tracker_file)
    guid, type = name_guid_lookup(database, argument)

    if (not guid and argument != 'all'):
        logging.error('Invalid arguments. Accepted arguments are [All, Map, Trader]')
        return False

    if (type == 'map'):
        tasks = get_tasks_by_map(database, guid)
    elif (type == 'trader'):
        tasks = get_tasks_by_trader(database, guid)
    else:
        tasks = get_available_tasks(database)

    if (len(tasks) == 0):
        logging.info('No available or tracked tasks')
    else:
        print_tasks(database, tasks)

    return True

def list_stations(tracker_file):
    database = open_database(tracker_file)
    stations = get_hideout_stations(database)

    if (len(stations) == 0):
        logging.info('No available or tracked hideout stations')
    else:
        print_hideout_stations(database, stations)
    
    return True

def list_barters(tracker_file, argument):
    database = open_database(tracker_file)
    guid, type = name_guid_lookup(database, argument)

    if (type == 'trader'):
        barters = get_barters_by_trader(database, guid)
    else:
        barters = get_barters(database)

    if (len(barters) == 0):
        logging.info('No available or tracked barters')
    else:
        print_barters(database, barters)
    
    return True

def list_untracked(tracker_file):
    database = open_database(tracker_file)
    untracked = get_untracked(database)

    if (len(untracked) == 0):
        logging.info('No untracked items')
    else:
        print_untracked(untracked)

    return True

# List maps or traders
def list_maps(tracker_file):
    database = open_database(tracker_file)
    maps = ', '.join(map['normalizedName'] for map in database['maps']).strip(', ')
    logging.info(f'Accepted map names are: {maps}')

def list_traders(tracker_file):
    database = open_database(tracker_file)
    traders = ', '.join(trader['normalizedName'] for trader in database['traders']).strip(', ')
    logging.info(f'Accepted trader names are: {traders}')

# Reset
def reset_tasks(tracker_file):
    database = open_database(tracker_file)
    
    for task in database['tasks']:
        task['status'] = 'incomplete'
        
        if (task['kappaRequired']):
            task['tracked'] = True
        else:
            task['tracked'] = False
    
    write_database(tracker_file, database)
    logging.info('All task progress has been reset')
    return True

def reset_stations(tracker_file):
    database = open_database(tracker_file)
    
    for station in database['hideout']:
        for level in station['levels']:
            level['status'] = 'incomplete'
            level['tracked'] = True
    
    write_database(tracker_file, database)
    logging.info('All hideout progress has been reset')
    return True

def reset_barters(tracker_file):
    database = open_database(tracker_file)
    
    for barter in database['barters']:
        barter['status'] = 'incomplete'
        barter['tracked'] = False
    
    write_database(tracker_file, database)
    logging.info('All barter progress has been reset')
    return True

def restart_barter(tracker_file, argument):
    return

def reset_inventory(tracker_file):
    database = open_database(tracker_file)
    
    for guid in database['inventory'].keys():
        database['inventory'][guid]['have_fir'] = 0
        database['inventory'][guid]['have_nir'] = 0
    
    write_database(tracker_file, database)
    logging.info('The player\'s inventory has been cleared')
    return True

def refresh(tracker_file):
    database = {
        'tasks': [],
        'hideout': [],
        'maps': [],
        'traders': [],
        'barters': [],
        'all_items': [],
        'inventory': {},
        'player_level': 1
    }

    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'query': """
            {
                tasks {
                    id
                    name
                    normalizedName
                    trader {
                        id
                    }
                    map {
                        id
                    }
                    minPlayerLevel
                    taskRequirements {
                        task {
                            id
                        }
                    }
                    traderRequirements {
                        id
                        requirementType
                        trader {
                            id
                        }
                    }
                    objectives {
                        id
                        type
                        description
                        optional
                        maps {
                            id
                        }
                        ... on TaskObjectiveExtract {
                            maps {
                                id
                            }
                            exitStatus
                            exitName
                            zoneNames
                        }
                        ... on TaskObjectiveItem {
                            id
                            count
                            foundInRaid
                            item {
                                id
                            }
                        }
                        ... on TaskObjectivePlayerLevel {
                            playerLevel
                        }
                        ... on TaskObjectiveQuestItem {
                            questItem {
                                id
                            }
                            count
                        }
                        ... on TaskObjectiveShoot {
                            targetNames
                            count
                            shotType
                            zoneNames
                            bodyParts
                            usingWeapon {
                                id
                            }
                            usingWeaponMods {
                                id
                            }
                            wearing {
                                id
                            }
                            notWearing {
                                id
                            }
                            distance {
                                value
                            }
                            playerHealthEffect {
                                bodyParts
                                effects
                                time {
                                    value
                                }
                            }
                            enemyHealthEffect {
                                bodyParts
                                effects
                                time {
                                    value
                                }
                            }
                            timeFromHour
                            timeUntilHour
                        }
                        ... on TaskObjectiveSkill {
                            skillLevel {
                                name
                                level
                            }
                        }
                        ... on TaskObjectiveTaskStatus {
                            task {
                                id
                            }
                            status
                        }
                        ... on TaskObjectiveTraderLevel {
                            trader {
                                id
                            }
                            level
                        }
                        ... on TaskObjectiveTraderStanding {
                            trader {
                                id
                            }
                            value
                        }
                        ... on TaskObjectiveUseItem {
                            useAny {
                                id
                            }
                            count
                            zoneNames
                        }
                    }
                    neededKeys {
                        keys {
                            id
                        }
                    }
                    kappaRequired
                    lightkeeperRequired
                }
            }
        """
    }
    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve task data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving task data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest task data from the api.tarkov.dev server')
        tasks = response.json()['data']['tasks']

    untracked_count = 0

    for task in tasks:
        task['status'] = 'incomplete'
        task['tracked'] = True

        if (not task['kappaRequired']):
            task['tracked'] = False
            untracked_count = untracked_count + 1
    
    logging.info(f'Untracked {untracked_count} tasks not required for Kappa')
    database['tasks'] = tasks

    data = {
        'query': """
            {
                hideoutStations {
                    id
                    normalizedName
                    levels {
                        id
                        level
                        itemRequirements {
                            id
                            count
                            item {
                                id
                            }
                        }
                        stationLevelRequirements {
                            level
                        }
                    }
                }
            }
        """
    }

    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve hideout data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving hideout data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest hideout data from the api.tarkov.dev server')
        hideout = response.json()['data']['hideoutStations']

    for station in hideout:
        for level in station['levels']:
            level['normalizedName'] = station['normalizedName'] + '-' + str(level['level'])

            if (level['normalizedName'] != 'stash-1'):
                level['status'] = 'incomplete'
            else:
                level['status'] = 'complete'
                logging.info('Automatically completed stash-1 hideout station')

            level['tracked'] = True

    database['hideout'] = hideout

    data = {
        'query': """
            {
                barters {
                    id
                    trader {
                    id
                    }
                    level
                    taskUnlock {
                    id
                    }
                    requiredItems {
                    item {
                        id
                    }
                    count
                    }
                    rewardItems {
                    item {
                        id
                    }
                    count
                    }
                }
            }
        """
    }

    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve barter data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving barter data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest barter data from the api.tarkov.dev server')
        barters = response.json()['data']['barters']

    for barter in barters:
        barter['status'] = 'incomplete'
        barter['tracked'] = False
    
    database['barters'] = barters

    data = {
        'query': """
            {
                maps {
                    id
                    normalizedName
                }
            }
        """
    }

    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve map data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving map data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest map data from the api.tarkov.dev server')
        database['maps'] = response.json()['data']['maps']

    data = {
        'query': """
            {
                traders {
                    id
                    normalizedName
                }
            }
        """
    }

    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve trader data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving trader data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest trader data from the api.tarkov.dev server')
        database['traders'] = response.json()['data']['traders']

    data = {
        'query': """
            {
                items {
                    id
                    normalizedName
                    shortName
                }
            }
        """
    }

    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        logging.error(f'Failed to retrieve item data! >> [{response.status_code}] {response.json()}')
        exit(1)
    else:
        if ('errors' in response.json().keys()):
                logging.error(f'Encountered an error while retrieving item data! >> {json.dumps(response.json())}')
                exit(1)

        logging.info('Retrieved latest item data from the api.tarkov.dev server')
        database['all_items'] = response.json()['data']['items']
    
    for task in database['tasks']:
        for objective in task['objectives']:
            if (objective['type'] == 'giveItem'):
                guid = objective['item']['id']

                if (guid not in database['inventory'].keys()):
                    database['inventory'][guid] = {
                        'need_fir': 0,
                        'need_nir': 0,
                        'have_fir': 0,
                        'have_nir': 0,
                        'consumed_fir': 0,
                        'consumed_nir': 0
                    }
                    
                if (objective['foundInRaid']):
                    database['inventory'][guid]['need_fir'] = database['inventory'][guid]['need_fir'] + objective['count']
                else:
                    database['inventory'][guid]['need_nir'] = database['inventory'][guid]['need_nir'] + objective['count']

    logging.info('Updated all inventory values for task items')

    for station in database['hideout']:
        for level in station['levels']:
            for requirement in level['itemRequirements']:
                guid = requirement['item']['id']

                if (guid not in database['inventory'].keys()):
                    database['inventory'][guid] = {
                        'need_fir': 0,
                        'need_nir': 0,
                        'have_fir': 0,
                        'have_nir': 0,
                        'consumed_fir': 0,
                        'consumed_nir': 0
                    }
                    
                database['inventory'][guid]['need_nir'] = database['inventory'][guid]['need_nir'] + requirement['count']

    logging.info('Updated all inventory values for hideout items')

    for map in database['maps']:
        if (map['normalizedName'] == 'streets-of-tarkov'):
            map['normalizedName'] = 'streets'
        elif (map['normalizedName'] == 'the-lab'):
            map['normalizedName'] = 'labs'
    
    logging.info('Overwrote normalized name for "Streets of Tarkov" to "streets" and for "The Lab" to "labs"')
    write_database(tracker_file, database)
    logging.info('Generated a new database file in /bin')
    return

# Searching
def search(tracker_file, argument, ignore_barters):
    database = open_database(tracker_file)
    tasks = []
    stations = []
    barters = []
    items = []
    traders = []
    maps = []

    for task in database['tasks']:
        if (super_normalize(task['name']).startswith(argument) or super_normalize(task['normalizedName']).startswith(argument)):
            tasks.append(task)

    for station in database['hideout']:
        for level in station['levels']:
            if (super_normalize(level['normalizedName']).startswith(argument)):
                stations.append(station)

    if (not ignore_barters):
        for barter in database['barters']:
            for requirement in barter['requiredItems']:
                item = guid_to_item_object(database, requirement['item']['id'])
                if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                    barters.append(barter)
            for reward in barter['rewardItems']:
                item = guid_to_item_object(database, reward['item']['id'])
                if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                    barters.append(barter)

    for item in database['all_items']:
        if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
            if (item['id'] in database['inventory'].keys()):
                items.append({
                    'need_fir': database['inventory'][item['id']]['need_fir'],
                    'need_nir': database['inventory'][item['id']]['need_nir'],
                    'have_fir': database['inventory'][item['id']]['have_fir'],
                    'have_nir': database['inventory'][item['id']]['have_nir'],
                    'consumed_fir': database['inventory'][item['id']]['consumed_fir'],
                    'consumed_nir': database['inventory'][item['id']]['consumed_nir'],
                    'shortName': item['shortName'],
                    'normalizedName': item['normalizedName'],
                    'id': item['id']
                })
            else:
                items.append({
                    'need_fir': 0,
                    'need_nir': 0,
                    'have_fir': 0,
                    'have_nir': 0,
                    'consumed_fir': 0,
                    'consumed_nir': 0,
                    'shortName': item['shortName'],
                    'normalizedName': item['normalizedName'],
                    'id': item['id']
                })

    for trader in database['traders']:
        if (super_normalize(trader['normalizedName']).startswith(argument)):
            traders.append(trader)

    for map in database['maps']:
        if (super_normalize(map['normalizedName']).startswith(argument)):
            maps.append(map)

    print_search(database, tasks, stations, barters, items, traders, maps)
    return True

def guid(tracker_file, argument):
    return

def fuzzy_search(tracker_file, argument):
    return

def requires(tracker_file, argument):
    return

# Tracking
def track(tracker_file, argument):
    database = open_database(tracker_file)

    if (is_guid(argument)):
        guid = argument
        type = 'barter'
    else:
        guid, type = name_guid_lookup(database, argument)

    if (not guid):
        logging.error('Invalid arguments. Accepted arguments are [Task Name, Station Name, Barter GUID]')
        return False

    if (type == 'task'):
        database = track_task(database, guid)
    elif (type == 'station'):
        database = track_station(database, guid)
    elif (type == 'barter'):
        database = track_barter(database, guid)
    else:
        logging.error(f'Track operation is unsupported for {type}')
        return False
    
    if (database):
        write_database(tracker_file, database)
        return True

    return False

def untrack(tracker_file, argument):
    database = open_database(tracker_file)

    if (is_guid(argument)):
        guid = argument
        type = 'barter'
    else:
        guid, type = name_guid_lookup(database, argument)

    if (not guid):
        logging.error('Invalid arguments. Accepted arguments are [Task Name, Station Name, Barter GUID]')
        return False

    if (type == 'task'):
        database = untrack_task(database, guid)
    elif (type == 'station'):
        database = untrack_station(database, guid)
    elif (type == 'barter'):
        database = untrack_barter(database, guid)
    else:
        logging.error(f'Untrack operation is unsupported for {type}')
        return False
    
    if (database):
        write_database(tracker_file, database)
        return True

    return False

# Completing
def complete(tracker_file, argument, force, recurse):
    database = open_database(tracker_file)

    if (is_guid(argument)):
        guid = argument
        type = 'barter'
    else:
        guid, type = name_guid_lookup(database, argument)

    if (not guid):
        logging.error('Invalid arguments. Accepted arguments are [Task Name, Station Name, Barter GUID]')
        return False

    if (type == 'task' and not recurse):
        database = complete_task(database, guid, force)
    elif (type == 'task' and recurse):
        database = complete_recursive_task(database, guid, True)
    elif (type == 'station'):
        database = complete_station(database, guid, force)
    elif (type == 'barter'):
        database = complete_barter(database, guid, force)
    else:
        logging.error(f'Complete operation is unsupported for {type}')
        return False
    
    if (database):
        write_database(tracker_file, database)
        return True

    return False

# Items
def add_item_fir(tracker_file, argument, count):
    database = open_database(tracker_file)
    guid = item_to_guid(database, argument)

    if (not guid):
        logging.error(f'Could not find any item that matches {argument}')
        return False
    
    if (not count or count < 1):
        logging.error(f'Invalid or missing count argument. Accepts an integer greater than 0')
        return False
    
    if (database['inventory'][guid]['have_fir'] + count > database['inventory'][guid]['need_fir']):
        if (database['inventory'][guid]['need_fir'] > 0):
            diff = database['inventory'][guid]['have_fir'] + count - database['inventory'][guid]['need_fir']
            database['inventory'][guid]['have_fir'] = database['inventory'][guid]['need_fir']
            logging.info(f'Added {count - diff} {argument} to Found In Raid (FIR) inventory')
        else:
            diff = count
        
        database['inventory'][guid]['have_nir'] = database['inventory'][guid]['have_nir'] + diff
        logging.info(f'Added {diff} {argument} to Not found In Raid (NIR) inventory')
    else:
        database['inventory'][guid]['have_fir'] = database['inventory'][guid]['have_fir'] + count
        logging.info(f'Added {count} {argument} to needed (FIR) inventory')

    write_database(tracker_file, database)
    return True

def add_item_nir(tracker_file, argument, count):
    database = open_database(tracker_file)
    guid = item_to_guid(database, argument)

    if (not guid):
        logging.error(f'Could not find any item that matches {argument}')
        return False
    
    if (not count or count < 1):
        logging.error(f'Invalid or missing count argument. Accepts an integer greater than 0')
        return False
    
    database['inventory'][guid]['have_nir'] = database['inventory'][guid]['have_nir'] + count
    logging.info(f'Added {count} {argument} to Not found In Raid (NIR) inventory')

    write_database(tracker_file, database)
    return True

# Level
def check_level(tracker_file):
    database = open_database(tracker_file)
    logging.info(f'Player level is {database["player_level"]}')
    return True

def set_level(tracker_file, level):
    database = open_database(tracker_file)
    database['player_level'] = level
    write_database(tracker_file, database)
    logging.info(f'Updated player level to {level}')
    return True

def level_up(tracker_file):
    database = open_database(tracker_file)
    database['player_level'] = database['player_level'] + 1
    write_database(tracker_file, database)
    logging.info(f'Incremented the player level by 1. Level is now {database["player_level"]}')
    return True


###################################################
#                                                 #
# MAIN FUNCTION                                   #
#                                                 #
###################################################


def main(args):
    logging.basicConfig(level = logging.INFO, format = '[%(asctime)s] [%(levelname)s]: %(message)s')
    parser(args[1:])

if (__name__ == '__main__'):
    main(sys.argv)  