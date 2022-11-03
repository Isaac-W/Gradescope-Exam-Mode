import time
import datetime
import json
from selenium.webdriver.common.by import By


def try_get(function, default=None):
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
    def __init__(self, course_id, name="", description=""):
        self.id = course_id
        self.name = name
        self.description = description

    @property
    def url(self):
        return f"{Gradescope.ROOT_URL}/courses/{self.id}"

    def __str__(self):
        return f"{self.id} | {self.name} | {self.url}"


class Assignment():
    def __init__(self, course_id, assignment_id, name="", release_date="", due_date="", hard_due_date="", published=False):
        self.course_id = course_id
        self.id = assignment_id
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

    def open(self, url):
        self.driver.get(url)
    
    def login(self):
        self.open(self.LOGIN_URL)
        
        if self.driver.current_url == self.LOGIN_URL:
            print("\n==> Please log in to Gradescope!")
            while self.driver.current_url == self.LOGIN_URL:
                time.sleep(2)

    def get_courses(self):
        courses = []
        self.open(self.ACCOUNT_URL)
        elements = self.driver.find_elements(By.CSS_SELECTOR, "a.courseBox")
        for e in elements:
            cid = e.get_attribute("href").strip(Gradescope.COURSES_URL)
            course = Course(cid)
            courses.append(course)

            # Get optional attributes
            course.name = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".courseBox--shortname").text, "")
            course.desc = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".courseBox--name").text, "")
        return courses

    def get_assignments(self, course_id):
        assignments = []
        self.open(f"{self.COURSES_URL}/{course_id}")
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".js-assignmentTableAssignmentRow")
        for e in elements:
            aid = e.get_attribute("data-assignment-id")
            assignment = Assignment(course_id, aid)
            assignments.append(assignment)

            # Get optional attributes
            assignment.name = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".assignments--rowTitle").text, "")
            
            assignment.release_date = self.parse_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--releaseDate").text.lower()))
            assignment.due_date = self.parse_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--dueDate").text.lower()))
            assignment.hard_due_date = self.parse_date(try_get(lambda: e.find_element(By.CSS_SELECTOR, ".submissionTimeChart--hardDueDate").text.lower().strip("late due date: ")))

            # Get published state
            assignment.published = len(e.find_elements(By.CSS_SELECTOR, ".workflowCheck-complete")) > 0
        return assignments

    def update_assignment(self, assignment):
        self.open(f"{assignment.url}/edit")

        # Check for date field existence
        date_field = self.driver.find_element(By.CSS_SELECTOR, "#assignment-form-dates-and-submission-format")
        style_str = date_field.get_attribute("style")
        if "none" not in style_str:
            # Update release date
            if assignment.release_date:
                release = date_field.find_element(By.CSS_SELECTOR, "#assignment_release_date_string")
                release.clear()
                release.send_keys(self.format_date(assignment.release_date))

            # Update due date
            if assignment.due_date:
                due = date_field.find_element(By.CSS_SELECTOR, "#assignment_due_date_string")
                due.clear()
                due.send_keys(self.format_date(assignment.due_date))

            # Update late due date (enable/disable it if needed)
            late = date_field.find_element(By.CSS_SELECTOR, "#assignment_hard_due_date_string")
            late_check = date_field.find_element(By.CSS_SELECTOR, "#allow_late_submissions")
            if assignment.hard_due_date:
                if not late.text:
                    self.driver.execute_script("arguments[0].click()", late_check)
                
                late.clear()
                late.send_keys(self.format_date(assignment.hard_due_date))
            else:
                if late.text: # Uncheck late submissions
                    self.driver.execute_script("arguments[0].click()", late_check)

        # TODO Not a full API -- could easily be modified to update name, etc.

        # Save the form
        save_button = self.driver.find_element(By.CSS_SELECTOR, "#assignment-actions input")
        save_button.click()

        # Update published state
        review_url = f"{assignment.url}/review_grades"
        if self.driver.current_url != review_url:
            self.open(review_url)
        
        if assignment.published:
            publish_button = try_get(lambda: self.driver.find_element(By.CSS_SELECTOR, ".review-grades-next-button"))
            if publish_button:
                publish_button.click()
        else:
            unpublish_form = try_get(lambda: self.driver.find_element(By.CSS_SELECTOR, ".button_to"))
            if unpublish_form:
                unpublish_form.submit()

    @staticmethod
    def parse_date(date_string):
        if not date_string:
            return None
        
        ''' Using RegEx
        result = re.match(r"(\w+ \d+) at ([0-9:]+)(\w+)", date_string)
        if not result:
            return ""
        return f"{result.group(1)} {datetime.date.today().year} {result.group(2)} {result.group(3)}"
        '''
        
        # TODO: Inserting current year (the assignment page doesn't display years)
        return datetime.datetime.strptime(date_string, "%b %d at %I:%M%p").replace(year=datetime.date.today().year)

    @staticmethod
    def format_date(date):
        if not date:
            return ""

        return datetime.datetime.strftime(date, "%b %d %Y %I:%S %p")


if __name__ == "__main__":
    browser = WebDrivers.EDGE  # Browsers: CHROME, FIREFOX, EDGE

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
    

    # Disable all assignments
    for i, a in enumerate(assignments):
        print(f"Disabling {i} of {len(assignments)}: {a.name}")

        if a.release_date:
            a.release_date = a.release_date.replace(year=9999)

        if a.due_date:
            a.due_date = a.due_date.replace(year=9999)

        if a.hard_due_date:
            a.hard_due_date = a.hard_due_date.replace(year=9999)

        a.published = False

        #gscope.update_assignment(a)

    input("Press ENTER to quit.")
    gscope.close()
