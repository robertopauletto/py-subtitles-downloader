# localfilemanagement.py

import os
from typing import Union
import zipfile


def extract_srt(zipfilename: str,
                outfolder: Union[str, None] = None, ext: str = '.srt') -> int:
    """
    Extract every .srt file in `zipfilename` to `outfolder`
    :param zipfilename:
    :param outfolder: Where to copy the .srt files, if None the folder of
                      the compressed file will be used
    :param ext: The extension of the file to extract (case insensitive)
    :return:
    """
    outfolder = outfolder or os.path.abspath(os.path.dirname(zipfilename))

    filesizes = 0
    try:
        with zipfile.ZipFile(zipfilename) as zfh:
            for info in zfh.infolist():
                if not info.filename.lower().endswith(ext):
                    continue
                print(f"Extracting {info.filename} to {outfolder}")
                zfh.extract(info.filename, outfolder)
                filesizes += info.file_size
        return filesizes
    except Exception as exc:
        print(exc)
        return -1


if __name__ == '__main__':
    fn = '../hr.zip'
    of = '/home/robby/Torrents/subtitles'
    print(extract_srt(fn, of))

