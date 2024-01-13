# Standard library
try:
    from datetime import datetime, timedelta
    from os import system, name, rename, remove, listdir
    import json
    import sys
    import re

    # Imported libraries
    import requests
except ModuleNotFoundError as exception:
    print('Failed to find a required module. Please use "pip install -r requirements.txt" to install required modules and verify your version of Python.')
    exit(1)


DEBUG = False

INV = 0
HAVE = 1
NEED = 2

USAGE = '''
tart.py {debug}\n
A lightweight python CLI for tracking tasks, hideout stations, barters, and items inventory for Escape From Tarkov. Use the "import" command if this is your first time! Using "debug" as a positional argument enters debug mode.\n
usage:\n
> command [required args] {optional args}\n
commands
\tinv help
\tls help
\tsearch help
\trequires help
\ttrack help
\tuntrack help
\tcomplete help
\trestart help
\tadd help
\tdel help
\tlevel help
\tclear help
\timport help
\tbackup help
\trestore help
'''
INV_HELP = '''
> inv {inventory}\n
Lists all items in all inventories or a specific inventory option\n
inventories
\ttasks : Lists all items in the inventory required for tracked tasks
\tstations : Lists all items in the inventory required for hideout stations
\thideout : Lists all items in the inventory required for hideout stations
\tbarters : Lists all items in the inventory required for tracked barters
\tcrafts : Lists all items in the inventory required for tracked craft recipes
\thave : Lists all items you have in the inventory
\tneed : Lists all items you still need
'''
LS_HELP = '''
> ls [iterable] {filter}\n
Lists all items in an available iterable\n
iterables
\ttasks : Lists all available tasks
\t\tfilters
\t\t\tmap : The name of a map to list tasks for
\t\t\ttrader : The name of a trader to list tasks for
\tstations : Lists all hideout stations
\thideout : Lists all hideout stations
\tbarters : Lists all tracked barters
\t\tfilters
\t\t\ttrader : The name of a trarder to list barters for
\tcrafts : Lists all tracked crafts
\tuntracked : Lists all untracked tasks and hideout stations
\t\tfilters
\t\t\tkappa : Includes non-Kappa required tasks, otherwise ignored
\tmaps : Lists all maps
\ttraders : Lists all traders
'''
SEARCH_HELP = '''
> search [pattern] {filter}\n
Searches the database on the specified pattern\n
pattern : The name or guid of an object to search for
filters : Will include extra filters in the search parameters (may cause excessive results)
\tbarters : Also searches barters for required items, reward items, and GUIDs
\tcrafts : Also searches craft recipes for required items, reward items, and GUIDs
\tall : Also searches both barters and craft recipes for required items, reward items, and GUIDs
'''
REQUIRES_HELP = '''
> requires [item] {barters}\n
Searches the database for objects which require the specified item name or guid\n
item : The name or guid of an item to search for
filters : Will include extra filters in the search parameters (may cause excessive results)
\tbarters : Also searches barters for required items, reward items, and GUIDs
\tcrafts : Also searches craft recipes for required items, reward items, and GUIDs
\tall : Also searches both barters and craft recipes for required items, reward items, and GUIDs
'''
TRACK_HELP = '''
> track [pattern]\n
Starts tracking and adds required items to the needed inventory for the object which matches the specified pattern\n
pattern : The name or guid of an object to track
'''
UNTRACK_HELP = '''
> untrack [pattern]\n
Stops tracking and removes required items from the needed inventory for the object which matches the specified pattern\n
pattern : The name or guid of an object to untrack
'''
COMPLETE_HELP = '''
> complete [pattern] {modifier}\n
Marks the object which matches the specified pattern as complete and consumes required items if available\n
pattern : The name or guid of an object to complete
modifiers
\tforce : Forcefully completes the object whether the requirements are satisfied or not (adds missing items to the inventory)
\trecurse: Recursively and forcefully completes all prerequisite objects whether the requirements are satisfied or not (adds missing items to the inventory)
'''
RESTART_HELP = '''
> restart [guid]\n
Restarts the barter at the specified guid. Required items for the barter are added to the needed inventory\n
guid : A guid belonging to a barter
'''
ADD_HELP = '''
> add [count] [item] {fir}\n
Adds [count] of the specified item by name or guid to the inventory\n
count : A positive integer of items to add to the inventory
item : The name or guid of an item to add
fir : Adds the item as Found In Raid (FIR), otherwise adds as Not found In Raid (NIR)
'''
DELETE_HELP = '''
> del [count] [item] {fir}\n
Removes [count] of the specified item by name or guid from the inventory\n
count : A positive integer of items to remove from the inventory
item : The name or guid of an item to remove
fir : Removes the item from the Found In Raid (FIR) inventory, otherwise removes from the Not found In Raid (NIR) inventory
'''
LEVEL_HELP = '''
> level {operation} {level}\n
Displays the player level\n
operations
\tup : Increments the player level by one (1)
\tset : Sets the player level to {level}
level : The integer value greater than 0 to set the player level at
'''
CLEAR_HELP = '''
> clear\n
Clears the terminal
'''
IMPORT_HELP = '''
> import {prices}\n
Pulls latest Escape From Tarkov game data from api.tarkov.dev and overwrites all application files (WARNING: This will reset all progress!)\n
prices : Manually imports only item price data (Does not reset any progress)
delta : Performs a delta import, attempting to save all current data, including task, hideout, barter, and craft progress while importing updated game data (WARNING: This may corrupt some data!)
'''
BACKUP_HELP = '''
> backup\n
Creates a manual backup of the current database file. This backup will be saved as "database.date.time.bak". You are alloted 2 autosave slots and 5 manual save slots
'''
RESTORE_HELP = '''
> restore\n
Allows you to restore from a backup file. You can choose one of the two autosave backups or any manual backup within the 5 save slots
'''
ITEM_HEADER = '{:<25} {:<60} {:<25} {:<15} {:<12} {:<20} {:<12} {:<20}\n'.format('Item Short Name', 'Item Normalized Name', 'Item GUID', 'Inv (FIR)', 'Sell To', 'Trade / Flea', 'Buy From', 'Trade / Flea')
MAP_HEADER = '{:<30} {:<20}\n'.format('Map Normalized Name', 'Map GUID')
TRADER_HEADER = '{:<30} {:<20}\n'.format('Trader Normalized Name', 'Trader GUID')
INVENTORY_HEADER = '{:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} \n'.format('Item', 'Inv (FIR)', 'Item', 'Inv (FIR)', 'Item', 'Inv (FIR)', 'Item', 'Inv (FIR)')
INVENTORY_HAVE_HEADER = '{:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} \n'.format('Item', 'Have (FIR)', 'Item', 'Have (FIR)', 'Item', 'Have (FIR)', 'Item', 'Have (FIR)')
INVENTORY_NEED_HEADER = '{:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} {:<20} \n'.format('Item', 'Need (FIR)', 'Item', 'Need (FIR)', 'Item', 'Need (FIR)', 'Item', 'Need (FIR)')
TASK_HEADER = '{:<40} {:<20} {:<20} {:<20} {:<20} {:<40}\n'.format('Task Title', 'Task Giver', 'Task Status', 'Tracked', 'Kappa?', 'Task GUID')
HIDEOUT_HEADER = '{:<40} {:<20} {:<20} {:<40}\n'.format('Station Name', 'Station Status', 'Tracked', 'Station GUID')
BARTER_HEADER = '{:<40} {:<20} {:<20} {:<20}\n'.format('Barter GUID', 'Trader', 'Loyalty Level', 'Tracked')
CRAFT_HEADER = '{:<40} {:<20} {:<30} {:<20}\n'.format('Craft Recipe GUID', 'Station', 'Station Level', 'Tracked')
UNTRACKED_HEADER = '{:<40} {:<20} {:<20} {:<20}\n'.format('Entity Name', 'Type', 'Tracked', 'Kappa?')
BUFFER = '-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n'


###################################################
#                                                 #
# UTILITY                                         #
#                                                 #
###################################################


# Command parsing
def parser(tracker_file, command):
    command = command.lower().split(' ')
    print_debug(f'Received command >> {command} <<')

    # Inventory
    if (command[0] == 'inv'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            inventory(tracker_file)
        elif (command[1] == 'tasks'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_tasks(tracker_file)
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_hideout(tracker_file)
        elif (command[1] == 'barters'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_barters(tracker_file)
        elif (command[1] == 'crafts'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_crafts(tracker_file)
        elif (command[1] == 'have'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_have(tracker_file)
        elif (command[1] == 'need'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_need(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(INV_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # List
    elif (command[0] == 'ls'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'tasks'):
            if (len(command) == 3):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                list_tasks(tracker_file, command[2])
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} all <<')
                list_tasks(tracker_file, 'all')
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_stations(tracker_file)
        elif (command[1] == 'barters'):
            if (len(command) == 3):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                list_barters(tracker_file, command[2])
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} all <<')
                list_barters(tracker_file, 'all')
        elif (command[1] == 'crafts'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_crafts(tracker_file)
        elif (command[1] == 'untracked'):
            if (len(command) == 3):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                
                if (command[2] == 'kappa'):
                    list_untracked(tracker_file, True)
                else:
                    print_debug(f'Failed >> {command[0]} {command[1]} <<')
                    print_error('Command not recognized')
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                list_untracked(tracker_file, False)
        elif (command[1] == 'maps'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_maps(tracker_file)
        elif (command[1] == 'traders'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_traders(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(LS_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Search
    elif (command[0] == 'search'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print_message(SEARCH_HELP)
            elif (command[-1] == 'barters'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = True
                pattern = ' '.join(command[1:-1])
                search(tracker_file, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'crafts'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = True
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                search(tracker_file, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'all'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                search(tracker_file, pattern, ignore_barters, ignore_crafts)
            else:
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                ignore_barters = True
                ignore_crafts = True
                pattern = ' '.join(command[1:])
                search(tracker_file, pattern, ignore_barters, ignore_crafts)
    # Requires
    elif (command[0] == 'requires'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print_message(REQUIRES_HELP)
            elif (command[-1] == 'barters'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = True
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'crafts'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = True
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'all'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, pattern, ignore_barters, ignore_crafts)
            else:
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                ignore_barters = True
                ignore_crafts = True
                pattern = ' '.join(command[1:])
                required_search(tracker_file, pattern, ignore_barters, ignore_crafts)
    # Track
    elif (command[0] == 'track'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(TRACK_HELP)
        else:
            print_debug(f'Executing >> {command[0]} {command[1:]} <<')
            track(tracker_file, ' '.join(command[1:]))
    elif (command[0] == 'untrack'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(UNTRACK_HELP)
        else:
            print_debug(f'Executing >> {command[0]} {command[1:]} <<')
            untrack(tracker_file, ' '.join(command[1:]))
    # Complete
    elif (command[0] == 'complete'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                print_message(COMPLETE_HELP)
                return True
            elif (command[-1] == 'force'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                force = True
                recurse = False
                argument = ' '.join(command[1:-1])
            elif (command[-1] == 'recurse'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                force = True
                recurse = True
                argument = ' '.join(command[1:-1])
            else:
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                force = False
                recurse = False
                argument = ' '.join(command[1:])

            complete(tracker_file, argument, force, recurse)
    # Restart
    elif (command[0] == 'restart'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1]):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            restart_barter_or_craft(tracker_file, command[1])
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(RESTART_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Add
    elif (command[0] == 'add'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print_message(ADD_HELP)
            elif (len(command) < 3):
                print_debug(f'Failed >> {command[0]} <<')
                print_error('Command not recognized')
            elif (not command[1].isdigit() or int(command[1]) < 1):
                print_debug(f'Failed >> {command[0]} {command[1]} {command[2:]} <<')
                print_error('Command not recognized')
            elif (command[-1] == 'fir'):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:-1]} {command[-1]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:-1])
                write_item_fir(tracker_file, count, argument = argument)
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:])
                write_item_nir(tracker_file, count, argument = argument)
    # Delete
    elif (command[0] == 'del'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print_message(DELETE_HELP)
            elif (len(command) < 3):
                print_debug(f'Failed >> {command[0]} <<')
                print_error('Command not recognized')
            elif (not command[1].isdigit() or int(command[1]) < 1):
                print_debug(f'Failed >> {command[0]} {command[1]} {command[2:]} <<')
                print_error('Command not recognized')
            elif (command[-1] == 'fir'):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:-1]} {command[-1]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:-1])
                unwrite_item_fir(tracker_file, count, argument = argument)
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:])
                unwrite_item_nir(tracker_file, count, argument = argument)
    # Level
    elif (command[0] == 'level'):
        if (len(command) > 1):
            if (command[1] == 'up'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                level_up(tracker_file)
            elif (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print_message(LEVEL_HELP)
            elif (command[1] == 'set'):
                if (len(command) == 3):
                    if (command[2].isdigit() and int(command[2]) > 0):
                        print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                        set_level(tracker_file, int(command[2]))
                    else:
                        print_debug(f'Failed >> {command[0]} {command[1]} {command[2]} <<')
                        print_error('Command not recognized')
                else:
                    print_debug(f'Failed >> {command[0]} {command[1]} <<')
                    print_error('Command not recognized')
            else:
                print_debug(f'Failed >> {command[0]} {command[1]} <<')
                print_error('Command not recognized')
        else:
            print_debug(f'Executing >> {command[0]} <<')
            check_level(tracker_file)
    # Clear
    elif (command[0] == 'clear'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            clear()
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(CLEAR_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Import
    elif (command[0] == 'import'):
        if (len(command) < 2):
            print_warning('Import and overwite all data? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                import_data(tracker_file, delta_import = False)
            else:
                print_debug(f'Abort >> {command[0]} << because >> {_confirmation_} <<')
                print_message('Aborted')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(IMPORT_HELP)
        elif (command[1] == 'prices'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            database = open_database(tracker_file)
            database = import_items(database, {
                'Content-Tyoe': 'application/json'
            })
            print_message('Price data refreshed')
            write_database(tracker_file, database)
        elif (command[1] == 'delta'):
            print_warning('Import new data without overwriting? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                import_data(tracker_file, delta_import = True)
            else:
                print_debug(f'Abort >> {command[0]} << because >> {_confirmation_} <<')
                print_message('Aborted')
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Backup
    elif (command[0] == 'backup'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            backup(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(BACKUP_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Restore
    elif (command[0] == 'restore'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            restore(tracker_file)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print_message(RESTORE_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Help
    elif (command[0] == 'help' or command[0] == 'h'):
        print_debug(f'Executing >> {command[0]} <<')
        print_message(USAGE)
    # Exit
    elif (command[0] == 'stop' or command[0] == 's' or command[0] == 'quit' or command[0] == 'q' or command[0] == 'exit'):
        print_debug(f'Executing >> {command[0]} <<')
        database = open_database(tracker_file)

        if (tracker_file == 'debug.json'):
            file = 'debug'
        else:
            file = 'database'

        if (f'{file}.prev.bak' in listdir('.')):
            remove(f'{file}.prev.bak')
        
        if (f'{file}.curr.bak' in listdir('.')):
            rename(f'{file}.curr.bak', f'{file}.prev.bak')

        write_database(f'{file}.curr.bak', database)
        print_message(f'Backup saved')
        return False
    # Error
    else:
        print_debug(f'Failed >> {command[0]} <<')
        print_error('Command not recognized. Type "help" for usage')
    
    return True

# Database editing
def open_database(file_path):
    try:
        with open(file_path, 'r', encoding = 'utf-8') as open_file:
            print_debug(f'Opened file >> {file_path} <<')
            file = json.load(open_file)
    except FileNotFoundError:
        print_error('Database not found')
        return False
    
    return file

def write_database(file_path, data):
    with open(file_path, 'w', encoding = 'utf-8') as open_file:
        open_file.write(json.dumps(data))
        print_debug(f'Wrote file >> {file_path} <<')
    return

# Find unique functions (return GUID)
def disambiguate(matches):
    options = []
    index = 0

    for guid, match in matches.items():
        options.append(guid)
        print_message(f'[{index + 1}] {match['normalizedName']} ({guid})')
        index = index + 1
    
    _choice_ = input('> ')

    if (_choice_.isdigit()):
        _choice_ = int(_choice_)

        if (_choice_ > 0 and _choice_ <= len(matches)):
            guid = options[_choice_ - 1]
            print_debug(f'Selected item >> {matches[guid]['normalizedName']}')
            return guid
    
    print_error('Invalid selection')
    return False

def find_task(text, database):
    print_debug(f'Searching for task >> {text} <<')
    tasks = {}

    for guid, task in database['tasks'].items():
        if (string_compare(text, task['normalizedName']) or guid == text):
            print_debug(f'Found matching task >> {task['normalizedName']} <<')
            tasks[guid] = task

    if (len(tasks) == 0):
        return False
    elif (len(tasks) == 1):
        return next(iter(tasks))
    else:
        print_warning(f'Found {len(tasks)} tasks for {text}. Please choose one')
        return disambiguate(tasks)

def find_station(text, database):
    print_debug(f'Searching for hideout station >> {text} <<')
    stations = {}

    for guid, station in database['hideout'].items():
        if (string_compare(text, station['normalizedName']) or guid == text):
            print_debug(f'Found matching station >> {station['normalizedName']} <<')
            stations[guid] = station

    if (len(stations) == 0):
        return False
    elif (len(stations) == 1):
        return next(iter(stations))
    else:
        print_warning(f'Found {len(stations)} hideout stations for {text}. Please choose one')
        return disambiguate(stations)

def find_barter(text, database):
    print_debug(f'Searching for hideout station >> {text} <<')
    barters = {}

    for guid, barter in database['barters'].items():
        if (guid == text):
            print_debug(f'Found matching barter >> {guid} <<')
            barters[guid] = barter

    if (len(barters) == 0):
        return False
    elif (len(barters) == 1):
        return next(iter(barters))
    else:
        print_warning(f'Found {len(barters)} barters for {text}. Please choose one')
        return disambiguate(barters)

def find_craft(text, database):
    print_debug(f'Searching for craft >> {text} <<')
    crafts = {}

    for guid, craft in database['crafts'].items():
        if (guid == text):
            print_debug(f'Found matching craft >> {guid} <<')
            crafts[guid] = craft

    if (len(crafts) == 0):
        return False
    elif (len(crafts) == 1):
        return next(iter(crafts))
    else:
        print_warning(f'Found {len(crafts)} crafts for {text}. Please choose one')
        return disambiguate(crafts)

def find_item(text, database):
    print_debug(f'Searching for item >> {text} <<')
    items = {}

    for guid, item in database['items'].items():
        if (string_compare(text, item['normalizedName']) or string_compare(text, item['shortName']) or guid == text):
            print_debug(f'Found matching item >> {item['normalizedName']} <<')
            items[guid] = item

    if (len(items) == 0):
        return False
    elif (len(items) == 1):
        return next(iter(items))
    else:
        print_warning(f'Found {len(items)} items for {text}. Please choose one')
        return disambiguate(items)

def find_map(text, database):
    print_debug(f'Searching for map >> {text} <<')
    maps = {}

    for guid, map in database['maps'].items():
        if (string_compare(text, map['normalizedName']) or guid == text):
            print_debug(f'Found matching map >> {map['normalizedName']} <<')
            maps[guid] = map

    if (len(maps) == 0):
        return False
    elif (len(maps) == 1):
        return next(iter(maps))
    else:
        print_warning(f'Found {len(maps)} maps for {text}. Please choose one')
        return disambiguate(maps)

def find_trader(text, database):
    print_debug(f'Searching for trader >> {text} <<')
    traders = {}

    for guid, trader in database['traders'].items():
        if (string_compare(text, trader['normalizedName']) or guid == text):
            print_debug(f'Found matching trader >> {trader['normalizedName']} <<')
            traders[guid] = trader

    if (len(traders) == 0):
        return False
    elif (len(traders) == 1):
        return next(iter(traders))
    else:
        print_warning(f'Found {len(traders)} traders for {text}. Please choose one')
        return disambiguate(traders)

def create_filter(text, database):
    filters = {}

    for guid, map in database['maps'].items():
        if (string_compare(text, map['normalizedName']) or guid == text):
            filters[guid] = map

    for guid, trader in database['traders'].items():
        if (string_compare(text, trader['normalizedName']) or guid == text):
            filters[guid] = trader

    if (len(filters) == 0):
        return False
    elif (len(filters) == 1):
        return next(iter(filters))
    else:
        print_warning(f'Found {len(filters)} filter matches for {text}. Please choose one')
        return disambiguate(filters)

# String functions
def normalize(text):
    unwanted_strings = ['', '.', '(', ')', '+', '=', '\'', '"', ',', '\\', '/', '?', '#', '$', '&', '!', '@', '[', ']', '{', '}', '-', '_']
    normalized = text.lower()

    for string in unwanted_strings:
        normalized = normalized.replace(string, '')
    
    normalized = re.sub(' +', ' ', normalized)
    print_debug(f'Normalized >> {text} << to >> {normalized} <<')
    return normalized

def string_compare(comparable, comparator):
    comparable_words = normalize(comparable).split(' ')
    comparator_words = normalize(comparator).split(' ')

    for comparable_word in comparable_words:
        for comparator_word in comparator_words:
            if (comparable_word not in comparator_word):
                print_debug(f'>> {comparable_words} << != >> {comparator_words} <<')
                return False

    print_debug(f'>> {comparable_words} << == >> {comparator_words} <<')
    return True

def alphabetize_items(items):
    print_debug(f'Alphabetizing dict of size >> {len(items)} <<')
    return {guid: item for guid, item in sorted(items.items(), key = lambda item: item[1]['shortName'])}

def format_price(price, currency):
    currency = currency.lower()

    if (currency == 'usd'):
        return '${:,}'.format(price)
    elif (currency == 'euro'):
        return '€{:,}'.format(price)
    else:
        return '₽{:,}'.format(price)

# Verify functions
def verify_task(database, task):
    if (task['status'] == 'complete'):
        return f'Task {task["name"]} is complete'
    
    if (not task['tracked']):
        return f'Task {task["name"]} is not tracked'
    
    if (database['player_level'] < task['minPlayerLevel']):
        return f'Task {task["name"]} requires player level {task["minPlayerLevel"]} > current level {database["player_level"]}'
    
    for prereq in task['taskRequirements']:
        if ('id' in prereq):
            id = prereq['id']
        else:
            id = prereq['task']['id']

        if (database['tasks'][id] == 'incomplete'):
            return f'{database['tasks'][id]['name']} must be completed first'
    
    print_debug(f'Verified task >> {task["name"]} <<')
    return True

def verify_station(database, station):
    if (station['status'] == 'complete'):
        return f'Hideout station {station["normalizedName"]} is complete'
    
    if (not station['tracked']):
        return f'Hideout station {station["normalizedName"]} is not tracked'

    for prereq in station['stationLevelRequirements']:
        if (database['hideout'][prereq['station']['id'] + '-' + str(prereq['level'])]['status'] != 'complete'):
            return f'{database['hideout'][prereq['station']['id']]['normalizedName']} must be completed first'
        
    print_debug(f'Verified station >> {station["normalizedName"]} <<')
    return True

def verify_barter(database, guid):
    if (database['barters'][guid]['status'] == 'complete'):
        return f'Barter {guid} is complete'
    
    if (not database['barters'][guid]['tracked']):
        return f'Barter {guid} is not tracked'
    
    print_debug(f'Barter verified >> {guid} <<')
    return True

def verify_craft(database, guid):
    if (database['crafts'][guid]['status'] == 'complete'):
        return f'Barter {guid} is complete'
    
    if (not database['crafts'][guid]['tracked']):
        return f'Barter {guid} is not tracked'
    
    print_debug(f'Barter verified >> {guid} <<')
    return True

# Add Items
def add_item_fir(database, count, guid):
    item_name = database['items'][guid]['normalizedName']

    if (database['items'][guid]['need_nir'] == 0 and database['items'][guid]['need_fir'] == 0):
        print_message(f'{item_name} is not needed')
        return False

    if (database['items'][guid]['need_fir'] == 0):
        print_message(f'{item_name} (FIR) is not needed')
        database = add_item_nir(database, count, guid = guid)
    elif (database['items'][guid]['have_fir'] == database['items'][guid]['need_fir']):
        print_message(f'{item_name} (FIR) already found')
        database = add_item_nir(database, count, guid = guid)
    elif (database['items'][guid]['have_fir'] + count > database['items'][guid]['need_fir']):
        _remainder_ = database['items'][guid]['have_fir'] + count - database['items'][guid]['need_fir']
        print_message(f'Added {count - _remainder_} {item_name} (FIR) (COMPLETED)')
        database = add_item_nir(database, count, guid = guid)
        database['items'][guid]['have_fir'] = database['items'][guid]['need_fir']
    elif (database['items'][guid]['have_fir'] + count == database['items'][guid]['need_fir']):
        database['items'][guid]['have_fir'] = database['items'][guid]['need_fir']
        print_message(f'Added {count} {item_name} (FIR) (COMPLETED)')
    else:
        database['items'][guid]['have_fir'] = database['items'][guid]['have_fir'] + count
        print_message(f'Added {count} {item_name} (FIR)')

    if (not database):
        print_error('Something went wrong. Aborted')
        return False

    return database

def add_item_nir(database, count, guid = ''):    
    item_name = database['items'][guid]['normalizedName']

    if (database['items'][guid]['need_nir'] == 0 and database['items'][guid]['need_fir'] == 0):
        print_message(f'{item_name} is not needed')
        return False

    if (database['items'][guid]['need_nir'] == 0):
        print_message(f'{item_name} (NIR) is not needed')
    elif (database['items'][guid]['have_nir'] == database['items'][guid]['need_nir']):
        print_message(f'{item_name} (NIR) already found')
    elif (database['items'][guid]['have_nir'] + count > database['items'][guid]['need_nir']):
        _remainder_ = database['items'][guid]['have_nir'] + count - database['items'][guid]['need_nir']
        database['items'][guid]['have_nir'] = database['items'][guid]['need_nir']
        print_message(f'Added {count - _remainder_} {item_name} (NIR) (COMPLETED). Skipped {_remainder_} items')
    elif (database['items'][guid]['have_nir'] + count == database['items'][guid]['need_nir']):
        database['items'][guid]['have_nir'] = database['items'][guid]['need_nir']
        print_message(f'Added {count} {item_name} (NIR) (COMPLETED)')
    else:
        database['items'][guid]['have_nir'] = database['items'][guid]['have_nir'] + count
        print_message(f'Added {count} {item_name} (NIR)')

    if (not database):
        print_error('Something went wrong. Aborted')
        return False

    return database

# Delete Items
def del_item_fir(database, count, guid = ''):    
    item_name = database['items'][guid]['normalizedName']
    
    if (database['items'][guid]['have_fir'] == 0):
        print_error(f'Nothing to delete for {item_name} (FIR)')
        return False

    if (database['items'][guid]['have_fir'] - count < 0):
        count = database['items'][guid]['have_fir']
        database['items'][guid]['have_fir'] = 0
    else:
        database['items'][guid]['have_fir'] = database['items'][guid]['have_fir'] - count

    remaining = database['items'][guid]['have_fir']
    print_message(f'Removed {count} {item_name} (FIR) ({remaining} remaining FIR)')
    return database

def del_item_nir(database, count, guid = ''):
    item_name = database['items'][guid]['normalizedName']
    
    if (database['items'][guid]['have_nir'] == 0):
        print_error(f'Nothing to delete for {item_name} (NIR)')
        return False

    if (database['items'][guid]['have_nir'] - count < 0):
        count = database['items'][guid]['have_nir']
        database['items'][guid]['have_nir'] = 0
    else:
        database['items'][guid]['have_nir'] = database['items'][guid]['have_nir'] - count

    remaining = database['items'][guid]['have_nir']
    print_message(f'Removed {count} {item_name} (NIR) ({remaining} remaining NIR)')
    return database

# Console output
def display_bool(bool_value):
    if (bool_value):
        return 'true'
    else:
        return 'false'
    
def print_debug(message):
    if (DEBUG):
        #print(f'>> (DEBUG) {message}')
        return True
    
    return False

def print_message(message):
    print(f'{message}')
    return True

def print_warning(message):
    print(f'>> (WARNING) {message}')
    return True

def print_error(message):
    print(f'>> (ERROR) {message}!')
    return True


###################################################
#                                                 #
# WORKER                                          #
#                                                 #
###################################################


# Inventory functions
def stage_inventory(database):
    for guid, item in database['items'].items():
        item['need_fir'] = 0
        item['need_nir'] = 0
        item['have_fir'] = 0
        item['have_nir'] = 0
        item['consumed_fir'] = 0
        item['consumed_nir'] = 0
        database['items'][guid] = item

    print_message('Inventory staged')
    return database

def calculate_inventory(database):
    for guid, task in database['tasks'].items():
        if (not task['tracked']):
            continue

        for objective in task['objectives']:
            if (objective['type'] == 'giveItem'):
                item_guid = objective['item']['id']
                fir = objective['foundInRaid']

                if (fir):
                    database['items'][item_guid]['need_fir'] = database['items'][item_guid]['need_fir'] + objective['count']
                else:
                    database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_fir'] + objective['count']
        
        if (task['neededKeys'] is not None and len(task['neededKeys']) > 0):
            for _key_ in task['neededKeys']:
                for key in _key_['keys']:
                    item_guid = key['id']
                    database['items'][item_guid]['need_nir'] = 1
    
    print_message('Added all items required for tracked tasks to the database')

    for guid, station in database['hideout'].items():
        if (not station['tracked']):
            continue

        for requirement in station['itemRequirements']:
            item_guid = requirement['item']['id']
            database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_fir'] + requirement['count']

    print_message('Added all items required for tracked hideout stations to the database')

    for guid, barter in database['barters'].items():
        if (not barter['tracked']):
            continue

        for requirement in barter['requiredItems']:
            item_guid = requirement['item']['id']
            database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_fir'] + requirement['count']

    print_message('Added all items required for tracked barters to the database')

    for guid, craft in database['crafts'].items():
        if (not craft['tracked']):
            continue

        for requirement in craft['requiredItems']:
            item_guid = requirement['item']['id']
            database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_fir'] + requirement['count']

    print_message('Added all items required for tracked crafts to the database')
    return database

def get_inventory(database):
    print_debug('Compiling inventory')
    items = {}

    for guid, item in database['items'].items():
        if (item['need_nir'] > 0 or item['need_fir'] > 0 or item['have_fir'] > 0 or item['have_nir'] > 0):
            items[guid] = item

    return items

def get_inventory_have(database):
    print_debug('Compiling have inventory')
    items = {}

    for guid, item in database['items'].items():
        if (item['have_fir'] > 0 or item['have_nir'] > 0):
            items[guid] = item

    return items

def get_inventory_need(database):
    print_debug('Compiling need inventory')
    items = {}

    for guid, item in database['items'].items():
        if (item['need_fir'] - item['have_fir'] > 0 or item['need_nir'] - item['have_nir'] > 0):
            item['need_fir'] = item['need_fir'] - item['have_fir']
            item['need_nir'] = item['need_nir'] - item['have_nir']
            items[guid] = item

    return items

def get_inventory_tasks(database):
    print_debug('Compiling inventory for tasks')
    items = {}

    for guid, task in database['tasks'].items():
        for objective in task['objectives']:
            if (task['tracked']):
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    fir = objective['foundInRaid']

                    if (item_guid not in items.keys()):
                        items[item_guid] = database['items'][item_guid]
                        items[item_guid]['need_fir'] = 0
                        items[item_guid]['need_nir'] = 0

                    if (fir):
                        items[item_guid]['need_fir'] = items[item_guid]['need_fir'] + objective['count']
                    else:
                        items[item_guid]['need_nir'] = items[item_guid]['need_nir'] + objective['count']

    return items

def get_inventory_hideout(database):
    print_debug('Compiling inventory for stations')
    items = {}

    for guid, station in database['hideout'].items():
        if (not station['tracked']):
            continue

        for requirement in station['itemRequirements']:
            item_guid = requirement['item']['id']

            if (item_guid not in items.keys()):
                items[item_guid] = database['items'][item_guid]
                items[item_guid]['need_fir'] = 0
                items[item_guid]['need_nir'] = 0

            items[item_guid]['need_nir'] = items[item_guid]['need_nir'] + requirement['count']

    return items

def get_inventory_barters(database):
    print_debug('Compiling inventory for barters')
    items = {}

    for guid, barter in database['barters'].items():
        if (not barter['tracked']):
            continue

        for requirement in barter['requiredItems']:
            item_guid = requirement['item']['id']

            if (item_guid not in items.keys()):
                items[item_guid] = database['items'][item_guid]
                items[item_guid]['need_fir'] = 0
                items[item_guid]['need_nir'] = 0

            items[item_guid]['need_nir'] = items[item_guid]['need_nir'] + requirement['count']

    return items

def get_inventory_crafts(database):
    print_debug('Compiling inventory for crafts')
    items = {}

    for guid, craft in database['crafts'].items():
        if (not craft['tracked']):
            continue

        for requirement in craft['requiredItems']:
            item_guid = requirement['item']['id']

            if (item_guid not in items.keys()):
                items[item_guid] = database['items'][item_guid]
                items[item_guid]['need_fir'] = 0
                items[item_guid]['need_nir'] = 0

            items[item_guid]['need_nir'] = items[item_guid]['need_nir'] + requirement['count']

    return items

# List functions
def get_tasks(database):
    print_debug('Compiling available tasks')
    tasks = {}

    for guid, task in database['tasks'].items():
        if (verify_task(database, task) == True):
            print_debug(f'Found available task >> {task["name"]} <<')
            tasks[guid] = task

    return tasks

def get_tasks_filtered(database, argument):
    print_debug(f'Compiling available tasks with filter >> {argument} <<')
    tasks = {}
    filter = create_filter(argument, database)

    for guid, task in database['tasks'].items():
        if (verify_task(database, task) != True):
            continue

        if (not filter):
            return {}

        if (filter in database['maps'].keys()):
            invalid = False
            potential = False

            for objective in task['objectives']:
                if (len(objective['maps']) == 0):
                    print_debug(f'Found task >> {task["name"]} << for map >> {argument} <<')
                    potential = True

                for map in objective['maps']:
                    if (map['id'] == filter):
                        print_debug(f'Found task >> {task["name"]} << for map >> {argument} <<')
                        tasks[guid] = task
                        break
                    else:
                        invalid = True
                else:
                    continue
                break
            else:
                if (potential and not invalid):
                    tasks[guid] = task
            continue

        else:
            if (task['trader']['id'] == filter):
                print_debug(f'Found task >> {task["name"]} << for trader >> {argument} <<')
                tasks[guid] = task

    return tasks

def get_hideout(database):
    print_debug('Compiling available stations')
    stations = {}

    for guid, station in database['hideout'].items():
        if (verify_station(database, station) == True):
            print_debug(f'Found available station >> {station["normalizedName"]} <<')
            stations[guid] = station
    
    return stations

def get_barters(database):
    print_debug('Compiling available barters')
    barters = {}

    for guid, barter in database['barters'].items():
        if (verify_barter(barter) == True):
            print_debug(f'Found available barter >> {guid} <<')
            barters[guid] = barter

    return barters

def get_barters_filtered(database, argument):
    print_debug(f'Compiling barters for trader >> {argument} <<')
    barters = {}
    filter = find_trader(argument, database)

    for guid, barter in database['barters'].items():
        if (verify_barter(barter) != True):
            continue

        if (not filter):
            return {}

        if (barter['trader']['id'] == filter):
            print_debug(f'Found barter >> {guid} << for trader ?> {argument} <<')
            barters[guid] = barter

    return barters

def get_crafts(database):
    print_debug('Compiling available crafts')
    crafts = {}

    for guid, craft in database['crafts'].items():
        if (verify_craft(craft) == True):
            print_debug(f'Found available craft >> {guid} <<')
            crafts.append(craft)

    return crafts

def get_untracked(database, ignore_kappa):
    print_debug(f'Compiling untracked entities for Kappa >> ({display_bool(ignore_kappa)}) <<')
    untracked = {}

    for guid, task in database['tasks'].items():
        if (not task['tracked']):
            if (not task['kappaRequired'] and not ignore_kappa):
                continue

            print_debug(f'Found untracked task >> {task["name"]} <<')
            untracked[guid] = task

    for guid, station in database['hideout'].items():
        if (not station['tracked']):
            print_debug(f'Found untracked station >> {station["normalizedName"]} <<')
            untracked[guid] = station
    
    return untracked

def get_saves(file):
    files = listdir()
    saves = []
    print_debug(f'Compiling save files for >> {file} <<')

    if (f'{file}.curr.bak' in files):
        print_debug(f'Found current autosave >> {file}.curr.bak <<')
        saves.append(f'{file}.curr.bak')
    else:
        print_debug('Current autosave not found')
        saves.append('')

    if (f'{file}.prev.bak' in files):
        print_debug(f'Found previous autosave >> {file}.prev.bak <<')
        saves.append(f'{file}.prev.bak')
    else:
        print_debug('Previous autosave not found')
        saves.append('')

    for save in files:
        if (file in save and save != f'{file}.json' and save != f'{file}.curr.bak' and save != f'{file}.prev.bak'):
            print_debug(f'Found save >> {save} <<')
            saves.append(save)
    
    return saves

# Search functions (return dict)
def search_tasks(text, database):
    print_debug(f'Searching for tasks matching >> {text} <<')
    tasks = {}

    for guid, task in database['tasks'].items():
        if (string_compare(text, task['normalizedName']) or guid == text):
            print_debug(f'Found matching task >> {task['normalizedName']} <<')
            tasks[guid] = task

    if (len(tasks) == 0):
        return False
        
    return tasks

def search_hideout(text, database):
    print_debug(f'Searching for hideout stations matching >> {text} <<')
    stations = {}

    for guid, station in database['hideout'].items():
        if (string_compare(text, station['normalizedName']) or guid == text):
            print_debug(f'Found matching station >> {station['normalizedName']} <<')
            stations[guid] = station

    if (len(stations) == 0):
        return False

    return stations

def search_barters(text, database):
    print_debug(f'Searching for barters matching >> {text} <<')
    barters = {}

    for guid, barter in database['barters'].items():
        if (guid == text):
            print_debug(f'Found matching barter >> {guid} <<')
            barters[guid] = barter

    if (len(barters) == 0):
        return False

    return barters

def search_crafts(text, database):
    print_debug(f'Searching for crafts matching >> {text} <<')
    crafts = {}

    for guid, craft in database['crafts'].items():
        if (guid == text):
            print_debug(f'Found matching craft >> {guid} <<')
            crafts[guid] = craft

    if (len(crafts) == 0):
        return False

    return crafts

def search_items(text, database):
    print_debug(f'Searching for items matching >> {text} <<')
    items = {}

    for guid, item in database['items'].items():
        if (string_compare(text, item['normalizedName']) or string_compare(text, item['shortName']) or guid == text):
            print_debug(f'Found matching item >> {item['normalizedName']} <<')
            items[guid] = item

    if (len(items) == 0):
        return False

    return items

def search_maps(text, database):
    print_debug(f'Searching for maps matching >> {text} <<')
    maps = {}

    for guid, map in database['maps'].items():
        if (string_compare(text, map['normalizedName']) or guid == text):
            print_debug(f'Found matching map >> {map['normalizedName']} <<')
            maps[guid] = map

    if (len(maps) == 0):
        return False

    return maps

def search_traders(text, database):
    print_debug(f'Searching for traders matching >> {text} <<')
    traders = {}

    for guid, trader in database['traders'].items():
        if (string_compare(text, trader['normalizedName']) or guid == text):
            print_debug(f'Found matching trader >> {trader['normalizedName']} <<')
            traders[guid] = trader

    if (len(traders) == 0):
        return False

    return traders

def search_tasks_by_item(text, database):
    tasks = {}

    for guid, task in database['tasks'].items():
        for objective in task['objectives']:
            if (objective['type'] == 'giveItem'):
                item_guid = objective['item']['id']

                if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                    tasks[guid] = task
                    break

        if (task['neededKeys'] is not None):
            for _key_ in task['neededKeys']:
                for key in _key_['keys']:
                    item_guid = key['id']

                    if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                        task[guid] = task
                        break
                else:
                    continue
                break
    
    if (len(tasks) == 0):
        return False

    return tasks

def search_hideout_by_item(text, database):
    hideout = {}

    for guid, station in database['hideout'].items():
        for requirement in station['itemRequirements']:
            item_guid = requirement['item']['id']

            if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                hideout[guid] = station
    
    if (len(hideout) == 0):
        return False

    return hideout

def search_barters_by_item(text, database, required_only = False):
    barters = {}

    for guid, barter in database['barters'].items():
        for item_guid in barter['requiredItems']:
            item_guid = item_guid['item']['id']

            if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                barters[guid] = barter

        if (not required_only):
            for item_guid in barter['rewardItems']:
                item_guid = item_guid['item']['id']

                if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                    barters[guid] = barter
    
    if (len(barters) == 0):
        return False
        
    return barters

def search_crafts_by_item(text, database, required_only = False):
    crafts = {}

    for guid, craft in database['crafts'].items():
        for item_guid in craft['requiredItems']:
            item_guid = item_guid['item']['id']

            if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                crafts[guid] = craft

        if (not required_only):
            for item_guid in craft['rewardItems']:
                item_guid = item_guid['item']['id']

                if (string_compare(text, database['items'][item_guid]['normalizedName']) or string_compare(text, database['items'][item_guid]['shortName']) or item_guid == text):
                    crafts[guid] = craft
    
    if (len(crafts) == 0):
        return False
        
    return crafts

# Track functions
def track_task(database, guid):
    print_debug(f'Tracking task >> {guid} <<')

    for task in database['tasks']:
        if (task['id'] == guid):
            if (task['tracked']):
                print_message(f'Already tracking {task["name"]}')
                return database
            
            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    count = objective['count']
                    print_debug(f'Adding >> {count} << of >> {item_guid} << for objective >> {objective["description"]} <<')

                    if (objective['foundInRaid']):
                        print_debug('FIR')
                        database['inventory'][item_guid]['need_fir'] = database['inventory'][item_guid]['need_fir'] + count
                        print_message(f'{count} more {item_name} (FIR) now needed')
                    else:
                        print_debug('NIR')
                        database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] + count
                        print_message(f'{count} more {item_name} (NIR) now needed')

            task['tracked'] = True
            print_message(f'Tracked {task["name"]}')
                
    return database

def track_station(database, guid):
    print_debug(f'Tracking station >> {guid} <<')

    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (level['tracked']):
                    print_message(f'Already tracking {level["normalizedName"]}')
                    return database
                
                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    count = requirement['count']
                    print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement >> {requirement["id"]} <<')
                    database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] + count
                    print_message(f'{count} more {item_name} (NIR) now needed')

                level['tracked'] = True
                print_message(f'Tracked {level["normalizedName"]}')
                
    return database

def track_barter(database, guid):
    print_debug(f'Tracking barter >> {guid} <<')
    write_database('test.json', database)

    for barter in database['barters']:
        if (barter['id'] == guid):
            print_debug(f'Found >> {guid} <<')

            if (barter['tracked']):
                print_message(f'Already tracking {barter["id"]}')
                return database, True
            
            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
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
                
                print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
                print_message(f'{count} more {item_name} (NIR) now needed')

            barter['tracked'] = True
            print_message(f'Tracked {barter["id"]}')
            break
    else:
        return database, False
                
    return database, True

def track_craft(database, guid):
    print_debug(f'Tracking craft >> {guid} <<')

    for craft in database['crafts']:
        if (craft['id'] == guid):
            if (craft['tracked']):
                print_message(f'Already tracking {craft["id"]}')
                return database, True
            
            for requirement in craft['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
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
                
                print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
                print_message(f'{count} more {item_name} (NIR) now needed')

            craft['tracked'] = True
            print_message(f'Tracked {craft["id"]}')
            break
    else:
        return database, False
                
    return database, False

def untrack_task(database, guid):
    for task in database['tasks']:
        if (task['id'] == guid):
            if (not task['tracked'] and task['id'] != '5c51aac186f77432ea65c552' and task['id'] != '5edac020218d181e29451446'):
                print_message(f'{task["name"]} is already untracked')
                return database
            
            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    count = objective['count']

                    if (objective['foundInRaid']):
                        database['inventory'][item_guid]['need_fir'] = database['inventory'][item_guid]['need_fir'] - count
                        print_message(f'{count} less {item_name} (FIR) needed')
                    else:
                        database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                        print_message(f'{count} less {item_name} (NIR) needed')

            task['tracked'] = False
            print_message(f'Untracked {task["name"]}')
                
    return database

def untrack_station(database, guid):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (not level['tracked']):
                    print_message(f'{level["normalizedName"]} is already untracked')
                    return database
                
                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    count = requirement['count']
                    database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                    print_message(f'{count} less {item_name} (NIR) needed')

                level['tracked'] = False
                print_message(f'Untracked {level["normalizedName"]}')
                
    return database

def untrack_barter(database, guid):
    for barter in database['barters']:
        if (barter['id'] == guid):
            if (not barter['tracked']):
                print_message(f'{barter["id"]} is already untracked')
                return database, True
            
            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                count = requirement['count']
                database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                print_message(f'{count} less {item_name} (NIR) needed')

            barter['tracked'] = False
            print_message(f'Untracked {barter["id"]}')
            break
    
    else:
        return database, False
                
    return database, True

def untrack_craft(database, guid):
    for craft in database['crafts']:
        if (craft['id'] == guid):
            if (not craft['tracked']):
                print_message(f'{craft["id"]} is already untracked')
                return database, True
            
            for requirement in craft['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                count = requirement['count']
                database['inventory'][item_guid]['need_nir'] = database['inventory'][item_guid]['need_nir'] - count
                print_message(f'{count} less {item_name} (NIR) needed')

            craft['tracked'] = False
            print_message(f'Untracked {craft["id"]}')
            break
    
    else:
        return database, False
                
    return database, True

# Complete functions
def complete_task(database, guid, force):
    for task in database['tasks']:
        if (task['id'] == guid):
            if (task['status'] == 'complete'):
                print_message(f'{task["name"]} is already complete')
                return False

            if (not task['tracked'] and not force):
                print_error(f'{task["name"]} is not tracked')
                return False

            task_table = {}
            consumer_table = {}

            for seen_task in database['tasks']:
                task_table[seen_task['id']] = seen_task['status']

            _return_ = verify_task(database, task, task_table)
                                    
            if (type(_return_) is str and not force):
                print_error(_return_)
                return False

            for objective in task['objectives']:
                if (objective['type'] == 'giveItem'):
                    item_guid = objective['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    available_fir = get_fir_count_by_guid(database, item_guid)
                    available_nir = get_nir_count_by_guid(database, item_guid)

                    if (objective['foundInRaid']):
                        need_fir = objective['count']
                        _remainder_ = need_fir - available_fir

                        if (_remainder_ > 0 and not force):
                            print_error(f'{_remainder_} more {item_name} (FIR) required')
                            return False                     
                        elif (force):
                            database = add_item_fir(database, _remainder_, guid = item_guid)

                            if (not database):
                                return False
                        
                        consumer_table[item_guid] = {
                            'count': need_fir,
                            'type': 'fir'
                        }
                    else:
                        need_nir = objective['count']
                        _remainder_ = need_nir - available_nir

                        if (_remainder_ > 0):
                            if (available_fir < _remainder_ and not force):
                                print_error(f'{_remainder_} more {item_name} required')
                                return False
                            elif (force):
                                database = add_item_nir(database, _remainder_, guid = item_guid)

                                if (not database):
                                    return False
                            else:
                                print_message(f'{_remainder_} more {item_name} required. Consume {_remainder_} (FIR) instead? (Y/N)')
                                _confirmation_ = input('> ').lower()

                                if (_confirmation_ == 'y'):
                                    database = del_item_fir(database, _remainder_, guid = item_guid)
                                    database = add_item_nir(database, _remainder_, guid = item_guid)

                                    if (not database):
                                        return False
                                else:
                                    print_error('Aborted')
                                    return False
                                
                        consumer_table[item_guid] = {
                            'count': need_nir,
                            'type': 'nir'
                        }
            
            for item_guid in consumer_table.keys():
                if (consumer_table[item_guid]['type'] == 'fir'):
                    database['inventory'][item_guid]['consumed_fir'] = database['inventory'][item_guid]['consumed_fir'] + consumer_table[item_guid]['count']
                else:
                    database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + consumer_table[item_guid]['count']
            
            task['status'] = 'complete'
            print_message(f'{task["name"]} completed')
            break
    else:
        print_error(f'Could not find {guid}')

    return database

def complete_recursive_task(database, guid, tasks = []):
    for task in database['tasks']:
        if (task['id'] == guid):
            for prereq in task['taskRequirements']:
                tasks.append(prereq['task']['id'])
                tasks =  complete_recursive_task(database, prereq['task']['id'], tasks)
    
    return tasks

def complete_station(database, guid, force):
    for station in database['hideout']:
        for level in station['levels']:
            if (level['id'] == guid):
                if (level['status'] == 'complete'):
                    print_message(f'{level["normalizedName"]} is already complete')
                    return False

                if (not level['tracked'] and not force):
                    print_error(f'{level["normalizedName"]} is not tracked')
                    return False

                _return_ = verify_hideout_level(database, level)
                consumer_table = {}

                if (type(_return_) is str and not force):
                    print_error(_return_)
                    return False

                for requirement in level['itemRequirements']:
                    item_guid = requirement['item']['id']
                    item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                    available_fir = get_fir_count_by_guid(database, item_guid)
                    available_nir = get_nir_count_by_guid(database, item_guid)
                    need_nir = requirement['count']
                    _remainder_ = need_nir - available_nir

                    if (_remainder_ > 0):
                        if (available_fir < _remainder_ and not force):
                            print_error(f'{_remainder_} more {item_name} required')
                            return False
                        elif (force):
                            database = add_item_nir(database, _remainder_, guid = item_guid)

                            if (not database):
                                return False
                        else:
                            print_message(f'{_remainder_} more {item_name} required. Consume {_remainder_} (FIR) instead? (Y/N)')
                            _confirmation_ = input('> ').lower()

                            if (_confirmation_ == 'y'):
                                database = del_item_fir(database, _remainder_, guid = item_guid)
                                database = add_item_nir(database, _remainder_, guid = item_guid)

                                if (not database):
                                    return False
                            else:
                                print_error('Aborted')
                                return False
                                
                    consumer_table[item_guid] = need_nir
                
                for item_guid in consumer_table.keys():
                    database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + consumer_table[item_guid]
                
                level['status'] = 'complete'
                print_message(f'{level["normalizedName"]} completed')
                break
        else:
            continue
        break
    else:
        print_error(f'Could not find {guid}')

    return database

def complete_barter(database, guid, force):
    for barter in database['barters']:
        if (barter['id'] == guid):
            if (barter['status'] == 'complete'):
                print_message(f'{barter["id"]} is already complete')
                return False
            
            if (not barter['tracked'] and not force):
                print_error(f'{barter["id"]} is not tracked')
                return False

            _return_ = verify_barter(barter)
            consumer_table = {}

            if (type(_return_) is str and not force):
                print_error(_return_)
                return False

            for requirement in barter['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                available_fir = get_fir_count_by_guid(database, item_guid)
                available_nir = get_nir_count_by_guid(database, item_guid)
                need_nir = requirement['count']
                _remainder_ = need_nir - available_nir

                if (_remainder_ > 0):
                    if (available_fir < _remainder_ and not force):
                        print_error(f'{_remainder_} more {item_name} required')
                        return False
                    elif (force):
                        database = add_item_nir(database, _remainder_, guid = item_guid)

                        if (not database):
                            return False
                    else:
                        print_message(f'{_remainder_} more {item_name} required. Consume {available_fir} (FIR) instead? (Y/N)')
                        _confirmation_ = input('> ').lower()

                        if (_confirmation_ == 'y'):
                            database = del_item_fir(database, _remainder_, guid = item_guid)
                            database = add_item_nir(database, _remainder_, guid = item_guid)

                            if (not database):
                                return False
                        else:
                            print_error('Aborted')
                            return False
                            
                consumer_table[item_guid] = need_nir
            
            for item_guid in consumer_table.keys():
                database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + consumer_table[item_guid]
            
            barter['status'] = 'complete'
            print_message(f'{barter["id"]} completed')
            break
    else:
        return None

    return database

def complete_craft(database, guid, force):
    for craft in database['crafts']:
        if (craft['id'] == guid):
            if (craft['status'] == 'complete'):
                print_message(f'{craft["id"]} is already complete')
                return False
            
            if (not craft['tracked'] and not force):
                print_error(f'{craft["id"]} is not tracked')
                return False

            _return_ = verify_craft(craft)
            consumer_table = {}

            if (type(_return_) is str and not force):
                print_error(_return_)
                return False

            for requirement in craft['requiredItems']:
                item_guid = requirement['item']['id']
                item_name = find(item_guid, database, type = GUID, object = ITEM)['normalizedName']
                available_fir = get_fir_count_by_guid(database, item_guid)
                available_nir = get_nir_count_by_guid(database, item_guid)
                need_nir = requirement['count']
                _remainder_ = need_nir - available_nir

                if (_remainder_ > 0):
                    if (available_fir < _remainder_ and not force):
                        print_error(f'{_remainder_} more {item_name} required')
                        return False
                    elif (force):
                        database = add_item_nir(database, _remainder_, guid = item_guid)

                        if (not database):
                            return False
                    else:
                        print_message(f'{_remainder_} more {item_name} required. Consume {available_fir} (FIR) instead? (Y/N)')
                        _confirmation_ = input('> ').lower()

                        if (_confirmation_ == 'y'):
                            database = del_item_fir(database, _remainder_, guid = item_guid)
                            database = add_item_nir(database, _remainder_, guid = item_guid)

                            if (not database):
                                return False
                        else:
                            print_error('Aborted')
                            return False
                            
                consumer_table[item_guid] = need_nir
            
            for item_guid in consumer_table.keys():
                database['inventory'][item_guid]['consumed_nir'] = database['inventory'][item_guid]['consumed_nir'] + consumer_table[item_guid]
            
            craft['status'] = 'complete'
            print_message(f'{craft["id"]} completed')
            break
    else:
        return None

    return database

# Import functions
def import_tasks(database, headers):
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
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False
        
        print_message('Retrieved latest task data from the api.tarkov.dev server')

    nonKappa = 0

    for task in response.json()['data']['tasks']:
        guid = task['id']
        del task['id']
        task['status'] = 'incomplete'
        task['tracked'] = True
        
        if (not task['kappaRequired']):
            task['tracked'] = False
            nonKappa = nonKappa + 1

        database['tasks'][guid] = task

    print_message(f'Successfully loaded task data into the database! {nonKappa} non-Kappa required tasks have been automatically untracked')
    return database

def import_hideout(database, headers):
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
                            station {
                                id
                            }
                            level
                        }
                    }
                }
            }
        """
    }
    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False
        
        print_message('Retrieved latest hideout data from the api.tarkov.dev server')
        hideout = response.json()['data']['hideoutStations']

    for station in hideout:
        for level in station['levels']:
            guid = level['id']
            del level['id']
            level['normalizedName'] = station['normalizedName'] + '-' + str(level['level'])
            level['status'] = 'incomplete'
            level['tracked'] = True

            if (level['normalizedName'] == 'stash-1'):
                level['status'] = 'complete'
                print_message('Completed stash-1 automatically')

            database['hideout'][guid] = level

    print_message(f'Successfully loaded hideout data into the database!')
    return database

def import_barters(database, headers):
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
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
                print_error(f'Errors detected {json.dumps(response.json())}')
                return False

        print_message('Retrieved latest barter data from the api.tarkov.dev server')
        barters = response.json()['data']['barters']

    for barter in barters:
        guid = barter['id']
        del barter['id']
        barter['status'] = 'incomplete'
        barter['tracked'] = False
        database['barters'][guid] = barter

    print_message(f'Successfully loaded barter data into the database!')
    return database

def import_crafts(database, headers):
    data = {
        'query': """
            {
                crafts {
                    id
                    duration
                    station {
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
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print_message('Retrieved latest craft data from the api.tarkov.dev server')
        crafts = response.json()['data']['crafts']

    for craft in crafts:
        guid = craft['id']
        del craft['id']
        craft['status'] = 'incomplete'
        craft['tracked'] = False
        database['crafts'][guid] = craft
    
    print_message(f'Successfully loaded craft data into the database!')
    return database

def import_items(database, headers):
    data = {
        'query': """
            {
                items {
                    id
                    normalizedName
                    shortName
                    sellFor {
                        vendor {
                            normalizedName
                        }
                        price
                        currency
                    }
                    buyFor {
                        vendor {
                            normalizedName
                        }
                        price
                        currency
                    }
                    fleaMarketFee
                }
            }
        """
    }
    response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_warning(f'Errors detected {json.dumps(response.json()["errors"])}')
            return False

        items = response.json()['data']['items']

    usd_to_roubles = 0
    euro_to_roubles = 0

    for item in items:
        if (item['id'] == '5696686a4bdc2da3298b456a'):
            for vendor in item['buyFor']:
                if (vendor['vendor']['normalizedName'] == 'peacekeeper'):
                    usd_to_roubles = int(vendor['price'])

        if (item['id'] == '569668774bdc2da2298b4568'):
            for vendor in item['buyFor']:
                if (vendor['vendor']['normalizedName'] == 'skier'):
                    euro_to_roubles = int(vendor['price'])

    for item in items:
        guid = item['id']
        del item['id']
        sell_price = 0
        sell_price_roubles = 0
        sell_trader = ''
        sell_currency = ''
        sell_to = ''
        buy_price = 0
        buy_price_roubles = sys.maxsize
        buy_trader = ''
        buy_currency = ''
        buy_from = ''
        
        for vendor in item['sellFor']:
            this_price = int(vendor['price'])
            this_price_roubles = 0
            this_currency = vendor['currency']

            if (this_currency.lower() == 'usd'):
                this_price_roubles = this_price * usd_to_roubles
            elif (this_currency.lower() == 'euro'):
                this_price_roubles = this_price * euro_to_roubles
            else:
                this_price_roubles = this_price

            if (vendor['vendor']['normalizedName'] == 'flea-market'):
                if (item['fleaMarketFee'] is None):
                    print_warning(f'Found an invalid flea market value (Will be corrected): {item['normalizedName']}')
                    item['fleaMarketFee'] = 100000000
                
                this_price_roubles = this_price_roubles - item['fleaMarketFee']
                item['sell_flea'] = this_price
                item['sell_flea_currency'] = this_currency

                if (this_price_roubles > sell_price_roubles):
                    sell_to = 'flea'

            elif (this_price_roubles > sell_price_roubles):
                sell_price = this_price
                sell_price_roubles = this_price_roubles
                sell_trader = vendor['vendor']['normalizedName']
                sell_currency = this_currency
                sell_to = sell_trader

        if ('sell_flea' not in item.keys()):
            item['sell_flea'] = 0
            item['sell_flea_currency'] = 'N/A'

        if (sell_price == 0):
            item['sell_trader'] = ''
            item['sell_trade'] = 0
            item['sell_trade_currency'] = 'N/A'
        else:
            item['sell_trader'] = sell_trader
            item['sell_trade'] = sell_price
            item['sell_trade_currency'] = sell_currency

        for vendor in item['buyFor']:
            this_price = int(vendor['price'])
            this_price_roubles = sys.maxsize
            this_currency = vendor['currency']

            if (this_currency.lower() == 'usd'):
                this_price_roubles = this_price * usd_to_roubles
            elif (this_currency.lower() == 'euro'):
                this_price_roubles = this_price * euro_to_roubles
            else:
                this_price_roubles = this_price

            if (vendor['vendor']['normalizedName'] == 'flea-market'):                
                this_price_roubles = this_price_roubles
                item['buy_flea'] = this_price
                item['buy_flea_currency'] = this_currency

                if (this_price_roubles < buy_price_roubles):
                    buy_from = 'flea'

            elif (this_price_roubles < buy_price_roubles):
                buy_price = this_price
                buy_price_roubles = this_price_roubles
                buy_trader = vendor['vendor']['normalizedName']
                buy_currency = this_currency
                buy_from = buy_trader

        if ('buy_flea' not in item.keys()):
            item['buy_flea'] = 0
            item['buy_flea_currency'] = 'N/A'

        if (buy_price == 0):
            item['buy_trader'] = ''
            item['buy_trade'] = 0
            item['buy_trade_currency'] = 'N/A'
        else:
            item['buy_trader'] = buy_trader
            item['buy_trade'] = buy_price
            item['buy_trade_currency'] = buy_currency

        del item['sellFor']
        del item['buyFor']
        del item['fleaMarketFee']
        item['sell_to'] = sell_to
        item['buy_from'] = buy_from
        database['items'][guid] = item

    database['refresh'] = datetime.now().isoformat()
    print_message(f'Successfully loaded item data into the database!')
    return database

def import_maps(database, headers):
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
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print_message('Retrieved latest map data from the api.tarkov.dev server')
        maps = response.json()['data']['maps']

    for map in maps:
        guid = map['id']
        del map['id']

        if (map['normalizedName'] == 'streets-of-tarkov'):
            map['normalizedName'] = 'streets'
        elif (map['normalizedName'] == 'the-lab'):
            map['normalizedName'] = 'labs'

        database['maps'][guid] = map

    print_message(f'Successfully loaded map data into the database!')
    return database

def import_traders(database, headers):
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
        print_error(f'Network error [{response.status_code}] {response.json()}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print_message('Retrieved latest trader data from the api.tarkov.dev server')
        traders = response.json()['data']['traders']

    for trader in traders:
        guid = trader['id']
        del trader['id']

        if (trader['normalizedName'] == 'btr-driver'):
            trader['normalizedName'] = 'btr'

        database['traders'][guid] = trader

    print_message(f'Successfully loaded trader data into the database!')
    return database

# Display
def display_inventory(items, output_type = INV):
    items = alphabetize_items(items)

    if (output_type == INV):
        display = INVENTORY_HEADER + BUFFER
    elif (output_type == HAVE):
        display = INVENTORY_HAVE_HEADER + BUFFER
    else:
        display = INVENTORY_NEED_HEADER + BUFFER
    
    _row_ = 1
    
    for guid, item in items.items():
        nir, fir = None, None
        _completed_ = 0
        _overstock_ = False
        prefix = ''

        if (output_type == HAVE or item['need_nir'] > 0):
            if (output_type == NEED):
                nir = item['need_nir']
            elif (output_type == 'have'):
                nir = item['have_nir']
            else:
                if (item['have_nir'] >= item['need_nir']):
                    _completed_ = 1

                    if (item['have_nir'] > item['need_nir']):
                        _overstock_ = True

                nir = f'{item["have_nir"]}/{item["need_nir"]}'
        
        if (output_type == HAVE or item['need_fir'] > 0):
            if (output_type == NEED):
                fir = item['need_fir']
            elif (output_type == HAVE):
                fir = item['have_fir']
            else:
                if (item['have_fir'] >= item['need_fir']):
                    _completed_ = _completed_ + 2
                    
                    if (item['have_fir'] > item['need_fir']):
                        _overstock_ = True

                fir = f'{item["have_fir"]}/{item["need_fir"]}'

        if ((_completed_ == 1 and item['need_fir'] == 0) or (_completed_ == 2 and item['need_nir'] == 0) or _completed_ == 3):
            if (_overstock_):
                prefix = '[!][*] '
            else:
                prefix = '[*] '
        elif (_overstock_):
            prefix = '[!] '

        if (nir and fir):
            display = display + '{:<20} {:<20} '.format(f'{prefix}{item["shortName"]}', f'{nir} ({fir})')
        elif (nir):
            display = display + '{:<20} {:<20} '.format(f'{prefix}{item["shortName"]}', nir)
        elif (fir):
            display = display + '{:<20} {:<20} '.format(f'{prefix}{item["shortName"]}', f'({fir})')
        else:
            continue
        
        if (_row_ == 4):
            display = display.strip(' ') + '\n'
            _row_ = 0

        _row_ = _row_ + 1
    
    display = display + '\n\n'
    print_message(f'\n{display}')
    return

def display_tasks(database, tasks):
    display = TASK_HEADER + BUFFER
    # There are some duplicate tasks for USEC and BEAR (i.e., Textile Part 1 and 2)
    guids = []
    
    for guid, task in tasks.items():
        if (guid in guids):
            print_debug(f'>> {task["name"]} << has already been seen and will be skipped during printing')
            continue

        guids.append(guid)
        display = display + '{:<40} {:<20} {:<20} {:<20} {:<20} {:<40}\n'.format(task['name'], database['traders'][task['trader']['id']]['normalizedName'], task['status'], display_bool(task['tracked']), display_bool(task['kappaRequired']), guid)

        for objective in task['objectives']:
            objective_string = '-->'

            if (objective['optional']):
                objective_string = objective_string + ' (OPT)'

            objective_string = objective_string + ' ' + objective['description']

            if (objective['type'] == 'giveItem'):
                item_guid = objective['item']['id']

                if (guid in database['items']):
                    have_available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
                    have_available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
                else:
                    have_available_fir = 0
                    have_available_nir = 0

                if ('foundInRaid' in objective and objective['foundInRaid']):
                    objective_string = objective_string + f' ({have_available_fir}/{objective["count"]} FIR available)'
                else:
                    objective_string = objective_string + f' ({have_available_nir}/{objective["count"]} available or {have_available_fir}/{objective["count"]} FIR)'

            elif ('count' in objective):
                objective_string = objective_string + f' ({objective["count"]})'

            if ('skillLevel' in objective):
                objective_string = objective_string + f'({objective["skillLevel"]["level"]})'

            if ('exitStatus' in objective):
                objective_string = objective_string + f' with exit status {objective["exitStatus"]}'

            objective_string = objective_string + '\n'
            display = display + objective_string
        
        if (task['neededKeys'] is not None and len(task['neededKeys']) > 0):
            for _key_ in task['neededKeys']:
                for key in _key_['keys']:
                    key_string = '-->'
                    key_guid = key['id']
                    key_string = key_string + f' Acquire {database['items'][key_guid]['shortName']} key'
                        
                    if (database['items'][key_guid]['have_nir'] - database['items'][key_guid]['consumed_nir'] > 0):
                        key_string = key_string + ' (have)'
                    
                    key_string = key_string + '\n'
                    display = display + key_string
    
        display = display + '\n\n'

    print_message(f'\n{display}')
    return True

def display_hideout(database, stations):
    display = HIDEOUT_HEADER + BUFFER

    for guid, station in stations.items():
        display = display + '{:<40} {:<20} {:<20} {:<40}\n'.format(station['normalizedName'], station['status'], display_bool(station['tracked']), guid)

        for item in station['itemRequirements']:
            item_guid = item['item']['id']
            have_available_nir = database['items'][guid]['have_nir'] - database['items'][guid]['consumed_nir']
            short_name = database['items'][item_guid]['shortName']
            count = item['count']
            display = display + f'--> {have_available_nir}/{count} {short_name} available\n'
        
        display = display + '\n\n'

    print_message(f'\n{display}')
    return True

def display_barters(database, barters):
    display = BARTER_HEADER + BUFFER

    for guid, barter in barters.items():
        display = display + '{:<40} {:<20} {:<20} {:<20}\n'.format(guid, database['traders'][barter['trader']['id']]['normalizedName'], barter['level'], display_bool(barter['tracked']))

        for item in barter['requiredItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            have_available_nir = database['inventory'][item_guid]['have_nir'] - database['inventory'][item_guid]['consumed_nir']
            count = item['count']
            display = display + f'--> Give {have_available_nir}/{count} {item_name} available\n'

        for item in barter['rewardItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']
            display = display + f'--> Receive {count} {item_name}\n'

        if (barter['taskUnlock'] is not None):
            display = display + f'--> Requires task {database['tasks'][barter["taskUnlock"]["id"]]['name']}\n'

        display = display + '\n\n'

    print_message(f'\n{display}')
    return True

def display_crafts(database, crafts):
    display = CRAFT_HEADER + BUFFER

    for guid, craft in crafts.items():
        display = display + '{:<40} {:<20} {:<30} {:<20}\n'.format(guid, find(craft['station']['id'], database, type = GUID, object = STATION)['normalizedName'], craft['level'], print_bool(craft['tracked']))

        for item in craft['requiredItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            have_available_nir = database['inventory'][item_guid]['have_nir'] - database['inventory'][item_guid]['consumed_nir']
            count = item['count']
            display = display + f'--> Give {have_available_nir}/{count} {item_name} available\n'

        for item in craft['rewardItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']
            display = display + f'--> Receive {count} {item_name}\n'

        if (craft['taskUnlock'] is not None):
            display = display + f'--> Requires task {database['tasks'][craft["taskUnlock"]["id"]]['name']}\n'

        display = display + f'--> Takes {str(timedelta(seconds = craft["duration"]))} to complete\n'
        display = display + '\n\n'

    print_message(f'\n{display}')
    return True

def display_untracked(untracked):
    display = UNTRACKED_HEADER + BUFFER

    for guid, entry in untracked.items():
        if (entry['id'] == 'task'):
            display = display + '{:<40} {:<20} {:<20} {:<20}\n'.format(entry['name'], 'task', display_bool(entry['tracked']), display_bool(entry['kappaRequired']))
        else:
            display = display + '{:<40} {:<20} {:<20}\n'.format(entry['normalizedName'], 'hideout station', display_bool(entry['tracked']))
        
    print_message(f'\n{display}')
    return True

def display_items(items):
    display = ITEM_HEADER + BUFFER
    items = alphabetize_items(items)

    for guid, item in items.items():
        item_display = f'{item["have_nir"]}/{item["need_nir"]} ({item["have_fir"]}/{item["need_fir"]})'
        sell_price = f'{format_price(item["sell_trade"], item["sell_trade_currency"])} / {format_price(item["sell_flea"], item["sell_flea_currency"])}'
        buy_price = f'{format_price(item["buy_trade"], item["buy_trade_currency"])} / {format_price(item["buy_flea"], item["buy_flea_currency"])}'
        display = display + '{:<25} {:<60} {:<25} {:<15} {:<12} {:<20} {:<12} {:<20}\n'.format(item['shortName'], item['normalizedName'], guid, item_display, item['sell_to'], sell_price, item['buy_from'], buy_price)

    display = display + '\n\n'
    print_message(f'\n{display}')
    return True

def display_maps(maps):
    display = MAP_HEADER + BUFFER

    for guid, map in maps.items():
        display = display + '{:<30} {:<20}\n'.format(map['normalizedName'], guid)

    display = display + '\n\n'
    print_message(f'\n{display}')
    return True

def display_traders(traders):
    display = TRADER_HEADER + BUFFER

    for guid, trader in traders.items():
        display = display + '{:<30} {:<20}\n'.format(trader['normalizedName'], guid)

    display = display + '\n\n'
    print_message(f'\n{display}')
    return True

def display_search(database, tasks, hideout, barters, crafts, items, traders, maps):
    if (tasks):
        display_tasks(database, tasks)
    
    if (hideout):
        display_hideout(database, hideout)

    if (barters):
        display_barters(database, barters)

    if (crafts):
        display_crafts(database, crafts)

    if (items):
        display_items(items)

    if (traders):
        display_traders(traders)

    if (maps):
        display_maps(maps)

    return True


###################################################
#                                                 #
# WRITABLE                                        #
#                                                 #
###################################################


# Inventory
def inventory(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False

    display_inventory(get_inventory(database))
    return True

def inventory_tasks(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    task_items = get_inventory_tasks(database)

    if (len(task_items) == 0):
        print_message('No items are required for tasks')
    else:
        display_inventory(task_items)

    return True

def inventory_hideout(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    hideout_items = get_inventory_hideout(database)

    if (len(hideout_items) == 0):
        print_message('No items are required for the hideout')
    else:
        display_inventory(hideout_items)

    return True

def inventory_barters(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    barter_items = get_inventory_barters(database)

    if (len(barter_items) == 0):
        print_message('No items are required for barters')
    else:
        display_inventory(barter_items)

    return True

def inventory_crafts(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    craft_items = get_inventory_crafts(database)

    if (len(craft_items) == 0):
        print_message('No items are required for crafts')
    else:
        display_inventory(craft_items)

    return True

def inventory_have(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    have_items = get_inventory_have(database)
    
    if (len(have_items) == 0):
        print_message('You have not collected any items')
    else:
        display_inventory(have_items, output_type = HAVE)

    return True

def inventory_need(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        return False
    
    need_items = get_inventory_need(database)
    
    if (len(need_items) == 0):
        print_message('No items needed. CONGRATULATIONS!')
    else:
        display_inventory(need_items, output_type = NEED)

    return True

# List
def list_tasks(tracker_file, argument):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    if (argument == 'all'):
        tasks = get_tasks(database)
    else:
        tasks = get_tasks_filtered(database, argument)

    if (len(tasks) == 0):
        print_message('No available or tracked tasks found')
        return False
    
    display_tasks(database, tasks)
    return True

def list_stations(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    stations = get_hideout(database)

    if (len(stations) == 0):
        print_message('No available or tracked hideout stations found')
    else:
        display_hideout(database, stations)
    
    return True

def list_barters(tracker_file, argument):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    if (argument == 'all'):
        barters = get_barters(database)
    else:
        barters = get_barters_filtered(database, argument)

    if (len(barters) == 0):
        print_message('No tracked barters found')
        return False
    
    display_barters(database, barters)
    return True

def list_crafts(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    crafts = get_crafts(database)

    if (len(crafts) == 0):
        print_message('No tracked crafts found')
    else:
        display_crafts(database, crafts)
    
    return True

def list_untracked(tracker_file, ignore_kappa):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    untracked = get_untracked(database, ignore_kappa)

    if (len(untracked) == 0 and ignore_kappa):
        print_message('No untracked items (including Kappa tasks) found')
    elif (len(untracked) == 0):
        print_message('No untracked items (excluding Kappa tasks) found')
    else:
        display_untracked(untracked)

    return True

def list_maps(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    maps = ', '.join(map['normalizedName'] for guid, map in database['maps'].items()).strip(', ')
    print_message(f'Accepted map names are: {maps}')

def list_traders(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    traders = ', '.join(trader['normalizedName'] for guid, trader in database['traders'].items()).strip(', ')
    print_message(f'Accepted trader names are: {traders}')

# Search
def search(tracker_file, argument, ignore_barters, ignore_crafts):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False

    tasks = search_tasks(argument, database)
    hideout = search_hideout(argument, database)
    barters = search_barters(argument, database)
    crafts = search_crafts(argument, database)
    items = search_items(argument, database)
    traders = search_traders(argument, database)
    maps = search_maps(argument, database)

    if (not ignore_barters):
        barters = barters | search_barters_by_item(argument, database)

    if (not ignore_crafts):
        crafts = crafts | search_crafts_by_item(argument, database)

    display_search(database, tasks, hideout, barters, crafts, items, traders, maps)
    return True

def required_search(tracker_file, argument, ignore_barters, ignore_crafts):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    tasks = search_tasks_by_item(argument, database)
    hideout = search_hideout_by_item(argument, database)
    barters = False
    crafts = False

    if (not ignore_barters):
        barters = search_barters_by_item(argument, database, required_only = True)

    if (not ignore_crafts):
        crafts = search_crafts_by_item(argument, database, required_only = True)

    display_search(database, tasks, hideout, barters, crafts, False, False, False)
    return True

# Track
def track(tracker_file, argument):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    type = string_to_type(argument)

    if (is_guid(argument)):
        guid = argument
        database, found = track_barter(database, guid)
        
        if (not found):
            database, found = track_craft(database, guid)
        
            if (not found):
                print_error(f'Could not find {argument}')
    else:
        guid = task_to_guid(database, argument)

        if (guid):
            database = track_task(database, guid)
        else:
            guid = station_to_guid(database, argument)

            if (guid):
                database = track_station(database, guid)
            else:
                print_error('Invalid argument')
                return False
    
    write_database(tracker_file, database)
    return True

def untrack(tracker_file, argument):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False

    if (is_guid(argument)):
        guid = argument
        database, found = untrack_barter(database, guid)

        if (not found):
            database = untrack_craft(database, guid)
        
            if (not found):
                print_error(f'Could not find {argument}')
    else:
        guid = task_to_guid(database, argument)

        if (guid):
            database = untrack_task(database, guid)
        else:
            guid = station_to_guid(database, argument)

            if (guid):
                database = untrack_station(database, guid)
            else:
                print_error('Invalid argument')
                return False

    write_database(tracker_file, database)
    return True

# Complete
def complete(tracker_file, argument, force, recurse):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    if (is_guid(argument)):
        guid = argument
        _copy_ = database
        database = complete_barter(database, guid, force)

        if (database is None):
            database = complete_craft(_copy_, guid, force)

            if (database is None):
                print_error(f'Could not find {argument}')
    else:
        guid = task_to_guid(database, argument)

        if (guid and not recurse):
            database = complete_task(database, guid, force)
        elif (guid and recurse):
            tasks = complete_recursive_task(database, guid)
            tasks.insert(0, guid)

            for task in tasks:
                database = complete_task(database, task, True)
        else:
            guid = station_to_guid(database, argument)

            if (guid):
                database = complete_station(database, guid, force)
            else:
                print_error('Invalid argument')
                return False
    
    if (database):
        write_database(tracker_file, database)
        return True

    return False

# Restart
def restart_barter_or_craft(tracker_file, argument):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False

    for barter in database['barters']:
        if (barter['id'] == argument):
            if (not barter['tracked']):
                print_error(f'Barter {argument} is not currently tracked and therefore cannot be restarted')
                return False
            
            if (barter['status'] == 'complete'):
                barter['status'] = 'incomplete'
            else:
                print_error(f'Barter {argument} is not yet completed and therefore cannot be restarted')
                return False
            
            for requirement in barter['requiredItems']:
                guid = requirement['item']['id']
                count = requirement['count']
                database['inventory'][guid]['need_nir'] = database['inventory'][guid]['need_nir'] + count
                print_message(f'{count} more {guid_to_item(database, guid)} (NIR) needed')
            
            return True
        
    for craft in database['crafts']:
        if (craft['id'] == argument):
            if (not craft['tracked']):
                print_error(f'Craft recipe {argument} is not currently tracked and therefore cannot be restarted')
                return False
            
            if (craft['status'] == 'complete'):
                craft['status'] = 'incomplete'
            else:
                print_error(f'Craft recipe {argument} is not yet completed and therefore cannot be restarted')
                return False
            
            for requirement in craft['requiredItems']:
                guid = requirement['item']['id']
                count = requirement['count']
                database['inventory'][guid]['need_nir'] = database['inventory'][guid]['need_nir'] + count
                print_message(f'{count} more {guid_to_item(database, guid)} (NIR) needed')
            
            return True
    
    print_error(f'Could not find a match for {argument}')
    return False

# Add
def write_item_fir(tracker_file, count, argument):
    database = open_database(tracker_file)
    database = add_item_fir(database, count, argument = argument)

    if (not database):
        print_error('No database file found')
        return False

    write_database(tracker_file, database)
    return True

def write_item_nir(tracker_file, count, argument):
    database = open_database(tracker_file)
    database = add_item_nir(database, count, argument = argument)

    if (not database):
        print_error('No database file found')
        return False

    write_database(tracker_file, database)
    return True

# Delete
def unwrite_item_fir(tracker_file, count, argument):
    database = open_database(tracker_file)
    database = del_item_fir(database, count, argument = argument)

    if (not database):
        print_error('No database file found')
        return False

    write_database(tracker_file, database)
    return True

def unwrite_item_nir(tracker_file, count, argument):
    database = open_database(tracker_file)
    database = del_item_nir(database, count, argument = argument)

    if (not database):
        print_error('No database file found')
        return False

    write_database(tracker_file, database)
    return True

# Level
def check_level(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    print_message(f'You are level {database["player_level"]}')
    return True

def set_level(tracker_file, level):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    database['player_level'] = level
    write_database(tracker_file, database)
    print_message(f'Your level is now {level}')
    return True

def level_up(tracker_file):
    database = open_database(tracker_file)

    if (not database):
        print_error('No database file found')
        return False
    
    database['player_level'] = database['player_level'] + 1
    write_database(tracker_file, database)
    print_message(f'Level up! Your level is now {database["player_level"]}')
    return True

#Clear
def clear():
    system('cls' if name == 'nt' else 'clear')
    return True

# Import
def import_data(tracker_file, delta_import):
    database = {
        'tasks': {},
        'hideout': {},
        'barters': {},
        'crafts': {},
        'items': {},
        'maps': {},
        'traders': {},
        'player_level': 1,
        'refresh': -1,
        'version': 'pineapple'
    }
    headers = {
        'Content-Type': 'application/json'
    }
    database = import_tasks(database, headers)

    if (not database):
        print_error('Encountered error while importing tasks. Import aborted')
        return False

    database = import_hideout(database, headers)

    if (not database):
        print_error('Encountered error while importing hideout stations. Import aborted')
        return False

    database = import_barters(database, headers)

    if (not database):
        print_error('Encountered error while importing barters. Import aborted')
        return False

    database = import_crafts(database, headers)

    if (not database):
        print_error('Encountered error while importing crafts. Import aborted')
        return False

    database = import_items(database, headers)

    if (not database):
        print_error('Encountered error while importing items. Import aborted')
        return False

    database = import_maps(database, headers)

    if (not database):
        print_error('Encountered error while importing maps. Import aborted')
        return False

    database = import_traders(database, headers)

    if (not database):
        print_error('Encountered error while importing traders. Import aborted')
        return False
    
    database = stage_inventory(database)
    database = calculate_inventory(database)

    if (delta_import):
        database = delta(tracker_file, database)

    write_database(tracker_file, database)
    print_message(f'Finished importing game data and saved to {tracker_file}')
    return True

def delta(database):
    memory = open_database(tracker_file)
    update = import_data(tracker_file)

    if (not update):
        print_error('Encountered an error while importing the database. Aborted')
        write_database(tracker_file, memory)
        return False

    database = open_database(tracker_file)

    if (not database):
        print_error('Something went wrong opening the database')
        return False

    # Tasks
    task_table = {}

    for index, task in enumerate(database['tasks']):
        task_table[task['id']] = index
    
    for task in memory['tasks']:
        if (task['id'] not in task_table):
            print_warning(f'Task {task["name"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                continue

            print_message('Aborted')
            write_database(tracker_file, memory)
            return False

        new_task = database['tasks'][task_table[task['id']]]

        if (new_task['status'] != task['status']):
            database['tasks'][task_table[task['id']]]['status'] = task['status']
        
        if (new_task['tracked'] != task['tracked']):
            if (task['kappaRequired'] and task['tracked'] and not new_task['kappaRequired']):
                print_warning(f'You are currently tracking {task["name"]} which is no longer Kappa required and will be untracked. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ != 'y'):
                    print_message('Aborted')
                    write_database(tracker_file, memory)
                    return False

                database = untrack_task(database, new_task['id'])
            elif (not task['kappaRequired'] and not task['tracked'] and new_task['kappaRequired']):
                print_warning(f'Task {task["name"]} is now Kappa required and has been tracked. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ != 'y'):
                    print_message('Aborted')
                    write_database(tracker_file, memory)
                    return False
                
            elif (task['kappaRequired'] and not task['tracked']):
                print_warning(f'You had previously untracked a Kappa required task {task["name"]} which will continue to be untracked')
                database = untrack_task(database, new_task['id'])
            elif (not new_task['tracked']):
                print_warning(f'You had previously tracked task {task["name"]} which will remain tracked')
                database = track_task(database, new_task['id'])
            else:
                print_error('Unhandled error with (un)tracked tasks. Aborted')
                write_database(tracker_file, memory)
                return False
                        
    print_message('Completed task delta import')
    
    # Hideout stations
    station_table = {}

    for index, station in enumerate(database['hideout']):
        for sub_index, level in enumerate(station['levels']):
            station_table[level['id']] = (index, sub_index)
    
    for station in memory['hideout']:
        for level in station['levels']:
            if (level['id'] not in station_table):
                print_warning(f'Hideout station {level["normalizedName"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ == 'y'):
                    continue

                print_message('Aborted')
                write_database(tracker_file, memory)
                return False

            new_station = database['hideout'][station_table[level['id']][0]]['levels'][station_table[level['id']][1]]

            if (new_station['status'] != level['status']):
                database['hideout'][station_table[level['id']][0]]['levels'][station_table[level['id']][1]]['status'] = level['status']
            
            if (new_station['tracked'] != level['tracked']):
                if (level['tracked']):
                    database = track_station(database, new_station['id'])
                else:
                    print_warning(f'You had previously untracked hideout station {level["normalizedName"]} which will continue to be untracked')
                    database = untrack_station(database, new_station['id'])

    print_message('Completed hideout station delta import')

    # Barters
    barter_table = {}

    for index, barter in enumerate(database['barters']):
        barter_table[barter['id']] = index
    
    for barter in memory['barters']:
        if (barter['id'] not in barter_table):
            print_warning(f'Barter {barter["id"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                continue

            print_message('Aborted')
            write_database(tracker_file, memory)
            return False

        new_barter = database['barters'][barter_table[barter['id']]]

        if (new_barter['status'] != barter['status']):
            database['barters'][barter_table[barter['id']]]['status'] = barter['status']
        
        if (new_barter['tracked'] != barter['tracked']):
                if (barter['tracked']):
                    print_warning(f'You had previously tracked barter {barter["id"]} which will continue to be tracked')
                    database = track_barter(database, new_barter['id'])[0]
                else:
                    database = untrack_barter(database, new_barter['id'])[0]
    
    print_message('Completed barter delta import')

    # Crafts
    craft_table = {}

    for index, craft in enumerate(database['crafts']):
        craft_table[craft['id']] = index
    
    if ('crafts' in memory.keys()):
        for craft in memory['crafts']:
            if (craft['id'] not in craft_table):
                print_warning(f'Craft {craft["id"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ == 'y'):
                    continue

                print_message('Aborted')
                write_database(tracker_file, memory)
                return False

            new_craft = database['crafts'][craft_table[craft['id']]]

            if (new_craft['tracked'] != craft['tracked']):
                if (craft['tracked']):
                    print_warning(f'You had previously tracked craft recipe {craft["id"]} which will continue to be tracked')
                    database = track_craft(database, new_craft['id'])[0]
                else:
                    database = untrack_craft(database, new_craft['id'])[0]
    
    print_message('Completed craft recipes delta import')

    # Inventory
    for item in database['inventory'].keys():
        if (item not in memory['inventory'].keys()):
            print_warning(f'Inventory item {guid_to_item(database, item)} cannot be found in the new inventory. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()
            
            if (_confirmation_ == 'y'):
                continue

            print_message('Aborted')
            write_database(tracker_file, memory)
            return False
        
        if (database['inventory'][item]['have_nir'] != memory['inventory'][item]['have_nir']):
            database['inventory'][item]['have_nir'] = memory['inventory'][item]['have_nir']

        if (database['inventory'][item]['have_fir'] != memory['inventory'][item]['have_fir']):
            database['inventory'][item]['have_fir'] = memory['inventory'][item]['have_fir']

        if (database['inventory'][item]['consumed_nir'] != memory['inventory'][item]['consumed_nir']):
            database['inventory'][item]['consumed_nir'] = memory['inventory'][item]['consumed_nir']
        
        if (database['inventory'][item]['consumed_fir'] != memory['inventory'][item]['consumed_fir']):
            database['inventory'][item]['consumed_fir'] = memory['inventory'][item]['consumed_fir']
    
    print_message('Completed inventory delta import')
    database['player_level'] = memory['player_level']
    database['last_price_refresh'] = memory['last_price_refresh']
    print_message('Restored player level and price refresh data')
    write_database(tracker_file, database)
    print_message('Completed database delta import')
    return True

# Backup
def backup(tracker_file):
    if (tracker_file == 'debug.json'):
        file = 'debug'
    else:
        file = 'database'

    saves = get_saves(file)
    
    if ((saves[0] != '' and saves[1] != '' and len(saves) == 7)
        or ((saves[0] == '' and saves[1] != '') or (saves[0] != '' and saves[1] == '') and len(saves) == 6)
        or (saves[0] == '' and saves[1] == '' and len(saves) == 5)):
        print_message(f'You are only allowed 5 save files. Please choose a file to overwrite!')
        _display_ = '\n'

        for index, save in enumerate(saves):
            if (index < 2):
                if (save == f'{file}.curr.bak'):
                    _save_ = 'Current autosave (1 exit ago)'
                else:
                    _save_ = 'Previous autosave (2 exits ago)'

                _display_ = _display_ + f'[{index + 1}] {_save_} (Autosave - Cannot overwrite)\n'
            else:
                _save_ = save.split('.')
                _save_[1] = datetime.strptime(_save_[1], '%Y-%m-%d').strftime('%B, %A %d, %Y')
                _save_[2] = datetime.strptime(_save_[2], '%H-%M-%S').strftime('%H:%M:%S')
                _save_ = f'{_save_[1]} at {_save_[2]}'
                _display_ = _display_ + f'[{index + 1}] {_save_}\n'

        print_message(_display_)
        overwrite = input('> ')

        if (not overwrite.isdigit() or int(overwrite) < 2 or int(overwrite) > len(saves)):
            print_error('Invalid overwrite argument')
            return False
        
        overwrite = saves[int(overwrite) - 1]
        print_message(f'Overwriting save file {overwrite}')
        remove(overwrite)

    database = open_database(tracker_file)
    filename = f'{file}.{datetime.now().strftime('%Y-%m-%d.%H-%M-%S')}.bak'
    write_database(filename, database)
    print_message(f'Created new save file {filename}')
    return True

# Restore
def restore(tracker_file):
    if (tracker_file == 'debug.json'):
        file = 'debug'
    else:
        file = 'database'

    saves = get_saves(file)
    print_message('Please choose a save file to restore from')
    _display_ = '\n'

    for index, save in enumerate(saves):
        if (index < 2):
            if (save == f'{file}.curr.bak'):
                _save_ = 'Current autosave (1 exit ago)'
            else:
                _save_ = 'Previous autosave (2 exits ago)'

            _display_ = _display_ + f'[{index + 1}] {_save_} (Autosave)\n'
        else:
            _save_ = save.split('.')
            _save_[1] = datetime.strptime(_save_[1], '%Y-%m-%d').strftime('%B, %A %d, %Y')
            _save_[2] = datetime.strptime(_save_[2], '%H-%M-%S').strftime('%H:%M:%S')
            _save_ = f'{_save_[1]} at {_save_[2]}'
            _display_ = _display_ + f'[{index + 1}] {_save_}\n'

    print_message(_display_)
    restore = input('> ')

    if (not restore.isdigit() or int(restore) > len(saves)):
        print_error('Invalid restore argument')
        return False
    
    restore = saves[int(restore) - 1]
    print_message(f'Restoring from save file {restore}')
    restore_database = open_database(restore)
    write_database(tracker_file, restore_database)
    return True


###################################################
#                                                 #
# APP LOOP                                        #
#                                                 #
###################################################


def main(args):
    if (len(args) > 1 and args[1] == 'debug'):
        global DEBUG
        DEBUG = True

        print_message('Welcome to the TARkov Tracker (TART)!')
        print_debug('RUNNING IN DEBUG MODE. All changes will affect only the debug database file!')
        tracker_file = 'debug.json'
    else:
        print_message('Welcome to the TARkov Tracker (TART)! Type help for usage')
        tracker_file = 'database.json'

    database = open_database(tracker_file)

    if ('version' not in database.keys() or database['version'] != 'pineapple'):
        print_warning('You must migrate your database to the newest version before continuing! Type migrate')

    while(True):
        command = input('> ')
        running = parser(tracker_file, command)
        
        if (not running):
            print_message('Goodbye.')
            return True

if (__name__ == '__main__'):
    main(sys.argv)