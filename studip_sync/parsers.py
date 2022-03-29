import cgi
import json
import re
import urllib.parse

from functools import wraps
from bs4 import BeautifulSoup


def log_html_on_exception():
    def decorator(func):
        @wraps(func)
        def inner(html, *args, **kwargs):
            try:
                return func(html, *args, **kwargs)
            except Exception as e:
                print(html)

                raise e

        return inner

    return decorator


def try_parser_functions(html, func_attempts):
    soup = BeautifulSoup(html, 'lxml')

    for func_attempt in func_attempts:
        try:
            return func_attempt(html, soup)
        except ParserError:
            continue

    raise ParserError("all attempts to parse data failed")


class ParserError(Exception):
    pass


@log_html_on_exception()
def extract_files_flat_last_edit(html):
    def extract_json(_, s):
        form = s.find('form', id="files_table_form")

        if not form:
            raise ParserError("last_edit: files_table_form not found")

        if "data-files" not in form.attrs:
            raise ParserError("last_edit: Missing data-files attribute in form")

        form_data_files = json.loads(form.attrs["data-files"])

        file_timestamps = []

        for file_data in form_data_files:
            if "chdate" not in file_data:
                raise ParserError("last_edit: No chdate: " + str(file_data.keys()))

            file_timestamps.append(file_data["chdate"])

        if len(file_timestamps) > 0:
            return max(file_timestamps)
        else:
            return 0

    def extract_html_table(_, s):
        for form in s.find_all('form'):
            if 'action' in form.attrs:
                tds = form.find('table').find('tbody').find_all('tr')[0].find_all('td')
                if len(tds) == 8:
                    td = tds[6]
                    if 'data-sort-value' in td.attrs:
                        try:
                            return int(td.attrs['data-sort-value'])
                        except:
                            raise ParserError("last_edit: Couldn't convert data-sort-value to int")
                    else:
                        raise ParserError(
                            "last_edit: Couldn't find td object with data-sort-value")
                elif len(tds) == 1 and "Keine Dateien vorhanden." in str(tds[0]):
                    return 0  # No files, so no information when was the last time a file was edited
                else:
                    raise ParserError("last_edit: row doesn't have expected length of cells")

        raise ParserError("last_edit: Found no valid form")

    return try_parser_functions(html, [extract_json, extract_html_table])


@log_html_on_exception()
def extract_files_index_data(html):
    soup = BeautifulSoup(html, 'lxml')

    form = soup.find('form', id="files_table_form")

    if "data-files" not in form.attrs:
        raise ParserError("index_data: Missing data-files attribute in form")

    if "data-folders" not in form.attrs:
        raise ParserError("index_data: Missing data-folders attribute in form")

    form_data_files = json.loads(form["data-files"])
    form_data_folders = json.loads(form["data-folders"])

    return form_data_files, form_data_folders


@log_html_on_exception()
def extract_parent_folder_id(html):
    soup = BeautifulSoup(html, 'lxml')
    folder_ids = soup.find_all(attrs={"name": "parent_folder_id"})

    if len(folder_ids) != 1:
        raise ParserError("Could not find parent folder ID")

    return folder_ids.pop().attrs.get("value", "")


@log_html_on_exception()
def extract_csrf_token(html):
    soup = BeautifulSoup(html, 'lxml')
    tokens = soup.find_all("input", attrs={"name": "security_token"})

    if len(tokens) < 1:
        raise ParserError("Could not find CSRF token")

    return tokens.pop().attrs.get("value", "")


@log_html_on_exception()
def extract_courses(html, only_recent_semester):
    soup = BeautifulSoup(html, 'lxml')

    div = soup.find("div", id="my_seminars")
    tables = div.find_all("table")

    for i in range(0, len(tables)):
        if only_recent_semester and i > 0:
            continue

        j = len(tables) - i

        table = tables[i]

        semester = table.find("caption").string.strip()

        matcher = re.compile(
            r"https://.*seminar_main.php\?auswahl=[0-9a-f]*$")
        links = table.find_all("a", href=matcher)

        for link in links:
            href = link.attrs.get("href", "")
            query = urllib.parse.urlsplit(href).query
            course_id = urllib.parse.parse_qs(query).get("auswahl", [""])[0]

            save_as = re.sub(r"\s\s+", " ", link.get_text(strip=True))
            save_as = save_as.replace("/", "--")

            yield {
                "course_id": course_id,
                "save_as": save_as,
                "semester": semester,
                "semester_id": j
            }


@log_html_on_exception()
def extract_filename_from_headers(headers):
    if "Content-Disposition" not in headers:
        raise ParserError(
            "media_filename_headers: \"Content-Disposition\" is missing")

    content_disposition = headers["Content-Disposition"]

    header_value, header_params = cgi.parse_header(content_disposition)

    if "filename" not in header_params:
        raise ParserError("media_filename_headers: \"filename\" is missing")

    if header_params["filename"] == "":
        raise ParserError("media_filename_headers: filename value is empty")

    return header_params["filename"]
