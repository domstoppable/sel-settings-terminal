# tp-setting-excel-tool
For extracting information from TP setting calculation aids

## Changelog
### v 0.4
* Feature: Add column output mode
* Feature: Allow specification/overwrite of output file
* Feature: Match := as value indicator
* Feature: Include file modification time in output
* Fix: Group and port header search strings were bad
* Fix: Less clunky default output file naming scheme
* Fix: If value is a list, only use 1st item in list
* Fix: If *any* parameter isn't found using regular search method, search for it as a "special parameter"
* Fix: Find settings in the last group of the file
* Fix: Find parameters don't fit the 6-chars-with-spaces convention
* Fix: Better parameter matching regex to grab values when multiple settings are on the same line
* Fix: Strip/replace CR's before searching (some units are inconsistent with carriage returns and linefeeds)
