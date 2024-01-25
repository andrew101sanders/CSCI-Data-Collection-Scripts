'''
Andrew Sanders
----------------------------

Overview:
    Using your provided AU credentials, this script downloads all assignments of all D2L "CSCI" courses in which the user is an "Instructor" to the course.
    It uses a local downloads folder to download all assignments and deletes all irrelevant files based on file extension.
    When finished, it combines all downloaded files into "downloads.zip".

Notes:
    - It uses the selenium webdriver with the chromedriver.exe to create a headless chrome browser and download all submissions.
        (download the correct version from https://googlechromelabs.github.io/chrome-for-testing/ depending on your chrome version)
    - It will automatically go through the DUO prompt and wait for you to accept it using the default authentication method.
    - Once it is finished, it will print "finished" in the console and "downloads.zip" should be available in the folder.

Running Instructions:
    1. Download and Install all requirements
       a. Make sure to put the chromedriver in the same folder as this script
    2. Change the username and password strings (lines 40 and 41) to your AU credentials
    3. Run this script ("Python download_D2L_submissions.py")
    4. Wait until downloads.zip is produced. This will happen the same time "finished" is written to the console.

Tested with:
Windows 11 23H2
Python 3.12.1 https://www.python.org/downloads/release/python-3121/ (Windows Installer 64-bit)
Chrome version 120.0.6099.225
chromedriver version 120.0.6099.224 https://googlechromelabs.github.io/chrome-for-testing/ (put in the same folder as this script)

Python package requirements (use in terminal after downloading and installing Python):
pip install beautifulsoup4==4.12.3
pip install Requests==2.31.0
pip install selenium==4.17.2


This script is adapted from a similar script that targetted Georgia Southern University's "Folio" system, which is the same D2L system AU uses.

'''

# Replace with your credentials and preferences
username = 'username' # just username, no email (i.e. 'asanders4' not 'asanders4@augusta.edu')
password = 'password' # The password gets used to login to D2L

if username == 'username' or password == 'password':
    print("Make sure to replace 'username' and 'password' in the python script before running!")
    print("(also I hope that you accidentally left 'username' or 'password' as their defaults values and those aren't your actually credentials)")
    exit()

from time import sleep
#from getpass import getuser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
#import pickle
from os.path import isfile
from os import getcwd,listdir
import os
from pathlib import Path
import requests
import shutil
import zipfile
import re
import io
import tokenize
from bs4 import BeautifulSoup
#import ast


executable_path = f'{getcwd()}/chromedriver.exe'
print(f"Chromedriver path: {executable_path}")

hostname_url = 'https://lms.augusta.edu'
home_url = f'{hostname_url}/d2l/home'
login_url = f'{hostname_url}/d2l/lp/auth/saml/login'
session_expired_url = f'{hostname_url}/d2l/login?sessionExpired=0&target=%2fd2l%2fhome'
advanced_course_search_url = f'{hostname_url}/d2l/le/manageCourses/search/6606'

allowed_extensions = [
    # Code file extensions
    '.txt',   # Text file
    '.py',    # Python
    '.java',  # Java
    '.js',    # JavaScript
    '.c',     # C
    '.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hxx', '.hh', '.h++',  # C++
    '.cs',    # C#
    '.php',   # PHP
    '.rb',    # Ruby
    '.swift', # Swift
    '.m', '.h', # Objective-C
    '.go',    # Go
    '.kt', '.kts', # Kotlin
    '.ts',    # TypeScript
    '.scala', # Scala
    '.r',     # R
    '.pl', '.pm', # Perl
    '.lua',   # Lua
    '.sh', '.bash', # Shell scripts
    '.vb',    # Visual Basic .NET
    '.fs', '.fsx', # F#
#    '.groovy', '.gvy', '.gy', '.gsh', # Groovy
    '.dart',  # Dart
    '.rs',    # Rust
    '.hs', '.lhs', # Haskell
#    '.m',     # MATLAB
#
#    # Additional file extensions for college CS courses
#    '.md', '.markdown', # Markdown
    '.ipynb',           # Jupyter Notebook
#    'Makefile',         # Makefile
#    '.json',            # JSON
#    '.xml',             # XML
#    '.yaml', '.yml',    # YAML
    '.sql',             # SQL
    '.css',             # CSS
    '.html', '.htm',    # HTML
    '.jar',             # Java Archive
#    '.log',             # Log
]

def remove_java_comments(java_code):
    # Remove single-line comments (//...)
    single_line_comment_pattern = r"//.*"
    java_code = re.sub(single_line_comment_pattern, '', java_code)

    # Remove multi-line comments (/*...*/)
    multi_line_comment_pattern = r"/\*[\s\S]*?\*/"
    java_code = re.sub(multi_line_comment_pattern, '', java_code)

    return java_code

def remove_python_comments_and_docstrings(source):
    io_obj = io.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        ltext = tok[4]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
                if prev_toktype != tokenize.NEWLINE:
                    if start_col > 0:
                        out += token_string
        else:
            out += token_string
        prev_toktype = token_type
        last_col = end_col
        last_lineno = end_line
    out = '\n'.join(l for l in out.splitlines() if l.strip())
    return out

def download_file(session, url, file_path):
    reply = session.get(url, stream=True)
    with open(file_path, 'wb') as file:
        for chunk in reply.iter_content(chunk_size=1024): 
            if chunk:
                file.write(chunk)

def zip_directory(folder_path, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

if __name__ == '__main__':

    # make directory if it doesn't exist
    if not os.path.exists(f"{getcwd()}/downloads/"):
        os.makedirs(f"{getcwd()}/downloads/")
    else:
        for root, dirs, files in os.walk(f"{getcwd()}/downloads/", topdown=False):
            for directory in dirs:
                os.rmdir(os.path.join(root, directory))
            for file in files:
                os.remove(os.path.join(root, file))

    if os.path.isfile(os.path.join(f"{getcwd()}", "downloads.zip")):
        os.remove(os.path.join(f"{getcwd()}", "downloads.zip"))

    s = requests.Session()

    # Initialize the WebDriver and authenticate
    options = webdriver.ChromeOptions()

    # Use existing broswer session. Warning: Will close all tabs
    #options.add_argument(f'user-data-dir=C:/Users/{getuser()}/AppData/Local/Google/Chrome/User Data/')
    prefs = {'download.prompt_for_download': False,
            'download.default_directory': f"{getcwd()}/downloads",
            'download.directory_upgrage': True,
            'profile.default_content_settings.popups': 0,
            }
    options.add_experimental_option("prefs",prefs)
    
    #options.add_argument("--headless")
    driver = webdriver.Chrome(options=options, service = Service(executable_path))
    original_window = driver.current_window_handle


    # # Go to homepage and load previously stored cookies if they exist
    # driver.get(home_url)
    # if isfile("cookies.pkl"):
    #     cookies = pickle.load(open("cookies.pkl", "rb"))
    #     for cookie in cookies:
    #         driver.add_cookie(cookie)
    # driver.refresh()
    # sleep(1)

    # go through Duo auth process
    print("Attempting DUO Authentication")
    if driver.current_url != home_url:
        print("Going to login url")
        driver.get(login_url)
        print("Inputting username and password")
        driver.find_element(By.ID, 'userNameInput').send_keys(username)
        driver.find_element(By.ID, 'passwordInput').send_keys(password)
        print("Pressing enter")
        driver.find_element(By.ID, 'passwordInput').send_keys(Keys.ENTER)
        driver.switch_to.default_content()
    print("Waiting for DUO Authentication")
    WebDriverWait(driver, 50).until(EC.url_to_be(home_url) or EC.url_to_be(session_expired_url))
    print("DUO Authentication appears successful")

    if driver.current_url == session_expired_url:
        driver.get(home_url)

    WebDriverWait(driver, 30).until(EC.url_to_be(home_url))
    print("Successfully redirected to home url")

    # Dumping cookies so it doesn't need to login every time
    # cookies = driver.get_cookies()
    # pickle.dump(cookies, open("cookies.pkl", "wb"))

    # for cookie in cookies:
    #     s.cookies.set(cookie['name'], cookie['value'])

    # Wait for the page to load
    print("Going to advanced course search")
    driver.get(advanced_course_search_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[3]/d2l-input-search')))
    print("At advanced course search")

    # only get CSCI courses
    print("Entering CSCI into search bar")
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div[3]/d2l-input-search").send_keys("CSCI")
    print("Sending Enter Key")
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div[3]/d2l-input-search").send_keys(Keys.ENTER)

    # only get courses in which the user was an Instructor
    print("Finding course role dropdown menu")
    select = Select(driver.find_element(By.XPATH, "/html/body/div[2]/div/form/div[1]/div/div/div/div/div[1]/div/select"))
    print("Clicking element with 'Instructor' role")
    select.select_by_visible_text("Instructor")
    print("Successfully clicked 'Instructor' Role")

    # get courses from all semesters
    print("Finding semester dropdown menu")
    select = Select(driver.find_element(By.XPATH, "/html/body/div[2]/div/form/div[1]/div/div/div/div/div[2]/div/select"))
    print("Clicking element with 'All' semester")
    select.select_by_visible_text("All")
    print("Successfully clicked 'All' semester")

    # little hack to load all courses
    print("Executing script to set '100 per page' to actually use 1000")
    driver.execute_script("document.evaluate('/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]', document, null, XPathResult.ANY_TYPE, null).iterateNext().value = 1000;")
    print("Executed script, waiting 2 seconds")
    sleep(2)
    print("Finding dropdown menu containing the 'x per page' options")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select')))
    sleep(2)
    print("Checking if downdown menu is visible, indicating that there are courses found")
    if not driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select').is_displayed():
        print("Dropdown menu is not displayed, which mean the search result failed. 'CSCI' and 'Instructor' seemed to not return any results")
        print("Ending program")
        quit()
    print("Clicking dropdown menu containing the 'x per page' options")
    driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select').click()
    print("Waiting for options to load")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]')))
    print("Clicking '100 per page' dropdown menu option, which will load 1000 courses")
    driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]').click()
    print("Clicked '100 per page' dropdown menu option, waiting")
    sleep(1)

    # loop through table of courses and add each course name and id to a list
    print("Looping through courses that contain a 'd2l-link', i.e., course name is a link")
    courses = []
    table = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/d2l-table-wrapper/table').find_elements(By.CLASS_NAME, 'd2l-link')
    print(f"Total found courses in table: {len(table)}")
    for row in table:
        course_name = row.text
        course_id = row.get_attribute("href").split("/")[-1]
        print(f"\tFound course: {course_name}, course_id: {course_id}")
        courses.append((course_name, course_id))

    # visit each course's page and get all of the assignments
    print("Going through each course and going through each assignment")
    all_assignments = []
    for course in courses:
        course_name = course[0].replace('/', '_').replace('\\', '_')
        course_id = course[1]
        print(f"\tGoing to assignments page of course name: {course_name}")
        driver.get(f"{hostname_url}/d2l/lms/dropbox/admin/folders_manage.d2l?ou={course_id}&d2l_stateScopes=%7B%221%22%3A%5B%22gridpagenum%22,%22search%22,%22pagenum%22%5D,%222%22%3A%5B%22lcs%22%5D,%223%22%3A%5B%22grid%22,%22pagesize%22,%22htmleditor%22,%22hpg%22%5D%7D&d2l_stateGroups=%5B%22grid%22,%22gridpagenum%22%5D&d2l_statePageId=223&d2l_state_grid=%7B%22Name%22%3A%22grid%22,%22Controls%22%3A%5B%7B%22ControlId%22%3A%7B%22ID%22%3A%22grid_main%22%7D,%22StateType%22%3A%22%22,%22Key%22%3A%22%22,%22Name%22%3A%22gridFolders%22,%22State%22%3A%7B%22PageSize%22%3A%222000%22,%22SortField%22%3A%22DropBoxId%22,%22SortDir%22%3A0%7D%7D%5D%7D&d2l_state_gridpagenum=%7B%22Name%22%3A%22gridpagenum%22,%22Controls%22%3A%5B%7B%22ControlId%22%3A%7B%22ID%22%3A%22grid_main%22%7D,%22StateType%22%3A%22pagenum%22,%22Key%22%3A%22%22,%22Name%22%3A%22gridFolders%22,%22State%22%3A%7B%22PageNum%22%3A1%7D%7D%5D%7D&d2l_change=1")
        print(f"\tAt assignments page, waiting .5 seconds")
        sleep(.5)

        # If there are no assignments, go to next course
        try:
            print("\tChecking to see if there is an assignments table")
            table = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div[2]/form/div/div/div/div/d2l-table-wrapper/table/tbody')
        except:
            print("\tNo assignments table found, going to next course")
            continue

        print("\tFound assignments table")
        # find all elements with "d2l-link" in the class name. This is only contained within the assignment links. I'm not aware of it being contained anywhere else.
        print("\tFinding all elements with 'd2l-link', which correspond to the assignments")
        table_inner_rows = table.find_elements(By.CLASS_NAME, 'd2l-link')
        print("\tFound all elements")

        # go through each row in table on the assignments page
        print(f"\tTotal found rows in table: {len(table_inner_rows)}")
        for row in table_inner_rows:
            # If a row doesn't have text, like a new category(?), skip it
            print("\t\tChecking if row has text")
            if row.text == '':
                print("\t\tRow doesn't have text, going to next row")
                print()
                continue
            print(f"\t\tRow has text: {row.text}")
            print("\t\tChecking if link goes to assignment")
            if len(row.get_attribute("title")) < 4 or row.get_attribute("title")[0:4] != 'View':
                    print("\t\tRow is not assignment, continuing...")
                    print()
                    continue
            
            print("\t\tGetting number of completed submissions")
            completed_assignment_string = row.find_elements(By.XPATH, './parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/*')[3].text
            print(f"\t\tValue of evaluated assignment string: {completed_assignment_string}")
            if completed_assignment_string != '':
                print("\t\tString not empty, indicating an assignment")
                print("\t\tEvaluating string")
                completed_assignment = eval(completed_assignment_string)
                print(f"\t\tEvaluated string successfully: {completed_assignment}")
                if completed_assignment > 0:
                    print("\t\tCompleted assignment is > 0, indicating there are assignment submissions")
                    assignment_id = row.get_attribute("href").split("?db=")[1].split("&")[0]
                    print(f"\t\tAssignment id: {assignment_id}")
                    all_assignments.append((course[0], course[1], assignment_id))
                else:
                    print("\t\tompleted assignment is <= 0, indicating no assignment submissions")
            else:
                print("\t\tString empty, indicating not an assignment")
            print("\tGoing to next row...")
            print()
        print(f"\tFinishing going through assignments of course: {course_id}")
        print()

    incrementing_unique_id = 0
    # for each assignment, go to the page and download all submissions
    print("Going through each assignment to download submissions")
    print(f"Total Assignments: {len(all_assignments)}")
    for assignment in all_assignments:
        course_name = assignment[0]
        course_id = assignment[1]
        assignment_id = assignment[2]
        print(f"\tGoing to submission page of course name: {course_name}, course id: {course_id}, assignment id: {assignment_id}")
        driver.get(f'{hostname_url}/d2l/lms/dropbox/admin/mark/folder_submissions_files.d2l?d2l_isfromtab=1&db={assignment_id}&ou={course_id}&d2l_change=0')
        print(f"\tSuccessfully navigated, waiting .1 seconds")
        sleep(.1)

        # little hack to load all submissions
        print("\tExecuting script to set '200 per page' to actually use 1000")
        driver.execute_script("document.evaluate('/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]', document, null, XPathResult.ANY_TYPE, null).iterateNext().value = 1000;")
        print("\tExecuted script, waiting .1 seconds")
        sleep(.1)

        # get grades
        # https://lms.augusta.edu/d2l/lms/grades/admin/enter/grade_item_edit.d2l?objectId=597438&ou=398537&dlg=true&d2l_body_type=2
        print("\tExecuting script to get D2L access token from localStorage")
        access_token = driver.execute_script("return JSON.parse(localStorage['D2L.Fetch.Tokens'])['*:*:*']['access_token']")
        print("\tExecuted script")
        print("\tSetting selenium cookies for requests session")
        d2lSecureSessionVal = driver.get_cookies()[0]['value']
        d2lSessionVal = driver.get_cookies()[1]['value']
        s.headers['Authorization'] = f'Bearer {access_token}'
        cookies = driver.get_cookies()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])
        print("\tUsing token to get grade object id")
        response = s.get(f'https://83ea0a02-fd06-4d2d-8623-48ed62e25340.activities.api.brightspace.com/old/activities/6606_2000_{assignment_id}/usages/{course_id}')
        associated_grade_object_id = response.json()['links'][17]['href'].split('/')[-1]
        print("\tDone")
        print("\tUsing grade object id to get assignment grades")
        response = s.get(f'{hostname_url}/d2l/lms/grades/admin/enter/grade_item_edit.d2l?objectId={associated_grade_object_id}&ou={course_id}&dlg=true&d2l_body_type=2')
        soup = BeautifulSoup(response.text, 'html.parser')
        student_id_assignment_grades = {}
        print("\tParsing Grades")
        if soup.find('table', id='z_p') is not None:
            for row in soup.find('table', id='z_p').find_all('tr')[1:]:
                student_id = row.find('input').get('value').split('_')[1]
                assignment_grade = row.find('d2l-input-number').get('value')
                student_id_assignment_grades[student_id] = assignment_grade
        print("\tParsed student grades for assignment")
        print(f"\tTotal student grades for assignment: {len(student_id_assignment_grades)}")
        table_path = '/html/body/div/div[2]/div[3]/div/div/div/form/div/div[4]/d2l-table-wrapper/table'

        # click on top-left select all box and click download
        print("\tClicking '200 per page' dropdown box option, which will load 1000")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select').click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]').click()

        print("\tClicking 'select all' box")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/d2l-table-wrapper/table/tbody/tr[1]/th[1]/input')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/d2l-table-wrapper/table/tbody/tr[1]/th[1]/input').click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[1]/tbody/tr/td/table/tbody/tr/td/div/d2l-overflow-group/d2l-button-subtle[1]')))

        # Wait for download window to open and click download
        print("\tClicking 'Download' and waiting for new window to pop up")
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[1]/tbody/tr/td/table/tbody/tr/td/div/d2l-overflow-group/d2l-button-subtle[1]').click()
        WebDriverWait(driver, 30).until(EC.number_of_windows_to_be(2))
        print("\tNew window appeared, waiting .2 seconds")
        sleep(.2)
        print("\tSwitching to new window")
        driver.switch_to.window(driver.window_handles[1])
        print("\tSwitching to frame")
        driver.switch_to.frame(driver.find_element(By.XPATH, '/html/frameset/frame[2]'))
        print("\tWaiting for download to be ready")
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH,'/html/body/div/div[1]/div[3]/div/div/div/form/div/div/span/a')))
        href = driver.find_element(By.XPATH,'/html/body/div/div[1]/div[3]/div/div/div/form/div/div/span/a').get_attribute('href')

        # Downloads zip and removes all irrelevant files
        print("\tDownload ready, downloading to /downloads/")
        download_file(s, href, f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}.zip")
        print("\tDownload complete")
        print("\tUnzipping")
        zip_path = Path(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}.zip")
        z = zipfile.ZipFile(zip_path)
        z.extractall(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}/")
        z.close()
        zip_path.unlink()
        zip_folder = Path(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}/")
        
        if os.path.isfile(os.path.join(zip_folder, "index.html")):
            os.remove(os.path.join(zip_folder, "index.html"))
        print("\tRenaming all files in folder")
        directory = listdir(zip_folder)
        print(f"\tNumber of submissions downloaded from assignment: {len(directory)}")
        for filename in directory:
            split_filename = filename.split('-')
            file_student_id = split_filename[0]
            file_assignment_id = split_filename[1]
            file_student_name = split_filename[2]
            file_rest_of_filename = " ".join(str(item) for item in split_filename[3:]).replace('/', '_').replace('\\', '_')
            if file_student_id in student_id_assignment_grades:
                print(f"\t\tThere is an associated grade with file")
                grade = student_id_assignment_grades[file_student_id]

                output_name = f'{grade}%---{incrementing_unique_id}---{file_assignment_id}---{file_rest_of_filename}'
                incrementing_unique_id+=1
                print(f"\t\tRenaming file to {output_name}")
                os.rename(os.path.join(zip_folder, filename), os.path.join(zip_folder, output_name))
                #os.remove(os.path.join(zip_folder, filename))
            else:
                print(f"\t\tThere is no associated grade with file")
                output_name = f'NA%---{incrementing_unique_id}---{file_assignment_id}---{file_rest_of_filename}'
                incrementing_unique_id+=1
                print(f"\t\tRenaming file to {output_name}")
                os.rename(os.path.join(zip_folder, filename), os.path.join(zip_folder, output_name))

        # directory = listdir(zip_folder)
        # for filename in directory:
        #     if not any(filename.endswith(ext) for ext in allowed_extensions):
        #         # If not, delete the file
        #         os.remove(os.path.join(zip_folder, filename))
            # elif filename.endswith('.py'): # if python file, remove comments
            #     if os.path.isfile(os.path.join(zip_folder, filename)):
            #         with open(os.path.join(zip_folder, filename), 'r') as fileobj:
            #             python_code = fileobj.read()

            #         cleaned_python_code = remove_python_comments_and_docstrings(python_code)

            #         with open(os.path.join(zip_folder, filename), 'w') as fileobj:
            #             fileobj.write(cleaned_python_code)

        print("\tDeleting original files")
        zip_directory(zip_folder, zip_path)
        shutil.rmtree(zip_folder)
        
        # close download window and go back to main window
        print("\tWaiting .5 seconds")
        sleep(.5)
        print("\tClosing extra window and going back to main window")
        driver.switch_to.default_content()
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        sleep(.1)
        print("\tDone with assignment")
        print()

    # combine all downloads together into downloads.zip
    print("Zipping all files together")
    zip_directory(f"{getcwd()}/downloads", f"{getcwd()}/downloads.zip")
    
    print("finished")
    # Close the browser

    driver.quit()
