# gui_settings.py

from configparser import ConfigParser

import PySimpleGUI as sg


def create_setttings_window(ini: ConfigParser) -> sg.Window:
    layout = []
    for section_name in ini.sections():
        section_items = []
        for name, value in ini.items(section_name):
            section_items.append(
                [
                    sg.Text(name, size=(25, 1)),
                    sg.InputText(default_text=value,
                                 key=f'{section_name}#{name.upper()}')
                ]
            )
        layout.append(section_items)
    layout.append([
        [sg.HorizontalSeparator()],
        sg.Button("SAVE", key="-GUICONFSAVE-"),
        sg.Button("CLOSE", key="-GUICONFCLOSE-"),
    ])

    window = sg.Window('Manage Configuration', layout,
                       keep_on_top=True, finalize=True)
    return window


def create_language_settings_window(languages: dict,
                                    lang_selected: list,
                                    items_by_row: int = 4) -> sg.Window:
    """
    Builds a window with all the subtitles languages available, the user
    can add or remove any language. The selected languages will be used
    in the query string.
    :param languages: all languages available
    :param lang_selected: the currently selected languages
    :param items_by_row: number of items to display for each row
    :return:
    """
    layout = []
    hor = items_by_row
    start = 0
    row = []
    for langname, langcode in languages.items():
        if start < hor:
            row.append(
                sg.Checkbox(
                    langname,
                    key=f'LNG#{langcode}',
                    size=(20, 1),
                    default=(langcode in lang_selected)
                ))
        start += 1
        if start >= hor:
            start = 0
            layout.append(row)
            row = []

    layout.append([
        [sg.HorizontalSeparator()],
        sg.Button(
            "SAVE",
            key="-LANGONFSAVE-",
            tooltip='The checked languages will be used in the next search '
        ),
        sg.Button("CLOSE", key="-LANGCONFCLOSE-"),
    ])
    window = sg.Window('Manage Subtitle Languages', layout,
                       keep_on_top=True, finalize=True)
    return window
