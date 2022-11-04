# Gradescope Exam Mode
Automatically disable all assignments in a Gradescope course and then re-enable them. Great for exams.

Uses Selenium WebDriver to automate browser actions.

## Disclaimer
Because Gradescope does not have an API, this is done solely with querying CSS selectors and injecting some crazy JavaScript. This means that this program may inexplicably break in the future. Thus, use at your own risk. I am NOT RESPONSIBLE for anything that goes wrong. (In my tests, it works pretty well tho :P)

## Requirements
Python 3.7 or greater.
You will also need the following packages installed:
```
selenium==4.5.0
webdriver-manager==3.8.4
```
Use the included `requirements.txt` to easily install these packages:
```
pip install -r requirements.txt
```

## Startup
Run the `gradescope.py` file from the command line, with the name of a browser (chrome, firefox, edge) as the first argument:
```
python gradescope.py chrome
```

If you don't provide a command line argument, the program will prompt you to type in the name of a browser and then hit Enter to continue.

## Usage

1. Run the program from the command line.
2. Once a browser instance opens, login to Gradescope.
3. Click on a course to open it.
4. At the top, you will see three new buttons, "Save Assignment Details", "Disable All", and "Enable All...".
    * **Save Assignment Details** will download the current assignment details to a `.json` file. Keep this safe!
    * **Disable All** will first download all the current assignment details, then disable and unpublish all assignments in the selected course.
    * **Update All...** will ask you to select the `.json` file containing the assignment details, which it will use to update the assignment details (due dates + published state).
5. Once the program is finished, go back to the command line and press Enter to quit.
