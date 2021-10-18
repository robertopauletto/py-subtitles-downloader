# gui.py

from configparser import ConfigParser
import os

import PySimpleGUI as sg

import backend.main as ost

CONFIG_FILENAME = 'config.ini'
if not os.path.exists(CONFIG_FILENAME):
    raise EnvironmentError("Cnfig file 'config.ini' is missing")
ini = ConfigParser()
ini.read(CONFIG_FILENAME)

sg.ChangeLookAndFeel(ini.get('gui', 'LOOKNFEEL'))


def _get_def_folder():
    return ini.get('paths', 'OST_DL_FOLDER')


layout = [
    # row 1
    [
        sg.Text("Enter show to search", size=(20, 1)),
        sg.InputText(key="-SEARCHTERMS-")
    ],
    # row 2
    [
        sg.Text("Download directory", size=(20, 1)),
        sg.Input(key="-DLFOLDER-", default_text=_get_def_folder(),
                 readonly=True),
        sg.FolderBrowse(tooltip='Directory to put downloaded srt files')
    ],
    # row 3
    [
        [sg.HSeparator()],  # row 3
        [sg.Text("", size=(80, 1), key='-LISTTITLE-')],
        [sg.Listbox(values=[], size=(80, 6), key="-OUTLIST-")],
        [sg.HSeparator()],
    ],
    # row 4
    [
        sg.OK("SEARCH", key="-SEARCH-"),
        sg.Button("DOWNLOAD", key="-DOWNLOAD-", disabled=True),
        sg.Button("CONFIGURE", key="-CONFIG-"),
        sg.Cancel('QUIT', key="-CANCEL-")
    ]  # last row
]


def on_btn_search(window, event, values) -> list:
    print("Search button pressed!")
    shows = ost.search_show(values['-SEARCHTERMS-'],
                            ini.get('parser', 'OST_SEARCH_URL'))
    window['-LISTTITLE-'].update('Shows matching the query string, please '
                                 'select one in order to download the '
                                 'subtitle file')
    window['-OUTLIST-'].update(values=[str(show) for show in shows])
    window['-DOWNLOAD-'].update(disabled=False)
    return shows


def on_btn_download(window, event, values, shows):
    print(values['-OUTLIST-'])
    if not values['-OUTLIST-']:
        sg.popup('Please select the show in order to download the subtitles')
    else:
        for i, show in enumerate(shows):
            if not str(show.name) == values['-OUTLIST-'][0]:
                continue
            show_url = shows[i].get_url(ini.get('parser', 'OST_DOMAIN'))
            srtfiles = ost.get_subtitle_for_show(show_url, 4)
            window['-LISTTITLE-'].update('Subtitle files found for the show')
            window['-OUTLIST-'].update(values=[srt.name for srt in srtfiles])
        window['-DOWNLOAD-'].update(disabled=False)


def mainloop(layout):
    shows = []
    window = sg.Window('Subtitles downloader', layout)
    while True:
        event, values = window.read()
        print(event)
        print(values)
        if event in (sg.WIN_CLOSED, '-CANCEL-'):
            break
        elif event in '-SEARCH-':
            shows = on_btn_search(window, event, values)
        elif event in '-DOWNLOAD-':
            on_btn_download(window, event, values, shows)
        elif event in '-CONFIG-':
            sg.popup_get_text('popup!')
    window.close()


if __name__ == '__main__':
    mainloop(layout=layout)
