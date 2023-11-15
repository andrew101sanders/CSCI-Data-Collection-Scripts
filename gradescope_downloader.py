'''
Andrew Sanders
----------------------------
This script downloads all assignment submissions of all non-placeholder Gradescope courses. It only collects the submissions of non-instructors.
It will place all downloaded files in a .zip file.
While effort has been made to make the script robust, there does not exist a public API for gradescope,
    meaning some inprecise webscrapping was used and some edge cases may cause errors.

Instructions:
---------------------------
1. Replace email and pswd with the correct credentials of gradescope.com
2. Download all relevant pip packages (pip install BeautifulSoup4)
3. Run and wait!
'''


email='email'
pswd='pswd' # for gradescope, not Folio

from time import sleep
from getpass import getuser
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
import os
from bs4 import BeautifulSoup
from pyscope.pyscope import GSConnection
from pyscope.person import GSRole

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

# Login to gradescope and get account details
session = GSConnection()
print(session.login(email=email, pswd=pswd))

# don't get details for placeholder courses, if they exist
session.get_account(excluded_courses=['Gradescope 101', 'Gradescope 202', 'Assignment Examples', 'Gradescope Tutorial'])

# increasing ID to replace student names
increasing_no = 0

# for each course and each assignment, we want to download all submissions for each student
for course in list(session.account.instructor_courses.values()):
    
    # required before looping through course assignments
    course._lazy_load_roster()
    course._lazy_load_assignments()

    # make a directory for each course to organize submission downloads
    os.mkdir(os.path.join(f"{os.getcwd()}/downloads/", f"{course.shortname}"))

    # for each assignment, download all submissions
    for assignment in course.assignments.values():

        # go to course url and parse html
        outline_resp = course.session.get('https://www.gradescope.com/courses/' + assignment.course.cid + '/assignments/' + assignment.aid + '/review_grades')
        parsed_outline_resp = BeautifulSoup(outline_resp.text, 'html.parser')

        # "out of" grade so each score can be properly scaled, e.g. 100/130 = 77%
        score_text = parsed_outline_resp.find(class_=["u-centeredText","sorting"]).find("span").text
        score = float(score_text.split("/")[-1])

        # parse html to get all student submissions
        submission_rows = parsed_outline_resp.find(class_="js-reviewGradesTable").find("tbody").find_all(class_=["table--primaryLink", " sorting_3"])

        # make directory for each assignment
        os.mkdir(os.path.join(os.path.join(f"{os.getcwd()}/downloads/", f"{course.shortname}"), f"{assignment.shortname}"))

        # for each student, get their information and submission url
        for row in submission_rows:
            a = row.find("a")

            # name is used to make sure a submission is by a student, not an instructor
            name = a.text

            # there's a weird duplication thing, so it needs to be checked if the name is in the course roster
            if name not in course.roster or course.roster[name].role == GSRole.INSTRUCTOR:
                continue

            # get url of submission
            link = a.get("href")

            # for some reason, some tables have different amounts of data, so we have to handle both cases.
            data = row.parent.find_all("td")
            if len(data) == 9:
                 grade_text = data[4].text
            else:
                grade_text = data[3].text

            # if a person does not have a submission,
            if grade_text == '':
                continue
            grade = float(grade_text)/score
            grade = round(grade * 100)
            print(f"{name}: {grade}%, {link}")

            file_path = Path(f"{getcwd()}/downloads/{course.shortname}/{assignment.shortname}/{increasing_no}_{grade}%.zip")
            download_file(course.session, f"https://www.gradescope.com{link}.zip", f"{file_path}")
            
            try:
                z = zipfile.ZipFile(f"{file_path}")
                z.extractall(f"{getcwd()}/downloads/{course.shortname}/{assignment.shortname}/{increasing_no}_{grade}%/")
                z.close()
                
                zip_folder = Path(f"{getcwd()}/downloads/{course.shortname}/{assignment.aid}/{increasing_no}_{grade}%/")

                if os.path.isfile(os.path.join(zip_folder, "metadata.yml")):
                    os.remove(os.path.join(zip_folder, "metadata.yml"))
            except zipfile.BadZipFile as e:
                print(e)
            finally:
                file_path.unlink()
            
            increasing_no += 1

    zip_directory(f"{getcwd()}/downloads", f"{getcwd()}/downloads.zip")