import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Synchronize Stud.IP files")

    parser.add_argument("-c", "--config", metavar="DIR",
                        default=None,
                        help="set the path to the config dir (Default is "
                             "'~/.config/studip-sync/')")

    parser.add_argument("-d", "--destination", metavar="DIR", default=None,
                        help="synchronize files to the given destination directory (If no config "
                             "is present this argument implies --full)")

    parser.add_argument("--init", action="store_true",
                        help="create new config file interactively")

    parser.add_argument("--full", action="store_true",
                        help="downloads all courses instead of only new ones")

    parser.add_argument("--recent", action="store_true",
                        help="only download the courses of the recent semester")

    parser.add_argument("-v", action="store_true",
                        help="show debug output")

    return parser.parse_known_args()[0]


ARGS = parse_args()
