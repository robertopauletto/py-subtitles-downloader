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
        sg.Button("SAVE", key="-GUICONFSAVE-"),
        sg.Button("CLOSE", key="-GUICONFCLOSE-"),
    ])

    window = sg.Window('Manage Configuration', layout,
                       keep_on_top=True, finalize=True)
    return window
