# localfilemanagement.py

import os
from typing import Union
import zipfile


def extract_srt(zipfilename: str,  outfolder: Union[str, None] = None,
                ext: str = '.srt', rename_as: str = "") -> int:
    """
    Extract every .srt file in `zipfilename` to `outfolder`
    :param zipfilename:
    :param outfolder: Where to copy the .srt files, if None the folder of
                      the compressed file will be used
    :param ext: The extension of the file to extract (case insensitive)
    :param rename_as: If not empty will be the name of the extracted .srt file
                      if such name exists will be manteined the original
                      filename. Useful to load automatically the .srt file in
                      smplayer.
    :return: Bytes extracted
    """
    outfolder = outfolder or os.path.abspath(os.path.dirname(zipfilename))

    filesizes = 0
    try:
        with zipfile.ZipFile(zipfilename) as zfh:
            for info in zfh.infolist():
                if not info.filename.lower().endswith(ext):
                    continue
                # print(f"Extracting {info.filename} to {outfolder}")
                zfh.extract(info.filename, outfolder)
                filesizes += info.file_size
                if rename_as:
                    _rename_srt_file(
                        os.path.join(outfolder, info.filename), rename_as)
        return filesizes
    except Exception as exc:
        print(exc)
        return -1


def _rename_srt_file(oldname_path: str, newname: str) -> None:
    if os.path.exists(oldname_path):
        return
    folder, _ = os.path.split(oldname_path)
    os.rename(oldname_path, os.path.join(folder, newname))
