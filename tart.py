from datetime import datetime, timedelta
from os import system, name, rename, remove, listdir, path, mkdir, getcwd, environ
from shutil import get_terminal_size
import threading
import subprocess
import time
import json
import sys
import re

try:
    import requests
    from rich.text import Text
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Console
except ModuleNotFoundError:
    with open('requirements.txt') as requirements:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        import requests
        from rich.table import Table
        from rich.console import Console


VERSION = 'asparagus'

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
\t\t\tkappa : Only kappa required tasks
\tstations : Lists all hideout stations
\thideout : Lists all hideout stations
\tbarters : Lists all tracked barters
\t\tfilters
\t\t\ttrader : The name of a trarder to list barters for
\tcrafts : Lists all tracked crafts
\tuntracked : Lists all untracked tasks and hideout stations
\t\tfilters
\t\t\tnokappa : Includes non-Kappa required tasks, otherwise ignored
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
\t\tlevel : The integer value greater than 0 to set the player level at
'''
NOTE_HELP = '''
> note {delete} [name] {element}\n
Accesses customizable notes\n
delete : USing the keyword delete before the name will delete the note
name : The  name of the note to show or add an element to
element : The text element to add to the specified note
'''
CLEAR_HELP = '''
> clear\n
Clears the terminal
'''
IMPORT_HELP = '''
> import {type}\n
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
ITEM_TABLE = ['Item Short Name', 'Item Normalized Name', 'Item GUID', 'A/T/N (FIR)', 'Best Trader Sell', 'Best Trader Buy', 'Flea', 'Task Req.']
MAP_TABLE = ['Map Normalized Name', 'Map GUID']
TRADER_TABLE = ['Trader Normalized Name', 'Trader GUID']
INVENTORY_TABLE = ['Item', 'A/T/N (FIR)']
INVENTORY_HAVE_TABLE = ['Item', 'Have (FIR)']
INVENTORY_NEED_TABLE = ['Item', 'Need (FIR)']
TASK_TABLE = ['Task Name', 'Task Giver', 'Task Status', 'Tracked', 'Kappa Required', 'Map', 'Priority', 'Task GUID']
HIDEOUT_TABLE = ['Station Name', 'Station Status', 'Tracked', 'Station GUID']
BARTER_TABLE = ['Barter GUID', 'Trader', 'Loyalty Level', 'Barter Status', 'Tracked', 'Restarts']
CRAFTS_TABLE = ['Craft GUID', 'Station', 'Craft Status', 'Tracked', 'Restarts']
UNTRACKED_TABLE = ['Entity Name', 'Type', 'Tracked', 'Kappa Required']


###################################################
#                                                 #
# UTILITY                                         #
#                                                 #
###################################################


# Command parsing
def parser(tracker_file, directory, command):
    command = command.lower().split(' ')
    print_debug(f'Received command >> {command} <<')

    # Inventory
    if (command[0] == 'inv'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            inventory(tracker_file, directory)
        elif (command[1] == 'tasks'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_tasks(tracker_file, directory)
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_hideout(tracker_file, directory)
        elif (command[1] == 'barters'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_barters(tracker_file, directory)
        elif (command[1] == 'crafts'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_crafts(tracker_file, directory)
        elif (command[1] == 'have'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_have(tracker_file, directory)
        elif (command[1] == 'need'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            inventory_need(tracker_file, directory)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(INV_HELP)
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
                list_tasks(tracker_file, directory, command[2])
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} all <<')
                list_tasks(tracker_file, directory, 'all')
        elif (command[1] == 'stations' or command[1] == 'hideout'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_stations(tracker_file, directory)
        elif (command[1] == 'barters'):
            if (len(command) == 3):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                list_barters(tracker_file, directory, command[2])
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} all <<')
                list_barters(tracker_file, directory, 'all')
        elif (command[1] == 'crafts'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_crafts(tracker_file, directory)
        elif (command[1] == 'untracked'):
            if (len(command) == 3):
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                
                if (command[2] == 'nokappa'):
                    list_untracked(tracker_file, directory, True)
                else:
                    print_debug(f'Failed >> {command[0]} {command[1]} <<')
                    print_error('Command not recognized')
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                list_untracked(tracker_file, directory, False)
        elif (command[1] == 'maps'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_maps(tracker_file, directory)
        elif (command[1] == 'traders'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            list_traders(tracker_file, directory)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(LS_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')    
    # Requires
    elif (command[0] == 'requires' or command[0] == 'r'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print(REQUIRES_HELP)
            elif (command[-1] == 'barters'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = True
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'crafts'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = True
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
            elif (command[-1] == 'all'):
                print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
                ignore_barters = False
                ignore_crafts = False
                pattern = ' '.join(command[1:-1])
                required_search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
            else:
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                ignore_barters = True
                ignore_crafts = True
                pattern = ' '.join(command[1:])
                required_search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
    # Track
    elif (command[0] == 'track'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(TRACK_HELP)
        else:
            print_debug(f'Executing >> {command[0]} {command[1:]} <<')
            track(tracker_file, directory, ' '.join(command[1:]))
    elif (command[0] == 'untrack'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(UNTRACK_HELP)
        else:
            print_debug(f'Executing >> {command[0]} {command[1:]} <<')
            untrack(tracker_file, directory, ' '.join(command[1:]))
    # Complete
    elif (command[0] == 'complete'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1:]} <<')
                print(COMPLETE_HELP)
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

            complete(tracker_file, directory, argument, force, recurse)
    # Restart
    elif (command[0] == 'restart'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(RESTART_HELP)
        elif (command[1]):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            restart(tracker_file, directory, command[1])
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
                print(ADD_HELP)
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
                write_item_fir(tracker_file, directory, count, argument = argument)
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:])
                write_item_nir(tracker_file, directory, count, argument = argument)
    # Delete
    elif (command[0] == 'del'):
        if (len(command) < 2):
            print_debug(f'Failed >> {command[0]} <<')
            print_error('Command not recognized')
        else:
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print(DELETE_HELP)
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
                unwrite_item_fir(tracker_file, directory, count, argument = argument)
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} {command[2:]} <<')
                count = int(command[1])
                argument = ' '.join(command[2:])
                unwrite_item_nir(tracker_file, directory, count, argument = argument)
    # Level
    elif (command[0] == 'level'):
        if (len(command) > 1):
            if (command[1] == 'up'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                level_up(tracker_file, directory)
            elif (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print(LEVEL_HELP)
            elif (command[1] == 'set'):
                if (len(command) == 3):
                    if (command[2].isdigit() and int(command[2]) > 0):
                        print_debug(f'Executing >> {command[0]} {command[1]} {command[2]} <<')
                        set_level(tracker_file, directory, int(command[2]))
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
            check_level(tracker_file, directory)
    # Notes
    elif (command[0] == 'note'):
        if (len(command) > 1):
            if (command[1] == 'help' or command[1] == 'h'):
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                print(NOTE_HELP)
            else:
                print_debug(f'Executing >> {command[0]} {command[1]} <<')
                note(tracker_file, directory, command[1:])
        else:
            print_debug(f'Executing >> {command[0]}<<')
            note(tracker_file, directory, [command[0]])
    # Clear
    elif (command[0] == 'clear'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            clear()
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(CLEAR_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Import
    elif (command[0] == 'import'):
        if (len(command) < 2):
            print_warning('Import and overwite all data? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                import_data(tracker_file, directory)
            else:
                print_debug(f'Abort >> {command[0]} << because >> {_confirmation_} <<')
                print('Aborted')
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(IMPORT_HELP)
        elif (command[1] == 'prices'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            database = open_database(tracker_file, directory)
            database = import_items(database, {
                'Content-Type': 'application/json'
            })
            print('Price data refreshed')
            write_database(tracker_file, directory, database)
        elif (command[1] == 'delta'):
            print_warning('Import new data without overwriting? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                delta(tracker_file, directory)
            else:
                print_debug(f'Abort >> {command[0]} << because >> {_confirmation_} <<')
                print('Aborted')
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Backup
    elif (command[0] == 'backup'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            backup(tracker_file, directory)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(BACKUP_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Restore
    elif (command[0] == 'restore'):
        if (len(command) == 1):
            print_debug(f'Executing >> {command[0]} <<')
            restore(tracker_file, directory)
        elif (command[1] == 'help' or command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(RESTORE_HELP)
        else:
            print_debug(f'Failed >> {command[0]} {command[1]} <<')
            print_error('Command not recognized')
    # Help
    elif (command[0] == 'help' or command[0] == 'h'):
        print_debug(f'Executing >> {command[0]} <<')
        print(USAGE)
    # Exit
    elif (command[0] == 'stop' or command[0] == 's' or command[0] == 'quit' or command[0] == 'q' or command[0] == 'exit'):
        print_debug(f'Executing >> {command[0]} <<')
        database = open_database(tracker_file, directory)

        if (not database):
            return False

        if (f'{tracker_file}.prev.bak' in listdir(directory)):
            remove(f'{directory}\\{tracker_file}.prev.bak')
        
        if (f'{tracker_file}.curr.bak' in listdir(directory)):
            rename(f'{directory}\\{tracker_file}.curr.bak', f'{directory}\\{tracker_file}.prev.bak')

        write_database(f'{tracker_file}.curr.bak', directory, database)
        print(f'Backup saved')
        return False
    # Search
    else:
        if (len(command) > 1 and command[0] == 'search' and command[1] == 'h'):
            print_debug(f'Executing >> {command[0]} {command[1]} <<')
            print(SEARCH_HELP)
        elif (command[-1] == 'barters'):
            print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
            ignore_barters = False
            ignore_crafts = True
            pattern = ' '.join(command[0:-1])
            search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
        elif (command[-1] == 'crafts'):
            print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
            ignore_barters = True
            ignore_crafts = False
            pattern = ' '.join(command[0:-1])
            search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
        elif (command[-1] == 'all'):
            print_debug(f'Executing >> {command[0]} {command[1:-1]} {command[-1]} <<')
            ignore_barters = False
            ignore_crafts = False
            pattern = ' '.join(command[0:-1])
            search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
        else:
            print_debug(f'Executing >> {command[0]} {command[1:]} <<')
            ignore_barters = True
            ignore_crafts = True
            pattern = ' '.join(command[0:])
            search(tracker_file, directory, pattern, ignore_barters, ignore_crafts)
    
    return True

# Database editing
def open_database(file_path, directory):
    try:
        with open(f'{directory}\\{file_path}', 'r', encoding = 'utf-8') as open_file:
            print_debug(f'Opened file >> {file_path} <<')
            file = json.load(open_file)

            if (file['version'] != VERSION):
                print_warning('Incorrect database version detected. Please update with a delta import')
                return file
    except FileNotFoundError:
        print_error('Database not found')
        return False
    
    return file

def write_database(file_path, directory, data):
    with open(f'{directory}\\{file_path}', 'w', encoding = 'utf-8') as open_file:
        open_file.write(json.dumps(data))
        print_debug(f'Wrote file >> {file_path} <<')
    return

# Find unique functions (return GUID)
def disambiguate(matches):
    options = []
    index = 0

    for guid, match in matches.items():
        options.append(guid)
        print(f'[{index + 1}] {match['normalizedName']} ({guid})')
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
        if (string_compare(text, task['normalizedName']) or string_compare(text, task['name']) or guid == text):
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

    if (string_compare(text, 'kappa')):
        return 'kappa'

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

def find_completable(text, database):
    guid = find_task(text, database)

    if (guid):
        return guid
    
    guid = find_station(text, database)

    if (guid):
        return guid
    
    guid = find_barter(text, database)

    if (guid):
        return guid
    
    guid = find_craft(text, database)

    if (guid):
        return guid
    
    return False

def find_restartable(text, database):
    guid = find_barter(text, database)

    if (guid):
        return guid
    
    guid = find_craft(text, database)

    if (guid):
        return guid
    
    return False

def task_to_map(task):
    maps = []

    for objective in task['objectives']:
        for map in objective['maps']:
            if (map['id'] not in maps):
                maps.append(map['id'])

    if (len(maps) == 0):
        return 'any'

    return maps

# String functions
def normalize(text):
    unwanted_strings = ['', '.', '(', ')', '+', '=', '\'', '"', ',', '\\', '/', '?', '#', '$', '&', '!', '@', '[', ']', '{', '}', '-', '_']
    normalized = text.lower()
    normalized = re.sub('-', ' ', normalized)

    for string in unwanted_strings:
        normalized = normalized.replace(string, '')
    
    normalized = re.sub(' +', ' ', normalized)
    return normalized

def string_compare(comparable, comparator: str):
    comparable_words = normalize(comparable).split(' ')
    comparator_words = normalize(comparator).split(' ')

    for comparable_word in comparable_words:
        if (comparable_word not in comparator_words and not comparator.lower().replace('-', '').startswith(comparable.lower().replace('-', '')) and not comparator.lower().replace('-', ' ').startswith(comparable.lower().replace('-', ' '))):
            return False

    print_debug(f'>> {comparable_words} << == >> {comparator_words} <<')
    return True

def alphabetize_items(items):
    print_debug(f'Alphabetizing dict of size >> {len(items)} <<')
    return {guid: item for guid, item in sorted(items.items(), key = lambda item: item[1]['shortName'].lower())}

def alphabetize_tasks(tasks):
    print_debug(f'Alphabetizing dict of size >> {len(tasks)} <<')
    ordered = ['any', 'multi']
    return {guid: task for guid, task in sorted(tasks.items(), key = lambda item: (ordered.index(item[1]['map'].lower()) if item[1]['map'].lower() in ordered else len(ordered), item[1]['map'].lower()))}

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

        if (database['tasks'][id]['status'] != 'complete'):
            return f'{database['tasks'][id]['name']} must be completed first'
    
    print_debug(f'Verified task >> {task["name"]} <<')
    return True

def verify_station(database, station):
    if (station['status'] == 'complete'):
        return f'Hideout station {station["normalizedName"]} is complete'
    
    if (not station['tracked']):
        return f'Hideout station {station["normalizedName"]} is not tracked'

    for prereq in station['stationLevelRequirements']:
        prereq_guid = prereq['station']['id'] + '-' + str(prereq['level'])

        if (database['hideout'][prereq_guid]['status'] != 'complete'):
            return f'{database['hideout'][prereq_guid]['normalizedName']} must be completed first'
        
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

# Task prioritization
# Only run during database creation)
def recurse_priority(all_tasks, guid, visited = None):
    if (visited is None):
        visited = set()

    follow_on_tasks = 0

    for task in all_tasks:
        if (task['id'] in visited):
            continue

        for prereq in task['taskRequirements']:
            if ('id' in prereq):
                if (prereq['id'] == guid):
                    visited.add(task['id'])
                    follow_on_tasks += 1
                    follow_on_tasks += recurse_priority(all_tasks, task['id'], visited)
            elif (prereq['task']['id'] == guid):
                visited.add(task['id'])
                follow_on_tasks += 1
                follow_on_tasks += recurse_priority(all_tasks, task['id'], visited)

    return follow_on_tasks

# Add Items
def add_item_fir(database, count, guid):
    item_name = database['items'][guid]['normalizedName']

    if (database['items'][guid]['need_nir'] == 0 and database['items'][guid]['need_fir'] == 0):
        print(f'{item_name} is not needed')
        return False

    if (database['items'][guid]['need_fir'] == 0):
        print(f'{item_name} (FIR) is not needed')
        database = add_item_nir(database, count, guid)
    elif (database['items'][guid]['have_fir'] == database['items'][guid]['need_fir']):
        print(f'{item_name} (FIR) already found')
        database = add_item_nir(database, count, guid)
    elif (database['items'][guid]['have_fir'] + count > database['items'][guid]['need_fir']):
        _remainder_ = database['items'][guid]['have_fir'] + count - database['items'][guid]['need_fir']
        print(f'Added {count - _remainder_} {item_name} (FIR) (COMPLETED)')
        database = add_item_nir(database, _remainder_, guid)
        database['items'][guid]['have_fir'] = database['items'][guid]['need_fir']
    elif (database['items'][guid]['have_fir'] + count == database['items'][guid]['need_fir']):
        database['items'][guid]['have_fir'] = database['items'][guid]['need_fir']
        print(f'Added {count} {item_name} (FIR) (COMPLETED)')
    else:
        database['items'][guid]['have_fir'] = database['items'][guid]['have_fir'] + count
        print(f'Added {count} {item_name} (FIR)')

    if (not database):
        print_error('Something went wrong. Aborted')
        return False

    return database

def add_item_nir(database, count, guid):
    item_name = database['items'][guid]['normalizedName']

    if (database['items'][guid]['need_nir'] == 0 and database['items'][guid]['need_fir'] == 0):
        print(f'{item_name} is not needed')
        return False

    if (database['items'][guid]['need_nir'] == 0):
        print(f'{item_name} (NIR) is not needed')
    elif (database['items'][guid]['have_nir'] == database['items'][guid]['need_nir']):
        print(f'{item_name} (NIR) already found')
    elif (database['items'][guid]['have_nir'] + count > database['items'][guid]['need_nir']):
        _remainder_ = database['items'][guid]['have_nir'] + count - database['items'][guid]['need_nir']
        database['items'][guid]['have_nir'] = database['items'][guid]['need_nir']
        print(f'Added {count - _remainder_} {item_name} (NIR) (COMPLETED). Skipped {_remainder_} items')
    elif (database['items'][guid]['have_nir'] + count == database['items'][guid]['need_nir']):
        database['items'][guid]['have_nir'] = database['items'][guid]['need_nir']
        print(f'Added {count} {item_name} (NIR) (COMPLETED)')
    else:
        database['items'][guid]['have_nir'] = database['items'][guid]['have_nir'] + count
        print(f'Added {count} {item_name} (NIR)')

    hideout_readiness(database, guid)

    if (not database):
        print_error('Something went wrong. Aborted')
        return False

    return database

# Delete Items
def del_item_fir(database, count, guid):
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
    print(f'Removed {count} {item_name} (FIR) ({remaining} remaining FIR)')
    return database

def del_item_nir(database, count, guid):
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
    print(f'Removed {count} {item_name} (NIR) ({remaining} remaining NIR)')
    return database

# Hideout Readiness
def hideout_readiness(database, guid = False):
    for station_guid, station in database['hideout'].items():
        ready = False
        
        if (type(verify_station(database, station)) is not str):
            for requirement in station['itemRequirements']:
                this_guid = requirement['item']['id']
                foundInRaid = False

                for attribute in requirement['attributes']:
                    if (attribute['type'] == 'foundInRaid' and attribute['value'] == 'true'):
                        foundInRaid = True

                if (foundInRaid):
                    if (database['items'][this_guid]['have_fir'] - database['items'][this_guid]['consumed_fir'] < requirement['count']):
                        ready = False
                        break
                    elif (guid and requirement['item']['id'] == guid):
                        ready = True
                else:
                    if (database['items'][this_guid]['have_nir'] - database['items'][this_guid]['consumed_nir'] < requirement['count']):
                        ready = False
                        break
                    elif (guid and requirement['item']['id'] == guid):
                        ready = True
            else:
                if (ready or not guid):
                    print(f'{station['normalizedName']} is ready to complete')
    
    return True

# Console output
def progress_bar(stop, width = 20):
    try:
        pos = 0

        while (not stop.is_set()):
            bar = '[' + '.' * pos + ']'
            sys.stdout.write('\r' + ' ' * (width + 2) + '\r' + bar)
            sys.stdout.flush()
            pos = (pos + 1) % (width + 1)
            time.sleep(0.2)
    finally:
        sys.stdout.write('\r' + ' ' * (width + 2) + '\r')
        sys.stdout.flush()

    return True

def display_bool(bool_value):
    if (bool_value):
        return 'true'
    else:
        return 'false'
    
def print_debug(message):
    if (DEBUG):
        print(f'>> (DEBUG) {message}')
        return True
    
    return False

def print_warning(message):
    print(f'>> (WARNING) {message}')
    return True

def print_error(message):
    print(f'>> (ERROR) {message}!')
    return True

def table_wrapper(rows, headers = None, padding = 3, max_chunks = 0):
    table = Table(expand = False, show_edge = False, show_lines = False)
    rows = [list(map(str, row)) for row in rows]

    if (not rows):
        return False

    columns = max(len(row) for row in rows)
    max_column_widths = [0] * columns
    
    for row in rows:
        for index, column in enumerate(row):
            max_column_widths[index] = max(max_column_widths[index], len(column))

    if (headers):
        for index, header in enumerate(headers):
            max_column_widths[index] = max(max_column_widths[index], len(header))

    width = sum(max_column_widths) + padding * (columns - 1)
    resolution = get_terminal_size().columns

    if (len(rows) == 1 or width + padding > resolution):
        max_chunks = 1
    elif (max_chunks > 0):
        max_chunks = max_chunks
    else:
        max_chunks = max(1, resolution // (width + padding))

    padding_needed = (-len(rows)) % max_chunks
    rows.extend([[''] * columns] * padding_needed)

    chunked = [
        rows[index : index + max_chunks]
        for index in range(0, len(rows), max_chunks)
    ]

    wrapped_headers = []

    if (headers):
        for _ in range(max_chunks):
            wrapped_headers.extend(headers)
    
    values = []

    for chunk in chunked:
        nrow = []

        for row in chunk:
            nrow.extend(row)

        values.append(nrow)

    for header in wrapped_headers:
        table.add_column(header, no_wrap = False)

    for value in values:
        table.add_row(*value)

    Console().print(table)
    return True


###################################################
#                                                 #
# WORKER                                          #
#                                                 #
###################################################


# Inventory functions
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
                    database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + objective['count']
        
        if (task['neededKeys'] is not None and len(task['neededKeys']) > 0):
            for _key_ in task['neededKeys']:
                for key in _key_['keys']:
                    item_guid = key['id']
                    database['items'][item_guid]['need_nir'] = 1
    
    print('Added all items required for tracked tasks to the database')

    for guid, station in database['hideout'].items():
        if (not station['tracked']):
            continue

        for requirement in station['itemRequirements']:
            item_guid = requirement['item']['id']
            foundInRaid = False

            for attribute in requirement['attributes']:
                if (attribute['type'] == 'foundInRaid' and attribute['value'] == 'true'):
                    foundInRaid = True

            if (foundInRaid):
                database['items'][item_guid]['need_fir'] = database['items'][item_guid]['need_fir'] + requirement['count']
            else:
                database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + requirement['count']

    print('Added all items required for tracked hideout stations to the database')

    for guid, barter in database['barters'].items():
        if (not barter['tracked']):
            continue

        for requirement in barter['requiredItems']:
            item_guid = requirement['item']['id']
            database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + requirement['count']

    print('Added all items required for tracked barters to the database')

    for guid, craft in database['crafts'].items():
        if (not craft['tracked']):
            continue

        for requirement in craft['requiredItems']:
            item_guid = requirement['item']['id']
            database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + requirement['count']

    print('Added all items required for tracked crafts to the database')
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
            foundInRaid = False

            if (item_guid not in items.keys()):
                items[item_guid] = database['items'][item_guid]
                items[item_guid]['need_fir'] = 0
                items[item_guid]['need_nir'] = 0

            for attribute in requirement['attributes']:
                if (attribute['type'] == 'foundInRaid' and attribute['value'] == 'true'):
                    foundInRaid = True

            if (foundInRaid):
                items[item_guid]['need_fir'] = items[item_guid]['need_fir'] + requirement['count']
            else:
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

        if (filter == 'kappa' and task['kappaRequired']):
            tasks[guid] = task
        elif (filter in database['maps'].keys() and (filter in task['maps'] or '0' in task['maps'])):
            tasks[guid] = task
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
        if (verify_barter(database, guid) == True):
            print_debug(f'Found available barter >> {guid} <<')
            barters[guid] = barter

    return barters

def get_barters_filtered(database, argument):
    print_debug(f'Compiling barters for trader >> {argument} <<')
    barters = {}
    filter = find_trader(argument, database)

    for guid, barter in database['barters'].items():
        if (verify_barter(database, guid) != True):
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
        if (verify_craft(database, guid) == True):
            print_debug(f'Found available craft >> {guid} <<')
            crafts[guid] = craft

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

def get_saves(tracker_file, directory):
    files = listdir(directory)
    saves = []
    print_debug(f'Compiling save files for >> {tracker_file} <<')

    if (f'{tracker_file}.curr.bak' in files):
        print_debug(f'Found current autosave >> {tracker_file}.curr.bak <<')
        saves.append(f'{tracker_file}.curr.bak')
    else:
        print_debug('Current autosave not found')
        saves.append('curr.null')

    if (f'{tracker_file}.prev.bak' in files):
        print_debug(f'Found previous autosave >> {tracker_file}.prev.bak <<')
        saves.append(f'{tracker_file}.prev.bak')
    else:
        print_debug('Previous autosave not found')
        saves.append('prev.null')

    for save in files:
        if (tracker_file in save and save != tracker_file and save != f'{tracker_file}.curr.bak' and save != f'{tracker_file}.prev.bak'):
            print_debug(f'Found save >> {save} <<')
            saves.append(save)
    
    return saves

# Search functions (return dict)
def search_tasks(text, database):
    print_debug(f'Searching for tasks matching >> {text} <<')
    tasks = {}

    for guid, task in database['tasks'].items():
        if (string_compare(text, task['normalizedName']) or string_compare(text, task['name']) or guid == text):
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

def search_barters_by_item(text, database, required_only = False, tracked_only = False):
    barters = {}

    for guid, barter in database['barters'].items():
        if (tracked_only and not barter['tracked']):
            continue
        
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

def search_crafts_by_item(text, database, required_only = False, tracked_only = False):
    crafts = {}

    for guid, craft in database['crafts'].items():
        if (tracked_only and not craft['tracked']):
            continue

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
    task = database['tasks'][guid]

    if (task['tracked']):
        print(f'Already tracking {task["name"]}')
        return database
    
    for objective in task['objectives']:
        if (objective['type'] == 'giveItem'):
            item_guid = objective['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = objective['count']
            print_debug(f'Adding >> {count} << of >> {item_guid} << for objective >> {objective["description"]} <<')

            if (objective['foundInRaid']):
                print_debug('FIR')
                database['items'][item_guid]['need_fir'] = database['items'][item_guid]['need_fir'] + count
                print(f'{count} more {item_name} (FIR) now needed')
            else:
                print_debug('NIR')
                database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
                print(f'{count} more {item_name} (NIR) now needed')

    if (task['neededKeys'] is not None and len(task['neededKeys']) > 0):
        for _key_ in task['neededKeys']:
            for key in _key_['keys']:
                item_guid = key['id']
                database['items'][item_guid]['need_nir'] = 1

    database['tasks'][guid]['tracked'] = True
    print(f'Tracked {task["name"]}')
    return database

def track_station(database, guid):
    print_debug(f'Tracking station >> {guid} <<')
    station = database['hideout'][guid]

    if (station['tracked']):
        print(f'Already tracking {station["normalizedName"]}')
        return database
    
    for requirement in station['itemRequirements']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement >> {requirement["id"]} <<')
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
        print(f'{count} more {item_name} (NIR) now needed')

    database['hideout'][guid]['tracked'] = True
    print(f'Tracked {station["normalizedName"]}')
    return database

def track_barter(database, guid):
    print_debug(f'Tracking barter >> {guid} <<')
    barter = database['barters'][guid]

    if (barter['tracked']):
        print(f'Already tracking {guid}')
        return database
    
    for requirement in barter['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
        print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
        print(f'{count} more {item_name} (NIR) now needed')

    database['barters'][guid]['tracked'] = True
    print(f'Tracked {guid}')          
    return database

def track_craft(database, guid):
    print_debug(f'Tracking craft >> {guid} <<')
    craft = database['crafts'][guid]

    if (craft['tracked']):
        print(f'Already tracking {guid}')
        return database
    
    for requirement in craft['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
        print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
        print(f'{count} more {item_name} (NIR) now needed')

    database['crafts'][guid]['tracked'] = True
    print(f'Tracked {guid}')          
    return database

def untrack_task(database, guid):
    print_debug(f'Untracking task >> {guid} <<')
    task = database['tasks'][guid]

    if (not task['tracked']):
        print(f'{task["name"]} is already untracked')
        return database
    
    for objective in task['objectives']:
        if (objective['type'] == 'giveItem'):
            item_guid = objective['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = objective['count']
            print_debug(f'Removing >> {count} << of >> {item_guid} << for objective >> {objective["description"]} <<')

            if (objective['foundInRaid']):
                print_debug('FIR')
                database['items'][item_guid]['need_fir'] = database['items'][item_guid]['need_fir'] - count
                print(f'{count} less {item_name} (FIR) now needed')
            else:
                print_debug('NIR')
                database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] - count
                print(f'{count} less {item_name} (NIR) now needed')

    database['tasks'][guid]['tracked'] = False
    print(f'Untracked {task["name"]}')
    return database

def untrack_station(database, guid):
    print_debug(f'Untracking station >> {guid} <<')
    station = database['hideout'][guid]

    if (not station['tracked']):
        print(f'{station["normalizedName"]} is already untracked')
        return database
    
    for requirement in station['itemRequirements']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        print_debug(f'Removing >> {count} << of >> {item_guid} << for requirement >> {requirement["id"]} <<')
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] - count
        print(f'{count} less {item_name} (NIR) now needed')

    database['hideout'][guid]['tracked'] = False
    print(f'Untracked {station["normalizedName"]}')
    return database

def untrack_barter(database, guid):
    print_debug(f'Untracking barter >> {guid} <<')
    barter = database['barters'][guid]

    if (not barter['tracked']):
        print(f'{barter["id"]} is already untracked')
        return database
    
    for requirement in barter['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
        print_debug(f'Removing >> {count} << of >> {item_guid} << for requirement')
        print(f'{count} less {item_name} (NIR) now needed')

    database['barters'][guid]['tracked'] = False
    print(f'Untracked {guid}')          
    return database

def untrack_craft(database, guid):
    print_debug(f'Untracking craft >> {guid} <<')
    craft = database['crafts'][guid]

    if (not craft['tracked']):
        print(f'{craft["id"]} is already untracked')
        return database
    
    for requirement in craft['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        count = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
        print_debug(f'Removing >> {count} << of >> {item_guid} << for requirement')
        print(f'{count} less {item_name} (NIR) now needed')

    database['crafts'][guid]['tracked'] = False
    print(f'Untracked {guid}')          
    return database

# Complete functions
def complete_task(database, guid, force):
    task = database['tasks'][guid]

    if (task['status'] == 'complete'):
        print(f'{task["name"]} is already complete')
        return False

    if (not task['tracked'] and not force):
        print_error(f'{task["name"]} is not tracked')
        return False

    _return_ = verify_task(database, task)
                            
    if (type(_return_) is str and not force):
        print_error(_return_)
        return False

    for objective in task['objectives']:
        if (objective['type'] == 'giveItem'):
            item_guid = objective['item']['id']
            item_name = database['items'][item_guid]['shortName']
            available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
            available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']

            if (objective['foundInRaid']):
                need_fir = objective['count']
                _remainder_ = need_fir - available_fir

                if (_remainder_ > 0 and not force):
                    print_error(f'{_remainder_} more {item_name} (FIR) required')
                    return False
                elif (force):
                    database = add_item_fir(database, _remainder_, item_guid)

                    if (not database):
                        print_error(f'Encountered an error. All item changes for this task have been aborted')
                        return False
                
                database['items'][item_guid]['consumed_fir'] = database['items'][item_guid]['consumed_fir'] + need_fir
            else:
                need_nir = objective['count']
                _remainder_ = need_nir - available_nir

                if (_remainder_ > 0):
                    if (available_fir < _remainder_ and not force):
                        print_error(f'{_remainder_} more {item_name} required')
                        return False
                    elif (force):
                        database = add_item_nir(database, _remainder_, item_guid)

                        if (not database):
                            print_error(f'Encountered an error. All item changes for this task have been aborted')
                            return False
                    else:
                        print(f'{_remainder_} more {item_name} required. Consume {_remainder_} (FIR) instead? (Y/N)')
                        _confirmation_ = input('> ').lower()

                        if (_confirmation_ == 'y'):
                            database = del_item_fir(database, _remainder_, item_guid)
                            database = add_item_nir(database, _remainder_, item_guid)

                            if (not database):
                                print_error(f'Encountered an error. All item changes for this task have been aborted')
                                return False
                        else:
                            print_error('All item changes for this task have been aborted')
                            return False
                
                database['items'][item_guid]['consumed_nir'] = database['items'][item_guid]['consumed_nir'] + need_nir
            
    database['tasks'][guid]['status'] = 'complete'
    print(f'{task["name"]} completed')
    return database

def complete_recursive_task(database, guid, tasks = []):
    if (len(database['tasks'][guid]['taskRequirements']) == 0):
        tasks.append(guid)

    for prereq in database['tasks'][guid]['taskRequirements']:
        tasks = complete_recursive_task(database, prereq['task']['id'], tasks = tasks)
        tasks.append(guid)
    
    return tasks

def complete_station(database, guid, force):
    station = database['hideout'][guid]

    if (station['status'] == 'complete'):
        print(f'{station["normalizedName"]} is already complete')
        return False

    if (not station['tracked'] and not force):
        print_error(f'{station["normalizedName"]} is not tracked')
        return False

    _return_ = verify_station(database, station)

    if (type(_return_) is str and not force):
        print_error(_return_)
        return False

    for requirement in station['itemRequirements']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
        available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
        need = requirement['count']
        foundInRaid = False

        for attribute in requirement['attributes']:
            if (attribute['type'] == 'foundInRaid' and attribute['value'] == 'true'):
                foundInRaid = True

        if (foundInRaid):
            _remainder_ = need - available_fir
        else:
            _remainder_ = need - available_nir

        if (_remainder_ > 0):
            if (not foundInRaid):
                if (available_fir < _remainder_ and not force):
                    print_error(f'{_remainder_} more {item_name} required')
                    return False
                elif (force):
                    database = add_item_nir(database, _remainder_, guid = item_guid)

                    if (not database):
                        print_error(f'Encountered an error. All item changes for this hideout station have been aborted')
                        return False
                else:
                    print(f'{_remainder_} more {item_name} required. Consume {_remainder_} (FIR) instead? (Y/N)')
                    _confirmation_ = input('> ').lower()

                    if (_confirmation_ == 'y'):
                        database = del_item_fir(database, _remainder_, guid = item_guid)
                        database = add_item_nir(database, _remainder_, guid = item_guid)

                        if (not database):
                            print_error(f'Encountered an error. All item changes for this hideout station have been aborted')
                            return False
                    else:
                        print_error('All item changes for this hideout station have been aborted')
                        return False
            else:
                if (not force):
                    print_error(f'{_remainder_} more {item_name} (FIR) required')
                    return False
                else:
                    database = add_item_fir(database, _remainder_, guid = item_guid)

                    if (not database):
                        print_error(f'Encountered an error. All item changes for this hideout station have been aborted')
                        return False
        
        if (foundInRaid):
            database['items'][item_guid]['consumed_fir'] = database['items'][item_guid]['consumed_fir'] + need
        else:
            database['items'][item_guid]['consumed_nir'] = database['items'][item_guid]['consumed_nir'] + need
    
    database['hideout'][guid]['status'] = 'complete'
    print(f'{station["normalizedName"]} completed')
    hideout_readiness(database)
    return database

def complete_barter(database, guid, force):
    barter = database['barters'][guid]

    if (barter['status'] == 'complete'):
        print(f'{barter["id"]} is already complete')
        return False
    
    if (not barter['tracked'] and not force):
        print_error(f'{barter["id"]} is not tracked')
        return False

    _return_ = verify_barter(database, guid)

    if (type(_return_) is str and not force):
        print_error(_return_)
        return False

    for requirement in barter['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
        available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
        need_nir = requirement['count']
        _remainder_ = need_nir - available_nir

        if (_remainder_ > 0):
            if (available_fir < _remainder_ and not force):
                print_error(f'{_remainder_} more {item_name} required')
                return False
            elif (force):
                database = add_item_nir(database, _remainder_, guid = item_guid)

                if (not database):
                    print_error(f'Encountered an error. All item changes for this barter have been aborted')
                    return False
            else:
                print(f'{_remainder_} more {item_name} required. Consume {available_fir} (FIR) instead? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ == 'y'):
                    database = del_item_fir(database, _remainder_, guid = item_guid)
                    database = add_item_nir(database, _remainder_, guid = item_guid)

                    if (not database):
                        print_error(f'Encountered an error. All item changes for this barter have been aborted')
                        return False
                else:
                    print_error('All item changes for this barter have been aborted')
                    return False
        
        database['items'][item_guid]['consumed_nir'] = database['items'][item_guid]['consumed_nir'] + need_nir
    
    database['barters'][guid]['status'] = 'complete'
    print(f'{guid} completed')
    return database

def complete_craft(database, guid, force):
    craft = database['crafts'][guid]

    if (craft['status'] == 'complete'):
        print(f'{craft["id"]} is already complete')
        return False
    
    if (not craft['tracked'] and not force):
        print_error(f'{craft["id"]} is not tracked')
        return False

    _return_ = verify_craft(database, guid)

    if (type(_return_) is str and not force):
        print_error(_return_)
        return False

    for requirement in craft['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
        available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
        need_nir = requirement['count']
        _remainder_ = need_nir - available_nir

        if (_remainder_ > 0):
            if (available_fir < _remainder_ and not force):
                print_error(f'{_remainder_} more {item_name} required')
                return False
            elif (force):
                database = add_item_nir(database, _remainder_, guid = item_guid)

                if (not database):
                    print_error(f'Encountered an error. All item changes for this craft have been aborted')
                    return False
            else:
                print(f'{_remainder_} more {item_name} required. Consume {available_fir} (FIR) instead? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ == 'y'):
                    database = del_item_fir(database, _remainder_, guid = item_guid)
                    database = add_item_nir(database, _remainder_, guid = item_guid)

                    if (not database):
                        print_error(f'Encountered an error. All item changes for this craft have been aborted')
                        return False
                else:
                    print_error('All item changes for this craft have been aborted')
                    return False
        
        database['items'][item_guid]['consumed_nir'] = database['items'][item_guid]['consumed_nir'] + need_nir
    
    database['crafts'][guid]['status'] = 'complete'
    print(f'{guid} completed')
    return database

# Restart functions
def restart_barter(database, guid):
    barter = database['barters'][guid]

    if (barter['status'] == 'incomplete'):
        print(f'{barter["id"]} is not complete')
        return False
    
    if (not barter['tracked']):
        print_error(f'{barter["id"]} is not tracked')
        return False

    for requirement in barter['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        need_nir = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + need_nir
        print_debug(f'Adding >> {need_nir} << of >> {item_guid} << for requirement')
        print(f'{need_nir} more {item_name} (NIR) now needed')
    
    database['barters'][guid]['status'] = 'incomplete'
    database['barters'][guid]['restarts'] = database['barters'][guid]['restarts'] + 1
    print(f'{guid} restarted')
    return database

def restart_craft(database, guid):
    craft = database['crafts'][guid]

    if (craft['status'] == 'incomplete'):
        print(f'{craft["id"]} is not complete')
        return False
    
    if (not craft['tracked']):
        print_error(f'{craft["id"]} is not tracked')
        return False

    for requirement in craft['requiredItems']:
        item_guid = requirement['item']['id']
        item_name = database['items'][item_guid]['shortName']
        need_nir = requirement['count']
        database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + need_nir
        print_debug(f'Adding >> {need_nir} << of >> {item_guid} << for requirement')
        print(f'{need_nir} more {item_name} (NIR) now needed')
    
    database['crafts'][guid]['status'] = 'incomplete'
    database['crafts'][guid]['restarts'] = database['crafts'][guid]['restarts'] + 1
    print(f'{guid} restarted')
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

    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False
        
        print('Retrieved latest task data from the api.tarkov.dev server')

    nonKappa = 0
    imported_tasks = 0

    for task in response.json()['data']['tasks']:
        guid = task['id']
        del task['id']
        task['maps'] = []
        del task['map']
        task['status'] = 'incomplete'
        task['tracked'] = True
        maps = task_to_map(task)
        
        if (maps == 'any'):
            task['maps'] = ['0']
        else:
            for map in maps:
                task['maps'].append(map)
        
        if (not task['kappaRequired']):
            task['tracked'] = False
            nonKappa = nonKappa + 1

        if (task['kappaRequired']):
            priority = 2
        else:
            priority = 0

        follow_on_tasks = recurse_priority(response.json()['data']['tasks'], guid)

        if (follow_on_tasks == 0):
            priority = priority
        elif (0 < follow_on_tasks < 3):
            priority += 1
        elif (2 < follow_on_tasks < 8):
            priority += 2
        else:
            priority += 3

        task['priority'] = priority
        imported_tasks = imported_tasks + 1
        database['tasks'][guid] = task

    print(f'Successfully loaded {imported_tasks} tasks into the database! {nonKappa} non-Kappa required tasks have been automatically untracked')
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
                            attributes {
                                type
                                value
                            }
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

    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False
        
        print('Retrieved latest hideout data from the api.tarkov.dev server')
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
                print('Completed stash-1 automatically')

            database['hideout'][guid] = level

    print(f'Successfully loaded hideout data into the database!')
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

    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()
    
    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
                print_error(f'Errors detected {json.dumps(response.json())}')
                return False

        print('Retrieved latest barter data from the api.tarkov.dev server')
        barters = response.json()['data']['barters']

    for barter in barters:
        guid = barter['id']
        del barter['id']
        barter['status'] = 'incomplete'
        barter['tracked'] = False
        barter['restarts'] = 0
        database['barters'][guid] = barter

    print(f'Successfully loaded barter data into the database!')
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
    
    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print('Retrieved latest craft data from the api.tarkov.dev server')
        crafts = response.json()['data']['crafts']

    for craft in crafts:
        guid = craft['id']
        del craft['id']
        craft['status'] = 'incomplete'
        craft['tracked'] = False
        craft['restarts'] = 0
        database['crafts'][guid] = craft
    
    print(f'Successfully loaded craft data into the database!')
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
                            ... on FleaMarket {
                                minPlayerLevel
                            }
                        }
                        price
                        currency
                    }
                    buyFor {
                        vendor {
                            normalizedName
                            ... on TraderOffer {
                                minTraderLevel
                                taskUnlock {
                                    normalizedName
                                }
                            }
                        }
                        price
                        currency
                    }
                    avg24hPrice
                    fleaMarketFee
                }
            }
        """
    }

    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_warning(f'Errors detected {json.dumps(response.json()["errors"])}')
            
            for error in response.json()['errors']:
                if ('fleaMarketFee' not in error['path']):
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

        # Flea vars
        if ('avg24hPrice' in item.keys() and item['avg24hPrice'] is not None):
            flea_price = item['avg24hPrice']
            flea_currency = 'RUB'
        else:
            flea_price = 0
            flea_currency = 'N/A'

        # Selling vars
        best_trader_sell = 'N/A'
        best_trader_sell_price = 0
        best_trader_sell_currency = 'N/A'
        best_trader_sell_roubles = 0
        flea_level = 0

        # Buying vars
        best_trader_buy = 'N/A'
        best_trader_buy_price = 0
        best_trader_buy_currency = 'N/A'
        best_trader_buy_roubles = 0
        best_trader_level = 0
        best_trader_task_req = 'N/A'

        # Sell logic

        max_sell = 0

        # Finds best trader to sell to
        for vendor in item['sellFor']:
            if ('flea' in vendor['vendor']['normalizedName']):
                flea_level = vendor['vendor']['minPlayerLevel']
                continue

            this_price = int(vendor['price'])
            this_currency = vendor['currency']
            this_price_converted = 0

            # Normalizes all prices to roubles
            if (this_currency.lower() == 'usd'):
                this_price_converted = this_price * usd_to_roubles
            elif (this_currency.lower() == 'euro'):
                this_price_converted = this_price * euro_to_roubles
            else:
                this_price_converted = this_price

            # Sets best trader sell
            if (this_price_converted > max_sell):
                best_trader_sell_price = this_price
                best_trader_sell = vendor['vendor']['normalizedName']
                best_trader_sell_currency = this_currency
                max_sell = this_price_converted

                if (best_trader_sell_currency.lower() in ['usd', 'euro']):
                    best_trader_sell_roubles = this_price_converted
                else:
                    best_trader_sell_roubles = 0

        # Buy logic

        min_buy = sys.maxsize

        # Finds best trader to buy from
        for vendor in item['buyFor']:
            if ('flea' in vendor['vendor']['normalizedName']):
                continue

            this_price = int(vendor['price'])
            this_currency = vendor['currency']
            this_price_converted = 0

            # Normalizes all prices to roubles
            if (this_currency.lower() == 'usd'):
                this_price_converted = this_price * usd_to_roubles
            elif (this_currency.lower() == 'euro'):
                this_price_converted = this_price * euro_to_roubles
            else:
                this_price_converted = this_price

            # Sets best trader buy
            if (this_price_converted < min_buy):
                best_trader_buy_price = this_price
                best_trader_buy = vendor['vendor']['normalizedName']
                best_trader_buy_currency = this_currency
                best_trader_level = vendor['vendor']['minTraderLevel']
                min_buy = this_price_converted

                if (vendor['vendor']['taskUnlock']):
                    best_trader_task_req = vendor['vendor']['taskUnlock']['normalizedName']
                else:
                    best_trader_task_req = 'N/A'

                if (best_trader_buy_currency.lower() in ['usd', 'euro']):
                    best_trader_buy_roubles = this_price_converted
                else:
                    best_trader_buy_roubles = 0

        # Setting inventory values
        if (guid not in database['items'].keys()):
            database['items'][guid] = {
                'need_fir': 0,
                'need_nir': 0,
                'have_fir': 0,
                'have_nir': 0,
                'consumed_fir': 0,
                'consumed_nir': 0
            }

        # Updating item in database
        database['items'][guid]['normalizedName'] = item['normalizedName']
        database['items'][guid]['shortName'] = item['shortName']
        database['items'][guid]['flea_price'] = flea_price
        database['items'][guid]['flea_currency'] = flea_currency
        database['items'][guid]['best_trader_sell'] = best_trader_sell
        database['items'][guid]['best_trader_sell_price'] = best_trader_sell_price
        database['items'][guid]['best_trader_sell_currency'] = best_trader_sell_currency
        database['items'][guid]['best_trader_buy'] = best_trader_buy
        database['items'][guid]['best_trader_buy_price'] = best_trader_buy_price
        database['items'][guid]['best_trader_buy_currency'] = best_trader_buy_currency
        database['items'][guid]['best_trader_level'] = best_trader_level
        database['items'][guid]['best_trader_task_req'] = best_trader_task_req
        database['items'][guid]['flea_level'] = flea_level

        if (best_trader_sell_roubles):
            database['items'][guid]['best_trader_sell_roubles'] = best_trader_sell_roubles

        if (best_trader_buy_roubles):
            database['items'][guid]['best_trader_buy_roubles'] = best_trader_buy_roubles

    database['refresh'] = datetime.now().isoformat()
    print(f'Successfully loaded item data into the database!')
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
    
    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print('Retrieved latest map data from the api.tarkov.dev server')
        maps = response.json()['data']['maps']

    for map in maps:
        guid = map['id']
        del map['id']

        if (map['normalizedName'] == 'streets-of-tarkov'):
            map['normalizedName'] = 'streets'
        elif (map['normalizedName'] == 'the-lab'):
            map['normalizedName'] = 'labs'

        database['maps'][guid] = map

    print(f'Successfully loaded map data into the database!')
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
    
    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        response = requests.post(url = 'https://api.tarkov.dev/graphql', headers = headers, json = data)
    except:
        print_error('Encountered error retrieving data')
        return False
    finally:
        stop.set()
        progress_bar_thread.join()

    if (response.status_code < 200 or response.status_code > 299):
        print_error(f'Network error [{response.status_code}] {response.content}')
        return False
    else:
        if ('errors' in response.json().keys()):
            print_error(f'Errors detected {json.dumps(response.json())}')
            return False

        print('Retrieved latest trader data from the api.tarkov.dev server')
        traders = response.json()['data']['traders']

    for trader in traders:
        guid = trader['id']
        del trader['id']

        if (trader['normalizedName'] == 'btr-driver'):
            trader['normalizedName'] = 'btr'

        database['traders'][guid] = trader

    print(f'Successfully loaded trader data into the database!')
    return database

# Display
def display_inventory(items, filtered = False):
    print('\nAvailable / Total / Need\n')
    items = alphabetize_items(items)
    table_rows = []
    
    for guid, item in items.items():
        nir, fir = False, False
        _completed_ = 0
        _overstock_ = False
        _invalid_ = False
        prefix = ''

        # Skip currencies
        if (guid in ['5449016a4bdc2d6f028b456f', '5696686a4bdc2da3298b456a', '569668774bdc2da2298b4568']):
            continue

        if ((item['need_nir'] > 0 or item['have_nir'] > 0) and not (filtered and item['need_nir'] == 0)):
            if (item['consumed_nir'] > item['have_nir'] or item['consumed_fir'] > item['have_fir']):
                _invalid_ = True
            if (item['have_nir'] > item['need_nir']):
                _overstock_ = True

            if (item['have_nir'] >= item['need_nir'] and item['need_nir'] != 0):
                _completed_ = 1

            nir = f'{item["have_nir"] - item["consumed_nir"]}/{item["have_nir"]}/{item["need_nir"]}'
        
        if ((item['have_fir'] > 0 or item['need_fir'] > 0) and not (filtered and item['need_fir'] == 0)):
            if (item['consumed_nir'] > item['have_nir'] or item['consumed_fir'] > item['have_fir']):
                _invalid_ = True
            if (item['have_fir'] > item['need_fir']):
                _overstock_ = True

            if (item['have_fir'] >= item['need_fir'] and item['need_fir'] != 0):
                _completed_ = _completed_ + 2

            fir = f'{item["have_fir"] - item["consumed_fir"]}/{item["have_fir"]}/{item["need_fir"]}'

        if ((_completed_ == 1 and item['need_fir'] == 0) or (_completed_ == 2 and item['need_nir'] == 0) or _completed_ == 3):
            if (_invalid_):
                prefix = '[>!!!<][*] '
            elif (_overstock_):
                prefix = '[!][*] '
            else:
                prefix = '[*] '
        elif (_invalid_):
            prefix = '[>!!!<] '
        elif (_overstock_):
            prefix = '[!] '

        item_text = f'{prefix}{item["shortName"]}'

        if (nir and fir):
            inv_text = f'{nir} ({fir})'
        elif (nir):
            inv_text = nir
        elif (fir):
            inv_text = f'({fir})'
        else:
            continue

        table_rows.append([item_text, inv_text])
    
    if (not table_wrapper(table_rows, headers = INVENTORY_TABLE)):
        print('Something went wrong.')

    print('\n')
    return True

def display_have(items):
    print('\n')
    items = alphabetize_items(items)
    table_rows = []
    
    for guid, item in items.items():
        nir, fir = False, False

        if (item['have_nir'] > 0):
            nir = f'{item["have_nir"]}'
        
        if (item['have_fir'] > 0):
            fir = f'{item["have_fir"]}'

        if (nir and fir):
            inv_text = f'{nir} ({fir})'
        elif (nir):
            inv_text = nir
        elif (fir):
            inv_text = f'({fir})'
        else:
            continue
        
        table_rows.append([item['shortName'], inv_text])
    
    if (not table_wrapper(table_rows, headers = INVENTORY_HAVE_TABLE)):
        print('Something went wrong.')

    print('\n')
    return True

def display_need(items):
    print('\n')
    items = alphabetize_items(items)
    table_rows = []
    
    for guid, item in items.items():
        nir, fir = False, False

        if (item['need_nir'] > 0):
            nir = f'{item["need_nir"]}'
        
        if (item['need_fir'] > 0):
            fir = f'{item["need_fir"]}'

        if (nir and fir):
            inv_text = f'{nir} ({fir})'
        elif (nir):
            inv_text = nir
        elif (fir):
            inv_text = f'({fir})'
        else:
            continue
        
        table_rows.append([item['shortName'], inv_text])
    
    if (not table_wrapper(table_rows, headers = INVENTORY_NEED_TABLE)):
        print('Something went wrong.')

    print('\n')
    return True

def display_tasks(database, tasks):
    print('\n')
    table_rows = []
    duplicates = [] # There are some duplicate tasks for USEC and BEAR (i.e., Textile Part 1 and 2)
    maps = {}

    # Setting up the map display
    for guid, task in tasks.items():
        if (len(task['maps']) > 1):
            map = 'multi'
        elif (task['maps'][0] == '0'):
            map = 'any'
        else:
            map = database['maps'][task['maps'][0]]['normalizedName']

        if (map in maps.keys()):
            maps[map] = maps[map] + 1
        else:
            maps[map] = 1
        
        task['map'] = map

    maps = dict(sorted(maps.items(), key = lambda item: item[1], reverse = True))
    tasks = alphabetize_tasks(tasks)
    
    for guid, task in tasks.items():
        if (task['name'] in duplicates):
            print_debug(f'>> {task["name"]} << has already been seen and will be skipped during printing')
            continue

        priority = task['priority']

        if (priority == 0):
            priority = 'Very low'
        elif (0 < priority < 3):
            priority = 'Low'
        elif (2 < priority < 5):
            priority = 'Normal'
        else:
            priority = 'Important'

        duplicates.append(task['name'])
        table_rows.append([task['name'], database['traders'][task['trader']['id']]['normalizedName'], task['status'], display_bool(task['tracked']), display_bool(task['kappaRequired']), task['map'], priority, guid])

        for objective in task['objectives']:
            objective_string = '-->'

            if (objective['optional']):
                objective_string = objective_string + ' (OPT)'

            objective_string = objective_string + ' ' + objective['description']

            if (objective['type'] == 'giveItem'):
                item_guid = objective['item']['id']
                have_available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
                have_available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']

                if ('foundInRaid' in objective and objective['foundInRaid']):
                    objective_string = objective_string + f' ({have_available_fir}/{objective["count"]} FIR available)'
                else:
                    objective_string = objective_string + f' ({have_available_nir}/{objective["count"]} available or {have_available_fir}/{objective["count"]} FIR)'

            elif ('count' in objective):
                objective_string = objective_string + f' ({objective["count"]})'

            if ('skillLevel' in objective):
                objective_string = objective_string + f' ({objective["skillLevel"]["level"]})'

            if ('exitStatus' in objective):
                objective_string = objective_string + f' with exit status {objective["exitStatus"]}'

            table_rows.append([objective_string])
        
        if (task['neededKeys'] is not None and len(task['neededKeys']) > 0):
            for _key_ in task['neededKeys']:
                for key in _key_['keys']:
                    key_string = '-->'
                    key_guid = key['id']
                    key_string = key_string + f' Acquire {database['items'][key_guid]['shortName']} key'
                        
                    if (database['items'][key_guid]['have_nir'] - database['items'][key_guid]['consumed_nir'] > 0):
                        key_string = key_string + ' (have)'
                    
                    table_rows.append([key_string])

        table_rows.append([])
    
    map_string = ''

    for map_name, hits in maps.items():
        map_string += f'{map_name}: {hits} | '

    map_string += f'(total: {len(tasks)})'

    if (not table_wrapper(table_rows, headers = TASK_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n' + map_string)
    print('\n')
    return True

def display_hideout(database, stations):
    print('\n')
    table_rows = []

    for guid, station in stations.items():
        table_rows.append([station['normalizedName'], station['status'], display_bool(station['tracked']), guid])

        for item in station['itemRequirements']:
            item_guid = item['item']['id']
            count = item['count']
            short_name = database['items'][item_guid]['shortName']
            foundInRaid = False

            if (station['status'] == 'incomplete'):
                have_available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
                have_available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']

                for attribute in item['attributes']:
                    if (attribute['type'] == 'foundInRaid' and attribute['value'] == 'true'):
                        foundInRaid = True

                if (foundInRaid):
                    table_rows.append([f'--> ({have_available_fir}/{count}) FIR {short_name} needed'])
                else:
                    display = f'--> {have_available_nir}/{count} {short_name} needed'

                    if (have_available_fir > 0):
                        display = display + f' ({have_available_fir}/{count}) FIR available'

                    table_rows.append([display])
            else:
                table_rows.append([f'--> {count}/{count} {short_name} consumed'])

        table_rows.append([])
            
    if (not table_wrapper(table_rows, headers = HIDEOUT_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_barters(database, barters):
    print('\n')
    table_rows = []

    for guid, barter in barters.items():
        table_rows.append([guid, database['traders'][barter['trader']['id']]['normalizedName'], barter['level'], barter['status'], display_bool(barter['tracked']), barter['restarts']])

        for item in barter['requiredItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']

            if (barter['status'] == 'incomplete'):
                have_available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
                have_available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
                display = f'--> Give {have_available_nir}/{count} {item_name} available'

                if (have_available_fir > 0):
                    display = display + f' ({have_available_fir}/{count}) FIR'

                table_rows.append([display])
            else:
                table_rows.append([f'--> {count}/{count} {item_name} consumed'])

        for item in barter['rewardItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']
            table_rows.append([f'--> Receive {count} {item_name}'])

        if (barter['taskUnlock'] is not None):
            if (barter['taskUnlock']['id'] in database['tasks'].keys()):
                table_rows.append([f'--> Requires task {database['tasks'][barter["taskUnlock"]["id"]]['name']}'])
            else:
                table_rows.append([f'--> Requires task {barter["taskUnlock"]["id"]} (Unknown task)'])
                print(f'--> Requires task {barter["taskUnlock"]["id"]} (Unknown task)')

        table_rows.append([])

    if (not table_wrapper(table_rows, headers = BARTER_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_crafts(database, crafts):
    print('\n')
    table_rows = []

    for guid, craft in crafts.items():
        station_guid = craft['station']['id'] + '-' + str(craft['level'])

        if (station_guid in database['hideout'].keys()):
            table_rows.append([guid, database['hideout'][station_guid]['normalizedName'], craft['status'], display_bool(craft['tracked']), craft['restarts']])
        else:
            table_rows.append([guid, 'unknown', craft['status'], display_bool(craft['tracked']), craft['restarts']])

        for item in craft['requiredItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']

            if (craft['status'] == 'incomplete'):
                have_available_nir = database['items'][item_guid]['have_nir'] - database['items'][item_guid]['consumed_nir']
                have_available_fir = database['items'][item_guid]['have_fir'] - database['items'][item_guid]['consumed_fir']
                display = f'--> Give {have_available_nir}/{count} {item_name} available'

                if (have_available_fir > 0):
                    display = display + f' ({have_available_fir}/{count}) FIR'

                table_rows.append([display])
            else:
                table_rows.append([f'--> {count}/{count} {item_name} consumed'])

        for item in craft['rewardItems']:
            item_guid = item['item']['id']
            item_name = database['items'][item_guid]['shortName']
            count = item['count']
            table_rows.append([f'--> Receive {count} {item_name}'])

        if (craft['taskUnlock'] is not None):
            table_rows.append([f'--> Requires task {database['tasks'][craft["taskUnlock"]["id"]]['name']}'])

        table_rows.append([f'--> Takes {str(timedelta(seconds = craft["duration"]))} to complete'])
        table_rows.append([])

    if (not table_wrapper(table_rows, headers = CRAFTS_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_untracked(database, untracked):
    print('\n')
    table_rows = []

    for guid, entry in untracked.items():
        if (guid in database['tasks'].keys()):
            table_rows.append([entry['name'], 'task', display_bool(entry['tracked']), display_bool(entry['kappaRequired'])])
        else:
            table_rows.append([entry['normalizedName'], 'hideout station', display_bool(entry['tracked'])])

    if (not table_wrapper(table_rows, headers = UNTRACKED_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_items(items):
    print('\nAvailable / Total / Need\n')
    items = alphabetize_items(items)
    table_rows = []

    for guid, item in items.items():
        try:
            item_display = f'{item["have_nir"] - item["consumed_nir"]}/{item["have_nir"]}/{item["need_nir"]} ({item["have_fir"] - item["consumed_fir"]}/{item["have_fir"]}/{item["need_fir"]})'
        except KeyError:
            print(item)
            return False

        flea_price = format_price(item["flea_price"], item["flea_currency"])
        flea_level = f'Level {item["flea_level"]}'

        if ('best_trader_sell_roubles' in item.keys()):
            sell_price = format_price(item["best_trader_sell_price"], item["best_trader_sell_currency"]) + f' ({format_price(item["best_trader_sell_roubles"], 'roubles')})'
        else:
            sell_price = format_price(item["best_trader_sell_price"], item["best_trader_sell_currency"])

        if ('best_trader_buy_roubles' in item.keys()):
            buy_price = format_price(item["best_trader_buy_price"], item["best_trader_buy_currency"]) + f' ({format_price(item["best_trader_buy_roubles"], 'roubles')})'
        else:
            buy_price = format_price(item["best_trader_buy_price"], item["best_trader_buy_currency"])

        if (item['best_trader_task_req'] != 'N/A'):
            buy_req = f'Complete {item["best_trader_task_req"]}'
        else:
            buy_req = 'None'

        if (item['best_trader_buy'] != 'N/A'):
            best_buy = item['best_trader_buy'] + ' LL' + str(item['best_trader_level'])
        else:
            best_buy = 'N/A'

        table_rows.append([item['shortName'], item['normalizedName'], guid, item_display, '{:<12} {:<12}'.format(sell_price, item['best_trader_sell']), '{:<12} {:<12}'.format(buy_price, best_buy), '{:<12} {:<8}'.format(flea_price, flea_level), buy_req])

    if (not table_wrapper(table_rows, headers = ITEM_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_maps(maps):
    print('\n')
    table_rows = []

    for guid, map in maps.items():
        table_rows.append([map['normalizedName'], guid])

    if (not table_wrapper(table_rows, headers = MAP_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_traders(traders):
    print('\n')
    table_rows = []

    for guid, trader in traders.items():
        table_rows.append([trader['normalizedName'], guid])

    if (not table_wrapper(table_rows, headers = TRADER_TABLE, max_chunks = 1)):
        print('Something went wrong.')

    print('\n')
    return True

def display_note(name, note):
    print('\n')
    table_rows = []

    for element in note:
        table_rows.append([element])

    if (not table_rows):
        print('No notes')
        return False

    if (not table_wrapper(table_rows, headers = [name], max_chunks = 1)):
        print('Something went wrong')
        return False

    print('\n')
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
def inventory(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False

    display_inventory(get_inventory(database))
    return True

def inventory_tasks(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    task_items = get_inventory_tasks(database)

    if (len(task_items) == 0):
        print('No items are required for tasks')
    else:
        display_inventory(task_items, filtered = True)

    return True

def inventory_hideout(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    hideout_items = get_inventory_hideout(database)

    if (len(hideout_items) == 0):
        print('No items are required for the hideout')
    else:
        display_inventory(hideout_items, filtered = True)

    return True

def inventory_barters(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    barter_items = get_inventory_barters(database)

    if (len(barter_items) == 0):
        print('No items are required for barters')
    else:
        display_inventory(barter_items, filtered = True)

    return True

def inventory_crafts(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    craft_items = get_inventory_crafts(database)

    if (len(craft_items) == 0):
        print('No items are required for crafts')
    else:
        display_inventory(craft_items, filtered = True)

    return True

def inventory_have(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    have_items = get_inventory_have(database)
    
    if (len(have_items) == 0):
        print('You have not collected any items')
    else:
        display_have(have_items)

    return True

def inventory_need(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        return False
    
    need_items = get_inventory_need(database)
    
    if (len(need_items) == 0):
        print('No items needed. CONGRATULATIONS!')
    else:
        display_need(need_items)

    return True

# List
def list_tasks(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    if (argument == 'all'):
        tasks = get_tasks(database)
    else:
        tasks = get_tasks_filtered(database, argument)

    if (len(tasks) == 0):
        print('No available or tracked tasks found')
        return False
    
    display_tasks(database, tasks)
    return True

def list_stations(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    stations = get_hideout(database)

    if (len(stations) == 0):
        print('No available or tracked hideout stations found')
    else:
        display_hideout(database, stations)
    
    return True

def list_barters(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    if (argument == 'all'):
        barters = get_barters(database)
    else:
        barters = get_barters_filtered(database, argument)

    if (len(barters) == 0):
        print('No tracked barters found')
        return False
    
    display_barters(database, barters)
    return True

def list_crafts(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    crafts = get_crafts(database)

    if (len(crafts) == 0):
        print('No tracked crafts found')
    else:
        display_crafts(database, crafts)
    
    return True

def list_untracked(tracker_file, directory, ignore_kappa):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    untracked = get_untracked(database, ignore_kappa)

    if (len(untracked) == 0 and ignore_kappa):
        print('No untracked items (including Kappa tasks) found')
    elif (len(untracked) == 0):
        print('No untracked items (excluding Kappa tasks) found')
    else:
        display_untracked(database, untracked)

    return True

def list_maps(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    maps = ', '.join(map['normalizedName'] for guid, map in database['maps'].items()).strip(', ')
    print(f'Accepted map names are: {maps}')

def list_traders(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    traders = ', '.join(trader['normalizedName'] for guid, trader in database['traders'].items()).strip(', ')
    print(f'Accepted trader names are: {traders}')

# Search
def search(tracker_file, directory, argument, ignore_barters, ignore_crafts):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False

    if (datetime.fromisoformat(database['refresh']) < (datetime.now() - timedelta(hours = 24))):
        print('Item price data is over 24 hours old. Refreshing...')
        database = import_items(database, headers = {
            'Content-Type': 'application/json'
        })
        write_database(tracker_file, directory, database)

    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        tasks = search_tasks(argument, database)
        hideout = search_hideout(argument, database)
        barters = search_barters(argument, database)
        crafts = search_crafts(argument, database)
        items = search_items(argument, database)
        traders = search_traders(argument, database)
        maps = search_maps(argument, database)
    finally:
        stop.set()
        progress_bar_thread.join()

    if (not ignore_barters):
        _barters_ = search_barters_by_item(argument, database)

        if (barters and _barters_):
            barters = barters | _barters_
        elif (not barters and _barters_):
            barters = _barters_

    if (not ignore_crafts):
        _crafts_ = search_crafts_by_item(argument, database)

        if (crafts and _crafts_):
            crafts = crafts | _crafts_
        elif (not crafts and _crafts_):
            crafts = _crafts_

    display_search(database, tasks, hideout, barters, crafts, items, traders, maps)
    return True

def required_search(tracker_file, directory, argument, ignore_barters, ignore_crafts):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    if (datetime.fromisoformat(database['refresh']) < (datetime.now() - timedelta(hours = 24))):
        print('Item price data is over 24 hours old. Refreshing...')
        database = import_items(database, headers = {
            'Content-Type': 'application/json'
        })
        write_database(tracker_file, directory, database)
        print('Complete')
    
    stop = threading.Event()
    progress_bar_thread = threading.Thread(target = progress_bar, args = (stop,))
    progress_bar_thread.start()

    try:
        tasks = search_tasks_by_item(argument, database)
        hideout = search_hideout_by_item(argument, database)
    finally:
        stop.set()
        progress_bar_thread.join()

    if (not ignore_barters):
        barters = search_barters_by_item(argument, database, required_only = True)
    else:
        barters = search_barters_by_item(argument, database, tracked_only = True)

    if (not ignore_crafts):
        crafts = search_crafts_by_item(argument, database, required_only = True)
    else:
        crafts = search_crafts_by_item(argument, database, tracked_only = True)

    if (not tasks and not hideout and not barters and not crafts):
        print('\nItem not required\n')

    display_search(database, tasks, hideout, barters, crafts, False, False, False)
    return True

# Track
def track(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    guid = find_completable(argument, database)

    if (not guid):
        print_error(f'Could not find {argument} to track')
        return False
    
    if (guid in database['tasks'].keys()):
        database = track_task(database, guid)
    elif (guid in database['hideout'].keys()):
        database = track_station(database, guid)
    elif (guid in database['barters'].keys()):
        database = track_barter(database, guid)
    else:
        database = track_craft(database, guid)
    
    write_database(tracker_file, directory, database)
    return True

def untrack(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    guid = find_completable(argument, database)

    if (not guid):
        print_error(f'Could not find {argument} to untrack')
        return False
    
    if (guid in database['tasks'].keys()):
        database = untrack_task(database, guid)
    elif (guid in database['hideout'].keys()):
        database = untrack_station(database, guid)
    elif (guid in database['barters'].keys()):
        database = untrack_barter(database, guid)
    else:
        database = untrack_craft(database, guid)
    
    write_database(tracker_file, directory, database)
    return True

# Complete
def complete(tracker_file, directory, argument, force, recurse):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    guid = find_completable(argument, database)

    if (not guid):
        print_error(f'Could not find {argument} to complete')
        return False
    
    if (guid in database['tasks'].keys()):
        if (not recurse):
            database = complete_task(database, guid, force)
        else:
            tasks = complete_recursive_task(database, guid)

            for guid in tasks:
                if (database):
                    database = complete_task(database, guid, force)

    elif (guid in database['hideout'].keys()):
        database = complete_station(database, guid, force)
    elif (guid in database['barters'].keys()):
        database = complete_barter(database, guid, force)
    else:
        database = complete_craft(database, guid, force)

    if (database):
        write_database(tracker_file, directory, database)
        return True
    
    return False

# Restart
def restart(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    guid = find_restartable(argument, database)

    if (not guid):
        print_error(f'Could not find {argument} to complete')
        return False
    
    if (guid in database['barters'].keys()):
        database = restart_barter(database, guid)
    else:
        database = restart_craft(database, guid)

    if (database):
        write_database(tracker_file, directory, database)
        return True
    
    return False

# Add
def write_item_fir(tracker_file, directory, count, argument):
    database = open_database(tracker_file, directory)
    guid = find_item(argument, database)

    if (not guid):
        print_error(f'Could not find any item matching {argument}')
        return False

    database = add_item_fir(database, count, guid)

    if (not database):
        return False

    write_database(tracker_file, directory, database)
    return True

def write_item_nir(tracker_file, directory, count, argument):
    database = open_database(tracker_file, directory)
    guid = find_item(argument, database)

    if (not guid):
        print_error(f'Could not find any item matching {argument}')
        return False

    database = add_item_nir(database, count, guid)

    if (not database):
        return False

    write_database(tracker_file, directory, database)
    return True

# Delete
def unwrite_item_fir(tracker_file, directory, count, argument):
    database = open_database(tracker_file, directory)
    guid = find_item(argument, database)

    if (not guid):
        print_error(f'Could not find any item matching {argument}')
        return False

    database = del_item_fir(database, count, guid)

    if (not database):
        return False

    write_database(tracker_file, directory, database)
    return True

def unwrite_item_nir(tracker_file, directory, count, argument):
    database = open_database(tracker_file, directory)
    guid = find_item(argument, database)

    if (not guid):
        print_error(f'Could not find any item matching {argument}')
        return False

    database = del_item_nir(database, count, guid)

    if (not database):
        return False

    write_database(tracker_file, directory, database)
    return True

# Level
def check_level(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    print(f'\nYou are level {database["player_level"]}\n')
    return True

def set_level(tracker_file, directory, level):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    database['player_level'] = level
    write_database(tracker_file, directory, database)
    print(f'\nYour level is now {level}\n')
    return True

def level_up(tracker_file, directory):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    database['player_level'] = database['player_level'] + 1
    write_database(tracker_file, directory, database)
    print(f'\nLevel up! Your level is now {database["player_level"]}\n')
    return True

# Notes
def note(tracker_file, directory, argument):
    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Failed to open database')
        return False
    
    if (len(argument) == 1 and argument[0] == 'note'):
        display_note('All Notes', [name for name in database['notes'].keys()])
        return True

    for name, note in database['notes'].items():
        if (argument[0] == 'delete'):
            if (len(argument) > 1 and argument[1] in database['notes'].keys()):
                del database['notes'][argument[1]]
                write_database(tracker_file, directory, database)
                print(f'Deleted note {argument[1]}')
                return True
            else:
                print_error('Could not find note to be deleted')
                return False
        if (name.lower() == argument[0].lower()):
            if (len(argument) == 1):
                display_note(name, note)
                break
            else:
                database['notes'][name].append(' '.join(argument[1:]))
                write_database(tracker_file, directory, database)
                print(f'Appended {" ".join(argument[1:])} to note {argument[0]}')
                break
    else:
        if (len(argument) > 1):
            database['notes'][argument[0]] = [' '.join(argument[1:])]
            write_database(tracker_file, directory, database)
            print(f'Created new note {argument[0]} with element {" ".join(argument[1:])}')
        else:
            print_error(f'No note found matching {argument[0]}')
            return False
    
    return True

# Clear
def clear():
    system('cls' if name == 'nt' else 'clear')
    return True

# Import
def import_data(tracker_file, directory):
    database = {
        'tasks': {},
        'hideout': {},
        'barters': {},
        'crafts': {},
        'items': {},
        'maps': {},
        'traders': {},
        'notes': {},
        'player_level': 1,
        'refresh': -1,
        'version': VERSION
    }
    headers = {
        'Content-Type': 'application/json'
    }
    database = import_maps(database, headers)

    if (not database):
        print_error('Encountered error while importing maps. Import aborted')
        return False

    database = import_traders(database, headers)

    if (not database):
        print_error('Encountered error while importing traders. Import aborted')
        return False

    database = import_items(database, headers)

    if (not database):
        print_error('Encountered error while importing items. Import aborted')
        return False

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
    
    database = calculate_inventory(database)
    write_database(tracker_file, directory, database)
    print(f'Finished importing game data and saved to {tracker_file}')
    return True

def delta(tracker_file, directory):
    previous = open_database(tracker_file, directory)
    delta = import_data(tracker_file, directory)

    if (not delta):
        print_error('Encountered an error while importing the database. Aborted')
        write_database(tracker_file, directory, previous)
        return False

    database = open_database(tracker_file, directory)

    if (not database):
        print_error('Something went wrong opening the database. Aborted')
        write_database(tracker_file, directory, previous)
        return False

    # Tasks    
    for guid, task in previous['tasks'].items():
        if (guid not in database['tasks'].keys()):
            print_warning(f'Task {task["name"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                continue

            print('Aborted')
            write_database(tracker_file, directory, previous)
            return False

        delta_task = database['tasks'][guid]

        if (delta_task['status'] != task['status']):
            database['tasks'][guid]['status'] = task['status']
        
        if (delta_task['tracked'] != task['tracked']):
            if (task['kappaRequired'] and task['tracked'] and not delta_task['kappaRequired']):
                print_warning(f'You are currently tracking {task["name"]} which is no longer Kappa required and will be untracked. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ != 'y'):
                    print('Aborted')
                    write_database(tracker_file, directory, previous)
                    return False

                database = untrack_task(database, guid)
            elif (not task['kappaRequired'] and not task['tracked'] and delta_task['kappaRequired']):
                print_warning(f'Task {task["name"]} is now Kappa required and has been tracked. Acknowledge? (Y/N)')
                _confirmation_ = input('> ').lower()

                if (_confirmation_ != 'y'):
                    print('Aborted')
                    write_database(tracker_file, directory, previous)
                    return False
                
            elif (task['kappaRequired'] and not task['tracked']):
                print_warning(f'You had previously untracked a Kappa required task {task["name"]} which will continue to be untracked')
                database = untrack_task(database, guid)
            elif (not delta_task['tracked']):
                print_warning(f'You had previously tracked a non-Kappa task {task["name"]} which will remain tracked')
                database = track_task(database, guid)
            else:
                print_error('Unhandled error with (un)tracked tasks. Aborted')
                write_database(tracker_file, directory, previous)
                return False
                        
    print('Completed tasks delta import')
    
    # Hideout stations    
    for guid, station in previous['hideout'].items():
        if (guid not in database['hideout'].keys()):
            print_warning(f'Hideout station {station["normalizedName"]} cannot be found in the new dataset. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()

            if (_confirmation_ == 'y'):
                continue

            print('Aborted')
            write_database(tracker_file, directory, previous)
            return False

        delta_station = database['hideout'][guid]

        if (delta_station['status'] != station['status']):
            database['hideout'][guid]['status'] = station['status']
        
        if (delta_station['tracked'] != station['tracked']):
            if (station['tracked']):
                database = track_station(database, guid)
            else:
                print_warning(f'You had previously untracked hideout station {station["normalizedName"]} which will continue to be untracked')
                database = untrack_station(database, guid)

    print('Completed hideout delta import')

    # Barters
    matched_guid = False

    for previous_guid, previous_barter in previous['barters'].items():
        if (previous_guid not in database['barters'].keys()):
            for delta_guid, delta_barter in database['barters'].items():
                for previous_requirement in previous_barter['requiredItems']:
                    for delta_requirement in delta_barter['requiredItems']:
                        if (previous_requirement['item']['id'] == delta_requirement['item']['id'] and previous_requirement['count'] == delta_requirement['count']):
                            # match for this requirement
                            break
                    else:
                        # did not match this requirement, move on to next delta_barter
                        break
                    # match for this requirement, continue to next requirement
                    continue
                else:
                    # matched all requirements
                    for previous_reward in previous_barter['rewardItems']:
                        for delta_reward in delta_barter['rewardItems']:
                            if (previous_reward['item']['id'] == delta_reward['item']['id'] and previous_reward['count'] == delta_reward['count']):
                                # match for this reward
                                break
                        else:
                            # did not match this reward, move on to next delta_barter
                            break
                        # match for this reward, continue to next reward
                        continue
                    else:
                        # matched all requirements and rewards
                        print_warning(f'The GUID of barter {previous_guid} has changed. Merging data into new barter GUID {delta_guid}')
                        matched_guid = delta_guid
                        break
                    # did not match this barter, move on to next delta_barter
                    continue
            else:
                # no match found for any delta_barter
                print_warning(f'Could not find a new barter matching the following. Data for this barter will be lost!')
                display_barters(database, {previous_guid: previous_barter})
                matched_guid = False
        else:
            matched_guid = previous_guid

        if (not matched_guid):
            continue

        delta_barter = database['barters'][matched_guid]

        if (delta_barter['status'] != previous_barter['status']):
            database['barters'][matched_guid]['status'] = previous_barter['status']
        
        if (delta_barter['tracked'] != previous_barter['tracked']):
            if (previous_barter['tracked']):
                print_warning(f'You had previously tracked barter {matched_guid} which will continue to be tracked')
                database = track_barter(database, matched_guid)
            else:
                database = untrack_barter(database, matched_guid)

        if ('restarts' in previous_barter.keys() and previous_barter['restarts'] > 0):
            for _restart_ in range(previous_barter['restarts']):
                for requirement in previous_barter['requiredItems']:
                    item_guid = requirement['item']['id']
                    item_name = database['items'][item_guid]['shortName']
                    count = requirement['count']
                    database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
                    print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
                    print(f'{count} more {item_name} (NIR) now needed')
            
            database['barters'][matched_guid]['restarts'] = previous_barter['restarts']
            print(f'Barter {matched_guid} had been restarted {previous_barter["restarts"]} times. Item counts for this have been retained')
    
    print('Completed barters delta import')

    # Crafts
    matched_guid = False

    for previous_guid, previous_craft in previous['crafts'].items():
        if (previous_guid not in database['crafts'].keys()):
            for delta_guid, delta_craft in database['crafts'].items():
                for previous_requirement in previous_craft['requiredItems']:
                    for delta_requirement in delta_craft['requiredItems']:
                        if (previous_requirement['item']['id'] == delta_requirement['item']['id'] and previous_requirement['count'] == delta_requirement['count']):
                            # match for this requirement
                            break
                    else:
                        # did not match this requirement, move on to next delta_craft
                        break
                    # match for this requirement, continue to next requirement
                    continue
                else:
                    # matched all requirements
                    for previous_reward in previous_craft['rewardItems']:
                        for delta_reward in delta_craft['rewardItems']:
                            if (previous_reward['item']['id'] == delta_reward['item']['id'] and previous_reward['count'] == delta_reward['count']):
                                # match for this reward
                                break
                        else:
                            # did not match this reward, move on to next delta_craft
                            break
                        # match for this reward, continue to next reward
                        continue
                    else:
                        # matched all requirements and rewards
                        print_warning(f'The GUID of craft {previous_guid} has changed. Merging data into new craft GUID {delta_guid}')
                        matched_guid = delta_guid
                        break
                    # did not match this craft, move on to next delta_craft
                    continue
            else:
                # no match found for any delta_craft
                print_warning(f'Could not find a new craft matching the following. Data for this craft will be lost!')
                display_crafts(database, {previous_guid: previous_craft})
                matched_guid = False
        else:
            matched_guid = previous_guid

        if (not matched_guid):
            continue

        delta_craft = database['crafts'][matched_guid]

        if (delta_craft['status'] != previous_craft['status']):
            database['crafts'][matched_guid]['status'] = previous_craft['status']
        
        if (delta_craft['tracked'] != previous_craft['tracked']):
            if (previous_craft['tracked']):
                print_warning(f'You had previously tracked craft {matched_guid} which will continue to be tracked')
                database = track_craft(database, matched_guid)
            else:
                database = untrack_craft(database, matched_guid)

        if ('restarts' in previous_craft.keys() and previous_craft['restarts'] > 0):
            for _restart_ in range(previous_craft['restarts']):
                for requirement in previous_craft['requiredItems']:
                    item_guid = requirement['item']['id']
                    item_name = database['items'][item_guid]['shortName']
                    count = requirement['count']
                    database['items'][item_guid]['need_nir'] = database['items'][item_guid]['need_nir'] + count
                    print_debug(f'Adding >> {count} << of >> {item_guid} << for requirement')
                    print(f'{count} more {item_name} (NIR) now needed')
            
            database['crafts'][matched_guid]['restarts'] = previous_craft['restarts']
            print(f'Craft {matched_guid} had been restarted {previous_craft["restarts"]} times. Item counts for this have been retained')
    
    print('Completed crafts delta import')

    # Inventory
    for guid, item in previous['items'].items():
        if (guid not in database['items'].keys()):
            print_warning(f'Item {item["shortName"]} cannot be found in the new inventory. Data will be lost. Acknowledge? (Y/N)')
            _confirmation_ = input('> ').lower()
            
            if (_confirmation_ == 'y'):
                continue

            print('Aborted')
            write_database(tracker_file, directory, previous)
            return False
        
        if (database['items'][guid]['have_nir'] != item['have_nir']):
            database['items'][guid]['have_nir'] = item['have_nir']

        if (database['items'][guid]['have_fir'] != item['have_fir']):
            database['items'][guid]['have_fir'] = item['have_fir']

        if (database['items'][guid]['consumed_nir'] != item['consumed_nir']):
            database['items'][guid]['consumed_nir'] = item['consumed_nir']
        
        if (database['items'][guid]['consumed_fir'] != item['consumed_fir']):
            database['items'][guid]['consumed_fir'] = item['consumed_fir']
    
    print('Completed items delta import')

    database['notes'] = previous['notes']
    database['player_level'] = previous['player_level']
    database['refresh'] = previous['refresh']
    print('Restored player level, price refresh timeout, and notes')
    write_database(tracker_file, directory, database)
    print('Completed database delta import')
    return True

# Backup
def backup(tracker_file, directory):
    saves = get_saves(tracker_file, directory)
    
    if (('curr.null' in saves and 'prev.null' in saves and len(saves) > 4) or
        (('curr.null' in saves and 'prev.null' not in saves) or ('prev.null' in saves and 'curr.null' not in saves) and len(saves) > 5) or
        ('curr.null' not in saves and 'prev.null' not in saves and len(saves) > 6)):
        print(f'You are only allowed 5 save files. Please choose a file to overwrite!')
        _display_ = '\n'

        for index, save in enumerate(saves):
            if (index < 2):
                if (save == f'{tracker_file}.curr.bak'):
                    _save_ = 'Current autosave (1 exit ago)'
                else:
                    _save_ = 'Previous autosave (2 exits ago)'

                _display_ = _display_ + f'[{index + 1}] {_save_} (Autosave - Cannot overwrite)\n'
            else:
                _save_ = save.split('.')
                _save_[2] = datetime.strptime(_save_[2], '%Y-%m-%d').strftime('%B, %A %d, %Y')
                _save_[3] = datetime.strptime(_save_[3], '%H-%M-%S').strftime('%H:%M:%S')
                _save_ = f'{_save_[2]} at {_save_[3]}'
                _display_ = _display_ + f'[{index + 1}] {_save_}\n'

        print(_display_)
        overwrite = input('> ')

        if (not overwrite.isdigit() or int(overwrite) < 2 or int(overwrite) > len(saves)):
            print_error('Invalid overwrite argument')
            return False
        
        overwrite = saves[int(overwrite) - 1]
        print(f'Overwriting save file {overwrite}')
        remove(directory + f'\\{overwrite}')

    database = open_database(tracker_file, directory)
    filename = f'{tracker_file}.{datetime.now().strftime('%Y-%m-%d.%H-%M-%S')}.bak'
    write_database(filename, directory, database)
    print(f'Created new save file {filename}')
    return True

# Restore
def restore(tracker_file, directory):
    saves = get_saves(tracker_file, directory)
    print('Please choose a save file to restore from')
    _display_ = '\n'

    for index, save in enumerate(saves):
        if (index < 2):
            if (save == f'{tracker_file}.curr.bak'):
                _save_ = 'Current autosave (1 exit ago)'
            else:
                _save_ = 'Previous autosave (2 exits ago)'

            _display_ = _display_ + f'[{index + 1}] {_save_} (Autosave)\n'
        else:
            _save_ = save.split('.')
            _save_[2] = datetime.strptime(_save_[2], '%Y-%m-%d').strftime('%B, %A %d, %Y')
            _save_[3] = datetime.strptime(_save_[3], '%H-%M-%S').strftime('%H:%M:%S')
            _save_ = f'{_save_[2]} at {_save_[3]}'
            _display_ = _display_ + f'[{index + 1}] {_save_}\n'

    print(_display_)
    restore = input('> ')

    if (not restore.isdigit() or int(restore) > len(saves) or int(restore) < 1):
        print_error('Invalid restore argument')
        return False
    
    restore = saves[int(restore) - 1]
    print(f'Restoring from save file {restore}')
    restore_database = open_database(restore, directory)
    write_database(tracker_file, directory, restore_database)
    return True


###################################################
#                                                 #
# APP LOOP                                        #
#                                                 #
###################################################


def main(args):
    database_directory = path.expanduser('~\\AppData\\Local\\Programs\\Tart')
    app_directory = getcwd()

    if (not path.isdir(database_directory)):
        mkdir(database_directory)

    if ((len(args) > 1 and args[1] == 'debug')):
        global DEBUG
        DEBUG = True
        print_debug('Debug mode enabled')
        tracker_file = 'debug.json'
    else:
        tracker_file = 'database.json'

    if (app_directory not in environ.get('PATH')):
        user_env = subprocess.check_output(['reg', 'query', 'HKEY_CURRENT_USER\\Environment']).decode('UTF-8')
        user_env = re.sub(' +', ' ', user_env[int(user_env.find('Path')):]).replace('\r\n', '').split(' ')[2]
        user_env = user_env + ';' + app_directory
        _child_ = subprocess.run(['SETX', 'PATH', user_env], capture_output = True, text = True)

        if (_child_.stderr):
            print_error(f'Encountered an error while adjusting $env:PATH for user: {_child_.stderr}')
            return False
        else:
            print('Successfully added TART to your $env:PATH. Restart your terminal and you can now type \'tart\' to run this program!')
            return True

    print('Welcome to the TARkov Tracker (TART)! Type help for usage. Enter "import" to get started')

    while(True):
        command = input('> ')
        running = parser(tracker_file, database_directory, command)
        
        if (not running):
            print('Goodbye.')
            return True

if (__name__ == '__main__'):
    main(sys.argv)