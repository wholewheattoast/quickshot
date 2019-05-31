import argparse
import logging
import os
from selenium import webdriver
import subprocess

# TODO should I rename 'to_compare_with' to 'base_target'


parser = argparse.ArgumentParser(description='get some stuff')
parser.add_argument('--page', type=str,
                    help='URL for page you want to compare with.')
parser.add_argument('--to_compare_with', type=str,
                    help='URL for page you want to compare against.')
# add an argument for a msg?

args = parser.parse_args()

log = logging.getLogger(__name__)

# Where am I saving these files for now?
# TODO if i'm going to put these in a local dir i should check if it exists,
#  and create if needed
SCREENSHOT_PATH = "screenshots"

# check that the screenshot path exists
if not os.path.exists(SCREENSHOT_PATH):
    os.makedirs(SCREENSHOT_PATH)
    print(".......... Created  {}".format(SCREENSHOT_PATH))


def popcorn(filetype="png"):
    """
        Get a datetime string and return it formatted for use as a filename.

        Extension defaults to `.png` in returned string.
    """
    import datetime
    import pytz

    time_of_shot = datetime.datetime.now(pytz.utc)
    formated_time = time_of_shot.strftime("quickshot_%Y-%m-%dT%H_%M_%S")

    return "{}.{}".format(formated_time, filetype)


def take_screenshot(page):
    """"
    Use webdriver to take a screenshot of the page.

    Currently using Geckodriver.
    Please note that `save_screenshot` takes full path of the file.
    """

    with webdriver.Firefox() as driver:
        driver.get(page)
        formated_time = popcorn()
        driver.save_screenshot("{}/{}".format(SCREENSHOT_PATH, formated_time))
        driver.close()
        return formated_time


def run_visdif_on_page(page, to_compare_with):
    """ Run a visdiff pass on a page against the to_compare_with."""

    this_screenshot = take_screenshot(args.page)
    that_screenshot = take_screenshot(args.to_compare_with)
    these_visdiff_results = diff_two_images(this_screenshot, that_screenshot)
    produce_report(these_visdiff_results)


# TODO i really need better names
def diff_two_images(page, to_compare_with):
    """
        Calculate the visual difference between a page and a base target.

        page: the page you are testing.
        to_compare_with: the base target you are comparing against
    """

    # create a dict to store results from run to make a report from
    visdiff_results = {}

    difference_img_file_name = popcorn()

    # save the names of the page and base target
    visdiff_results["base_target"] = to_compare_with
    visdiff_results["diff_result"] = difference_img_file_name
    visdiff_results["page"] = page
    visdiff_results["path"] = SCREENSHOT_PATH

    # build the command to pass to check_output()
    # The special "-metric" setting of 'AE' ("Absolute Error" count),
    # will report (to standard error), a count of the actual number of
    # pixels that were masked, at the current fuzz factor.
    # http://www.imagemagick.org/Usage/compare/
    imagemagick_compare_command_string = """
    compare -metric AE {path}/{page} {path}/{to_compare_with} {path}/{diff_result}""".format(
        page=page,
        to_compare_with=to_compare_with,
        path=SCREENSHOT_PATH,
        diff_result=difference_img_file_name
    )

    print("----- Going to try")
    print(imagemagick_compare_command_string)

    try:
        diff_metric_output = subprocess.check_output(
            imagemagick_compare_command_string,
            stderr=subprocess.STDOUT,
            shell=True
        )

        visdiff_results["visdiff_difference"] = int(
            diff_metric_output.decode('ascii')
        )

    except subprocess.CalledProcessError as e:
        log.info("....... exception output:  {}".format(e.output))
        diff_metric_output = e.output
        try:
            visdiff_results["visdiff_difference"] = float(
                e.output.decode('ascii')
            )
        except ValueError:
            # Some unrecoverable error occurred.
            # need a better error here?
            print("----- Some error occurred: ({})".format(e.output))

    # attempt to create a flicker gif
    appended_results = create_flicker_gif(visdiff_results)

    return appended_results


def create_flicker_gif(visdiff_results):
    """ Test if difference between two screenshots, and if so make "flicker" gif

        'flicker' refers to an animated gif switching between two results.
    """

    flicker_img_path = "{}/{}".format(
        visdiff_results["path"],
        popcorn(filetype="gif")
    )

    if float(visdiff_results["visdiff_difference"]) > 0:
        flicker_string = "convert -delay 100 {path}/{shot1} {path}/{shot2} -loop 0 {flicker}".format(
            shot1=visdiff_results["page"],
            shot2=visdiff_results["base_target"],
            path=visdiff_results["path"],
            flicker=flicker_img_path,
        )

        subprocess.call(flicker_string, shell=True)
        print("----- creating flicker gif at {}".format(flicker_img_path))
        visdiff_results['flicker'] = flicker_img_path
    else:
        log.warning(
            "....... No difference between {shot1} and {shot2}".format(
                shot1=visdiff_results["page"],
                shot2=visdiff_results["base_target"]
            )
        )

    return visdiff_results


def produce_report(visdiff_results):
    """ Take results from diff_two_images() and produce a report for review."""
    print("----- prepare results")
    # need to json load the visdiff_results
    # pass into a template (mustache?)
    # let's base the report on qatool
    # return the file name
    print(visdiff_results)


print("Let's do the diff between {} and {}.".format(
    args.page, args.to_compare_with)
)
run_visdif_on_page(args.page, args.to_compare_with)
