import time
import datetime
import re
from selenium import webdriver
from selenium.webdriver.common.by import By


def try_get(function, default=""):
    try:
        return function()
    except:
        return default


class WebDrivers():
    CHROME = 1
    FIREFOX = 2
    EDGE = 3

    @staticmethod
    def get(driver_type):
        options = None

        if driver_type == WebDrivers.CHROME:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager as DriverManager
            from selenium.webdriver import Chrome as Driver

            options = Options()
            options.add_argument('log-level=3')
        elif driver_type == WebDrivers.FIREFOX:
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            from webdriver_manager.firefox import GeckoDriverManager as DriverManager
            from selenium.webdriver import Firefox as Driver

            options = Options()
            options.log.level = "fatal"
        elif driver_type == WebDrivers.EDGE:
            from selenium.webdriver.edge.options import Options
            from selenium.webdriver.edge.service import Service
            from selenium.webdriver import Edge as Driver
            from webdriver_manager.microsoft import EdgeChromiumDriverManager as DriverManager

            options = Options()
            options.add_argument('log-level=3')
        else:
            return None

        return Driver(service=Service(DriverManager().install()), options=options)


class Course():
    def __init__(self, id, name="", description=""):
        self.id = id
        self.name = name
        self.description = description

    @property
    def url(self):
        return f"{Gradescope.ROOT_URL}/courses/{self.id}"

    def __str__(self):
        return f"{self.id} | {self.name} | {self.url}"


class Assignment():
    def __init__(self, course_id, id, name="", release_date="", due_date="", hard_due_date="", published=False):
        self.course_id = course_id
        self.id = id
        self.name = name
        self.release_date = release_date
        self.due_date = due_date
        self.hard_due_date = hard_due_date
        self.published = published

    @property
    def url(self):
        return f"{Gradescope.ROOT_URL}/courses/{course_id}/assignments/{self.id}"

    def __str__(self):
        return f"{self.id} | {self.name} | {self.url}"


class Gradescope():
    ROOT_URL = "https://www.gradescope.com"
    LOGIN_URL = f"{ROOT_URL}/login"
    ACCOUNT_URL = f"{ROOT_URL}/account"
    COURSES_URL = f"{ROOT_URL}/courses"

    def __init__(self, webdriver):
        self.driver = webdriver
    
    def close(self):
        self.driver.quit()

    def load(self, url):
        self.driver.get(url)
    
    def login(self):
        self.load(self.LOGIN_URL)
        
        if self.driver.current_url == self.LOGIN_URL:
            print("\n==> Please log in to Gradescope!")
            while self.driver.current_url == self.LOGIN_URL:
                time.sleep(2)

    def get_courses(self):
        courses = []
        self.load(self.ACCOUNT_URL)
        elements = self.driver.find_elements(By.CSS_SELECTOR, "a.courseBox")
        for e in elements:
            id = e.get_attribute("href").strip(Gradescope.COURSES_URL)
            course = Course(id)
            courses.append(course)

            # Get optional attributes
            course.name = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".courseBox--shortname").text)
            course.desc = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".courseBox--name").text)
        return courses

    def get_assignments(self, course_id):
        assignments = []
        self.load(f"{self.COURSES_URL}/{course_id}")
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".js-assignmentTableAssignmentRow")
        for e in elements:
            id = e.get_attribute("data-assignment-id")
            assignment = Assignment(course_id, id)
            assignments.append(assignment)

            # Get optional attributes
            assignment.name = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".assignments--rowTitle").text)
            
            assignment.release_date = self.format_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--releaseDate").text.lower()))
            assignment.due_date = self.format_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--dueDate").text.lower()))
            assignment.hard_due_date = self.format_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--hardDueDate").text.lower().strip("late due date: ")))
        return assignments

    @staticmethod
    def format_date(date_string):
        if not date_string:
            return ""

        print(date_string)
        result = re.match(r"(\w+ \d+) at ([0-9:]+)(\w+)", date_string)
        print(result)

        # TODO: Inserting current year (the assignment page doesn't display years)
        return f"{result.group(1)} {datetime.date.today().year} {result.group(2)} {result.group(3)}"


if __name__ == "__main__":
    browser = WebDrivers.EDGE  # Browsers: CHROME, FIREFOX, EDGE
    course_url = "https://www.gradescope.com/courses/426823"

    print("Initializing WebDriver...")
    gscope = Gradescope(WebDrivers.get(browser))
    gscope.login()

    courses = gscope.get_courses()
    for x in courses:
        print(x)

    courses = {x.id: x for x in courses}
    course_id = None
    while (course_id := input("Enter a course ID: ")) not in courses:
        print("Invalid course ID, try again!")
    
    assignments = gscope.get_assignments(course_id)
    for a in assignments:
        print(a)

    input("Press ENTER to quit.")
    gscope.close()
