import argparse
from ConfigParser import SafeConfigParser
import json
import logging
import os.path
import re
import requests
import sys
from itertools import takewhile

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s")

# File logging
fh = logging.FileHandler("result.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
LOG.addHandler(fh)

# Console logging
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
LOG.addHandler(ch)

parser = argparse.ArgumentParser(description='EasyImport for Redmine',
    version='1.0', add_help=True)
parser.add_argument('inputfile', action="store", type=file)
args = parser.parse_args()

api_key = ''
api_url = ''

configfile_path = os.path.join(os.path.expanduser('~'), '.redmine_easyimport')

def processConfig(configfile_path):
    global api_key
    global api_url

    parser = SafeConfigParser()
    parser.read(configfile_path)

    error_count = 0

    potential_api_url = parser.get('api_settings', 'api_url')
    if potential_api_url == '':
        printMessage.err('Configuration file needs valid api_url')
        error_count += 1
    else:
        if not potential_api_url.endswith('/'):
            potential_api_url += '/'
        api_url = potential_api_url

    potential_api_key = parser.get('api_settings', 'api_key')
    if potential_api_key == "":
        printMessage.err('Configuration file needs valid api_key')
        error_count += 1
    else:
        api_key = potential_api_key

    if error_count > 0:
        sys.exit()

def writeBlankConfig():
    try:
        with open(configfile_path, 'w') as configfile:
            configfile.write("[api_settings]\n")
            configfile.write("api_url = \n")
            configfile.write("api_key = ")
    except IOError:
        # TODO provide instruction on config file
        printMessage.err('Could not create template config file.')
        sys.exit()

try:
    with open(configfile_path) as configfile:
        # The file exists, so process it (note that we're passing the path, not the file object)
        processConfig(configfile_path)
except IOError:
    writeBlankConfig()
    LOG.warning('No config file found. Created a blank config file.')
    LOG.warning('Please edit %s and try again.', configfile_path)
    sys.exit()

def makePostRequest(path, data_payload, parameters = {}):
    headers = {
        'X-Redmine-API-Key': api_key,
        'Content-Type': 'application/json',
    }
    r = requests.post(api_url + path, params = parameters,
        data = json.dumps(data_payload), headers=headers)
    if r.status_code == requests.codes.ok or r.status_code == 201:
        return r.json()
    else:
        r.raise_for_status() # TODO remove this after testing
        return False

def makeGetRequest(path, parameters = {}):
    headers = {
        'X-Redmine-API-Key': api_key,
        'Content-Type': 'application/json',
    }
    r = requests.get(api_url + path, params = parameters, headers=headers)
    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        r.raise_for_status() # TODO remove this after testing
        return False

def allProjects():
    result = makeGetRequest('projects.json')
    # TODO could have a problem with the "limit" and "offset" if > 25 projects
    all = {}
    for project in result['projects']:
        # TODO consider accepting name OR identifier
        all[project['id']] = project['name']
    return all

def findProjectByName(search_name, projects):
    for id, name in projects.items():
        if search_name.lower() == name.lower():
            return id
    return 0

# TODO unused method?
def findIssueByName(search_name, project_issues):
    for id, issue in project_issues.items():
        if search_name.lower() == issue.lower():
            return id
    return 0

def findIssueById(check_id, project_issues):
    if check_id in project_issues:
        return id
    return 0

def projectIssues(project_id):
    # Returns open and closed tasks that are not archived
    result = makeGetRequest('issues.json?project_id=' + str(project_id))
    all = {}
    if result:
        for issue in result['issues']:
            all[issue['id']] = issue['subject']
    return all

def createIssue(project_id, subject, attributes):
    validKeys = ['project_id', 'subject', 'priority_id', 'done_ratio',
            'subproject_id', 'tracker_id', 'status_id', 'description',
            'category_id', 'fixed_version_id', 'assigned_to_id',
            'parent_issue_id', 'watcher_user_ids', 'custom_fields']

    data = {'issue': {}}
    # TODO consider passing all values as single dictionary
    #      having separate was due to AC url requirements
    data['issue']['project_id'] = project_id
    data['issue']['subject'] = subject

    for key, val in attributes.items():
        data['issue'][key] = val
    result = makePostRequest('issues.json', data)
    return result

# First, we need a dictionary of all projects (id, name)
projects = allProjects()

# We need these outside of the loop so we can reduce API queries
# because we should only need to lookup a specific project's milestones/tasks once
project_id = 0
last_depth = 0
last_issue_id = 0
error_count = 0
warning_count = 0

# We'll populate this once per project to reduce API calls
project_issues = {}

# loop through all of the lines in the input file and process them
lines = args.inputfile.read().splitlines()

i = 0
for line in lines:
    # Increase the line number by one for our user messages
    i += 1

    # Strip off beginning hyphen and space chars
    lineclean = line.lstrip('- ')

    # Blank line
    if line.strip() == '':
        LOG.info('Line %3s: Ignoring blank line', i)
        continue

    # Comment
    if line.startswith('#'):
        LOG.info('Line %3s: Ignoring commented-out line', i)
        continue

    # Project
    if not line.startswith('-'):
        # This is a project, so start fresh (clear any items)
        project_id = findProjectByName(lineclean, projects)
        if not project_id:
            LOG.error('Line %3s: Invalid project name, cannot create subitems of "%s"', i, lineclean)
            error_count += 1
        else:
            LOG.info('Line %3s: Loaded project "%s"', i, lineclean)

        issue_id = 0
        project_issues = {}

        # We've dealt with the project line, so move to next line
        continue

    # Process any attributes for this line
    attributes = {}
    matches = re.findall(' [atscpd^]=[\d-]*', lineclean)
    if matches:
        for match in matches:
            # Separate the attribute key and its value
            key, val = match.split('=')

            if key == ' ^':
                # TODO check if this is a valid parent_issue_id
                attributes['parent_issue_id'] = int(val)

            if key == ' a':
                # TODO check if this is a valid assignee id
                attributes['assigned_to_id'] = int(val)

            if key == ' t':
                # TODO check if this is a valid tracker_id
                attributes['tracker_id'] = int(val)

            if key == ' s':
                # TODO check if this is a valid status_id
                attributes['status_id'] = int(val)

            if key == ' c':
                # TODO check if this is a valid category_id
                attributes['category_id'] = int(val)

            if key == ' p':
                attributes['priority_id'] = int(val)
                if int(attributes['priority_id']) < 1 or int(attributes['priority_id']) > 5:
                    attributes['priority_id'] = 1
                    LOG.warning('Line %3s: Priority must be between 1 and 5. Setting priority of 1 (normal) for "%s"', i, lineclean)
                    warning_count += 1

            if key == ' d':
                attributes['done_ratio'] = int(val)
                if int(attributes['done_ratio']) < 0 or int(attributes['done_ratio']) > 100:
                    attributes['done_ratio'] = 0
                    LOG.warning('Line %3s: Done Ratio must be between 0 and 100. Setting done ratio to 0 for "%s"', i, lineclean)
                    warning_count += 1

            lineclean = lineclean.replace(match, '')

    # If we don't have a valid project, we can't add any subitems
    # TODO This may be redundant (see above)
    if not project_id:
        LOG.error('Line %3s: Invalid project name, could not add "%s"', i, lineclean)
        error_count += 1
        continue

    # Issue
    if line.startswith('-'):
        this_depth = sum(1 for _ in takewhile(lambda z: z == '-', line))

        if 'parent_issue_id' in attributes:
            if this_depth != 1:
                # This is a sub-issue in the structure; don't allow ^=n
                LOG.error('Line %3s: Parent (^=n) only allowed on single-hyphen lines; set parent based on import structure', i)
                del attributes['parent_issue_id']

        if last_issue_id and this_depth > last_depth and 'parent_issue_id' not in attributes:
            # We're adding a parent based on depth
            attributes['parent_issue_id'] = last_issue_id

        issue_id = 0
        issue_name = lineclean

        if 'parent_issue_id' in attributes:
            # Get all issues within the project
            project_issues = projectIssues(project_id)

            # See if a matching issue exists
            parent_issue_id = findIssueById(attributes['parent_issue_id'], project_issues)

            if not parent_issue_id:
                # No matching issue, so remove this attribute
                del attributes['parent_issue_id']
                LOG.error('Line %3s: Invalid parent issue ID; not setting parent issue ID for this issue', i, lineclean)

        # Create a new task and store its issue id for subissues
        created_issue = createIssue(project_id, issue_name, attributes)
        issue_id = created_issue['issue']['id']
        if created_issue:
            LOG.info('Line %3s: Created new issue #%d "%s"', i, issue_id, issue_name)
        else:
            LOG.error('Line %3s: Could not create issue "%s"', i, lineclean)
            error_count += 1

        last_depth = this_depth
        last_issue_id = issue_id
        continue

LOG.info('Finished processing import file')

if error_count > 0 or warning_count > 0:
    LOG.info('%d errors detected. Please view the log.', error_count)
    LOG.info('%d warnings detected. Please view the log.', warning_count)

sys.exit()

# TODO document priority_id values: 1=low, 2=normal, 3=high, 4=urgent, 5=immediate
# TODO document tracker_id values: 1=bug, 2=feature, 3=support
# TODO document status_id values: 1=new, 2=in progress, 3=resolved, 4=feedback, 5=closed
# TODO document category_id values: 1=documentation, 2=server administration

# TODO implement ^=123 to set parent task
# TODO remove duplicate issue checking functionality and require IDs if adding
#      subitems to an existing issue
# TODO allow unlimited nesting of sub-issues... push and pop to get parents
#      when number of hyphens changes
