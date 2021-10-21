# gui_utils

import base64
from typing import Union
import PySimpleGUI as sg


def convert_to_base64(filename: str) -> Union[bytes, None]:
    """Return a base64 encoded string of `filename`"""
    enc = None
    try:
        with open(filename, 'rb') as fh:
            enc = base64.b64encode(fh.read())
    except:  # If anything goes wrong don't care, simple return None
        pass
    finally:
        return enc
