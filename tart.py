import zipfile
import shutil
import json
import sys
import os

from git import Repo, rmtree


USAGE = '''
A simple python CLI for tracking Tarkov quests, hideout modules, needed items, and barters

USAGE: python tarkovtracker.py COMMAND [OPTION] ...

COMMANDS:
- PULL --> Pulls down latest game data from github (NOTICE: MAY CAUSE ISSUES)
- RESET [QUESTS / HIDEOUT / BARTERS / ALL] --> Resets all [QUESTS / HIDEOUT / BARTERS / ALL]
- COMPLETE/UNCOMPLETE [QUEST / HIDEOUT / BARTER NAME] --> Marks [QUEST / HIDEOUT NAME] as complete or incomplete or resets barter required items to 0
- RECURSE [QUEST / HIDEOUT NAME] --> Marks [QUEST / HIDEOUT NAME] as complete and recursively marks all required quests or hideout modules as complete
- COLLECT/UNCOLLECT [#] [ITEM SHORT NAME] --> Adds or subtracts [#] of [ITEM SHORT NAME] to appropriate quests, then modules, then barters
- FIND/UNFIND [#] [ITEM SHORT NAME] --> Adds or subtracts [#] of [ITEM SHORT NAME] to appropriate quests as FIR, then quests as collected, then modules, then barters
- TRACK/UNTRACK [QUEST / HIDEOUT NAME] --> Tracks [QUEST / HIDEOUT NAME] for item collection
- TRACK [BARTER] [NAME] [GIVE [#] [ITEM SHORT NAME]][...] [GIVE [#] [ITEM SHORT NAME]][...] --> Creates the specified barter and tracks the required items for collection
- UNTRACK [BARTER] [NAME] --> Destroys the [NAME] barter and stops tracking the required items for collection
- SEARCH [ITEM SHORT NAME / QUEST / HIDEOUT / BARTER NAME] --> Searches the database for [ITEM SHORT NAME / QUEST / HIDEOUT / BARTER NAME]
- CONTAINS [TEXT] --> Searches the database for any item, quest, hideout, or barter which contains [TEXT] (WARNING: THIS IS AN EXPENSIVE REQUEST)
- LIST [QUEST / HIDEOUT / BARTER / ALL] ITEMS --> Lists the items needed for collection for [QUESTS / HIDEOUT / BARTERS / ALL]
- LIST QUESTS [MAP / ANY / ALL / TRADER] --> Lists all eligible quests for [MAP / ANY / ALL] or all quests regardless for [TRADER]
- LIST HIDEOUT -- Lists all hideout modules
- LIST BARTERS -- Lists all tracked barters
- LIST UNTRACKED -- Lists all untracked quests and hideout modules
- REQUIRE [ITEM SHORT NAME] --> Lists all quests, modules, and barters which require [ITEM SHORT NAME]
- LEVEL [[#] / UP] --> Sets player level to [NUMBER] or increments by one

NOTES:
- Hideout modules are named as "Module name - Level N". All modules have a level starting at 1
- Inputted text does not have to include dashes, hyphens, apostrophes, commas, colons, or periods
- Avoid naming barters the same as a quest or module.. may result in unpredictable behavior
'''


DEV_MODE = False
REPO = 'https://github.com/TarkovTracker/tarkovdata.git'

if (DEV_MODE):
    TRACKER = './appdata/trackerdev.json'
else:
    TRACKER = './appdata/tracker.json'

QUESTS = './appdata/quests.json'
HIDEOUT = './appdata/hideout.json'
ITEMS = './appdata/items.en.json'
TRADERS = './appdata/traders.json'
MAPS = './appdata/maps.json'

ITEM_HEADER = '{:<25} {:<60} {:<30} {:<12}\n'.format('Item Short Name', 'Item Name', 'Item ID', 'Need (FIR)')
QUEST_HEADER = '{:<40} {:<20} {:<20} {:<20} {:<20}\n'.format('Quest Title', 'Quest Giver', 'Quest Status', 'Tracked', 'Kappa')
MODULE_HEADER = '{:<40} {:<20} {:<20}\n'.format('Module Name', 'Module Status', 'Tracked')
BARTER_HEADER = '{:<40}\n'.format('Barter Name')
BUFFER = '-------------------------------------------------------------------------------------------------------------------------------------\n'


###################################################
#                                                 #
# WORKER FUNCTIONS                                #
#                                                 #
###################################################

def read_command(command):
    command = command.lower().strip('\n')
    ran = False

    if (command == 'quit' or command == 'exit' or command == 'stop'):
        sys.exit()

    if (command == '' or command == 'help'):
        print(USAGE)

    if (command.startswith('list') and command.endswith('items')):
        ran = list_items(command)
    if (command.startswith('list quests')):
        ran = list_quests(command)
    if (command.startswith('list hideout')):
        ran = list_hideout()
    if (command.startswith('list barters')):
        ran = list_barters()
    if (command.startswith('list untracked')):
        ran = list_untracked()
    if (command.startswith('require')):
        ran = requires_item(command)
    if (command.startswith('reset quests') or command == 'reset all'):
        ran = reset_quests()
    if (command.startswith('reset hideout') or command == 'reset all'):
        ran = reset_hideout()
    if (command.startswith('reset items') or command == 'reset all'):
        ran = reset_items()
    if (command.startswith('reset barters') or command == 'reset all'):
        ran = reset_barters()
    if (command.startswith('complete') or command.startswith('uncomplete')):
        ran = complete(command)
    if (command.startswith('recurse')):
        ran = recurse(command)
    if (command.startswith('find') or command.startswith('unfind')):
        ran = collect(command, True)
    if (command.startswith('collect') or command.startswith('uncollect')):
        ran = collect(command, False)
    if (command.startswith('track') or command.startswith('untrack')):
        ran = track(command)
    if (command.startswith('search')):
        ran = search(command, False)
    if (command.startswith('contains')):
        ran = search(command, True)
    if (command.startswith('level')):
        ran = set_level(command)
    if (command.startswith('pull')):
        ran = pull_repo()
    if (not ran):
        print('Command not recognized or run failed. Type "help" for usage')
    return

def read_file(readme):
    try:
        with open(readme, 'r', encoding = 'utf-8') as readfile:
            file = json.load(readfile)
    except FileNotFoundError:
        if (readme == TRACKER):
            write_file(TRACKER, {
                'quests': [],
                'hideout': [],
                'barters': [],
                'level': 0
            })
            file = read_file(TRACKER)
        else: raise FileNotFoundError
    return file

def write_file(writeme, data):
    with open(writeme, 'w', encoding = 'utf-8') as writefile:
        writefile.write(json.dumps(data))
    return

def normalize(string, chars = "-:',. "):
    for char in chars:
        string = string.replace(char, '')
    
    return ' '.join(string.lower().split())

def duplicates(duplicates):
    print('More than one item found which matches your selection. Please select an item with its corresponding number\n')

    for index, duplicate in enumerate(duplicates):
        print(f'[{index}] {duplicate["name"]}')

    return duplicates[int(input('\ntart > '))]['id']

def item_to_guid(name):
    items = read_file(ITEMS)
    found = []

    for item in items.values():
        if (normalize(item['shortName']) == normalize(name) or normalize(item['name']) == normalize(name)):
            found.append(item)
    
    if (len(found) > 1):
        return duplicates(found)
    elif (len(found) == 1):
        return found[0]['id']
    else:
        return {
            'return': False,
            'reason': f'Could not find >{name}<'
        }

def guid_to_item(guid):
    items = read_file(ITEMS)

    for item in items.values():
        if (item['id'] == guid):
            return item['shortName']
    
    return guid

def increment(to_add, have, max):
    need = max - have

    if (to_add > need or to_add == need):
        to_add = to_add - need
        have = max
    else:
        have = have + to_add
        to_add = 0

    return to_add, have

def decrement(to_sub, have):
    if (to_sub > have or to_sub == have):
        to_sub = to_sub - have
        have = 0
    else:
        have = have - to_sub
        to_sub = 0
    
    return to_sub, have

def location_lookup(query):
    maps = read_file(MAPS)

    for map in maps.values():
        if (map['id'] == query):
            return map['locale']['en']

def item_lookup(query, fuzzy = False, contains = False):
    items = read_file(ITEMS)
    tracker = read_file(TRACKER)
    result = []

    for item in items.values():
        item['find'] = item['collect'] = 0

        if (item['id'] in ('5696686a4bdc2da3298b456a', '569668774bdc2da2298b4568', '5449016a4bdc2d6f028b456f')):
            continue

        if (fuzzy):
            if (contains):
                if (normalize(query) in normalize(item['shortName']) or normalize(query) in normalize(item['name'])):
                    result.append(item)
            else:
                if (normalize(item['shortName']).startswith(normalize(query)) or normalize(item['name']).startswith(normalize(query))):
                    result.append(item)
        else:
            if (normalize(item['shortName']) == normalize(query) or normalize(item['name']) == query):
                result.append(item)

    for item in result:
        quests = get_quests_containing_GUID(item['id'])
        modules = get_modules_containing_GUID(item['id'])
        barters = get_barters_containing_GUID(item['id'])

        for quest in quests:
            quest = tracker['quests'][quest]

            for objective in quest['objectives']:
                if (objective['target'] == item['id'] and objective['type'] == 'find'):
                    item['find'] = item['find'] + (objective['number'] - objective['have'])
                elif (objective['target'] == item['id'] and objective['type'] == 'collect'):
                    item['collect'] = item['collect'] + (objective['number'] - objective['have'])

        for module in modules:
            module = tracker['hideout'][module]

            for require in module['require']:
                if (require['target'] == item['id']):
                    item['collect'] = item['collect'] + (require['number'] - require['have'])
        
        for barter in barters:
            barter = tracker['barters'][barter]

            for require in barter['require']:
                if (require['target'] == item['id']):
                    item['collect'] = item['collect'] + (require['number'] - require['have'])

    return result

def quest_lookup(query, fuzzy = False, contains = False):
    tracker = read_file(TRACKER)
    result = []

    for index, quest in enumerate(tracker['quests']):
        if (fuzzy):
            if (contains):
                if (normalize(query) in normalize(quest['title'])):
                    result.append(index)
            else:
                if (normalize(quest['title']).startswith(normalize(query))):
                    result.append(index)
        else:
            if (normalize(quest['title']) == normalize(query)):
                return index

    if (len(result) > 0):
        return result

    return {
        'return': False,
        'reason': f'Could not find quest >{query}<'
    }

def module_lookup(query, fuzzy = False, contains = False):
    tracker = read_file(TRACKER)
    result = []

    for index, module in enumerate(tracker['hideout']):
        if (fuzzy):
            if (contains):
                if (normalize(query) in normalize(module['name'])):
                    result.append(index)
            else:
                if (normalize(module['name']).startswith(normalize(query))):
                    result.append(index)
        else:
            if (normalize(module['name']) == normalize(query)):
                return index

    if (len(result) > 0):
        return result

    return {
        'return': False,
        'reason': f'Could not find module >{query}<'
    }

def barter_lookup(query, fuzzy = False, contains = False):
    tracker = read_file(TRACKER)
    result = []

    for index, barter in enumerate(tracker['barters']):
        if (fuzzy):
            if (contains):
                if (normalize(query) in normalize(barter['name'])):
                    result.append(index)
            else:
                if (normalize(barter['name']).startswith(normalize(query))):
                    result.append(index)
        else:
            if (normalize(barter['name']).startswith(normalize(query))):
                result.append(index)

    if (len(result) > 0):
        return result

    return {
        'return': False,
        'reason': f'Could not find barter >{query}<'
    }

def prereq_check(quest):
    tracker = read_file(TRACKER)
    prereqs = quest['require']['quests']

    if ('level' in quest['require'] and quest['require']['level'] > tracker['level']):
        return False

    for prereq in prereqs:
        for prereq_quest in tracker['quests']:
            if (prereq_quest['id'] == prereq and prereq_quest['status'] == 'Incomplete'):
                return False
    
    return True

def recurse_prereqs(prereq, objects_to_complete):
    tracker = read_file(TRACKER)

    if (type(prereq) is int):
        for index, quest in enumerate(tracker['quests']):
            if (quest['id'] == prereq):
                objects_to_complete.append(index)

                for prereq in quest['require']['quests']:
                    objects_to_complete = recurse_prereqs(prereq, objects_to_complete)
                
                break
    else:
        for index, module in enumerate(tracker['hideout']):
            if (normalize(module['name']) == normalize(prereq)):
                objects_to_complete.append(index)

                for prereq in module['require']:
                    if (prereq['type'] == 'module'):
                        objects_to_complete = recurse_prereqs(f'{prereq["target"]} - Level {prereq["number"]}', objects_to_complete)
                
                break
    
    return objects_to_complete

def create_barter(command):
    barter = {
        'name': ' '.join(command[2:command.index('give')]),
        'require': [],
        'receive': []
    }
    command = command[command.index('give'):]
    end = len(command) - 1
    barter_item = []

    if (barter['name'] == ''):
        return {
            'return': False,
            'reason': f'Cannot take empty name for barter'
        }

    for index, word in enumerate(command):
        if (word == 'get' or word == 'give' or index == end):
            if (index == end):
                barter_item.append(word)

            if (len(barter_item) != 0):
                number = int(barter_item[1])
                target = item_to_guid(normalize(' '.join(barter_item[2:])))

                if (type(target) is dict):
                    return target

                if (barter_item[0] == 'give'):
                    barter['require'].append({
                        'number': number,
                        'target': target,
                        'have': 0
                    })
                else:
                    barter['receive'].append({
                        'number': number,
                        'target': target
                    })
            barter_item = [word]
            continue
        barter_item.append(word)

    tracker = read_file(TRACKER)
    tracker['barters'].append(barter)
    write_file(TRACKER, tracker)
    return {
        'return': True,
        'reason': f'Started tracking barter >{barter["name"]}<'
    }

def destroy_barter(command):
    tracker = read_file(TRACKER)
    query = ' '.join(command[2:])
    barter = barter_lookup(query)

    if (type(barter) is dict):
        return barter

    barter = tracker['barters'][barter]
    tracker['barters'] = tracker['barters'].remove(barter)
    
    if (tracker['barters'] is None):
        tracker['barters'] = []

    write_file(TRACKER, tracker)
    return {
        'return': True,
        'reason': f'Stopped tracking barter >{barter["name"]}<'
    }

def get_quests_containing_GUID(guid):
    tracker = read_file(TRACKER)
    quests = []

    for index, quest in enumerate(tracker['quests']):
        if (quest['status'] == 'Complete' or quest['tracked'] == 'Untracked'):
            continue

        for objective in quest['objectives']:
            if (objective['target'] == guid):
                quests.append(index)
    
    return quests

def get_modules_containing_GUID(guid):
    tracker = read_file(TRACKER)
    modules = []

    for index, module in enumerate(tracker['hideout']):
        if (module['status'] == 'Complete' or module['tracked'] == 'Untracked'):
            continue

        for require in module['require']:
            if (require['target'] == guid):
                modules.append(index)
    
    return modules

def get_barters_containing_GUID(guid):
    tracker = read_file(TRACKER)
    barters = []

    for index, barter in enumerate(tracker['barters']):
        for require in barter['require']:
            if (require['target'] == guid):
                barters.append(index)
    
    return barters

def get_quest_items():
    tracker = read_file(TRACKER)
    items = {}

    for quest in tracker['quests']:
        if (quest['status'] == 'Complete' or quest['tracked'] == 'Untracked'):
            continue

        for objective in quest['objectives']:
            if (objective['target'] in ('5696686a4bdc2da3298b456a', '569668774bdc2da2298b4568', '5449016a4bdc2d6f028b456f')):
                continue

            if (objective['type'] == 'find'):
                if (objective['target'] in items):
                    items[objective['target']]['find'] = items[objective['target']]['find'] + objective['number'] - objective['have']
                else:
                    value = {
                        'find': objective['number'] - objective['have'],
                        'collect': 0
                    }
                    items[objective['target']] = value
            elif (objective['type'] == 'collect'):
                if (objective['target'] in items):
                    items[objective['target']]['collect'] = items[objective['target']]['collect'] + objective['number'] - objective['have']
                else:
                    value = {
                        'find': 0,
                        'collect': objective['number'] - objective['have']
                    }
                    items[objective['target']] = value

    return items

def get_hideout_items():
    tracker = read_file(TRACKER)
    items = {}

    for module in tracker['hideout']:
        if (module['status'] == 'Complete' or module['tracked'] == 'Untracked'):
            continue

        for require in module['require']:
            if (require['target'] in ('5696686a4bdc2da3298b456a', '569668774bdc2da2298b4568', '5449016a4bdc2d6f028b456f') or require['type'] != 'item'):
                continue

            if (require['target'] in items):
                items[require['target']]['collect'] = items[require['target']]['collect'] + require['number'] - require['have']
            else:
                value = {
                    'find': 0,
                    'collect': require['number'] - require['have']
                }
                items[require['target']] = value

    return items

def get_barter_items():
    tracker = read_file(TRACKER)
    items = {}

    for barter in tracker['barters']:
        for require in barter['require']:
            if (require['target'] in ('5696686a4bdc2da3298b456a', '569668774bdc2da2298b4568', '5449016a4bdc2d6f028b456f')):
                continue

            if (require['target'] in items):
                items[require['target']]['collect'] = items[require['target']]['collect'] + require['number'] - require['have']
            else:
                value = {
                    'find': 0,
                    'collect': require['number'] - require['have']
                }
                items[require['target']] = value

    return items

def get_quests_by_location(query):
    maps = read_file(MAPS)
    tracker = read_file(TRACKER)
    quests = []

    if (query == 'all'):
        id = 99
    elif (query == 'other'):
        id = -1

    for map in maps.values():
        if (normalize(map['locale']['en']) == normalize(query)):
            id = map['id']
            break
    else:
        return False
    
    for index, quest in enumerate(tracker['quests']):
        if (quest['tracked'] == 'Tracked' and quest['status'] == 'Incomplete' and prereq_check(quest)):
            for objective in quest['objectives']:
                if (('location' in objective and (objective['location'] == id or objective['location'] is None and id == -1)) or id == 99):
                    quests.append(index)
                    break

    return quests

def get_quests_by_trader(query):
    tracker = read_file(TRACKER)
    quests = []

    for index, quest in enumerate(tracker['quests']):
        if (quest['status'] == 'Incomplete' and normalize(quest['giver']) == normalize(query)):
            quests.append(index)

    return quests

def print_item(item, string):
    string = string + '{:<25} {:<60} {:<30} {:<12}\n'.format(item['shortName'], item['name'], item['id'], f'{item["collect"]} ({item["find"]})')
    return string

def print_quest(quest, string):
    string = string + '{:<40} {:<20} {:<20} {:<20} {:<20}\n'.format(quest['title'], quest['giver'], quest['status'], quest['tracked'], quest['kappa'])

    for objective in quest['objectives']:
        target = objective['target']

        if (type(target) is list):
            targets = ''

            for index, trgt in enumerate(target):
                targets = targets + guid_to_item(trgt)

                if (index != len(target) -1 ):
                    targets = targets + ' or '

            target = targets
        elif (type(target) is int):
            traders = read_file(TRADERS)
            target = int(target)
            
            for trader in traders.values():
                if (trader['id'] == target):
                    target = trader['locale']['en']
        else:
            target = guid_to_item(target)

        string = string + f'--> {objective["type"]}'

        if (objective['type'] in ('collect', 'find', 'kill', 'place')):
            string = string + f' {objective["number"]}'

        string = string + f' {target}'

        if ('location' in objective and objective['location'] != -1):
            string = string + f' on {location_lookup(objective["location"])}'

        if ('with' in objective):
            string = string + f' with {objective["with"]}'
        
        string = string + '\n'

    return string + '\n'

def print_module(module, string):
    string = string + '{:<40} {:<20} {:<20}\n'.format(module['name'], module['status'], module['tracked'])

    for require in module['require']:
        if (require['type'] != 'item'):
            continue
        
        string = string + f'--> Collect {require["number"]} {guid_to_item(require["target"])}\n'

    string = string + '\n'
    return string

def print_barter(barter, string):
    string = string + '{:<40}\n'.format(barter['name'])

    for require in barter['require']:
        string = string + f'--> Collect {require["number"]} {guid_to_item(require["target"])}\n'
    
    for receive in barter['receive']:
        string = string + f'--> Receive {receive["number"]} {guid_to_item(receive["target"])}\n'

    string = string + '\n'
    return string

def print_item_list(item_list, string):
    row = 1

    for item in item_list:
        if (item['collect'] != 0 and item['find'] != 0):
            need = f'{item["collect"]} ({item["find"]})'
        elif (item['collect'] == 0 and item['find'] != 0):
            need = f'({item["find"]})'
        else:
            need = item['collect']
            
        string = string + '{:<20} {:<10} '.format(guid_to_item(item['guid']), need)
        
        if (row == 3):
            string = string.strip(' ') + '\n'
            row = 1
        else:
            row = row + 1
        
    return string


###################################################
#                                                 #
# HANDLER FUNCTIONS                               #
#                                                 #
###################################################

def reset_quests():
    new_quests = []
    default_quests = read_file(QUESTS)
    traders = read_file(TRADERS)

    for default_quest in default_quests:
        new_quest = {
            'id': default_quest['id'],
            'status': 'Incomplete',
            'giver': default_quest['giver'],
            'require': {
                'quests': default_quest['require']['quests']
            },
            'title': default_quest['title'],
            'tracked': 'Tracked',
            'kappa': 'Yes',
            'objectives': []
        }

        if ('level' in default_quest['require'] and default_quest['require']['level'] is not None):
            new_quest['require']['level'] = default_quest['require']['level']
        else:
            new_quest['require']['level'] = 0

        if ('nokappa' in default_quest and default_quest['nokappa']):
            new_quest['tracked'] = 'Untracked'
            new_quest['kappa'] = 'No'

        for default_objective in default_quest['objectives']:
            new_objective = {
                'type': default_objective['type'],
                'target': default_objective['target'],
                'number': default_objective['number']
            }

            if (new_objective['type'] == 'collect' or new_objective['type'] == 'find'):
                new_objective['have'] = 0

            if ('location' in default_objective):
                new_objective['location'] = default_objective['location']

            if ('with' in default_objective):
                new_objective['with'] = default_objective['with']

            new_quest['objectives'].append(new_objective)

        for trader in traders.values():
            if (new_quest['giver'] == trader['id']):
                new_quest['giver'] = trader['locale']['en']
    
        new_quests.append(new_quest)

    tracker = read_file(TRACKER)
    old_quests = tracker['quests']

    for old_quest in old_quests:
        for new_quest in new_quests:
            if (old_quest['id'] == new_quest['id']):
                for old_objective in old_quest['objectives']:
                    for new_objective in new_quest['objectives']:
                        if (old_objective['type'] == new_objective['type'] and old_objective['target'] == new_objective['target'] and 'have' in old_objective):
                            new_objective['have'] = old_objective['have']
                            break
                break

    tracker['quests'] = new_quests
    tracker['level'] = 1
    write_file(TRACKER, tracker)
    print('Reset all quests to current loaded defaults')
    return True

def reset_hideout():
    new_hideout = []
    default_hideout = read_file(HIDEOUT)['modules']

    for default_module in default_hideout:
        new_module = {
            'id': default_module['id'],
            'status': 'Incomplete',
            'require': [],
            'name': f'{default_module["module"]} - Level {default_module["level"]}',
            'tracked': 'Tracked'
        }

        if (new_module['id'] == 37):
            new_module['status'] = 'Complete'

        if (new_module['id'] == 5):
            new_module['tracked'] = 'Untracked'

        for default_requirement in default_module['require']:
            new_requirement = {
                'type': default_requirement['type'],
                'target': default_requirement['name'],
                'number': default_requirement['quantity'],
                'have': 0
            }
            new_module['require'].append(new_requirement)

        new_hideout.append(new_module)

    tracker = read_file(TRACKER)
    old_hideout = tracker['hideout']

    for old_module in old_hideout:
        for new_module in new_hideout:
            if (old_module['id'] == new_module['id']):
                for old_require in old_module['require']:
                    for new_require in new_module['require']:
                        if (old_require['target'] == new_require['target']):
                            new_require['have'] = old_require['have']
                            break
                break

    tracker['hideout'] = new_hideout
    write_file(TRACKER, tracker)
    print('Reset all hideout modules to current loaded defaults')
    return True

def reset_items():
    tracker = read_file(TRACKER)

    for quest in tracker['quests']:
        for objective in quest['objectives']:
            if ('have' in objective):
                objective['have'] = 0
    
    for module in tracker['hideout']:
        for require in module['require']:
            if ('have' in require):
                require['have'] = 0

    for barter in tracker['barters']:
        for require in barter['require']:
            require['have'] = 0

    write_file(TRACKER, tracker)
    print('Reset all collected and found items to zero')
    return True

def reset_barters():
    tracker = read_file(TRACKER)
    tracker['barters'] = []
    write_file(TRACKER, tracker)
    print('Reset all tracked barters, please manually add barters with the TRACK command')
    return True

def complete(command):
    command = command.split(' ')
    query = ' '.join(command[1:])
    tracker = read_file(TRACKER)
    quest = quest_lookup(query)
    module = module_lookup(query)
    barter = barter_lookup(query)

    if (type(quest) is not dict):
        quest = tracker['quests'][quest]

        if (command[0] == 'complete'):
            quest['status'] = 'Complete'
            print(f'Completed >{quest["title"]}<')
        else:
            quest['status'] = 'Incomplete'
            print(f'Incompleted >{quest["title"]}<')
    elif (type(module) is not dict):
        module = tracker['hideout'][module]

        if (command[0] == 'complete'):
            module['status'] = 'Complete'
            print(f'Completed >{module["name"]}<')
        else:
            module['status'] = 'Incomplete'
            print(f'Incompleted >{module["name"]}<')
    elif (type(barter) is not dict):
        barter = tracker['barters'][barter]

        for require in barter['require']:
            require['have'] = 0

        print(f'Reset all required items to 0 for >{barter["name"]}<')
    else:
        print(f'Could not find a match for >{query}<')
        return True
                
    write_file(TRACKER, tracker)
    return True

def recurse(command):
    command = command.split(' ')
    query = ' '.join(command[1:])
    tracker = read_file(TRACKER)
    quest = quest_lookup(query)
    module = module_lookup(query)
    quests = modules = []

    if (type(quest) is not dict):
        quests.append(quest)
        root = tracker['quests'][quest]

        for child in root['require']['quests']:
            quests = recurse_prereqs(child, quests)

        for quest in quests:
            tracker['quests'][quest]['status'] = 'Complete'

        print(f'Recursively completed all quests required to reach >{query}<, including itself')
    elif (type(module) is not dict):
        modules.append(module)
        root = tracker['hideout'][module]

        for child in root['require']:
            if (child['type'] == 'module'):
                modules = recurse_prereqs(f'{child["target"]} - Level {child["number"]}', modules)

        for module in modules:
            tracker['hideout'][module]['status'] = 'Complete'

        print(f'Recursively completed all modules required to reach >{query}<, including itself')
    else:
        print(f'Could not find a match for >{query}<')
        return True

    write_file(TRACKER, tracker)
    return True

def track(command):
    command = command.split(' ')

    if (command[1] == 'barter'):
        if (command[0] == 'track'):
            result = create_barter(command)
            print(result['reason'])
            return True
        else:
            result = destroy_barter(command)
            print(result['reason'])
            return True
    else:
        tracker = read_file(TRACKER)
        query = ' '.join(command[1:])
        quest = quest_lookup(query)
        module = module_lookup(query)

        if (type(quest) is not dict):
            quest = tracker['quests'][quest]

            if (command[0] == 'track'):
                quest['tracked'] = 'Tracked'
                print(f'Tracked >{quest["title"]}<')
            else:
                quest['tracked'] = 'Untracked'
                print(f'Untracked >{quest["title"]}<')
        elif (type(module) is not dict):
            module = tracker['hideout'][module]

            if (command[0] == 'track'):
                module['tracked'] = 'Tracked'
                print(f'Tracked >{module["name"]}<')
            else:
                module['tracked'] = 'Untracked'
                print(f'Untracked >{module["name"]}<')
        else:
            print(f'Could not find a match for >{query}<')
                    
        write_file(TRACKER, tracker)
        return True

def collect(command, fir):
    command = command.split(' ')
    tracker = read_file(TRACKER)
    item = ' '.join(command[2:])
    guid = item_to_guid(item)

    if ('return' in guid):
        print(f'Failed to find or collect item. {guid["reason"]}')
        return True

    quests = get_quests_containing_GUID(guid)
    modules = get_modules_containing_GUID(guid)
    barters = get_barters_containing_GUID(guid)

    try:
        const = number = int(command[1])
    except:
        print(f'Could not understand inputted number >{command[1]}<')
        return True

    if (fir):
        for quest in quests:
            quest = tracker['quests'][quest]

            for objective in quest['objectives']:
                if (objective['type'] == 'find' and objective['target'] == guid):
                    if (command[0] == 'find'):
                        number, objective['have'] = increment(number, objective['have'], objective['number'])
                    else:
                        number, objective['have'] = decrement(number, objective['have'])
    
    for quest in quests:
        quest = tracker['quests'][quest]

        for objective in quest['objectives']:
            if (objective['type'] == 'collect' and objective['target'] == guid):
                if (command[0] == 'collect'):
                    number, objective['have'] = increment(number, objective['have'], objective['number'])
                else:
                    number, objective['have'] = decrement(number, objective['have'])
    
    for module in modules:
        module = tracker['hideout'][module]

        for require in module['require']:
            if (require['target'] == guid):
                if (command[0] == 'collect' or command[0] == 'find'):
                    number, require['have'] = increment(number, require['have'], require['number'])
                else:
                    number, require['have'] = decrement(number, require['have'])
            
    for barter in barters:
        barter = tracker['barters'][barter]

        for require in barter['require']:
            if (require['target'] == guid):
                if (command[0] == 'collect' or command[0] == 'find'):
                    number, require['have'] = increment(number, require['have'], require['number'])
                else:
                    number, require['have'] = decrement(number, require['have'])

    if (number == const):
        print(f'Nothing to be done')
        return True

    write_file(TRACKER, tracker)

    if (command[0] == 'collect' or command[0] == 'find'):
        print(f'Added {const - number} of {item}')
    else:
        print(f'Removed {const - number} of {item}')

    return True

def search(command, contains):
    if (contains):
        print('WARNING: This is an expensive function which may return excessive results. Continue? [Y/(N)]')

        if (input('tart > ').lower() == 'y'):
            pass
        else:
            return True

    query = ' '.join(command.split(' ')[1:])
    tracker = read_file(TRACKER)
    items = item_lookup(query, True, contains)
    quests = quest_lookup(query, True, contains)
    modules = module_lookup(query, True, contains)
    barters = barter_lookup(query, True, contains)
    display = ''

    if (type(items) is not dict and len(items) != 0):
        display = display + ITEM_HEADER + BUFFER

        for item in items:
            display = print_item(item, display)
        
        display = display + '\n'

    if (type(quests) is not dict and len(quests) != 0):
        display = display + QUEST_HEADER + BUFFER

        for quest in quests:
            display = print_quest(tracker['quests'][quest], display)

    if (type(modules) is not dict and len(modules) != 0):
        display = display + MODULE_HEADER + BUFFER

        for module in modules:
            display = print_module(tracker['hideout'][module], display)

    if (type(barters) is not dict and len(barters) != 0):
        display = display + BARTER_HEADER + BUFFER

        for barter in barters:
            display = print_barter(tracker['barters'][barter], display)
    
    if (display == ''):
        print(f'Nothing could be found for >{query}<')
        return True

    print('\n' + display)
    return True

def list_items(command):
    query = command.split(' ')[1]
    quests = hideout = barters = {}
    all = []

    if (query == 'quest' or query == 'all'):
        quests = get_quest_items()

    if (query == 'hideout' or query == 'all'):
        hideout = get_hideout_items()

    if (query == 'barter' or query == 'all'):
        barters = get_barter_items()

    for items in (quests, hideout, barters):
        for key, value in items.items():
            for item in all:
                if (item['guid'] == key):
                    item['find'] = item['find'] + value['find']
                    item['collect'] = item['collect'] + value['collect']
                    item['total'] = item['find'] + item['collect']
                    break
            else:
                all.append({
                    'find': value['find'],
                    'collect': value['collect'],
                    'total': value['find'] + value['collect'],
                    'guid': key
                })

    if (len(all) == 0):
        print('No items needed')
        return True

    display = '{:<20} {:<10} {:<20} {:<10} {:<20} {:<10} \n'.format('Item Short Name', 'Need (FIR)', 'Item Short Name', 'Need (FIR)', 'Item Short Name', 'Need (FIR)') + BUFFER
    display = print_item_list(sorted(all, key = lambda item: item['total'], reverse = True), display)
    print(display)
    return True

def list_quests(command):
    command = command.split(' ')
    query = ' '.join(command[2:])
    display = QUEST_HEADER + BUFFER
    quests = get_quests_by_location(query)
    tracker = read_file(TRACKER)

    if (not quests):
        quests = get_quests_by_trader(query)

    for quest in quests:
        quest = tracker['quests'][quest]
        display = print_quest(quest, display)

    if (display == QUEST_HEADER + BUFFER):
        print('No quests found')
        return True

    print(display)
    return True

def list_hideout():
    tracker = read_file(TRACKER)
    display = MODULE_HEADER + BUFFER

    for module in tracker['hideout']:
        if (module['status'] == 'Incomplete' and module['tracked'] == 'Tracked'):
            display = print_module(module, display)
    
    if (display == MODULE_HEADER + BUFFER):
        print('No modules to list')
        return True
    
    print(display)
    return True

def list_barters():
    tracker = read_file(TRACKER)
    display = BARTER_HEADER + BUFFER

    for barter in tracker['barters']:
        display = print_barter(barter, display)
    
    if (display == BARTER_HEADER + BUFFER):
        print('No barters to list')
        return True
    
    print(display)
    return True

def list_untracked():
    tracker = read_file(TRACKER)
    display = QUEST_HEADER + BUFFER

    for quest in tracker['quests']:
        if (quest['tracked'] == 'Untracked'):
            display = print_quest(quest, display)
    
    display = display + MODULE_HEADER + BUFFER

    for module in tracker['hideout']:
        if (module['tracked'] == 'Untracked'):
            display = print_module(module, display)

    if (display == QUEST_HEADER + BUFFER):
        print('Nothing untracked to list')
        return True
    
    print(display)
    return True

def requires_item(command):
    command = command.split(' ')
    query = ' '.join(command[1:])
    guid = item_to_guid(query)
    tracker = read_file(TRACKER)
    display = ''

    if (type(guid) is dict):
        print(guid['reason'])
        return True
    
    quests = get_quests_containing_GUID(guid)
    modules = get_modules_containing_GUID(guid)
    barters = get_barters_containing_GUID(guid)

    if (len(quests) != 0):
        display = display + QUEST_HEADER + BUFFER

        for quest in quests:
            quest = tracker['quests'][quest]
            display = print_quest(quest, display)

    if (len(modules) != 0):
        display = display + MODULE_HEADER + BUFFER

        for module in modules:
            module = tracker['hideout'][module]
            display = print_module(module, display)

    if (len(barters) != 0):
        display = display + BARTER_HEADER + BUFFER

        for barter in barters:
            barter = tracker['barters'][barter]
            display = print_barter(barter, display)

    if (display == ''):
        print(f'Nothing found which requires >{query}<')
        return True
    
    print(display)
    return True

def set_level(command):
    command = command.split(' ')
    tracker = read_file(TRACKER)

    if (command[1] == 'up'):
        tracker['level'] = tracker['level'] + 1
    else:
        tracker['level'] = int(command[1])

    print(f'Set player level to {tracker["level"]}')
    write_file(TRACKER, tracker)
    return True

def pull_repo():
    print('\nWARNING! This will delete all existing application data, including any data you have entered.')
    print('\nWARNING! This may break the application!')

    if (input('\nProceed? Y/N > ').lower() != 'y'):
        print('Aborted!')
        return False
    
    if (os.path.exists('./appdata')):
        print('Clearing all application data...')
        shutil.rmtree('./appdata')
        print('Cleared.')
    
    print('Pulling latest game data from github... ', end = '', flush = True)
    repo = Repo.clone_from(REPO, './temp')

    assert not repo.bare

    with open('./temp/repo.zip', 'wb') as archive:
        repo.archive(archive, format = 'zip')
        archive.close()

    with zipfile.ZipFile('./temp/repo.zip', 'r') as archive:
        archive.extractall('./appdata')
        archive.close()

    repo.close()
    rmtree('./temp')
    print(f'done. Pulled files from {REPO}')
    return True

###################################################
#                                                 #
# MAIN FUNCTION                                   #
#                                                 #
###################################################

def main():
    if (DEV_MODE):
        print('DEV MODE ENABLED')

    while(True):
        command = input('tart > ')
        read_command(command)

if (__name__ == '__main__'):
    main()