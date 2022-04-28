# gui.py

import json
import os
from pathlib import Path
import subprocess
import sys
from configparser import ConfigParser
from typing import Union, Tuple

import PySimpleGUI as sg

import gui_settings as guiconf
import gui_utils as gutils
from localfilemanagement import extract_srt

# Add parent folder as source root to python path
# careful, not exensively tested
script_folder = Path(os.path.abspath(__name__)).parent.absolute()
if len(script_folder.parts) == 1:
    # In case we are already in the root of the filesystem (!?!)
    sys.path.append(os.path.join(script_folder.parts[0]))
else:
    sys.path.append(os.path.join(*script_folder.parts[0:-1]))

import backend.ostdownloader as ost

# Get configuration, MUST be present
CONFIG_FILENAME = 'config.ini'
if not os.path.exists(CONFIG_FILENAME):
    raise EnvironmentError("Cnfig file 'config.ini' is missing")
ini = ConfigParser()
ini.read(CONFIG_FILENAME)

# Load resource files
RES_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'res')
INFO_BTN_FILENAME = os.path.abspath(
    os.path.join(RES_FOLDER, 'info_btn16x16.png'))
LANGCONF_BTN_FILENAME = os.path.abspath(
    os.path.join(RES_FOLDER, 'config116x16.png'))
APPLOGO_FILENAME = os.path.abspath(os.path.join(RES_FOLDER, 'applogo.png'))
LANGUAGES_FILE = os.path.join(RES_FOLDER, 'languages.json')
INFO_TIMEOUT = 10  # seconds before autoclosing the search tips window
ITEMS_BY_ROW = 4
APP_NAME = 'Subtitles downloader'
VERSION = "v1.0"


# sg.theme_previewer()


def _check_delzip_option():
    """
    If the option "Extract srl file after download is **NOT** selected,
    no matter what option the user has set in the config file, will return
    always `False`; does not make any sense deleting the zip file if you don't
    extract the .srt file contained first.
    """
    if not ini.getboolean('gui', 'extract_srt'):
        return False
    return ini.getboolean('gui', 'delete_zip')


def _get_languages(languages_file: str = LANGUAGES_FILE) -> dict:
    retval = None
    with open(languages_file) as fh:
        retval = json.load(fh)
    return retval


def _get_sel_languages(ini: ConfigParser = ini) -> str:
    """Get selected languages from user configuration"""
    # normalize all lower and no spaces, then recontruct the string to retrun
    sel_lngs = [lng.strip().lower()
                for lng in ini.get('gui', 'selected_languages').split(',')]
    return ','.join(sel_lngs)


LANGUAGES = _get_languages()
sg.ChangeLookAndFeel(ini.get('gui', 'LOOKNFEEL'))


def _save_config(ini: ConfigParser, inifile: str):
    """Persist config changes to `inifile`"""
    with open(inifile, 'w') as fh:
        ini.write(fh)


def _parse_languages(languages: dict):
    """
    Parse the value returned by the gui windoe for managing languages, write
    the update values to the config, return a string to write in the
    corresponding inputtext widget
    :param languages:
    :return: ex. 'ita,eng,fre' if user selects english, italian and french
    """
    sel_by_user = {k: v for k, v in languages.items() if v == True}
    values_sel_by_user = [v.split('#')[1].strip() for v in sel_by_user]
    ini.set('gui', 'selected_languages', ','.join(values_sel_by_user))
    _save_config(ini, CONFIG_FILENAME)


def _change_settings(sg_keyvalues: dict, inifile: str) -> list:
    """Modify configuration setting"""
    changes = []
    for sgkey, value in sg_keyvalues.items():
        section, key = sgkey.split('#')
        if ini.get(section, key) == value:
            continue
        changes.append(f"{section} -> {key} modified: {value}")
        ini.set(section, key, value)
    with open(inifile, 'w') as fh:
        ini.write(fh)
    return changes


def _get_def_folder():
    return os.path.abspath(ini.get('paths', 'OST_DL_FOLDER'))


layout = [
    # row 1 - search
    [
        sg.Text("Enter show to search", size=(20, 1)),
        sg.InputText(key="-SEARCHTERMS-", size=(53, 1)),
        sg.Button(
            '',
            tooltip='Tips for searching',
            image_data=gutils.convert_to_base64(INFO_BTN_FILENAME),
            button_color=(sg.theme_background_color(),
                          sg.theme_background_color()),
            border_width=0, key='-SRCTERMSINFO-'
        )

    ],
    # row 2 - download folder
    [
        sg.Text(
            "Download folder",
            size=(20, 1)
        ),
        sg.Input(
            key="-DLFOLDER-",
            default_text=_get_def_folder(),
            readonly=True, size=(53, 1)
        ),
        sg.FolderBrowse(tooltip='Folder to save downloaded srt files')
    ],
    # row 3 - output
    [
        [sg.HSeparator()],  # row 3
        [
            sg.Listbox(
                values=[],
                size=(85, 6),
                key="-OUTLIST-",
                horizontal_scroll=True,
            ),
        ],
        [sg.Text("Enter text to search, then click the 'SEARCH' button",
                 size=(80, 1), key='-LISTTITLE-')],
        [sg.HSeparator()],
    ],
    # row 5 - Options
    [
        [sg.Checkbox(
            "Extract srl file after download",
            default=ini.getboolean('gui', 'extract_srt'),
            tooltip="When selected extract the subtitles file(s) directly "
                    "in the Download folder",
            enable_events=True,
            key='-CHKEXTRACTSRT-'
        ),
        sg.Text('Languages: '),
        sg.InputText(
            default_text=_get_sel_languages(), readonly=True,
            tooltip='Subtitles languages to search for',
            size=(40, 1),
            key='-LANGSELECTED-'
        ),
        sg.Button(
            '',
            tooltip='Add/Remove subtitle languages to search for',
            image_data=gutils.convert_to_base64(LANGCONF_BTN_FILENAME),
            button_color=(sg.theme_background_color(),
                          sg.theme_background_color()),
            border_width=0, key='-LANGCONF-'
        )],
        sg.HorizontalSeparator(),
        [sg.Checkbox(
            "Delete zip file after extraction",
            default=_check_delzip_option(),
            tooltip="Delete the subtitles compressed file"
                    "if 'Extract srl file after download' option is selected",
            key='-CHKDELETEZIP-'
        )]

    ],
    # row 5 - Commands
    [
        sg.OK("SEARCH", key="-SEARCH-"),
        sg.Button("GET SHOW", key="-SELSHOW-", disabled=True),
        sg.Button("GET SUBTITLES", key="-GETSUBT-", disabled=True),
        sg.Button("CONFIGURE", key="-CONFIG-"),
        sg.Cancel("QUIT", key="-CANCEL-")
    ]  # last row
]


def _enumerate_items(items: list, start: int = 1, idx_sep: str = ' - ') -> list:
    """
    Prepend a numeric progressive index (starting by `start`) in every
    item in `items`, the number is separed by the original content of each item
    by `idx-sep`
    :param items: collection to parse **must be a one level list**
    :param start: the starting number
    :param idx_sep: string separating the number and the item content
    :return:
    """
    items_numbered = []
    for i, item in enumerate(items):
        if not isinstance(item, str):
            continue
        items_numbered.append(f"{i + 1}{idx_sep}{item}")
    return items_numbered


def on_btn_search(window, event, values) -> list:
    try:
        print("Search button pressed!")
        window['-GETSUBT-'].update(disabled=True)
        window['-SELSHOW-'].update(disabled=True)
        lng = values['-LANGSELECTED-']
        qs = ini.get('parser', 'OST_SEARCH_URL').format(lng)
        shows = ost.search_show(values['-SEARCHTERMS-'], qs)
        window['-LISTTITLE-'].update('Shows matching the query string, please '
                                     'select one in order to download the '
                                     'subtitle file')
        numbered_shows = _enumerate_items([str(show) for show in shows])
        window['-OUTLIST-'].update(values=numbered_shows)
        window['-SELSHOW-'].update(disabled=False)
        return shows
    except Exception as ex:
        prompt = f"An error occurred:{ex} "
        sg.popup_error(prompt, title="")


def _get_idx_from_selected(item,
                           ndx_shift: int = 1, ndx_sep: str = '-') -> int:
    """Extract the number of `item`, subtract `ndx_shift and return the value"""
    idx_str = item.split(ndx_sep, 1)[0].strip()
    if not idx_str.isdigit():
        raise ValueError("This string does non start with a digit(s)")
    return int(idx_str) - ndx_shift


def on_btn_select_show(window, event, values, shows) -> ost.SubtitledShow:
    """
    For the selected show will be retrieved info about the subtitle files
    associated with
    """
    try:
        print(values['-OUTLIST-'])
        if not values['-OUTLIST-']:
            sg.popup(
                'Please select the show in order to download the subtitles')
        else:
            # Parse the index of the selected show related to the list "shows"
            idx = _get_idx_from_selected(values['-OUTLIST-'][0])
            selected_show = shows[idx]

            # For the selected show retrieve the subtitle files
            show_url = selected_show.get_url(ini.get('parser', 'OST_DOMAIN'))
            srtfiles = ost.get_subtitles_for_show(show_url)
            # Pass sutitles files to the selected show object
            selected_show.srt_files = srtfiles
            numbered_srtfiles = _enumerate_items([srt.name for srt in srtfiles])
            window['-LISTTITLE-'].update('Subtitle files found for the show, '
                                         'please pick one to download')
            window['-OUTLIST-'].update(values=numbered_srtfiles)
            window['-GETSUBT-'].update(disabled=False)
            # Return the selected show, we need this for the subsequential
            # retrieving of the subtitle file
            return selected_show
    except Exception as ex:
        prompt = f"An error occurred:{ex} "
        sg.popup_error(prompt, title="")


def _get_remote_and_local_subtitles_filenames(
        local_folder: str, selected_show: ost.SubtitledShow,
        srtfile_idx) -> Tuple[str, str]:
    """Get the remote file url to download and the local filename to save"""
    srturl = selected_show.srt_files[srtfile_idx].href
    # Sometimes the domain is in the resourse path, a check is needed
    if not srturl.startswith('http'):
        srturl = selected_show.srt_files[srtfile_idx].get_url(
            ini.get('parser', 'OST_DOMAIN'))
    filename = os.path.join(local_folder,
                            selected_show.build_local_srt_zip_filename())
    return srturl, filename


def on_btn_get_subtitles(window, event, values,
                         selected_show: ost.SubtitledShow) -> None:
    """Download the subtitle file chosen"""
    try:
        window['-SELSHOW-'].update(disabled=True)
        print(selected_show)
        if not values['-OUTLIST-']:
            sg.popup('Please select a subtitles file to download')
        else:
            idx = _get_idx_from_selected(values['-OUTLIST-'][0])
            srturl, filename = _get_remote_and_local_subtitles_filenames(
                values['-DLFOLDER-'], selected_show, idx)
            print("Downloading " + srturl)
            filesize = ost.download_srt_files(url=srturl,
                                              local_filename=filename)
            print(f"File {filename} ({filesize} bytes) created")
            if filesize < 0:
                sg.popup_error("Srt file download",
                               "Un error has occurred, unable to download the "
                               "selected file")
            else:
                if values['-CHKEXTRACTSRT-']:
                    filesize = extract_srt(filename, values['-DLFOLDER-'])
                    if filesize:
                        os.remove(filename)
                _open_folder_upon_choice(filename, filesize,
                                         values['-DLFOLDER-'])
    except Exception as ex:
        prompt = f"An error occurred:{ex} "
        sg.popup_error(prompt, title="")


def _open_folder_upon_choice(filename: str, filesize: int, folder: str) -> None:
    prompt = f"The subtitles file has been downloaded\n"\
             f" do you want to open the containing folder?"
    choice = sg.popup_ok_cancel(prompt, title="")
    if choice.lower() == 'ok':
        folder = os.path.abspath(folder)
        # TODO: Only unix-like supported, make it valid for Windows SO too
        subprocess.call(["xdg-open", folder])


def config_languages_settings_loop(languages: dict, sel_lang: list,
                                   items_by_row: int):
    gui_window = guiconf.create_language_settings_window(
        languages, sel_lang, items_by_row)
    while True:
        gui_event, gui_values = gui_window.read()
        print(gui_values)
        if gui_event in (sg.WIN_CLOSED, '-CANCEL-') \
                or gui_event in '-LANGCONFCLOSE-':
            gui_window.close()
            break
        elif gui_event in '-LANGONFSAVE-':
            _parse_languages(gui_values)
            gui_window.close()


def config_settings_loop():
    gui_window = guiconf.create_setttings_window(ini)
    while True:
        gui_event, gui_values = gui_window.read()
        if gui_event in (sg.WIN_CLOSED, '-CANCEL-') \
                or gui_event in '-GUICONFCLOSE-':
            gui_window.close()
            break
        elif gui_event in '-GUICONFSAVE-':
            prompt = "OK to confirm configuration changes?"
            choice = sg.popup_ok_cancel(prompt, title='Settings',
                                        keep_on_top=True)
            if choice.lower() == 'ok':
                changes = _change_settings(gui_values, CONFIG_FILENAME)
                prompt = "Settings update completed, you may need to restart" \
                         " the application to apply changes"

                sg.popup_ok(prompt, title='Settings', keep_on_top=True)


def on_btn_search_tips(timeout):
    prompt = [
        'If you are looking for a specific tv series episode ',
        'add season and episode number in the format SXXEXX\n\n'
        'ex. Grey\'s Anatomy S01E03\n',
        'The returned results are limited to 40, if you don\'t find '
        'what you are looking for you may need to refine \nyour search\n\n',
        'Sometimes the title exists but the subtitles in the\n'
        'selected language(s) are not available\n\n'
        f'This window will close in {timeout} seconds'
    ]
    sg.popup_quick_message('\n'.join(prompt), auto_close_duration=10)


def mainloop(layout: list) -> None:
    """
    Main event loop, tipically:

    1) USER: types the query string for a show, then click -SEARCH-
    2) APP: populate -OUTLIST- with the shows found for the search string,
       enable the -SELSHOW- button
    3) USER: single click on the desired show, then click on -SELSHOW-
    4) APP: retrieve and populate -OUTLIST- with the subtitle file name
       associated with the selected show, enable the -GETSUBT- button
    5) USER: single click on the subtitle file he needs, theN click on -GETSUBT-
    6) APP: download the selected subtitle file and saves locally to the path
       specified in the textbox -OUTFOLDER-, prompting the user.

    :param layout: widget disposition
    :return:
    """
    shows = []
    selected_show: Union[ost.SubtitledShow, None] = None
    window = sg.Window(
        f'{APP_NAME} - {VERSION}',
        layout,
        finalize=True,
        icon=gutils.convert_to_base64(APPLOGO_FILENAME)
    )
    while True:
        event, values = window.read()
        window['-SEARCHTERMS-'].bind("<Return>", "_srcenter")
        # print(event)
        # print(values)
        if event in (sg.WIN_CLOSED, '-CANCEL-'):
            break
        # Search opensubtitles.org by the user provided string
        elif event in ['-SEARCH-', '_srcenter']:
            shows = on_btn_search(window, event, values)
        # Search tips popup window
        elif event in '-SRCTERMSINFO-':
            on_btn_search_tips(INFO_TIMEOUT)
        # Retrieve subtitles files for the selected show
        elif event in '-SELSHOW-':
            selected_show = on_btn_select_show(window, event, values, shows)
        # Download the subtitle file (compressed) chosen by the user
        elif event in '-GETSUBT-':
            on_btn_get_subtitles(window, event, values, selected_show)
        # GUI for configuration
        elif event in '-CONFIG-':
            config_settings_loop()
        # GUI for subtitle languages selection
        elif event in '-LANGCONF-':
            sel_lang = values['-LANGSELECTED-'].split(',')
            config_languages_settings_loop(LANGUAGES, sel_lang, ITEMS_BY_ROW)
            window['-LANGSELECTED-'].update(_get_sel_languages())
        # Syncronize the 'extract srt file' and 'delete zip file' options
        elif event in '-CHKEXTRACTSRT-':
            if not values[event]:
                # If 'extract srl file' is disable no matter what the
                # downloaded .zip file will not be deleted
                window['-CHKDELETEZIP-'].update(False)
                window['-CHKDELETEZIP-'].update(disabled=True)
            else:
                window['-CHKDELETEZIP-'].update(disabled=False)

    window.close()


if __name__ == '__main__':
    mainloop(layout=layout)
