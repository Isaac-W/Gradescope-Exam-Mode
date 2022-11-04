import sys
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
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"

    @staticmethod
    def get(driver_type):
        driver_type = driver_type.lower()
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

        print(f"Initializing {driver_type.title()} WebDriver...")
        return Driver(service=Service(DriverManager().install()), options=options)


class Course():
    def __init__(self, course_id, name="", description=""):
        self.type = "Course"
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
        self.type = "Assignment"
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

    SLEEP_TIME = 1

    def __init__(self, webdriver):
        self.driver = webdriver
    
    def close(self):
        self.driver.quit()

    def open(self, url, refresh=False):
        if refresh or self.driver.current_url != url:
            self.driver.get(url)
    
    def prompt_login(self):
        self.open(self.LOGIN_URL)
        print("\n==> Please log in to Gradescope!\n")
        
        # Wait for URL to change
        if self.driver.current_url == self.LOGIN_URL:
            while self.driver.current_url == self.LOGIN_URL:
                time.sleep(self.SLEEP_TIME)

    def prompt_select_course(self):
        # Modify header to prompt user
        self.open(self.ACCOUNT_URL)
        self.driver.execute_script("""e = document.querySelector(".pageHeading"); e.textContent = "Please select a course below:"; e.style.fontWeight = "bold";""")
        
        # Wait until user selects a course
        course_id = ""
        while not (course_id := self.driver.current_url.strip(f"{self.COURSES_URL}/")).isnumeric():
            time.sleep(self.SLEEP_TIME)
        return course_id

    def prompt_assignment_command(self, course_id):
        assignments_url = f"{self.COURSES_URL}/{course_id}"
        self.open(assignments_url)
        
        # Add buttons for disable/enable assignments
        header = self.driver.find_element(By.CSS_SELECTOR, ".courseHeader")
        self.driver.execute_script("""arguments[0].innerHTML += '<br><a class="actionBar--action" href="#save_details">Save Assignment Details</a><a class="actionBar--action" href="#disable_all">Disable All</a><button type="button" class="actionBar--action" id="enable_all_btn">Update All...</button><input type="file" id="filepicker" style="display: none;" />';""", header)
        
        # Make magic file picker
        self.driver.execute_script("""
        fileinput = document.querySelector("#filepicker");
        fileinput.onchange = () => {
            window.location = "#enable_all";
        };
        
        button = document.querySelector("#enable_all_btn");
        button.onclick = () => {
            fileinput.click();
        };
        """)

        # Wait for user to make a selection
        command = ""
        while ("#" not in self.driver.current_url) or not (command := self.driver.current_url.split("#")[1]):
            time.sleep(self.SLEEP_TIME)
        return command

    def load_filepicker_data(self):
        self.driver.set_script_timeout(300)  # Wait for 5 minutes
        data = self.driver.execute_async_script("""
        done = arguments[0];
        fileinput = document.querySelector("#filepicker");
        fr = new FileReader();
        fr.onload = () => {
            console.log(fr.result);
            console.log(fr.result.length);
            done(fr.result);
        };
        fr.readAsText(fileinput.files[0]);
        """)
        #self.driver.set_script_timeout(0)
        return data

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
            course.description = try_get(lambda: e.find_element(By.CSS_SELECTOR, ".courseBox--name").text, "")
        return courses

    def get_assignments(self, course_id):
        assignments = []
        self.open(f"{self.COURSES_URL}/{course_id}/assignments")
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
        style_str = try_get(lambda: date_field.get_attribute("style"), "")
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
                if late.get_attribute("disabled"):
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


class GscopeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Course, Assignment)):
            return obj.__dict__
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class GscopeDecoder(json.JSONDecoder):
    @staticmethod
    def parse_time(time):
        return datetime.datetime.fromisoformat(time) if time else None

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        if "type" in dct:
            if dct["type"] == "Course":
                return Course(
                    course_id=dct["id"],
                    name=dct["name"],
                    description=dct["description"]
                )
            elif dct["type"] == "Assignment":
                return Assignment(
                    course_id=dct["course_id"],
                    assignment_id=dct["id"],
                    name=dct["name"],
                    release_date=self.parse_time(dct["release_date"]),
                    due_date=self.parse_time(dct["due_date"]),
                    hard_due_date=self.parse_time(dct["hard_due_date"]),
                    published=dct["published"]
                )
        return dct


if __name__ == "__main__":
    driver = WebDrivers.get(sys.argv[1] if len(sys.argv) > 1 else "")
    while not driver:
        browser = input("Enter a browser name (chrome, firefox, edge): ")
        driver = WebDrivers.get(browser)
    
    gscope = Gradescope(driver)
    gscope.prompt_login()

    ''' Old command-line method
    courses = gscope.get_courses()
    for x in courses:
        print(x)
    print()

    courses = {x.id: x for x in courses}
    course_id = None

    while (course_id := input("Enter a course ID: ")) not in courses:
        print("Invalid course ID, try again!")
    '''

    course_id = gscope.prompt_select_course()
    command = gscope.prompt_assignment_command(course_id)
    
    if command == "save_details":
        print("Getting all assignment details...")
        assignments = gscope.get_assignments(course_id)
        print(f"Loaded {len(assignments)} entries.")

        # Save through browser
        json_string = json.dumps(assignments, indent=4, cls=GscopeEncoder)
        save_script = f"""
        var file = new Blob([arguments[0]], {{
            type: "application/json"
        }});
        var a = document.createElement("a");
        a.href = URL.createObjectURL(file);
        a.download = "assignments_{course_id}.json";
        a.click();
        """
        driver.execute_script(save_script, json_string)
    elif command == "disable_all":
        print("Getting all assignment details...")
        assignments = gscope.get_assignments(course_id)
        print(f"Loaded {len(assignments)} entries.")

        """ Save through Python
        json_filename = input("Enter a filename to save assignment details (.json): ")
        if json_filename:
            json_filename = json_filename.strip(".json") + ".json"
            with open(json_filename, 'w') as file:
                json.dump(assignments, file, indent=4, cls=GscopeEncoder)
            print("Saved to: {json_filename}")
        """

        # Save through browser
        json_string = json.dumps(assignments, indent=4, cls=GscopeEncoder)
        save_script = f"""
        var file = new Blob([arguments[0]], {{
            type: "application/json"
        }});
        var a = document.createElement("a");
        a.href = URL.createObjectURL(file);
        a.download = "assignments_{course_id}.json";
        a.click();
        """
        driver.execute_script(save_script, json_string)

        # Disable all assignments
        #input("Press ENTER to begin updating assignments.")
        for i, a in enumerate(assignments):
            print(f"Disabling {i + 1} of {len(assignments)}: {a.name}")

            if a.release_date:
                a.release_date = a.release_date.replace(year=9999)

            if a.due_date:
                a.due_date = a.due_date.replace(year=9999)

            if a.hard_due_date:
                a.hard_due_date = a.hard_due_date.replace(year=9999)

            a.published = False

            gscope.update_assignment(a)
        print("Done.")
    elif command == "enable_all":
        raw_data = gscope.load_filepicker_data()
        assignments = json.loads(raw_data, cls=GscopeDecoder)
        print(f"Loaded {len(assignments)} entries.")

        #input("Press ENTER to begin updating assignments.")
        for i, a in enumerate(assignments):
            print(f"Updating {i + 1} of {len(assignments)}: {a.name}")
            gscope.update_assignment(a)
        print("Done.")


    gscope.close()
    input("\n==> Press ENTER to quit.")
