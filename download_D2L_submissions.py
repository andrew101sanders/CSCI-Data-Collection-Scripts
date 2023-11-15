'''
Andrew Sanders
----------------------------

Overview:
    This script downloads all assignments of all D2L "CSCI" courses in which the user is an "Instructor" to the course.
    It uses a local downloads folder to download all assignments and deletes all irrelevant files based on file extension.
    When finished, it combines all downloaded files into "downloads.zip".

Notes:
    - It uses the selenium web driver with the chromedriver.exe (included: version 118.0.5993.88) to create a headless Chrome browser and download all submissions.
        (you may need to change the included chromedriver.exe to use the correct version from https://googlechromelabs.github.io/chrome-for-testing/ depending on your Chrome version)
    - It will automatically go through the DUO prompt and wait for you to accept it using the default authentication method.
    - Once it is finished, it will print "finished" in the console, and "downloads.zip" should be available in the folder.

This script is adapted from a similar script that targeted Georgia Southern University's "Folio" system, which is the same D2L system AU uses.

'''

# Replace with your credentials and preferences
username = 'username' # just username, no email (i.e. 'asanders4' not 'asanders4@augusta.edu')
password = 'password'

if username == 'username' or password == 'password':
    print("Make sure to replace 'username' and 'password' in the python script before running!")
    print("(also I hope that you accidentally left 'username' or 'password' as their default values and those aren't your actual credentials)")
    exit()

from time import sleep
from getpass import getuser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import pickle
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
import ast


executable_path = f'{getcwd()}/chromedriver.exe'

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
    
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options, service = Service(executable_path))
    original_window = driver.current_window_handle

    '''
    # Go to homepage and load previously stored cookies if they exist
    driver.get(home_url)
    if isfile("cookies.pkl"):
        cookies = pickle.load(open("cookies.pkl", "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.refresh()
    sleep(1)
    '''
    # If cookies do not exist or session is expired, go through Duo auth process
    if driver.current_url != home_url:
        driver.get(login_url)
        driver.find_element(By.ID, 'userNameInput').send_keys(username)
        driver.find_element(By.ID, 'passwordInput').send_keys(password)
        driver.find_element(By.ID, 'passwordInput').send_keys(Keys.ENTER)
        driver.switch_to.default_content()
    WebDriverWait(driver, 50).until(EC.url_to_be(home_url) or EC.url_to_be(session_expired_url))

    if driver.current_url == session_expired_url:
        driver.get(home_url)

    WebDriverWait(driver, 30).until(EC.url_to_be(home_url))

    # Dumping cookies so it doesn't need to login every time
    cookies = driver.get_cookies()
    # pickle.dump(cookies, open("cookies.pkl", "wb"))

    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    # Wait for the page to load
    driver.get(advanced_course_search_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[3]/d2l-input-search')))

    # only get CSCI courses
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div[3]/d2l-input-search").send_keys("AIST")
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div[3]/d2l-input-search").send_keys(Keys.ENTER)

    # only get courses in which the user was an Instructor
    driver.find_element(By.XPATH, "/html/body/div[2]/div/form/div[1]/div/div/div/div/div[1]/div/select").click()
    driver.find_element(By.XPATH, "/html/body/div[2]/div/form/div[1]/div/div/div/div/div[1]/div/select/option[2]").click()

    # little hack to load all courses
    driver.execute_script("document.evaluate('/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]', document, null, XPathResult.ANY_TYPE, null).iterateNext().value = 1000;")
    sleep(2)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select')))
    sleep(2)
    driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select').click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]')))
    driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/div[2]/div/div/div[2]/div/select/option[4]').click()
    sleep(1)

    # loop through table of courses and add each course name and id to a list
    courses = []
    table = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[5]/div/div/d2l-table-wrapper/table').find_elements(By.CLASS_NAME, 'd2l-link')
    for row in table:
        course_name = row.text
        course_id = row.get_attribute("href").split("/")[-1]
        courses.append((course_name, course_id))

    # visit each course's page and get all of the assignments
    all_assignments = []
    for course in courses:
        course_name = course[0]
        course_id = course[1]
        driver.get(f"{hostname_url}/d2l/lms/dropbox/admin/folders_manage.d2l?ou={course_id}&d2l_stateScopes=%7B%221%22%3A%5B%22gridpagenum%22,%22search%22,%22pagenum%22%5D,%222%22%3A%5B%22lcs%22%5D,%223%22%3A%5B%22grid%22,%22pagesize%22,%22htmleditor%22,%22hpg%22%5D%7D&d2l_stateGroups=%5B%22grid%22,%22gridpagenum%22%5D&d2l_statePageId=223&d2l_state_grid=%7B%22Name%22%3A%22grid%22,%22Controls%22%3A%5B%7B%22ControlId%22%3A%7B%22ID%22%3A%22grid_main%22%7D,%22StateType%22%3A%22%22,%22Key%22%3A%22%22,%22Name%22%3A%22gridFolders%22,%22State%22%3A%7B%22PageSize%22%3A%222000%22,%22SortField%22%3A%22DropBoxId%22,%22SortDir%22%3A0%7D%7D%5D%7D&d2l_state_gridpagenum=%7B%22Name%22%3A%22gridpagenum%22,%22Controls%22%3A%5B%7B%22ControlId%22%3A%7B%22ID%22%3A%22grid_main%22%7D,%22StateType%22%3A%22pagenum%22,%22Key%22%3A%22%22,%22Name%22%3A%22gridFolders%22,%22State%22%3A%7B%22PageNum%22%3A1%7D%7D%5D%7D&d2l_change=1")
        sleep(.5)

        # If there are no assignments, go to next course
        try:
            table = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div[2]/form/div/div/div/div/d2l-table-wrapper/table/tbody')
        except:
            continue

        # find all elements with "d2l-link" in the class name. This is only contained within the assignment links. I'm not aware of it being contained anywhere else.
        table_inner_rows = table.find_elements(By.CLASS_NAME, 'd2l-link')

        # go through each row in table on the assignments page
        for row in table_inner_rows:
            # If a row doesn't have text, like a new category(?), skip it
            if row.text == '':
                continue
            evaluated_assignment_string = row.find_elements(By.XPATH, './parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/parent::*/*')[4].text
            if evaluated_assignment_string != '':
                evaluated_assignment = eval(evaluated_assignment_string)
                if evaluated_assignment > 0:
                    assignment_id = row.get_attribute("href").split("?db=")[1].split("&")[0]
                    all_assignments.append((course[0], course[1], assignment_id))

    incrementing_unique_id = 0

    # for each assignment, go to the page and download all submissions
    for assignment in all_assignments:
        course_name = assignment[0]
        course_id = assignment[1]
        assignment_id = assignment[2]
        driver.get(f'{hostname_url}/d2l/lms/dropbox/admin/mark/folder_submissions_files.d2l?d2l_isfromtab=1&db={assignment_id}&ou={course_id}&d2l_change=0')
        sleep(.1)

        # little hack to load all submissions
        driver.execute_script("document.evaluate('/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]', document, null, XPathResult.ANY_TYPE, null).iterateNext().value = 1000;")
        sleep(.1)

        # get grades
        # https://lms.augusta.edu/d2l/lms/grades/admin/enter/grade_item_edit.d2l?objectId=597438&ou=398537&dlg=true&d2l_body_type=2
        access_token = driver.execute_script("return JSON.parse(localStorage['D2L.Fetch.Tokens'])['*:*:*']['access_token']")
        d2lSecureSessionVal = driver.get_cookies()[0]['value']
        d2lSessionVal = driver.get_cookies()[1]['value']
        s.headers['Authorization'] = f'Bearer {access_token}'
        response = s.get(f'https://83ea0a02-fd06-4d2d-8623-48ed62e25340.activities.api.brightspace.com/old/activities/6606_2000_{assignment_id}/usages/{course_id}')
        associated_grade_object_id = response.json()['links'][17]['href'].split('/')[-1]
        response = s.get(f'{hostname_url}/d2l/lms/grades/admin/enter/grade_item_edit.d2l?objectId={associated_grade_object_id}&ou={course_id}&dlg=true&d2l_body_type=2')
        soup = BeautifulSoup(response.text, 'html.parser')
        student_id_assignment_grades = {}
        for row in soup.find('table', id='z_p').find_all('tr')[1:]:
            student_id = row.find('input').get('value').split('_')[1]
            assignment_grade = row.find('d2l-input-number').get('value')
            student_id_assignment_grades[student_id] = assignment_grade
        table_path = '/html/body/div/div[2]/div[3]/div/div/div/form/div/div[4]/d2l-table-wrapper/table'

        # click on top-left select all box and click download
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select').click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/select/option[5]').click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/d2l-table-wrapper/table/tbody/tr[1]/th[1]/input')))
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/d2l-table-wrapper/table/tbody/tr[1]/th[1]/input').click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[1]/tbody/tr/td/table/tbody/tr/td/div/d2l-overflow-group/d2l-button-subtle[1]')))

        # Wait for download window to open and click download
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/form/div/div/div[2]/div[3]/div/table[1]/tbody/tr/td/table/tbody/tr/td/div/d2l-overflow-group/d2l-button-subtle[1]').click()
        WebDriverWait(driver, 30).until(EC.number_of_windows_to_be(2))
        sleep(.2)
        driver.switch_to.window(driver.window_handles[1])
        driver.switch_to.frame(driver.find_element(By.XPATH, '/html/frameset/frame[2]'))
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH,'/html/body/div/div[1]/div[3]/div/div/div/form/div/div/span/a')))
        href = driver.find_element(By.XPATH,'/html/body/div/div[1]/div[3]/div/div/div/form/div/div/span/a').get_attribute('href')

        # Downloads zip and removes all irrelevant files
        download_file(s, href, f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}.zip")
        zip_path = Path(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}.zip")
        z = zipfile.ZipFile(zip_path)
        z.extractall(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}/")
        z.close()
        zip_path.unlink()
        zip_folder = Path(f"{getcwd()}/downloads/{course_id}_{course_name}_{assignment_id}/")
        
        if os.path.isfile(os.path.join(zip_folder, "index.html")):
            os.remove(os.path.join(zip_folder, "index.html"))

        directory = listdir(zip_folder)
        for filename in directory:
            split_filename = filename.split('-')
            file_student_id = split_filename[0]
            file_assignment_id = split_filename[1]
            file_student_name = split_filename[2]
            file_rest_of_filename = " ".join(str(item) for item in split_filename[3:])
            if file_student_id in student_id_assignment_grades:
                grade = student_id_assignment_grades[file_student_id]

                output_name = f'{grade}%---{incrementing_unique_id}---{file_assignment_id}---{file_rest_of_filename}'
                incrementing_unique_id+=1

                os.rename(os.path.join(zip_folder, filename), os.path.join(zip_folder, output_name))
                #os.remove(os.path.join(zip_folder, filename))

        directory = listdir(zip_folder)
        for filename in directory:
            if not any(filename.endswith(ext) for ext in allowed_extensions):
                # If not, delete the file
                os.remove(os.path.join(zip_folder, filename))
            # elif filename.endswith('.py'): # if python file, remove comments
            #     if os.path.isfile(os.path.join(zip_folder, filename)):
            #         with open(os.path.join(zip_folder, filename), 'r') as fileobj:
            #             python_code = fileobj.read()

            #         cleaned_python_code = remove_python_comments_and_docstrings(python_code)

            #         with open(os.path.join(zip_folder, filename), 'w') as fileobj:
            #             fileobj.write(cleaned_python_code)

        
        zip_directory(zip_folder, zip_path)
        shutil.rmtree(zip_folder)
        
        # close download window and go back to main window
        sleep(.5)
        driver.switch_to.default_content()
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        sleep(.1)

    # combine all downloads together into downloads.zip
    zip_directory(f"{getcwd()}/downloads", f"{getcwd()}/downloads.zip")
    
    print("finished")
    # Close the browser

    driver.quit()
