# quickshot
Make a quick visualdiff between two pages.


## Requirements
Currently Quickshot only uses the Geckodriver webdriver.
Downloading and installing [Firefox](https://www.mozilla.org/en-US/firefox/new/) should be sufficient to get you set up.
Ensure Firefox is in your path after installing.

You should also have ImageMagick installed.
Test if you already have ImageMagick installed by running, `convert -version` in your terminal.

### Installing ImageMagick
- On a Mac run, `brew install imagemagick`
- [Windows binaries](https://imagemagick.org/script/download.php#windows)
- [Unix Binaries](https://imagemagick.org/script/download.php#unix)


## Installation
- Set up a virtuanenv in some fashion, `vex --python /usr/local/bin/python3 -m quickshot`
- Install dependencies `pip3 install -r requirements.txt`


## ini files
You can add credentials to sign in to a web form in a file called 'quickshot.ini'.

Since the .ini is included in the `.gitignore` file, (To help prevent you from committing your credentials to the cloud), you'll first need to create it.

Each block can contain an `email` and `password` items.

Quickshot will attempt to use `webdriver.find_element_by_name()` to locate elements on the page that correspond to these values.

An example configuration block might look like;
```
[example]
email = doe@example.com
password = foobar
```


## Usage
Quickshot takes two required arguments being the urls of the two pages you want to compare.
```python quickshot.py "http://www.google.com" "http://www.google.fr"```

There are also two optional arguments;
- `-w, --wait`, length in seconds to wait after loading a page before taking a screenshot.
- `-i, --ini`, named section to load from `quickshot.ini` configuration file.
