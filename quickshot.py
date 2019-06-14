import argparse
import configparser
import os
import subprocess

parser = argparse.ArgumentParser(description="""
    Take screenshots of two pages and perform a visual difference on them.""")
parser.add_argument('page_a', type=str,
                    help='URL for page you want to compare with.')
parser.add_argument('page_b', type=str,
                    help='URL for page you want to compare against.')
parser.add_argument('-i', '--ini', type=str, help="""
    Which section from the .ini file to load configurations from.""")
parser.add_argument('-w', '--wait', type=int,
                    help='Time in seconds to wait before taking a screenshot.')
# TODO add an argument for a msg to display in report?

args = parser.parse_args()

# The directory screenshots will be saved in.
# TODO test for ini value if none then use this as a default
SCREENSHOT_PATH = "screenshots"


def get_credentials(configuration):
    """Checks for ini and for section passed in configuration."""

    import sys

    try:
        config_parser = configparser.ConfigParser()
        config_parser.read("quickshot.ini")

        email = config_parser.get(configuration, "email")
        password = config_parser.get(configuration, "password")

        return email, password

    except configparser.NoSectionError as e:
        print("""
            !!!!! No config section found.
            Check that `quickshot.ini` exists and that {} is present.""".format(args.ini))
        print("!!!!! {}".format(e))
        sys.exit(1)


def sign_in(driver, page, credentials):
    """
    Sign into a login form with credentials.

    driver: pass in the webdriver object
    page: page being tested
    credentials: email and password returned from get_credentials()

    """
    from selenium.common.exceptions import (
        NoSuchElementException,
        WebDriverException
    )

    try:
        driver.find_element_by_name('email').send_keys(credentials[0])
        driver.find_element_by_name('password').send_keys(credentials[1])
        driver.find_element_by_id('sign-in').click()

    except NoSuchElementException as e:
        print("!!!!! Woops, no element found at {}! {}".format(
            page, e)
        )
        return False
    except WebDriverException as e:
        print("!!!!! Oh no that's an error on {}. {}".format(page, e))
        return False


def check_if_dir_exists(dir_to_check):
    """ Check if a given directory exists, if not create it. """
    if not os.path.exists(dir_to_check):
        os.makedirs(dir_to_check)
        print("----- Created `{}` directory".format(dir_to_check))


# TODO Should make this function more all purpose?
# For example `write_report()` needs the datetime for display and for the file
def popcorn(filetype="png"):
    """
        Get a datetime string and return it formatted for use as a filename.
    """
    import datetime
    import pytz

    time_of_shot = datetime.datetime.now(pytz.utc)
    formated_time = time_of_shot.strftime("quickshot_%Y-%m-%dT%H_%M_%S")

    return "{}.{}".format(formated_time, filetype)


def wait(length_of_wait):
    import time
    time.sleep(int(length_of_wait))


def take_screenshot(page, credentials=None):
    """"
        Use webdriver to take a screenshot of the page.

        credentials: optional vales to sing in to a page

        Currently only using Geckodriver.
        Please note that `save_screenshot` takes full path of the file.
    """
    from selenium import webdriver
    from selenium.common.exceptions import (
        NoSuchElementException,
        WebDriverException
    )

    # TODO add ability to use other webdrivers
    with webdriver.Firefox() as driver:
        driver.get(page)

        if credentials is not None:
            sign_in(driver, page, credentials)

        if args.wait is not None:
            wait(args.wait)

        formated_time = popcorn()
        check_if_dir_exists(SCREENSHOT_PATH)
        driver.save_screenshot("{}/{}".format(SCREENSHOT_PATH, formated_time))
        driver.close()

        # TODO is there something better to return here then formated_time?
        return formated_time


def run_visdif_on_page(page_a, page_b):
    """ Run a visual difference pass of page_a against the page_b."""

    if args.ini is not None:
        credentials = get_credentials(args.ini)
    else:
        credentials = None

    this_screenshot = take_screenshot(page_a, credentials)
    that_screenshot = take_screenshot(page_b, credentials)

    these_visdiff_results = diff_two_images(this_screenshot, that_screenshot)
    produce_report(these_visdiff_results)


def diff_two_images(page_a, page_b):
    """
        Calculate the visual difference between one page and another.

        page_a: the page you are testing.
        page_b: page to compare against.
    """

    # Create a dict to store results from run to make a report from
    visdiff_results = {}

    difference_img_file_name = popcorn()

    # Save the names of the pages
    visdiff_results["page_b"] = page_b
    visdiff_results["diff_result"] = difference_img_file_name
    visdiff_results["page_a"] = page_a
    visdiff_results["path"] = SCREENSHOT_PATH

    # Build the command to pass to check_output()
    # The special "-metric" setting of 'AE' ("Absolute Error" count),
    # will report (to standard error), a count of the actual number of
    # pixels that were masked, at the current fuzz factor.
    # http://www.imagemagick.org/Usage/compare/
    imagemagick_compare_command_string = """
    compare -metric AE {path}/{shot_1} {path}/{shot_2} {path}/{diff_result}""".format(
        shot_1=page_a,
        shot_2=page_b,
        path=SCREENSHOT_PATH,
        diff_result=difference_img_file_name
    )

    try:
        diff_metric_output = subprocess.check_output(
            imagemagick_compare_command_string,
            stderr=subprocess.STDOUT,
            shell=True
        )

        visdiff_results["visdiff_difference"] = float(
            diff_metric_output.decode('ascii')
        )

    # > The compare program returns 2 on error, 0 if the images are similar,
    # > or a value between 0 and 1 if they are not similar.
    # from https://www.imagemagick.org/script/compare.php
    # Need to catch the exception to get the diff value
    except subprocess.CalledProcessError as e:
        try:
            # e.output contains the diff value as a byte string
            formated_difference = float(e.output.decode('ascii'))
            visdiff_results["visdiff_difference"] = formated_difference
            print("----- Difference: {}".format(formated_difference))
        except ValueError:
            print("----- Some error occurred: ({}) ???".format(e.output))

    # Attempt to create a flicker gif
    appended_results = create_flicker_gif(visdiff_results)

    return appended_results


def create_flicker_gif(visdiff_results):
    """
        Test if difference between two screenshots, if so make "flicker" gif.

        'Flicker' refers to an animated gif switching between two results.
    """

    # TODO should I pass in the things i need rather then the whole report
    # I would need to pass in page_a, page_b, and path
    # that way this function is more atomic?
    flicker_img_file_name = popcorn(filetype="gif")
    flicker_img_path = "{}/{}".format(
        visdiff_results["path"],
        flicker_img_file_name
    )

    if float(visdiff_results["visdiff_difference"]) > 0:
        # TODO document options to convert command
        flicker_string = """
        convert -delay 100 {path}/{shot_1} {path}/{shot_2} -loop 0 {flicker}""".format(
            shot_1=visdiff_results["page_a"],
            shot_2=visdiff_results["page_b"],
            path=visdiff_results["path"],
            flicker=flicker_img_path,
        )

        subprocess.call(flicker_string, shell=True)
        print("----- Creating flicker gif at {}".format(flicker_img_path))
        visdiff_results['flicker'] = flicker_img_file_name
    else:
        # TODO I think this should be in diff_two_images instead?
        print("----- No difference between {shot_1} and {shot_2}".format(
            shot_1=visdiff_results["page_a"],
            shot_2=visdiff_results["page_b"]
            )
        )

    return visdiff_results


def write_out_template(dictionary, path, fn, template):
    """
    Render the dictionary using the given template.

    path: the location to write file to
    fn: filename to use
    template: which mustache template use when rendering
    """

    import pystache

    html_path = "{}/{}".format(path, fn)
    results_template = open("_templates/{}".format(template)).read()
    html_results = pystache.render(results_template, dictionary)
    # need to encode to pass to write()
    html_results_encoded = html_results.encode(
        encoding='UTF-8', errors='strict'
    )

    check_if_dir_exists(path)

    with open(html_path, "w") as html_file:
        html_file.write(html_results_encoded.decode('utf-8'))
        print("----- Wrote out {}".format(html_path))


def produce_report(visdiff_results):
    """ Take results from diff_two_images() and produce a report for review."""

    import datetime
    import pytz

    time_of_report = datetime.datetime.now(pytz.utc)
    formated_time = time_of_report.strftime("%Y-%m-%d %H:%M:%S %Z")

    report_file_name = "{}.html".format(
        time_of_report.strftime("quickshot_%Y-%m-%dT%H_%M_%S")
    )
    visdiff_results["when"] = formated_time

    write_out_template(
        visdiff_results,
        "reports",
        report_file_name,
        "quickshot_report.mustache",
    )
    print("----- Results: {}".format(visdiff_results))
    print("##### Done")
    print("""
        You can view your results at reports/{}
    """.format(report_file_name))


print("##### Let's do the diff between {} and {}".format(
    args.page_a, args.page_b)
)

run_visdif_on_page(args.page_a, args.page_b)
