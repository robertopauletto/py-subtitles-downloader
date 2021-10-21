# gui.py

import os
import subprocess
from configparser import ConfigParser
from typing import Union, Tuple

import PySimpleGUI as sg

import gui_settings as guiconf
import gui_utils as gutils
import main as ost

CONFIG_FILENAME = 'config.ini'
if not os.path.exists(CONFIG_FILENAME):
    raise EnvironmentError("Cnfig file 'config.ini' is missing")
ini = ConfigParser()
ini.read(CONFIG_FILENAME)

INFO_BTN_FILENAME = os.path.abspath('info_btn16x16.png')
APPLOGO_FILENAME = os.path.abspath('applogo.png')

sg.ChangeLookAndFeel(ini.get('gui', 'LOOKNFEEL'))


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
        sg.InputText(key="-SEARCHTERMS-"),
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
        sg.Text("Download folder", size=(20, 1)),
        sg.Input(key="-DLFOLDER-", default_text=_get_def_folder(),
                 readonly=True),
        sg.FolderBrowse(tooltip='Folder to save downloaded srt files')
    ],
    # row 3 - output
    [
        [sg.HSeparator()],  # row 3
        [
            sg.Listbox(
                values=[],
                size=(80, 6),
                key="-OUTLIST-",
                horizontal_scroll=True,
            ),
        ],
        [sg.Text("Enter text to search, then hit the 'SEARCH BUTTON'",
                 size=(80, 1), key='-LISTTITLE-')],
        [sg.HSeparator()],
    ],
    # row 5 - Options
    [
        sg.Checkbox(
            "Extract srl file after download",
            default=ini.getboolean('gui', 'extract_srt'),
            tooltip="When selected extract the subtitles file(s) directly "
                    "in the Download folder",
            key='-CHKEXTRACTSRT-'
        )
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
        shows = ost.search_show(values['-SEARCHTERMS-'],
                                ini.get('parser', 'OST_SEARCH_URL'))
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
            print(f"Create file {filename} ({filesize} bytes)")
            if filesize < 0:
                sg.popup_error("Srt file download",
                               "Un error has occurred, unable to download the "
                               "selected file")
            else:
                _open_folder_upon_choice(filename, filesize,
                                         values['-DLFOLDER-'])
    except Exception as ex:
        prompt = f"An error occurred:{ex} "
        sg.popup_error(prompt, title="")


def _open_folder_upon_choice(filename: str, filesize: int, folder: str) -> None:
    prompt = f"The subtitles file\n{os.path.basename(filename)}\n({filesize}" \
             f" bytes)\nhas been downloaded, do you want to open the " \
             f" containing folder?"
    choice = sg.popup_ok_cancel(prompt, title="")
    if choice.lower() == 'ok':
        folder = os.path.abspath(folder)
        # TODO: Only unix-like supported, make it valid for Windows SO too
        subprocess.call(["xdg-open", folder])


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


def on_btn_search_tips():
    timeout = 10
    prompt = [
        'If you are looking for a specific tv series episode ',
        'add season and episode number in the format SXXEXX\n\n'
        'ex. Grey\'s Anatomy S01E03\n',
        'The returned results are limited to 40, if you don\'t find '
        'what you are looking for you may need to refine \nyour search\n',
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
        'Subtitles downloader',
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
        elif event in ['-SEARCH-', '_srcenter']:
            shows = on_btn_search(window, event, values)
        elif event in '_srcenter':
            print("Return pressed!")
        elif event in '-SRCTERMSINFO-':
            on_btn_search_tips()
            print(values['-CHKEXTRACTSRT-'])
            # sg.theme_previewer()
        elif event in '-SELSHOW-':
            selected_show = on_btn_select_show(window, event, values, shows)
        elif event in '-GETSUBT-':
            on_btn_get_subtitles(window, event, values, selected_show)
        elif event in '-CONFIG-':
            config_settings_loop()
    window.close()


if __name__ == '__main__':
    mainloop(layout=layout)
