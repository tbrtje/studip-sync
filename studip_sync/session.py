import os
import shutil
import time
import urllib.parse

import requests

from studip_sync import parsers
from studip_sync.constants import URL_BASEURL_DEFAULT, AUTHENTICATION_TYPES
from studip_sync.plugins.plugin_list import PluginList


class SessionError(Exception):
    pass


class FileError(Exception):
    pass


class MissingFeatureError(Exception):
    pass


class MissingPermissionFolderError(Exception):
    pass


class DownloadError(SessionError):
    pass


class URL(object):
    def __init__(self, base_url):
        self.base_url = base_url

    def __relative_url(self, rel_url):
        return urllib.parse.urljoin(self.base_url, rel_url)

    def login_page(self):
        return self.__relative_url("index.php?again=yes")

    def files_main(self):
        return self.__relative_url("dispatch.php/course/files")

    def files_index(self, folder_id):
        return self.__relative_url("dispatch.php/course/files/index/{}".format(folder_id))

    def files_flat(self):
        return self.__relative_url("dispatch.php/course/files/flat")

    def bulk_download(self, folder_id):
        return self.__relative_url("dispatch.php/file/bulk/{}".format(folder_id))

    def studip_main(self):
        return self.__relative_url("dispatch.php/start")

    def courses(self):
        return self.__relative_url("dispatch.php/my_courses")


class Session(object):

    def __init__(self, plugins=None, base_url=URL_BASEURL_DEFAULT):
        super(Session, self).__init__()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WeWantFileSync"})
        self.url = URL(base_url)

        if plugins is None:
            self.plugins = PluginList()
        else:
            self.plugins = plugins

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.__exit__()

    def set_base_url(self, new_base_url):
        self.url = URL(new_base_url)

    def login(self, auth_type, auth_type_data, username, password):
        auth = AUTHENTICATION_TYPES[auth_type]
        auth.login(self, username, password, auth_type_data)

    def get_courses(self, only_recent_semester=False):
        with self.session.get(self.url.courses()) as response:
            if not response.ok:
                raise SessionError("Failed to get courses")

            return parsers.extract_courses(response.text, only_recent_semester)

    def check_course_new_files(self, course_id, last_sync):
        params = {"cid": course_id}

        with self.session.get(self.url.files_flat(), params=params) as response:
            if not response.ok:
                if response.status_code == 403 and "Documents" in response.text:
                    raise MissingFeatureError("This course has no files")
                else:
                    raise DownloadError("Cannot access course files_flat page")
            last_edit = parsers.extract_files_flat_last_edit(response.text)

        if last_edit == 0:
            print("\tLast file edit couldn't be detected!")
        else:
            print("\tLast file edit: {}".format(
                time.strftime("%d.%m.%Y %H:%M", time.gmtime(last_edit))))
        return last_edit == 0 or last_edit > last_sync

    def download(self, course_id, workdir, sync_only=None):
        params = {"cid": course_id}

        with self.session.get(self.url.files_main(), params=params) as response:
            if not response.ok:
                raise DownloadError("Cannot access course files page")
            folder_id = parsers.extract_parent_folder_id(response.text)
            csrf_token = parsers.extract_csrf_token(response.text)

        download_url = self.url.bulk_download(folder_id)
        data = {
            "security_token": csrf_token,
            # "parent_folder_id": folder_id,
            "ids[]": sync_only or folder_id,
            "download": 1
        }

        with self.session.post(download_url, params=params, data=data, stream=True) as response:
            if not response.ok:
                raise DownloadError("Cannot download course files")
            path = os.path.join(workdir, course_id)
            with open(path, "wb") as download_file:
                shutil.copyfileobj(response.raw, download_file)
                return path

    def download_file(self, download_url, tempfile):
        with self.session.post(download_url, stream=True) as response:
            if not response.ok:
                raise DownloadError("Cannot download file")

            with open(tempfile, "wb") as file:
                shutil.copyfileobj(response.raw, file)

    def get_files_index(self, course_id, folder_id=None):
        params = {"cid": course_id}

        if folder_id:
            url = self.url.files_index(folder_id)
        else:
            url = self.url.files_main()

        with self.session.get(url, params=params) as response:
            if not response.ok:
                if response.status_code == 403 and "Documents" in response.text:
                    raise MissingFeatureError("This course has no files")
                elif response.status_code == 403 and "Zugriff verweigert" in response.text:
                    raise MissingPermissionFolderError(
                        "You are missing the required pemissions to view this folder")
                else:
                    raise DownloadError("Cannot access course files/files_index page")
            return parsers.extract_files_index_data(response.text)
