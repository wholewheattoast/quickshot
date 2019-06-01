import argparse
import os
import subprocess

# TODO should I rename 'to_compare_with' to 'base_target'

parser = argparse.ArgumentParser(description='get some stuff')
parser.add_argument('--page', type=str,
                    help='URL for page you want to compare with.')
parser.add_argument('--to_compare_with', type=str,
                    help='URL for page you want to compare against.')
# TODO add an argument for a msg?

args = parser.parse_args()

# Directory screenshots will be saved to.
# TODO should i setup an ini for this instead?
SCREENSHOT_PATH = "screenshots"


def check_if_dir_exists(dir_to_check):
    """ Check if a given directory exists, if not create it. """
    if not os.path.exists(dir_to_check):
        os.makedirs(dir_to_check)
        print("----- Created `{}` directory".format(dir_to_check))


# TODO Should make this function more robust?
# For example, like how write_report needs the datetime in for display and html
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
    from selenium import webdriver

    with webdriver.Firefox() as driver:
        driver.get(page)
        formated_time = popcorn()
        check_if_dir_exists(SCREENSHOT_PATH)
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

    # Create a dict to store results from run to make a report from
    visdiff_results = {}

    difference_img_file_name = popcorn()

    # Save the names of the page and base target
    visdiff_results["base_target"] = to_compare_with
    visdiff_results["diff_result"] = difference_img_file_name
    visdiff_results["page"] = page
    visdiff_results["path"] = SCREENSHOT_PATH

    # Build the command to pass to check_output()
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

    # attempt to create a flicker gif
    appended_results = create_flicker_gif(visdiff_results)

    return appended_results


def create_flicker_gif(visdiff_results):
    """
        Test if difference between two screenshots, if so make "flicker" gif.

        'Flicker' refers to an animated gif switching between two results.
    """

    # TODO should I pass in the things i need rather then the whole report
    # that way this function is more atomic?
    flicker_img_file_name = popcorn(filetype="gif")
    flicker_img_path = "{}/{}".format(
        visdiff_results["path"],
        flicker_img_file_name
    )

    if float(visdiff_results["visdiff_difference"]) > 0:
        # TODO document options to convert
        flicker_string = """
        convert -delay 100 {path}/{shot1} {path}/{shot2} -loop 0 {flicker}""".format(
            shot1=visdiff_results["page"],
            shot2=visdiff_results["base_target"],
            path=visdiff_results["path"],
            flicker=flicker_img_path,
        )

        subprocess.call(flicker_string, shell=True)
        print("----- Creating flicker gif at {}".format(flicker_img_path))
        visdiff_results['flicker'] = flicker_img_file_name
    else:
        # TODO I think this should be in diff_two_images instead?
        print("----- No difference between {shot1} and {shot2}".format(
            shot1=visdiff_results["page"],
            shot2=visdiff_results["base_target"]
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
        print("----- Wrote out: {}".format(html_path))


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
    print("!!!!! Done")
    print("""
        You can view your results at "reports/{}"
    """.format(report_file_name))


print("!!!!! Let's do the diff between {} and {}".format(
    args.page, args.to_compare_with)
)
run_visdif_on_page(args.page, args.to_compare_with)
