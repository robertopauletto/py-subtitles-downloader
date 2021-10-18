# main.py

from configparser import ConfigParser
from dataclasses import dataclass, field
import os
import subprocess
from typing import List, Union, Tuple, Any

from bs4 import BeautifulSoup, Tag, ResultSet
import requests


@dataclass
class Subtitle:
    """Subtitle downloader base class"""
    name: str
    href: str

    def get_url(self, domain):
        """Return an url appending `self.href` to the `domain` part"""
        return f"{domain}{self.href}"

    @staticmethod
    def parse(**kwargs) -> Any:
        return NotImplementedError


@dataclass
class SubtitleSrtFile(Subtitle):
    """Represent a subtitle file"""
    pass


@dataclass
class SubtitledShow(Subtitle):
    """Represent a show to search for subtitles"""
    episode: str = ""
    srt_files: List[SubtitleSrtFile] = field(default_factory=[])

    def __str__(self):
        """The user need to know show name and episode (if any) in order to
        choose the desidered show"""
        return f"{self.name} {'- ' + self.episode if self.episode else ''}"

    def build_local_srt_zip_filename(self, extension: str = '.zip'):
        """Compose a filename based on name + episode if available"""
        temp = f"{self.name.strip()}-{self.episode.strip()}"
        ep = "".join([c for c in temp if c.isalpha()
                      or c.isdigit() or c == ' ']).rstrip()
        return ep + extension

    @staticmethod
    def parse(col: Tag) -> Union["SubtitledShow", None]:
        """Parse element and return an instance of the class"""
        show_cell: Tag = col.find('strong')
        show_url = show_cell.find('a', attrs={"class": "bnone"})
        if not show_url:
            return None
        show_href = show_url.attrs['href']
        show_name = show_url.text.strip().replace('\n', ' ')
        show_episode = \
            show_cell.next_sibling.text.strip().replace('\n', ' ')
        return SubtitledShow(href=show_href, name=show_name,
                             episode=show_episode, srt_files=[])


def _get_html(url: str) -> BeautifulSoup:
    """Read from `url` and return an object for parsing"""
    resp = requests.get(url)
    if not resp.ok:
        resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def _parse_show_disambiguation(results_table: Tag) -> List[Subtitle]:
    """Parse and return the possible shows found in the results table"""
    rows: ResultSet = results_table.find_all('tr')
    shows_found = []
    for row in rows:
        if 'id' not in row.attrs or not row.attrs['id'].startswith('name'):
            continue
        cols: ResultSet = row.find_all('td')
        for col in cols:
            if 'id' not in col.attrs or not col.attrs['id'].startswith('main'):
                continue
            show = SubtitledShow.parse(col=col)
            if not show:
                print(f"Failed parsing of {row.text}")
                continue
            shows_found.append(show)
    return shows_found


def search_show(search_terms: str, root_search: str):
    """Get the disambiguation page results"""
    soup: BeautifulSoup = _get_html(
        root_search + search_terms.replace(' ', '+'))
    results_table: Tag = soup.find('table', {'id': 'search_results'})
    if not results_table:
        raise ValueError("Unable to parse search results")
    shows_found = _parse_show_disambiguation(results_table)
    return shows_found


def get_subtitles_for_show(show_url: str,
                           srtfile_col_index: int) -> List[SubtitleSrtFile]:
    return _get_subtitle_for_show(show_url, srtfile_col_index)


def _get_subtitle_for_show(show_url: str,
                           srtfile_col_index: int) -> List[SubtitleSrtFile]:
    """Parse subtitle files available for `show`"""
    soup: BeautifulSoup = _get_html(show_url)
    results_table: Tag = soup.find('table', {'id': 'search_results'})
    retval = []
    if not results_table:
        itemscope = soup.find("div", {"itemtype": "http://schema.org/Movie"})
        onefile: Tag = itemscope.find('a', {'itemprop': "url"})
        reval.append(SubtitleSrtFile(
            name=onefile.text.strip().replace('\n', ' '),
            href=onefile.attrs['href']))
    else:
        rows: ResultSet = results_table.find_all('tr')
        for row in rows:
            if 'id' not in row.attrs or not row.attrs['id'].startswith('name'):
                continue
            cells = row.find_all('td')
            title = _parse_title(cells[0])
            retval.append(SubtitleSrtFile(name=title,
                                          href=_parse_srt_file_url(
                                              cells[srtfile_col_index])))
    return retval


def _parse_title(tag: Tag) -> str:
    text = tag.text.strip().replace('\n', ' ')
    return text[0:text.lower().index('watch')]


def _parse_srt_file_url(tag: Tag) -> str:
    href = tag.find('a')
    if not href:
        return ""
    return href.attrs['href']


def _download_srt_file(url: str, local_filename: str) -> int:
    """
    Download the subtitle file (.zip)
    :param url:
    :param local_filename: optional extension, default .zip will be added
                            if missing
    :return:  file size of downloaded file
    """
    _, ext = os.path.splitext(local_filename)
    if not ext:
        local_filename = f"{local_filename}.zip"
    print('Retrieving ' + url)
    resp = requests.get(url)
    if not resp.ok:
        resp.raise_for_status()
    print(os.path.abspath(local_filename))
    with open(local_filename, 'wb') as fh:
        fh.write(resp.content)
    if os.path.exists(local_filename):
        return os.path.getsize(local_filename)
    return -1


def _check_choice(choice: str, max_id: int) -> Tuple[int, str]:
    if not choice:
        return -1, "Empty choice"
    if not choice.strip().isdigit():
        return -1, "Invalid choice, must be a number"
    if int(choice) == 0:
        return -1, "Program terminated by user"
    if int(choice) > max_id:
        return -1, f"Invalid choice, must be between 1 and {max_id}"
    return int(choice) - 1, ""


def cli():
    """A rudimentary cli interface, just to use the app for the moment"""
    message = ""

    # 1) Get user input
    search_terms = input("Show to search: ")

    # 2) Parse search page to find possible matches
    shows: List[Subtitled] = search_show(
        search_terms, ini.get('parser', 'OST_SEARCH_URL'))
    if not shows:
        print("No shows found")

    # 3) Ask user which show to process
    while True:
        subprocess.call('clear')
        for i, show in enumerate(shows):
            print(f"{i + 1} - {str(show)}")
        print(f"0 - Quit")
        choice = input("Find subtitles for show number ")
        code, msg = _check_choice(choice, len(shows))
        if code < 0:
            message = msg
            break
        subprocess.call('clear')

        # 4) Find subtitles for the show chosen by the user
        upd_show = shows[code]
        show_url = upd_show.get_url(ini.get('parser', 'OST_DOMAIN'))
        upd_show.srt_files = (
            _get_subtitle_for_show(show_url,
                                   ini.getint('parser',
                                              'OST_SUBTITLE_FILE_COLUMN')))
        for i, srtfile in enumerate(upd_show.srt_files):
            print(f"{i + 1} - {srtfile.name}")
        print(f"0 - Quit")

        # 5) Ask user which subtitle file to retrieve
        choice = input("Get subtitle file number ")
        code, msg = _check_choice(choice, len(upd_show.srt_files))
        if code < 0:
            message = msg
            break
        subprocess.call('clear')
        srturl = upd_show.srt_files[code].href
        if not srturl.startswith('http'):
            srturl = upd_show.srt_files[code].get_url(
                ini.get('parser', 'OST_DOMAIN'))

        # 6) Retrieve and lacally save the file .zip containing the .srt file
        filename = os.path.join(ini.get('paths', 'OST_DL_FOLDER'),
                                upd_show.build_local_srt_zip_filename())
        filesize = _download_srt_file(url=srturl, local_filename=filename)
        print(f"Retrieved {filename} ({filesize}) bytes")
        message = f"File srt downloaded"
        break

    print(message)


if __name__ == '__main__':
    CONFIG_FILENAME = 'config.ini'
    if not os.path.exists(CONFIG_FILENAME):
        raise EnvironmentError("Cnfig file 'config.ini' is missing")
    ini = ConfigParser()
    ini.read(CONFIG_FILENAME)
    cli()
