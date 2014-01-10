EasyImport for Redmine
=============

## Description

EasyImport for Redmine makes it easy to import issues into Redmine.

## Features

- Only supports existing projects
- Does not modify existing objects (just adds items and sub-items)
- Looks up existing items by title. If title matches exactly, subitems will be added to the existing item.
- Prevents duplicate issues at the project-level
- Prevents duplicate sub-issues
- Set assignee, tracker, status, category, priority, and done-ratio independently on each item
- Allows nesting of issues as many levels deep as you need (assuming Redmine doesn't have a limitation)
- You can add sub-issues to issues that are already in Redmine before the import (see ^=n in *Attributes and values*)

## Usage

### Setup
This script requires a configuration file. The script will automatically create this for you the first time you run the script with a valid import file (see *How to use the script*). Here's an example of the output:

> [WARNING ] No config file found. Created a blank config file.
> 
> [WARNING ] Please edit /Users/adam/.redmine_easyimport and try again.

You must open this new file and add an API url (your Redmine url) and an API key (find this in your Redmine user settings).

### How to use the script
Please run the script with `-h` to show how to use the script.
> `python redmine_easyimport.py -h`

The script only requires one argument, which is the path to an import file (explained below).
> `python redmine_easyimport.py myimportfile.txt`

## Import Files
This script is called EasyImport for a reason! It's meant to be a very simple way to import issues into projects.

* Each separate project, issue, or sub-issue must be on its own line
* Issues must have a parent project line (see *Import file example*)
* How you begin the line determines what type of item you're importing (see *Character Table*)
* Each line may accept various attributes like *Assignee ID* and *Priority ID* (see *Attributes and values*)
* When a project line is read, all issues following, until the next project line is read, will be added under that project.
* You may include a space after the opening characters if you'd like (shown in "Paint" example below)

### Character Table

| Begin line with                             | type          | handling                     |
| --------------------------------------------| -----------   | ---------------------------- |
| `#`                                         | Comment       | ignore line                  |
| First character is anything but `#` and `-` | Project       | title lookup only (required) |
| `-`                                         | Issue         | create only                  |
| `--`                                        | Sub-issue     | create only                  |
| `---`                                       | Sub-sub-issue | create only                  |
| `etc...`                                    | etc...        | create only                  |

### Attributes and values

- Set assignee ID with: a=*n*
- Set tracker ID with: t=*n*
- Set status ID with: s=*n*
- Set category ID with: c=*n*
- Set priority ID with: p=*n*
- Set done-ratio with: d=*n* (e.g., use "55" for 55% done)
- Set parent issue ID with: ^=*n*
  - This only works for top-level issues (one hyphen) see Paint example below

Note 1: all of the "ID" attributes require integer values. e.g., a=5

Note 2: each attribute must have a space before it, and no spaces before or after the "=" sign

## Import file example

    # Import File Demo
    # Blank lines are OK and may make it easy to visually separate projects

    Clean
    -Clean attic a=5 p=5 d=75
    --Throw away as much as possible d=80
    --Donate clothes to Goodwill p=1 t=2
    --Clean basement
    --Clean shed p=2
    
    # This first issue below will be a child of issue 234.
    # The two bedrooms will be grandchildren of issue 234.
    # "Ceiling" hierarchy: Paint > Upstairs > Kids bedroom > Ceiling

    Paint
    - Upstairs ^=234
    -- Master bedroom t=2
    -- Kids bedroom p=4
    --- Ceiling a=6
    --- Walls a=6 t=1
    --- Closet a=6

## Future plans
- Fix TODO items in code
- Attribute lookups to verify validity
- Rework how attributes work
  - current setup only works with integers
  - it'd be nice to set the issue ""description", for example
- Support multiple levels of subtasks

## Disclaimer
Please try out the importer on a test project until you are comfortable with how it works.

Note: this utility does not perform any explicit issue deletion or issue update operations, though it can create sub-issues within existing issues, so use with care.
