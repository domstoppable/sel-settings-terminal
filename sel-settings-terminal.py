#!/usr/bin/python

# NB: As per Debian Python policy #!/usr/bin/env python2 is not used here.

"""
sel-settings-terminal.py

A tool to (at least) extract information from Transpower setting spreadsheets.

Usage defined by running with option -h.

This tool can be run from the IDLE prompt using the main def.

Thoughtful ideas most welcome.

Installation instructions (for Python 2.7):
 - pip install tablib
 - pip install regex

TODO:
 - so many things
 - sorting options on display and dump output?
 - sort out guessing of Transpower standard design version
 - sort out dumping all parameters and argparse dependencies
 - sort out extraction of DNP data
"""

__author__ = "Daniel Mulholland and Dominic Canare"
__copyright__ = "Copyright 2015, Daniel Mulholland, 2016 Dominic Canare"
__credits__ = ["Kenneth Reitz https://github.com/kennethreitz/tablib"]
__license__ = "GPL"
__version__ = '0.04'
__maintainer__ = "Dominic Canare"
__hosted__ = "https://github.com/domstyle/sel-settings-terminal/"
__email__ = "dom@greenlightgo.org"

import sys
import os
import time
import argparse
import glob
import regex
import tablib
import string

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_BASE_OUTPUT_FILE_NAME = "output"
TXT_EXTENSION = 'TXT'
PARAMETER_SEPARATOR = ':'

"""
Construct list of headers. Settings are located by searching between headers
"""
SEL_SEARCH_EXPR = {}
def build_header_exprs():
    group_headers = ['Group {{id}}\nGroup Settings:', 'SELogic group {{id}}\n', 'SEL Group {{id}} Settings - {{id}}\n']
    for gID in '123456':
        starts = []
        stops = ['=\>']
        for header in group_headers:
            starts.append(header.replace('{{id}}', gID))
            stops.append(header.replace('{{id}}', '[123456]'.replace(gID, '')))
        SEL_SEARCH_EXPR['G%s' % gID] = [starts, stops]

    ports = '12345F'
    for port in ports:
        SEL_SEARCH_EXPR['P%s' % port] = [
            ['Port %s\n' % port],
            ['$', '=\>', 'Port [%s]\n' % (ports.replace(port, ''))]
        ]
        starts.append(header.replace('{{id}}', str(gID)))
        stops.append(header.replace('{{id}}', '[123456]'.replace(str(gID), '')))

def main(arg=None):
    build_header_exprs()
    parser = argparse.ArgumentParser(
        description='Process individual or multiple RDB files and produce summary' \
                    ' of results as a csv or xls file.',
        epilog='Enjoy. Bug reports and feature requests welcome. Feel free to build a GUI :-)',
        prefix_chars='-/')

    parser.add_argument('-o', choices=['csv', 'xlsx'],
                        help='Produce output as either comma separated values (csv) or as' \
                        ' a Micro$oft Excel .xls spreadsheet. If no output provided then' \
                        ' output is to the screen.')

    parser.add_argument('-f', '--output-file',
                        help='Specify the name of the output file')
                        
    parser.add_argument('-p', '--path', metavar='PATH|FILE', nargs='+',
                        help='Go recursively go through path PATH. Redundant if FILE' \
                        ' with extension .rdb is used. When recursively called, only' \
                        ' searches for files with:' + TXT_EXTENSION + '. Globbing is' \
                        ' allowed with the * and ? characters.')

    parser.add_argument('-c', '--console', action="store_true",
                        help='Show output to screen')

    parser.add_argument('-s', '--settings', metavar='G:S', type=str, nargs='+',
                        help='Settings in the form of G:S where G is the group' \
                        ' and S is the SEL variable name. If G: is omitted the search' \
                        ' goes through all groups. Otherwise G should be the '\
                        ' group of interest. S should be the setting name ' \
                        ' e.g. OUT201.' \
                        ' Examples: G1:50P1P or G2:50P1P or 50P1P' \
                        ' ' \
                        ' You can also get port settings using P:S' \
                        ' Note: Applying a group for a non-grouped setting is unnecessary' \
                        ' and will prevent you from receiving results.'\
                        ' Special parameters are the following self-explanatory items:' \
                        ' FID, PARTNO, DEVID')

    parser.add_argument('-m', '--mode', choices=['rows', 'columns'],
                        help='Set the output mode to either rows or columns' \
                        ' In rows, each setting will have it\'s own row. There will be 3' \
                        ' columns (input file, setting name, value).' \
                        ' ' \
                        ' In columns, each file will have just one row, and each setting will' \
                        ' be presented in it\'s own column.')

    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    if arg == None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(arg.split())

    # read in list of files
    files_to_do = return_file_paths([' '.join(args.path)], TXT_EXTENSION)

    if files_to_do != []:
        process_txt_files(files_to_do, args)
    else:
        print('Found nothing to do for path: ' + args.path[0])
        raw_input("Press any key to exit...")
        sys.exit()

def return_file_paths(args_path, file_extension):
    paths_to_work_on = []
    for p in args_path:
        p = p.translate(None, ",\"")
        if not os.path.isabs(p):
            paths_to_work_on += glob.glob(os.path.join(BASE_PATH, p))
        else:
            paths_to_work_on += glob.glob(p)

    files_to_do = []
    # make a list of files to iterate over
    if paths_to_work_on != None:
        for p_or_f in paths_to_work_on:
            if os.path.isfile(p_or_f) == True:
                # add file to the list
                print(os.path.normpath(p_or_f))
                files_to_do.append(os.path.normpath(p_or_f))
            elif os.path.isdir(p_or_f) == True:
                # walk about see what we can find
                files_to_do = walkabout(p_or_f, file_extension)
    return files_to_do

def walkabout(p_or_f, file_extension):
    """ searches through a path p_or_f, picking up all files with EXTN
    returns these in an array.
    """
    return_files = []
    for root, dirs, files in os.walk(p_or_f): #, topdown=False
        for name in files:
            if (os.path.basename(name)[-3:]).upper() == file_extension:
                return_files.append(os.path.join(root, name))
    return return_files

def process_txt_files(files_to_do, args):
    parameter_info = []

    for filename in files_to_do:
        extracted_data = extract_parameters(filename, args.settings)
        if len(extracted_data) > 0:
            mod_time = time.strftime("%Y-%m-%d %H:%M", time.gmtime(os.path.getmtime(filename)))
            extracted_data.insert(0, [extracted_data[0][0], 'File date', mod_time])
            parameter_info += extracted_data
    # Some regex's return lists. We just want the first item from that list
    for k in parameter_info:
        if not isinstance(k[2], basestring):
            if len(k[2]) == 0:
                k[2] = ''
            else:
                k[2] = k[2][0]
                
    if args.mode == 'columns':
        data = create_output_as_columns(parameter_info)
    else:
        data = create_output_as_rows(parameter_info)
      
    if args.o is not None:
        do_output(args, data)
    
    if args.console:
        display_info(parameter_info)

def create_output_as_columns(parameter_info):
    headers = ['Filename', 'File date']
    record = None
    raw_data = []
    for k in parameter_info:
        if record is None or k[0] != record[0]:
            # this is a new filename
            if record is not None:
                raw_data.append(record)
            record = [k[0]]

        # add the header to the list if it's the first time we've seen it
        if k[1] not in headers:
            headers.append(k[1])

        for headerID, header in enumerate(headers):
            if header == k[1]:
                # put in blanks for any columns we don't have yet for this file
                for i in range(headerID - len(record) + 1):
                    record.append(None)
                record[headerID] = k[2]
                break

    if record is not None:
        raw_data.append(record)

    data = tablib.Dataset()
    data.headers = headers
    for record in raw_data:
        # make sure the trailing empty columns actually exist
        for i in range(len(headers) - len(record)):
            record.append(None)
        data.append(record)

    return data

def create_output_as_rows(parameter_info):
    # for exporting to Excel or CSV
    data = tablib.Dataset()
    for k in parameter_info:
        data.append(k)
    data.headers = ['Filename','Setting Name', 'Val']
    
    return data

def do_output(args, data):
    # don't overwrite existing file
    if args.output_file is not None:
        name = args.output_file
    else:
        name = DEFAULT_BASE_OUTPUT_FILE_NAME
        # this is stupid and klunky
        attempt = 0
        while os.path.exists(name + '.' + args.o):
            attempt += 1
            name = DEFAULT_BASE_OUTPUT_FILE_NAME + ' - ' + str(attempt)
        name += '.' + args.o
    
    print('Writing %s' % name)
    with open(name, 'wb') as output:
        if args.o == 'csv':
            output.write(data.csv)
        elif args.o == 'xlsx':
            output.write(data.xlsx)

def extract_parameters(filename, settings):
    parameter_info = []

    # read data
    with open(filename, 'r') as f:
        read_data = f.read()

    parameter_list = []
    for k in settings:
        parameter_list.append(k.translate(None, '\"'))

    for parameter in parameter_list:
        data = read_data
        result = None
        grouper = None
        setting = None
        # parameter is e.g. G1:50P1P and there is a separator
        # if parameter.find(PARAMETER_SEPARATOR) != -1:
        if parameter.find(PARAMETER_SEPARATOR) != -1:
            grouper = parameter.split(PARAMETER_SEPARATOR)[0]
            setting = parameter.split(PARAMETER_SEPARATOR)[1]

        if parameter.find(PARAMETER_SEPARATOR) == -1 or SEL_SEARCH_EXPR[grouper] == None:
            result = find_SEL_text_parameter(parameter, [data])
            if result is None:
                result = get_special_parameter(parameter, data)

        else:
            # now search inside this data group for the desired setting
            data = find_between_text(
                start_options=SEL_SEARCH_EXPR[grouper][0],
                end_options=SEL_SEARCH_EXPR[grouper][1],
                text=data
            )

            if data:
                result = find_SEL_text_parameter(setting, data)

        if result != None:
            filename = os.path.basename(filename)
            parameter_info.append([filename, parameter, result])

    return parameter_info

def find_SEL_text_parameter(setting, data_array):
    for row in data_array:
        """
        How this regex works:
         * (\n| |^)
           - Looks for either a new line CR/LF  or a space or the start of the file.
           - This is always true in process terminal views.

         * ([A-Z0-9 _]{6})
           - SEL setting names are typically uppercase without spaces comprising
             characters A-Z 0-9 and sometimes with underscores (exception, DNP)

         * =
           - Then followed by an equals character

         * ( *([\w :+/\\()!,.\-_\\*]+ ?)*(?!(\w* *)=))((\w* ?)=)?
           - Followed by maybe whitespace, followed by the value
           -- The value could include alphanumerics, spaces, and a bunch of
              other special characters.
           -- But any alphanumeric word that is followed by an "=" should NOT
              be included
        """

        """
        TODO: This is how the --all or -a parameter should be implemented
        results = regex.findall('(\n| |^)([A-Z0-9 _]{6})=(?>([\w :+/\\()!,.\-_\\*]+)([ ]{0}[A-Z0-9 _]{6}=|\n))',
            data, flags=regex.MULTILINE, overlapped=True)

        Just need to break down the groups. Trivial. Exercise for the reader.
        :-)
        """

        found_parameter = regex.findall(
            '(\n| |^)' +
            '(' + setting + ' *):?=' +
            ' *"?(([\w :+/\\()!,.\-_\\*]+ ?)*(?!(\w* *):?=))"?((\w* ?):?=)?',
            row, flags=regex.MULTILINE, overlapped=True
        )

        if found_parameter:
            return found_parameter[0][2]

def find_between_text(start_options, end_options, text):
    # return matches between arbitrary start and end options
    # with matches across lines
    results = []
    start_regex = ''
    for k in start_options:
        start_regex = k

        # create ending regex expression
        end_regex = '('
        for k in end_options:
            end_regex += k + '|'
        end_regex = end_regex[0:-1]
         # make sure you pull things from the last group in the file too
        end_regex += '|\\Z)'

        result = regex.findall(start_regex + '((.|\n)+?)' + end_regex, text, flags=regex.MULTILINE)

        if result:
            results.append(result[0][0])

    return results

def get_special_parameter(name, data):
    # some units are inconsistent with CR's and LF's
    data = regex.sub(r'\r([^\n])', r'\n\1', data) # replace trailing \r with \n
    data = regex.sub(r'\r\n', r'\n', data) # drop \r's from the end of line

    # Something like:
    # name=FID for "FID=SEL-351S-6-R107-V0-Z003003-D20011129","0958"
    # name=PARTNO for "PARTNO=0351S61H3351321","05AE"
    # name=DEVID for "DEVID=TMU 2782","0402"
    
    expr = r'^\"' + name + r':?=([\w :+/\\()!,.\-_\\*]*)".*\n'
    return regex.findall(expr, data, flags=regex.MULTILINE, overlapped=True)

def display_info(parameter_info):
    lengths = []
    # first pass to determine column widths:
    for line in parameter_info:
        for index, element in enumerate(line):
            try:
                lengths[index] = max(lengths[index], len(element))
            except IndexError:
                lengths.append(len(element))

    parameter_info.insert(0, ['Filename', 'Setting Name', 'Val'])
    # now display in columns
    for line in parameter_info:
        display_line = ''
        for index, element in enumerate(line):
            display_line += element.ljust(lengths[index] + 2, ' ')
        print(display_line)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        main('-m rows -f output.csv -o csv -p RDBs --settings RID G1:TID FID PARTNO G1:TR G1:81D1P G1:81D1D G1:81D2P G1:81D2P G1:E81')
    else:
        main()
