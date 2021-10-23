# ostdownloader.py

import os
from dataclasses import dataclass, field
from typing import List, Union, Any

import requests
from bs4 import BeautifulSoup, Tag, ResultSet

SRTFILE_COL_EP_INDEX = 4
SRTFILE_COL_SEASON_INDEX = 2


@dataclass
class Subtitle:
    """Subtitle downloader base class"""
    name: str
    href: str

    def get_url(self, domain):
        """Return an url appending `self.href` to the `domain` part"""
        return f"{domain}{self.href}"

    def to_json(self) -> dict:
        return {"name": self.name, href: "self.href"}

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

    def to_json(self) -> dict:
        retval = super().to_json()
        retval['srtfiles'] = [srt.to_json() for srt in self.srt_files]
        return retval

    def __str__(self):
        """The user need to know show name and episode (if any) in order to
        choose the desidered show"""
        return f"{self.name} {'- ' + self.episode if self.episode else ''}"

    def build_local_srt_zip_filename(self, extension: str = '.zip'):
        """
        Compose a valid local filename based on name + episode
        if available
        """
        temp = f"{self.name.strip()}-{self.episode.strip()}"
        ep = "".join([c for c in temp if c.isalpha()
                      or c.isdigit() or c == ' ']).rstrip()
        return ep + extension

    @staticmethod
    def parse(col: Tag) -> Union["SubtitledShow", None]:
        """Parse `col` and return an instance of the class"""
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
    url = root_search + search_terms.replace(' ', '+')
    print("Searching " + url)
    soup: BeautifulSoup = _get_html(url)
    results_table: Tag = soup.find('table', {'id': 'search_results'})
    if not results_table:
        raise ValueError("Unable to parse search results")
    shows_found = _parse_show_disambiguation(results_table)
    return shows_found


def get_subtitles_for_show(show_url: str) -> List[SubtitleSrtFile]:
    """Parse subtitle files available for `show`"""
    srtfile_col_ep_index = SRTFILE_COL_EP_INDEX
    srtfile_col_season_index = SRTFILE_COL_SEASON_INDEX
    soup: BeautifulSoup = _get_html(show_url)
    results_table: Tag = soup.find('table', {'id': 'search_results'})
    retval = []
    if not results_table:  # Movies or TV Episodes
        itemscope = soup.find("div", {"itemtype": "http://schema.org/Movie"})
        onefile: Tag = itemscope.find('a', {'itemprop': "url"})
        retval.append(SubtitleSrtFile(
            name=onefile.text.strip().replace('\n', ' '),
            href=onefile.attrs['href']))
    else:  # Complete TV Series season or TV Episodes with 1 subtitles file
        if 'itemprop' in results_table.attrs \
                and results_table.attrs['itemprop'] == 'season':
            srts = _parse_complete_tvseries(results_table,
                                            srtfile_col_season_index)
            retval.extend(srts)
        else:  # Single srt file
            rows: ResultSet = results_table.find_all('tr')
            for row in rows:
                if 'id' not in row.attrs or not row.attrs['id'].startswith(
                        'name'):
                    continue
                cells = row.find_all('td')
                title = _parse_title(cells[0])
                retval.append(
                    SubtitleSrtFile(name=title,
                                    href=_parse_srt_file_url(
                                        cells[srtfile_col_ep_index]))
                )
    return retval


def _parse_complete_tvseries(
        results_table: Tag, srtfile_col_season_index) -> List[SubtitleSrtFile]:
    """Parse subtitles links for a TvSeries page (collection of episodes) """
    retval = []
    rows = results_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if not cells:
            continue
        if len(cells) == 1 \
                and cells[0].text.strip().lower().startswith('season'):
            title = cells[0].text.strip()
            links = cells[0].find_all('a')
            href = None
            for link in links:
                # Trying to retrieve the number of episodes in the season
                if 'itemprop' in link.attrs:
                    if not link.find('meta'):
                        continue
                    title = f"{title} ("\
                            f"{link.find('meta').attrs['content']} episodes)"
                else:
                    href = link.attrs['href']
            retval.append(SubtitleSrtFile(name=title, href=href))
        else:
            title = _parse_title(cells[0])
            retval.append(SubtitleSrtFile(
                name=title,
                href=_parse_srt_file_url(
                    cells[srtfile_col_season_index])))
    return retval


def _parse_title(tag: Tag) -> str:
    text = tag.text.strip().replace('\n', ' ')
    if 'watch' in text.lower():
        return text[0:text.lower().index('watch')]
    return text


def _parse_srt_file_url(tag: Tag) -> str:
    href = tag.find('a')
    if not href:
        return ""
    return href.attrs['href']


def download_srt_files(url: str, local_filename: str) -> int:
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


def get_available_languages():
    retval = {}
    with open('temp.html') as fh:
        soup = BeautifulSoup(fh.read(), 'html.parser')
    for item in soup.find_all('input', {"name": "multiselect_SubLanguageID"}):
        # print(item.attrs)
        retval[item.attrs['title']] = item.attrs['value']
    print(retval)

if __name__ == '__main__':
    get_available_languages()
