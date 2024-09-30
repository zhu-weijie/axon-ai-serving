# Change Log

## Version v1.1.2

- Added `python manage.py migrate` command to the upgrade process.

## Version v1.1.1

- Fixed an issue where p900upgrade can not identify the old upgrade flag file.

## Version v1.1.0

- Added the ability to allow the upgrade file names to contain version numbers and other information, provided that the upgrade file name must include either "p900master" or "p900webserver" to be valid for the upgrade process.
- Removed killing pid steps before replacing the upgrade file.

## Version v1.0.0

- Added basic functionality to the program.
