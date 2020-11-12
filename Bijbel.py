import os
import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


# Load bibles from http://debijbel.nl
def read_bible(driver, bible, books, timeout=15):

    books_processed = []
    file_name = "{:s}-Bijbel.csv".format(bible)
    if os.path.exists(file_name):
        print('Found checkpoint')
        df = pd.read_csv(file_name, sep="|", index_col=False, header='infer')
        if len(df) > 0:
            books_processed = list(df['code'].unique())
            print('Processed', ','.join(books_processed))
    print('Checkpoint read')

    # remove already processed books
    for code in books_processed:
        books.pop(code)

    for code, book in books.items():
        verses = {}
        for chapter in range(1, book['chapters'] + 1):

            # Handle inconsistencies
            # Skip chapter this because the data is already loaded in the previous chapter
            if bible=='HSV' and code=='JOL' and chapter==4: continue

            import urllib.parse
            import time
            target_url = 'https://debijbel.nl/bijbel/{:s}/{:s}.{:d}/{:s}-{:d}'.format(bible, code, chapter,
                                                                                      book['name'], chapter)

            started = time.time()
            driver.get(target_url)

            # Xpath find verses containing a verse number
            span_path = "//app-root/app-bible-reader//span[@class='verse part' and @data-verse-org-id!='']"

            # Wait until the page has loaded the data we need
            title = '{:s}-{:d}'.format(book['name'], chapter).replace('-',' ')
            WebDriverWait(driver, timeout=timeout).until(
                ec.title_contains(title),
                message='Waiting for title contains {:s}'.format(title)
                #ec.presence_of_element_located((By.XPATH, span_path))
            )

            time.sleep(5)

            spans = driver.find_elements_by_xpath(span_path)
            if not spans or len(spans) == 0:
                raise Exception("No verses found")

            current_url = urllib.parse.unquote(driver.current_url)

            # Verify that we are on the expected page
            # We usualy get redirected if we had specified an incorrect target_url
            # Ignore the past part because on this site /Richteren-1 equals /Rechters-1
            if current_url.split('/')[:-1] != target_url.split('/')[:-1]:
                raise Exception('Redirected from {:s} to {:s}'.format(target_url, current_url))
                print('Redirected from {:s} to {:s}'.format(target_url, current_url))

            prev = None
            text = ''
            for span in spans:
                verse_id = span.get_attribute("data-verse-org-id").split(",")
                verse = verse_id[0]
                print(book['chapters'], verse, text)
                if verse != prev:
                    text = span.get_attribute("textContent").strip()
                    prev = verse
                else:
                    text = text + ' ' + span.get_attribute("textContent").strip()
                verses[verse] = {'id': verse_id[0],
                                 'code': code,
                                 'book': book['name'],
                                 'chapter': chapter,
                                 'verse': verse_id[0].split('.')[-1],
                                 'end': verse_id[-1].split('.')[-1],
                                 'text': text}

            print('De {:s} bijbel, boek {:s} hoofstuk {:d} van {:d} {:s} response={:2.3f}'.format(bible, book['name'],
                                                                                                  chapter,
                                                                                                  book['chapters'],
                                                                                                  target_url,
                                                                                                  time.time() - started))

        # Save every completed book
        df = pd.DataFrame.from_dict(verses.values())
        if os.path.exists(file_name):
            df.to_csv('%s-Bijbel.csv' % bible, index=False, sep="|", mode='a', header=False)
        else:
            df.to_csv('%s-Bijbel.csv' % bible, index=False, sep="|", mode='w', header=True)


def process_bible(bible, books, timeout=15, retries=0, cooldown=30):
    from time import sleep
    failed = False

    print('Process bible',bible)

    for x in range(0, retries + 1):  # try 4 times
        failed = False
        try:
            read_bible(driver, bible, books, timeout=timeout)
            print('{:s} Bible finished'.format(bible))
        except Exception as str_error:
            failed = True
            print('Exception',str_error.args)
            traceback.print_exc()
            driver.save_screenshot("screenshot.png")
        finally:
            # driver.quit()
            pass

        if failed:
            print('Waiting {:d} seconds for retry ....'.format(cooldown))
            sleep(cooldown)  # wait before trying to fetch the data again
        else:
            break


import time
import traceback


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()

ap.add_argument("-u", "--user", type=str, required=True,
                help="username")
ap.add_argument("-p", "--password", type=str, required=True,
                help="username")

args = vars(ap.parse_args())


# Windows path to chromedriver
DRIVER_PATH = r'C:\Data\Selenium\chromedriver'

# Read bible book code, name , number of chapters
bible_books = pd.read_excel('Index.xlsx', index_col=0).to_dict(orient='index')
for book in bible_books.values():
    print(book)

driver = webdriver.Chrome(executable_path=DRIVER_PATH)
driver.maximize_window()
driver.set_page_load_timeout(15)

# Open website
driver.get('https://debijbel.nl/')

WebDriverWait(driver, 15).until(
    ec.presence_of_element_located((By.XPATH, "//span[@class='notice dismiss']"))
)

# dismiss cookies
element = driver.find_elements_by_xpath("//span[@class='notice dismiss']")
if len(element) > 0:
    element[0].click()


element = driver.find_elements_by_xpath("//a[@id='signin']")
if len(element)>0:
    element[0].click()

    # Login
    element = driver.find_element_by_xpath("//input[@id='email']")
    element.send_keys(args["user"])

    element = driver.find_element_by_xpath("//input[@id='password']")
    element.send_keys(args["password"])

    element = driver.find_element_by_xpath("//button[@id='submitSignin']")
    element.click()

time.sleep(5)
# dismiss create new account
#element = driver.find_elements_by_xpath("//i[@class='fal fa-times']")
#if len(element)>0 and element[0].is_displayed() and element[0].is_enabled():
#    element[0].click()

for bible_name in ['NBV', 'BGT', 'HSV','GNB', 'NBG51','SV1977']:
    process_bible(bible_name, bible_books.copy())

print('Done')
