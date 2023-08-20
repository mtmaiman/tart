# Standard library
import logging
import json
import sys
import re

# Imported libraries
import requests


#TODO: Alphabetize items on print
#TODO: Alphabetize tasks by map, then by level
#TODO: Add single slot value lookup for items (need to check API)
#TODO: Add bullet rankings (need to check API)
USAGE = '''
tart.py {debug}\n
> command [positional args] {options}\n
A lightweigth python CLI for tracking task, hideout, and barter progression, including item collection, for Escape From Tarkov. Please read below for usage notes and command details.\n
NOTE: Command arguments expect names or GUIDs. Please use search functions to find these if you are unsure\n
DEBUG: Execute the python script with a positional argument of "debug" to enter debug mode
Commands:
\tinv -help
\tls -help
\treset -help
\trestart -help
\trefresh -help
\tsearch -help
\ttrack -help
\tuntrack -help
\tcomplete -help
\tadd -help
\tlevel -help
'''
INV_HELP = '''
> inv {inventory}\n
Lists all items in all inventories or a specific inventory option\n
inventories
\ttasks : Lists all items in the inventory required for tracked tasks
\tstations : Lists all items in the inventory required for hideout stations
\thideout : Lists all items in the inventory required for hideout stations
\tbarters : Lists all items in the inventory required for tracked barters
\towned : Lists all items in the owned inventory
\tneeded : Lists all items in the needed inventory (all needed minus owned)
'''
LS_HELP = '''
> ls [iterable] {filter}\n
Lists all items in an available iterable\n
iterables
\ttasks : Lists all available tasks
\t\tfilters
\t\t\t{map} : Lists all available tasks for the specified map
\t\t\t{trader} : Lists all available tasks for the specified trader
\tstations : Lists all hideout stations
\thideout : Lists all hideout stations
\tbarters : Lists all tracked barters
\tuntracked : Lists all untracked tasks and hideout stations
\tmaps : Lists all maps
\ttraders : Lists all traders
'''
RESET_HELP = '''
> reset [data structure]\n
Resets all progression on a or all data structure(s)\n
data structures
\ttasks : Resets all progress on tasks
\tstations : Resets all progress on hideout stations
\thideout : Resets all progress on hideout stations
\tbarters : Resets all progress on barters
\tinv : Clears the inventory of owned items
\tall : Resets progress for all data structures and clears the inventory of owned items
'''
RESTART_HELP = '''
> restart [guid]\n
Restarts the barter at the specified guid. Required items for the barter are added to the needed inventory\n
guid
\t{guid} : A guid belonging to a barter
'''
REFRESH_HELP = '''
> refresh\n
Pulls latest Escape From Tarkov game data from api.tarkov.dev and overwrites all application files (WARNING: This will reset all progress!)
'''
SEARCH_HELP = '''
> search [pattern] {method} {barters}\n
Searches the database on the specified pattern\n
pattern
\t{pattern} : The name or guid of an object to search for
\t\tmethods
\t\t\tfuzzy : Searches for objects which contain the specified pattern anywhere in the name
\t\t\trequired : Searches for objects which have the specified pattern as a requirement
\t\tbarters
\t\t\tbarters : Will also search all available barters (May cause excessive results)
'''
TRACK_HELP = '''
> track [pattern]\n
Starts tracking and adds required items to the needed inventory for the object which matches the specified pattern\n
pattern
\t{pattern} : The name or guid of an object to track
'''
UNTRACK_HELP = '''
> untrack [pattern]\n
Stops tracking and removes required items from the needed inventory for the object which matches the specified pattern\n
pattern
\t{pattern} : The name or guid of an object to untrack
'''
COMPLETE_HELP = '''
> complete [pattern] {modifier}\n
Marks the object which matches the specified pattern as complete and consumes required items if available\n
pattern
\t{pattern} : The name or guid of an object to complete
\t\tmodifiers
\t\t\tforce : Forcefully completes the object whether the requirements are satisfied or not (adds missing items to the owned inventory)
\t\t\trecurse: Recursively and forcefully completes all prerequisite objects whether the requirements are satisfied or not (adds missing items to the inventory)
'''
ADD_HELP = '''
> add [item] {fir}\n
Adds the specified item by name or guid to the owned inventory\n
item
\t{item} : The name or guid of an item to add
\t\tfir
\t\t\tfir : Adds the item as Found In Raid (FIR), otherwise adds as Not found In Raid (NIR)
'''
LEVEL_HELP = '''
> level {operation} {level}\n
Displays the player level\n
operations
\tup : Increments the player level by one (1)
\tset : Sets the player level to {level}
\t\tlevel
\t\t\tlevel : The integer value greater than 0 to set the player level at
'''
ITEM_HEADER = '{:<25} {:<60} {:<30} {:<25}\n'.format('Item Short Name', 'Item Normalized Name', 'Item GUID', 'Have (FIR) Need (FIR)')
MAP_HEADER = '{:<30} {:<20}\n'.format('Map Normalized Name', 'Map GUID')
TRADER_HEADER = '{:<30} {:<20}\n'.format('Trader Normalized Name', 'Trader GUID')
INVENTORY_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Have (FIR) Need (FIR)', 'Item', 'Have (FIR) Need (FIR)', 'Item', 'Have (FIR) Need (FIR)')
INVENTORY_OWNED_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Have (FIR)', 'Item', 'Have (FIR)', 'Item', 'Have (FIR)')
INVENTORY_NEEDED_HEADER = '{:<20} {:<25} {:<20} {:<25} {:<20} {:<25} \n'.format('Item', 'Need (FIR)', 'Item', 'Need (FIR)', 'Item', 'Need (FIR)')
TASK_HEADER = '{:<40} {:<20} {:<20} {:<20} {:<20} {:<40}\n'.format('Task Title', 'Task Giver', 'Task Status', 'Tracked', 'Kappa?', 'Task GUID')
HIDEOUT_HEADER = '{:<40} {:<20} {:<20} {:<40}\n'.format('Station Name', 'Station Status', 'Tracked', 'Station GUID')
BARTER_HEADER = '{:<40} {:<20} {:<20} {:<20}\n'.format('Barter GUID', 'Trader', 'Level', 'Tracked')
UNTRACKED_HEADER = '{:<40} {:<20} {:<20}\n'.format('Entity Name', 'Type', 'Tracked')
BUFFER = '-------------------------------------------------------------------------------------------------------------------------------------\n'


###################################################
#                                                 #
# UTIL FUNCTIONS (DEBUGGED)                       #
#                                                 #
###################################################


# Command parsing
def parser(tracker_file, command):
    command = command.lower().split(' ')
    logging.debug(f'Parsing command: {command}')

    # Inventory
    if (command[0] == 'inv'):
        if (len(command) == 1):
            logging.debug(f'Executing command: {command[0]}')
            list_inventory(tracker_file)
        elif (command[1] == 'tasks'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_inventory_tasks(tracker_file)
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_inventory_stations(tracker_file)
        elif (command[1] == 'barters'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_inventory_barters(tracker_file)
        elif (command[1] == 'owned'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_inventory_owned(tracker_file)
        elif (command[1] == 'needed'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_inventory_needed(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(INV_HELP)
        else:
            logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
            logging.error('Unhandled inv argument')
            logging.info(INV_HELP)
    # List
    elif (command[0] == 'ls'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing ls argument')
            logging.info(LS_HELP)
        elif (command[1] == 'tasks'):
            if (len(command) == 3):
                logging.debug(f'Executing command: {command[0]} {command[1]} {command[2]}')
                list_tasks(tracker_file, command[2])
            else:
                logging.debug(f'Executing command: {command[0]} {command[1]} all')
                list_tasks(tracker_file, 'all')
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_stations(tracker_file)
        elif (command[1] == 'barters'):
            if (len(command) == 3):
                logging.debug(f'Executing command: {command[0]} {command[1]} {command[2]}')
                list_barters(tracker_file, command[2])
            else:
                logging.debug(f'Executing command: {command[0]} {command[1]} all')
                list_barters(tracker_file, 'all')
        elif (command[1] == 'untracked'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_untracked(tracker_file)
        elif (command[1] == 'maps'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_maps(tracker_file)
        elif (command[1] == 'traders'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            list_traders(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(LS_HELP)
        else:
            logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
            logging.error('Unhandled ls argument')
            logging.info(LS_HELP)
    # Reset
    elif (command[0] == 'reset'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing reset argument')
            logging.info(RESET_HELP)
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.info(RESET_HELP)
        else:
            logging.warning('You are about to reset progress! Are you sure you wish to proceed? (Y/N)')
            confirmation = input('> ').lower()

            if (confirmation == 'y'):
                if (command[1] == 'tasks'):
                    logging.debug(f'Executing command: {command[0]} {command[1]}')
                    reset_tasks(tracker_file)
                elif (command[1] == 'stations' or command[1] == 'hideout'):
                    logging.debug(f'Executing command: {command[0]} {command[1]}')
                    reset_stations(tracker_file)
                elif (command[1] == 'barters'):
                    logging.debug(f'Executing command: {command[0]} {command[1]}')
                    reset_barters(tracker_file)
                elif (command[1] == 'inv'):
                    logging.debug(f'Executing command: {command[0]} {command[1]}')
                    reset_inventory(tracker_file)
                elif (command[1] == 'all'):
                    logging.debug(f'Executing command: {command[0]} {command[1]}')
                    reset_tasks(tracker_file)
                    reset_stations(tracker_file)
                    reset_barters(tracker_file)
                    reset_inventory(tracker_file)
                else:
                    logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
                    logging.error('Unhandled reset argument')
                    logging.info(RESET_HELP)
            else:
                logging.debug(f'Aborted command execution for {command[0]} {command[1]} due to confirmation response of {confirmation}')
                logging.info('Reset aborted')
    # Restart
    elif (command[0] == 'restart'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing barter GUID')
            logging.info(RESTART_HELP)
        elif (is_guid(command[1])):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            restart_barter(tracker_file, command[1])
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(RESTART_HELP)
        else:
            logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
            logging.error('Invalid GUID argument')
            logging.info(RESTART_HELP)
    # Refresh
    elif (command[0] == 'refresh'):
        if (len(command) < 2):
            logging.warning('You are about to reset progress! Are you sure you wish to proceed? (Y/N)')
            confirmation = input('> ').lower()

            if (confirmation == 'y'):
                refresh(tracker_file)
            else:
                logging.debug(f'Aborted command execution for {command[0]} {command[1]} due to confirmation response of {confirmation}')
                logging.info('Refresh aborted')
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(REFRESH_HELP)
        else:
            logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
            logging.error('Invalid refresh argument')
            logging.info(REFRESH_HELP)
    # Search
    elif (command[0] == 'search'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing search pattern')
            logging.info(SEARCH_HELP)
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                logging.debug(f'Executing command: {command[0]} {command[1]}')
                logging.info(SEARCH_HELP)
            elif (command[-1] == 'barters'):
                if (command[-2] == 'fuzzy'):
                    logging.debug(f'Executing command: {command[0]} {command[1:-2]} {command[-2]} {command[-1]}')
                    ignore_barters = False
                    pattern = ' '.join(command[1:-2])
                    fuzzy_search(tracker_file, pattern, ignore_barters)
                elif (command[-2] == 'required'):
                    logging.debug(f'Executing command: {command[0]} {command[1:-2]} {command[-2]} {command[-1]}')
                    ignore_barters = False
                    pattern = ' '.join(command[1:-2])
                    required_search(tracker_file, pattern, ignore_barters)
                else:
                    logging.debug(f'Executing command: {command[0]} {command[1:-1]} {command[-1]}')
                    ignore_barters = False
                    pattern = ' '.join(command[1:-1])
                    search(tracker_file, pattern, ignore_barters)
            elif (command[-1] == 'fuzzy'):
                logging.debug(f'Executing command: {command[0]} {command[1:-1]} {command[-1]}')
                ignore_barters = True
                pattern = ' '.join(command[1:-1])
                fuzzy_search(tracker_file, pattern, ignore_barters)
            elif (command[-1] == 'required'):
                logging.debug(f'Executing command: {command[0]} {command[1:-1]}  {command[-1]}')
                ignore_barters = True
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, pattern, ignore_barters)
            else:
                logging.debug(f'Executing command: {command[0]} {command[1:]}')
                ignore_barters = True
                pattern = ' '.join(command[1:])
                search(tracker_file, pattern, ignore_barters)
    # Track
    elif (command[0] == 'track'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing name or barter GUID')
            logging.info(TRACK_HELP)
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(TRACK_HELP)
        else:
            logging.debug(f'Executing command: {command[0]} {command[1:]}')
            track(tracker_file, ' '.join(command[1:]))
    elif (command[0] == 'untrack'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing name or barter GUID')
            logging.info(UNTRACK_HELP)
        elif (command[1] == 'help' or command[1] == 'h'):
            logging.debug(f'Executing command: {command[0]} {command[1]}')
            logging.info(UNTRACK_HELP)
        else:
            logging.debug(f'Executing command: {command[0]} {command[1:]}')
            untrack(tracker_file, ' '.join(command[1:]))
    # Complete
    elif (command[0] == 'complete'):
        if (len(command) < 2):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing name or barter GUID')
            logging.info(COMPLETE_HELP)
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                logging.debug(f'Executing command: {command[0]} {command[1]}')
                logging.info(COMPLETE_HELP)
                return True
            elif (command[-1] == 'force'):
                logging.debug(f'Executing command: {command[0]} {command[1:-1]} {command[-1]}')
                force = True
                recurse = False
                argument = ' '.join(command[1:-1])
            elif (command[-1] == 'recurse'):
                logging.debug(f'Executing command: {command[0]} {command[1:-1]} {command[-1]}')
                force = True
                recurse = True
                argument = ' '.join(command[1:-1])
            else:
                logging.debug(f'Executing command: {command[0]} {command[1:]}')
                force = False
                recurse = False
                argument = ' '.join(command[1:])

            complete(tracker_file, argument, force, recurse)
    # Add
    elif (command[0] == 'add'):
        if (len(command) < 3):
            logging.debug(f'Failed to execute command: {command[0]}')
            logging.error('Missing item name or item count')
            logging.info(ADD_HELP)
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                logging.debug(f'Executing command: {command[0]} {command[1]}')
                logging.info(ADD_HELP)
            if ((not command[-1] == 'fir' and (not command[-1].isdigit() or int(command[-1]) < 1)) or (command[-1] == 'fir' and (not command[-2].isdigit() or int(command[-2]) < 1))):
                logging.debug(f'Failed to execute command: {command[0]} {command[1:]}')
                logging.error('Invalid integer entered for count')
                logging.info(ADD_HELP)
            elif (command[-1] == 'fir'):
                logging.debug(f'Executing command: {command[0]} {command[1:-2]} {command[-2]} {command[-1]}')
                count = int(command[-2])
                argument = ' '.join(command[1:-2])
                add_item_fir(tracker_file, argument, count)
            else:
                logging.debug(f'Executing command: {command[0]} {command[1:-1]} {command[-1]}')
                count = int(command[-1])
                argument = ' '.join(command[1:-1])
                add_item_nir(tracker_file, argument, count)
    # Level
    elif (command[0] == 'level'):
        if (len(command) > 1):
            if (command[1] == 'up'):
                logging.debug(f'Executing command: {command[0]} {command[1]}')
                level_up(tracker_file)
            elif (command[1] == 'help' or command[1] == 'h'):
                logging.debug(f'Executing command: {command[0]} {command[1]}')
                logging.info(LEVEL_HELP)
            elif (command[1] == 'set'):
                if (len(command) == 3):
                    if (command[2].isdigit() and int(command[2]) > 0):
                        logging.debug(f'Executing command: {command[0]} {command[1]} {command[2]}')
                        set_level(tracker_file, int(command[2]))
                    else:
                        logging.debug(f'Failed to execute command: {command[0]} {command[1]} {command[2]}')
                        logging.error('Invalid integer entered for level')
                        logging.info(LEVEL_HELP)
                else:
                    logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
                    logging.error('Missing integer for level')
                    logging.info(LEVEL_HELP)
            else:
                logging.debug(f'Failed to execute command: {command[0]} {command[1]}')
                logging.error('Unhandled level argument')
                logging.info(LEVEL_HELP)
        else:
            logging.debug(f'Executing command: {command[0]}')
            check_level(tracker_file)
    # Help
    elif (command[0] == 'help' or command[0] == 'h'):
        logging.debug(f'Executing command: {command[0]}')
        logging.info(USAGE)
    # Exit
    elif (command[0] == 'stop' or command[0] == 's' or command[0] == 'quit' or command[0] == 'q' or command[0] == 'exit'):
        logging.debug(f'Executing command: {command[0]}')
        return False
    # Error
    else:
        logging.debug(f'Failed to execute command: {command[0]}')
        logging.error('Unhandled command')
        logging.info(USAGE)
    
    return True

# Database editing
def open_database(file_path):
    try:
        with open(file_path, 'r', encoding = 'utf-8') as open_file:
            logging.debug(f'Opened file at {file_path}')
            file = json.load(open_file)
    except FileNotFoundError:
        logging.error('Database file not found. Please perform a refresh')
        exit(1)
    return file

def write_database(file_path, data):
    with open(file_path, 'w', encoding = 'utf-8') as open_file:
        open_file.write(json.dumps(data))
        logging.debug(f'Wrote to file at {file_path}')
    return

# GUID to name or object
def guid_to_item(database, guid):
    logging.debug(f'Searching for item matching guid {guid}')
    for item in database['all_items']:
        if (item['id'] == guid):
            logging.debug(f'Found item matching guid {guid}')
            return item['shortName']
    
    return False

def guid_to_item_object(database, guid):
    logging.debug(f'Searching for item matching guid {guid}')
    for item in database['all_items']:
        if (item['id'] == guid):
            logging.debug(f'Found item matching guid {guid}')
            return item
    
    return False

def guid_to_task(database, guid):
    logging.debug(f'Searching for task matching guid {guid}')
    for task in database['tasks']:
        if (task['id'] == guid):
            logging.debug(f'Found task matching guid {guid}')
            return task['name']
        
    return False

def guid_to_station(database, guid):
    logging.debug(f'Searching for hideout station matching guid {guid}')
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                logging.debug(f'Found hideout station matching guid {guid}')
                return level['normalizedName']
    
    return False

def guid_to_map(database, guid):
    logging.debug(f'Searching for map matching guid {guid}')
    for map in database['maps']:
        if (map['id'] == guid):
            logging.debug(f'Found map matching guid {guid}')
            return map['normalizedName']
    
    return False

def guid_to_trader(database, guid):
    logging.debug(f'Searching for trader matching guid {guid}')
    for trader in database['traders']:
        if (trader['id'] == guid):
            logging.debug(f'Found trader matching guid {guid}')
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
                        logging.debug(f'Did not find anything matching guid {guid}')
                        return False, None
    
    return normalized_name, found

# Name to GUID
def item_to_guid(database, item_name):
    logging.debug(f'Searching for item matching name {item_name}')
    for item in database['all_items']:
        if (item['shortName'].lower() == item_name or item['normalizedName'] == item_name):
            logging.debug(f'Found item matching name {item_name}')
            return item['id']
    
    return False

def task_to_guid(database, task_name):
    logging.debug(f'Searching for task matching name {task_name}')
    for task in database['tasks']:
        if (task['normalizedName'] == task_name):
            logging.debug(f'Found task matching name {task_name}')
            return task['id']
    
    return False

def station_to_guid(database, station_name):
    logging.debug(f'Searching for hideout station matching name {station_name}')
    for station in database['hideout']:
        for level in station['levels']:
            if (level['normalizedName'] == station_name):
                logging.debug(f'Found hideout station matching name {station_name}')
                return level['id']
    
    return False

def map_to_guid(database, map_name):
    logging.debug(f'Searching for map matching name {map_name}')
    for map in database['maps']:
        if (map['normalizedName'] == map_name):
            logging.debug(f'Found map matching name {map_name}')
            return map['id']
    
    return False

def trader_to_guid(database, trader_name):
    logging.debug(f'Searching for trader matching name {trader_name}')
    for trader in database['traders']:
        if (trader['normalizedName'] == trader_name):
            logging.debug(f'Found trader matching name {trader_name}')
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
                        logging.debug(f'Did not find anything matching name {name}')
                        return False, None

    return guid, found

# Inventory functions
def get_fir_count_by_guid(database, guid):
    logging.debug(f'Searching for item matching guid {guid}')
    for this_guid in database['inventory'].keys():
        if (this_guid == guid):
            logging.debug(f'Found item matching guid {guid} and matching FIR count')
            return database['inventory'][this_guid]['have_fir']
    
    return False

def get_nir_count_by_guid(database, guid):
    logging.debug(f'Searching for item matching guid {guid}')
    for this_guid in database['inventory'].keys():
        if (this_guid == guid):
            logging.debug(f'Found item matching guid {guid} and matching NIR count')
            return database['inventory'][this_guid]['have_nir']
    
    return False

# String functions
def is_guid(text):
    if (len(text) == 24 and text[0].isdigit()):
        logging.debug(f'{text} matches 24 character guid')
        return True
    if (len(text) > 24 and text[0].isdigit() and text[24] == '-'):
        logging.debug(f'{text} matches over 24 character guid')
        return True
    
    logging.debug(f'{text} is not a guid')
    return False

def normalize(text):
    normalized = text.lower().replace('-',' ')
    normalized = re.sub(' +', ' ', normalized)
    normalized = normalized.replace(' ','-')
    logging.debug(f'Normalized {text} to {normalized}')
    return normalized

def super_normalize(text):
    super_normalized = text.lower().replace('-',' ')
    super_normalized = super_normalized.replace('the', '')
    super_normalized = re.sub(' +', ' ', super_normalized)
    super_normalized = super_normalized.replace(' ','')
    logging.debug(f'Normalized {text} to {super_normalized}')
    return super_normalized

def alphabetize_items(database, items):
    unsorted_items = {}

    for guid in items.keys():
        short_name = guid_to_item(database, guid)
        items[guid]['short_name'] = short_name
        unsorted_items[short_name] = guid
    
    return {short_name:unsorted_items[short_name] for short_name in sorted(unsorted_items.keys())}

# Verify functions
def verify_task(database, task, task_table):
    if (task['status'] == 'complete'):
        logging.debug(f'Task {task["name"]} is complete')
        return False
    
    if (not task['tracked']):
        logging.debug(f'Task {task["name"]} is not tracked')
        return False
    
    if (database['player_level'] < task['minPlayerLevel']):
        logging.debug(f'Task {task["name"]} has minPlayerLevel {task["minPlayerLevel"]} above current {database["player_level"]}')
        return False
    
    for prereq in task['taskRequirements']:
        if (task_table[prereq['id']] == 'incomplete'):
            logging.debug(f'Task {task["name"]} has incomplete prereq')
            return False
    
    logging.debug(f'Task {task["name"]} successfully verified')
    return True

def verify_hideout_level(station, level):
    max_level = 0

    if (not level['tracked']):
        logging.debug(f'Hideout station {level["normalizedName"]} is not tracked')
        return False
    
    if (level['status'] == 'complete'):
        logging.debug(f'Hideout station {level["normalizedName"]} is complete')
        return False

    for prereq in level['stationLevelRequirements']:
        if (prereq['level'] > max_level):
            max_level = prereq['level']

    for prereq_level in station['levels']:
        if (prereq_level['level'] <= max_level and prereq_level['status'] == 'incomplete'):
            logging.debug(f'Hideout station {level["normalizedName"]} requires at least level {max_level}')
            return False
        
    return True

def verify_barter(barter):
    if (barter['status'] == 'complete' or not barter['tracked']):
        logging.debug(f'Barter {barter["id"]} is complete or not tracked')
        return False
    
    return True

# Get functions
def get_items_needed_for_tasks(database):
    items = {}
    logging.debug('Compiling all items required for tracked tasks')

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
    logging.debug('Compiling all items required for tracked hideout stations')

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
    logging.debug('Compiling all items required for tracked barters')

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
    logging.debug('Compiling all items in the owned inventory')

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
    logging.debug('Compiling all items in the needed inventory')

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
    logging.debug('Compiling all tasks for map with guid {guid}')

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
    logging.debug('Compiling all tasks for trader with guid {guid}')

    for task in database['tasks']:
        task_table[task['id']] = task['status']

    for task in database['tasks']:
        if (task['trader']['id'] == guid and verify_task(database, task, task_table)):
            tasks.append(task)

    return tasks

def get_available_tasks(database):
    tasks = []
    task_table = {}
    logging.debug('Compiling all available tasks')

    for task in database['tasks']:
        task_table[task['id']] = task['status']

    for task in database['tasks']:
        if (verify_task(database, task, task_table)):
            tasks.append(task)

    return tasks

def get_hideout_stations(database):
    hideout_stations = []
    logging.debug('Compiling all available hideout stations')

    for station in database['hideout']:
        for level in station['levels']:
            if (verify_hideout_level(station, level)):
                hideout_stations.append(level)
    
    return hideout_stations

def get_barters(database):
    barters = []
    logging.debug('Compiling all tracked barters')

    for barter in database['barters']:
        if (verify_barter(barter)):
            barters.append(barter)

    return barters

def get_barters_by_trader(database, guid):
    barters = []
    logging.debug(f'Compiling all tracked barters for trader with guid {guid}')

    for barter in database['barters']:
        if (verify_barter(barter) and barter['trader']['id'] == guid):
            barters.append(barter)

    return barters

def get_untracked(database):
    untracked = []
    logging.debug('Compiling all untracked tasks and hideout stations')

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


###################################################
#                                                 #
# WORKER (SUB) FUNCTIONS                          #
#                                                 #
###################################################


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
                        logging.info(f'Added {count} {guid_to_item(database, item_guid)} to needed Found In Raid (FIR) inventory')
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
                
                if (item_guid not in database['inventory'].keys()):
                    database['inventory'][item_guid] = {
                        'need_fir': 0,
                        'need_nir': count,
                        'have_fir': 0,
                        'have_nir': 0,
                        'consumed_fir': 0,
                        'consumed_nir': 0
                    }
                else:
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
                        logging.info(f'Removed {count} {guid_to_item(database, item_guid)} from needed Found In Raid (FIR) inventory')
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
                                logging.error(f'{diff_fir} more {guid_to_item(database, item_guid)} required to complete this task. Override with the force optional argument')
                                return False
                            else:
                                continue
                        else:
                            have_nir = get_nir_count_by_guid(database, item_guid)
                            need_nir = objective['count']
                            diff_nir = need_nir - have_nir

                            if (diff_nir > 0):
                                logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this task. Override with the force optional argument')
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
                            logging.info(f'Added {diff_fir} {guid_to_item(database, item_guid)} to the inventory as Found In Raid (FIR) to complete {task["name"]}')
                        
                        database['inventory'][item_guid]['consumed_fir'] = database['inventory'][item_guid]['consumed_fir'] + need_fir
                    else:
                        have_nir = get_nir_count_by_guid(database, item_guid)
                        need_nir = objective['count']
                        diff_nir = need_nir - have_nir

                        if (diff_nir > 0):
                            database['inventory'][item_guid]['have_nir'] = database['inventory'][item_guid]['have_nir'] + diff_nir
                            logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the inventory to complete {task["name"]}')
                        
                        database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + need_nir
            
            task['status'] = 'complete'
            logging.info(f'Set status of {task["name"]} to complete')
            break
    else:
        logging.error(f'Failed to find a matching task with GUID {guid}')

    return database

def complete_recursive_task(database, guid, force):
    updated_database = complete_task(database, guid, force)

    if (updated_database):
        database = updated_database

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
                            logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this hideout station. Override with the force optional argument')
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
                        logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the inventory to complete {level["normalizedName"]}')
                    
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
                        logging.error(f'{diff_nir} more {guid_to_item(database, item_guid)} required to complete this barter. Override with the force optional argument')
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
                    logging.info(f'Added {diff_nir} {guid_to_item(database, item_guid)} to the inventory to complete {barter["id"]}')
                
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
    sorted_items = alphabetize_items(database, items)

    for short_name, guid in sorted_items.items():
        if (items[guid]["have_nir"] != 0 or items[guid]["have_fir"] != 0 or items[guid]["need_nir"] != 0 or items[guid]["need_fir"]):
            item_string = f'{items[guid]["have_nir"]} ({items[guid]["have_fir"]}) {items[guid]["need_nir"]} ({items[guid]["need_fir"]})'
            display = display + '{:<20} {:<25} '.format(short_name, item_string)
            items_in_this_row = items_in_this_row + 1
            
            if (items_in_this_row == 3):
                display = display.strip(' ') + '\n'
                items_in_this_row = 0
    
    display = display + '\n\n'
    print(display)
    return

def print_inventory_owned(database, items):
    display = INVENTORY_OWNED_HEADER + BUFFER
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
        display = display + '{:<40} {:<20} {:<20} {:<20} {:<20} {:<40}\n'.format(task['name'], guid_to_trader(database, task['trader']['id']), task['status'], print_bool(task['tracked']), print_bool(task['kappaRequired']), task['id'])

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
        display = display + '{:<40} {:<20} {:<20} {:<40}\n'.format(level['normalizedName'], level['status'], print_bool(level['tracked']), level['id'])

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
# CALLABLE FUNCTIONS                              #
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

def list_inventory_owned(tracker_file):
    database = open_database(tracker_file)
    owned_items = get_items_owned(database)
    
    if (not bool(owned_items)):
        logging.info('Your inventory is empty!')
    else:
        print_inventory_owned(database, owned_items)

    return

def list_inventory_needed(tracker_file):
    database = open_database(tracker_file)
    needed_items = get_items_needed(database)
    
    if (not bool(needed_items)):
        logging.info('Congratulations, you have no items remaining to collect!')
    else:
        print_inventory_needed(database, needed_items)

    return

# List
def list_tasks(tracker_file, argument):
    database = open_database(tracker_file)
    argument = normalize(argument)
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
    argument = normalize(argument)
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

def reset_inventory(tracker_file):
    database = open_database(tracker_file)
    
    for guid in database['inventory'].keys():
        database['inventory'][guid]['have_fir'] = 0
        database['inventory'][guid]['have_nir'] = 0
    
    write_database(tracker_file, database)
    logging.info('The inventory has been cleared')
    return True

# Restart
def restart_barter(tracker_file, argument):
    database = open_database(tracker_file)

    for barter in database['barters']:
        if (barter['id'] == argument):
            if (not barter['tracked']):
                logging.error(f'Barter {argument} is not currently tracked and therefore cannot be restarted')
                return False
            
            if (barter['status'] == 'complete'):
                barter['status'] = 'incomplete'
                logging.info(f'Set barter {argument} to incomplete')
            else:
                logging.error(f'Barter {argument} is not yet completed and therefore cannot be restarted')
                return False
            
            for requirement in barter['requiredItems']:
                guid = requirement['item']['id']
                count = requirement['count']
                database['inventory'][guid]['need_nir'] = database['inventory'][guid]['need_nir'] + count
                logging.info(f'Added {count} of {guid_to_item(database, guid)} to the needed inventory')
            
            return True
    
    logging.error(f'Encountered an unhandled error when restarting barter {argument}')
    return False

# Refresh
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
    logging.info(f'Generated a new database file {tracker_file}')
    return

# Search
def search(tracker_file, argument, ignore_barters):
    database = open_database(tracker_file)
    
    if (not is_guid(argument)):
        argument = super_normalize(argument)
        guid = False
    else:
        guid = True

    tasks = []
    stations = []
    barters = []
    items = []
    traders = []
    maps = []

    for task in database['tasks']:
        if (not guid):
            if (super_normalize(task['name']).startswith(argument) or super_normalize(task['normalizedName']).startswith(argument)):
                tasks.append(task)
        elif (task['id'] == argument):
            tasks.append(task)

    for station in database['hideout']:
        for level in station['levels']:
            if (not guid):
                if (super_normalize(level['normalizedName']).startswith(argument)):
                    stations.append(level)
            elif (level['id'] == argument):
                stations.append(level)

    if (not ignore_barters):
        for barter in database['barters']:
            if (not guid):
                for requirement in barter['requiredItems']:
                    item = guid_to_item_object(database, requirement['item']['id'])

                    if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                        barters.append(barter)
                for reward in barter['rewardItems']:
                    item = guid_to_item_object(database, reward['item']['id'])

                    if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                        barters.append(barter)
            elif (barter['id'] == argument):
                barters.append(barter)

    for item in database['all_items']:
        if (not guid):
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
        elif (item['id'] == argument):
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
        if (not guid):
            if (super_normalize(trader['normalizedName']).startswith(argument)):
                traders.append(trader)
        elif (trader['id'] == argument):
            traders.append(trader)

    for map in database['maps']:
        if (not guid):
            if (super_normalize(map['normalizedName']).startswith(argument)):
                maps.append(map)
        elif (map['id'] == argument):
            maps.append(map)

    print_search(database, tasks, stations, barters, items, traders, maps)
    return True

def fuzzy_search(tracker_file, argument, ignore_barters):
    database = open_database(tracker_file)
    
    if (not is_guid(argument)):
        argument = super_normalize(argument)
        guid = False
    else:
        guid = True

    tasks = []
    stations = []
    barters = []
    items = []
    traders = []
    maps = []

    for task in database['tasks']:
        if (not guid):
            if (argument in super_normalize(task['name']) or argument in super_normalize(task['normalizedName'])):
                tasks.append(task)
        elif (task['id'] == argument):
            tasks.append(task)

    for station in database['hideout']:
        for level in station['levels']:
            if (not guid):
                if (argument in super_normalize(level['normalizedName'])):
                    stations.append(level)
            elif (level['id'] == argument):
                stations.append(level)

    if (not ignore_barters):
        for barter in database['barters']:
            if (not guid):
                for requirement in barter['requiredItems']:
                    item = guid_to_item_object(database, requirement['item']['id'])

                    if (argument in super_normalize(item['shortName']) or argument in super_normalize(item['normalizedName'])):
                        barters.append(barter)
                for reward in barter['rewardItems']:
                    item = guid_to_item_object(database, reward['item']['id'])

                    if (argument in super_normalize(item['shortName']) or argument in super_normalize(item['normalizedName'])):
                        barters.append(barter)
            elif (barter['id'] == argument):
                barters.append(barter)

    for item in database['all_items']:
        if (not guid):
            if (argument in super_normalize(item['shortName']) or argument in super_normalize(item['normalizedName'])):
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
        elif (item['id'] == argument):
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
        if (not guid):
            if (argument in super_normalize(trader['normalizedName'])):
                traders.append(trader)
        elif (trader['id'] == argument):
            traders.append(trader)

    for map in database['maps']:
        if (not guid):
            if (argument in super_normalize(map['normalizedName'])):
                maps.append(map)
        elif (map['id'] == argument):
            maps.append(map)

    print_search(database, tasks, stations, barters, items, traders, maps)
    return True

def required_search(tracker_file, argument, ignore_barters):
    database = open_database(tracker_file)
    
    if (not is_guid(argument)):
        argument = super_normalize(argument)
        guid = False
    else:
        guid = True

    tasks = []
    stations = []
    barters = []
    items, traders, maps = [], [], []

    for task in database['tasks']:
        for objective in task['objectives']:
            if (objective['type'] == 'giveItem'):
                if (not guid):
                    item = guid_to_item_object(database, objective['item']['id'])

                    if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                        tasks.append(task)
                elif (objective['item']['id'] == argument):
                    tasks.append(task)

    for station in database['hideout']:
        for level in station['levels']:
            for requirement in level['itemRequirements']:
                if (not guid):
                    item = guid_to_item_object(database, requirement['item']['id'])

                    if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                        stations.append(level)
                elif (requirement['item']['id'] == argument):
                    stations.append(level)

    if (not ignore_barters):
        for barter in database['barters']:
            for requirement in barter['requiredItems']:
                if (not guid):
                    item = guid_to_item_object(database, requirement['item']['id'])

                    if (super_normalize(item['shortName']).startswith(argument) or super_normalize(item['normalizedName']).startswith(argument)):
                        barters.append(barter)
                elif (requirement['item']['id'] == argument):
                    barters.append(barter)

    print_search(database, tasks, stations, barters, items, traders, maps)
    return True

# Track
def track(tracker_file, argument):
    database = open_database(tracker_file)
    argument = normalize(argument)

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
    argument = normalize(argument)

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

# Complete
def complete(tracker_file, argument, force, recurse):
    database = open_database(tracker_file)
    argument = normalize(argument)
    
    if (is_guid(argument)):
        guid = argument
        type = 'barter'
    else:
        guid, type = name_guid_lookup(database, argument)

    if (not guid):
        logging.error('Invalid arguments')
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

# Add
def add_item_fir(tracker_file, argument, count):
    database = open_database(tracker_file)
    argument = normalize(argument)
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
    argument = normalize(argument)
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
# APP LOOP                                        #
#                                                 #
###################################################


def main(args):
    if (args[1].lower() == 'debug'):
        logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s] [%(levelname)s]: %(message)s')
        logging.info('Welcome to the TARkov Tracker (TART)!')
        logging.info('RUNNING IN DEBUG MODE. All changes will affect only the debug database file!')
        tracker_file = 'debug.json'
    else:
        logging.basicConfig(level = logging.INFO, format = '[%(asctime)s] [%(levelname)s]: %(message)s')
        logging.info('Welcome to the TARkov Tracker (TART)!')
        tracker_file = 'database.json'

    while(True):
        command = input('> ')
        exited = parser(tracker_file, command)
        
        if (not exited):
            logging.info('Gracefully quit!')
            break

if (__name__ == '__main__'):
    main(sys.argv)