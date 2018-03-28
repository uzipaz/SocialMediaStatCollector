import re
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

browser = None
URLs = ['http://www.gatherproxy.com/proxylist/country/?c=United%20States'
        , 'http://www.gatherproxy.com/proxylist/country/?c=Netherlands'
        , 'http://www.gatherproxy.com/proxylist/country/?c=France'
        , 'http://gatherproxy.com/proxylist/country/?c=United%20Kingdom'
        , 'http://gatherproxy.com/proxylist/country/?c=Germany'
        ]

class BrowserUninitialized(BaseException):
    pass

def gatherproxy_req():
    """Loads gatherproxy.com webpages on selenium headless browser because the page has ajax elements and iterates through list and calls parse_page with html source as argument"""
    gatherproxy_list = []

    if browser is not None:
        for url in URLs:
            browser.get(url)
            button = browser.find_element_by_class_name("button")
            button.click()
            WebDriverWait(browser, timeout=10)
            gatherproxy_list.extend(parse_page(browser.page_source))
            index = 2
            while True:
                try:
                    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    link = browser.find_element_by_link_text(str(index))
                    link.click()
                    WebDriverWait(browser, timeout=10)
                    gatherproxy_list.extend(parse_page(browser.page_source))
                except:
                    break
                else:
                    index += 1
    else:
        raise BrowserUninitialized('Browser was not or failed to intialized')

    return gatherproxy_list

def parse_page(page_source):
    """receives html page source of gatherproxy.com proxy list page and returns the list of proxies, each item in list contains tuple(rank, 'ip:port')"""
    proxylist = []
    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table', {'id': 'tblproxy'})
    rows = table.find_all('tr')

    for row in rows[2:]:
        cells = row.find_all('td')
        if len(cells) < 8:
            raise RuntimeError

        ip = re.search(r'\d+.\d+.\d+.\d+', str(cells[1]))
        port = re.search(r'>\d+<', str(cells[2]))
        rank = 0

        if not (ip.group() is None or port.group() is None):
            proxylist.append((rank, ip.group() + ':' + port.group()[1:-1]))
    return proxylist

def initBrowser():
    """launch firefox headless browser"""
    options = Options()
    options.add_argument('-headless')
    global browser
    browser = webdriver.Firefox(firefox_options=options)