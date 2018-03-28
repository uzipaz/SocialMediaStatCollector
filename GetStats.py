import requests
import threading
import time

from bs4 import BeautifulSoup

import socialmedia_stats
import parse_gatherproxy as parse_gp
import priority_queue as pq

# ----------------------------------------------------------------------------------------------------------------------------

def prepData(pmid):
    """PMID as string argument, extracts returns list of 'Additional text sources' URLs on the webpage"""
    MainURL = BaseURLPubmed + pmid
    URLs = [MainURL]

    ProxyRank, proxy = ProxyQueue.pollTillAvailable()
    proxies = {"http": "http://%s" % proxy}

    try:
        response = requests.get(MainURL, proxies=proxies, headers=Headers, timeout=RequestTimeOut)
        if response.status_code != 200:
            raise Exception('incorrect url/response')
        webpage = response.text
    except Exception as e:
        ProxyRank += 1
        flog.write(str(e) + ' on pmid: ' + str(pmid) + '\n')
    else:
        ProxyRank -= 1

        try:
            soup = BeautifulSoup(webpage, 'html.parser')
            LinkOutList = soup.find_all('div', {'class':'linkoutlist'})
            URLLists = LinkOutList[0].find_all('ul')
            URLTags = URLLists[0].find_all('a')

            for url in URLTags:
                URLs.append(url['href'])
        except Exception as e:
            flog.write(str(e) + ' Error parsing on pmid: ' + str(pmid) + '\n')

    ProxyQueue.addItem(proxy, ProxyRank)
    return URLs

class StatCollectThread(threading.Thread):
    def __init__(self, ListURL, statObj):
        threading.Thread.__init__(self)
        self.ListURL = ListURL
        self.TotalCount = 0
        self.statObj = statObj

    def run(self):
        """Fetch social media count of all the URLs"""
        ProxyRank, proxy = ProxyQueue.pollTillAvailable()

        i = 0
        while i < len(self.ListURL):
            try:
                count = self.statObj.getStats(self.ListURL[i], proxy, Headers, RequestTimeOut)
            except Exception as e:
                ProxyQueue.addItem(proxy, ProxyRank + 1)
                ProxyRank, proxy = ProxyQueue.pollTillAvailable()
                flog.write(str(e) + ' on url: ' + str(self.ListURL[i]) + '\n')
            else:
                global URLFetchCount
                URLFetchCount += 1
                self.TotalCount += count
                i += 1

        ProxyQueue.addItem(proxy, ProxyRank - 1)

class PMIDThread(threading.Thread):
    NumOfThreads = 0
    lock = threading.Lock()

    def __init__(self, pmid, index):
        threading.Thread.__init__(self)
        self.daemon = True
        self.pmid = pmid
        self.index = index

        self.FacebookStat = socialmedia_stats.FacebookStat()
        self.TwitterStat = socialmedia_stats.TwitterStat()

        self.TwitterStat.AccessTokenKey = 'qmgBRwbl4W5QaYTy5RUscCoEo'
        self.TwitterStat.AccessTokenSecret = 'J2WJ0TkRbzB1TUGm0IUH6ho0edRqiDeV2BGvXkR0T5UyoEGL4R'
        self.TwitterStat.ConsumerKey = '898039630238543872-eJMVMrieBgN1SQZKmuHbjf45TRxyVy7'
        self.TwitterStat.ConsumerSecret = 'QyHrM6IVb7gfkxoiMXuLMGqGNt39D0gK7eF8ESHdSM1DK'

    def run(self):
        """get List of URLs from PMID, and enter their respective counts into ListCount"""
        with PMIDThread.lock:
            PMIDThread.NumOfThreads += 1
        try:
            ListURL = prepData(self.pmid)
        except:
            flog.write('At ' + str(round(time.clock(), 2)) + ' sec: ' + 'Failed to fetch data on ' + self.pmid + '\n')
        else:
            ft = StatCollectThread(ListURL, self.FacebookStat)
            tt = StatCollectThread(ListURL, self.TwitterStat)
            ft.start()
            tt.start()
            ft.join()
            tt.join()

            global PMIDReadCount
            PMIDReadCount += 1
            ListCount[self.index] = "{}|{}\n".format(ft.TotalCount, tt.TotalCount)
        with PMIDThread.lock:
            PMIDThread.NumOfThreads -= 1

class CollectThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        i = 0
        while i < len(ListPMID):
            if PMIDThread.NumOfThreads < NumOfCollectThreads:
                PMIDThread(ListPMID[i], i).start()
                i += 1

class WriteThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.file = open(NameOutputFile, 'a')

    def run(self):
        i = 0
        while i < len(ListPMID):
            if ListCount[i] is not None:
                self.file.write(ListPMID[i] + '|' + ListCount[i])
                i += 1
        self.file.close()

# ----------------------------------------------------------------------------------------------------------------------------

class ProxyThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        try:
            self.fetchProxyList()
        except Exception as e:
            print(str(e) + 'Failed to fetch proxy')

    def fetchProxyList(self):
        try:
            ProxyQueue.addToList(parse_gp.gatherproxy_req())
        except parse_gp.BrowserUninitialized:
            flog.write(
                'At ' + str(round(time.clock(), 2)) + ' sec: ' + 'browser not working\n')

    def run(self):
        dProxyTime = time.clock() - ProxyUpdateTime
        while wt.is_alive():
            if time.clock() - dProxyTime > ProxyUpdateTime:
                self.fetchProxyList()
                dProxyTime = time.clock()

# ----------------------------------------------------------------------------------------------------------------------------

def readLines(File, SkipIndex):
    count = 0
    for line in File:
        if count >= SkipIndex:
            string = line[:-1]  # discard the newline character read from the file at each line
            ListPMID.append(string)  # Append PMID to list
        else:
            count += 1

def printStats():
    #os.system('cls')
    print('\n')
    print(str(round(((time.clock() - StartTime) / 60.0), 2)), 'minutes elapsed')
    print(str(PMIDReadCount), 'results fetched,', str(round(((PMIDReadCount / float(NumOfPMIDs)) * 100.0), 2)), '% done')

    print('URL Fetch rate', str(URLFetchCount - dFetchRate), 'per', str(UpdateTimeInSec), 'sec,', str(
        URLFetchCount), 'total URLs fetched')

    print('Total Proxies:', str(len(ProxyQueue.ItemList)))

ProxyQueue = pq.PriorityQueue()

ListCount = 0 # Python list, each item is string 'facebook_count|twitter_count'
skip_index = 0 # number of inputs PMIDs to ignore
ListPMID = [] # Python list, each entry is a PMID as a string

PMIDReadCount = skip_index # Number of PMIDs that have their count done so far
URLFetchCount = 0 # Number of successful URLs requests so far

NumOfPMIDs = 0 # Number of PMIDs
StartTime = 0 # start time of our program on clock
dFetchRate = 0 # delta fetch rate, to be used to trigger refresh of program performance stats after a specified time interval

NameInputFile = 'pubmed_test.txt'
NameOutputFile = NameInputFile[0:-4] + '_stats.' +  NameInputFile[-3:]
BaseURLPubmed = 'https://www.ncbi.nlm.nih.gov/pubmed/'

NumOfCollectThreads = 20 # Number of allowed simultaneous data collection threads
UpdateTimeInSec = 10.0 # interval of number of seconds after which we print our program stats
ProxyUpdateTime = 360 # interval of number of seconds after which request and parse all gatherproxy.com proxy lists
RequestTimeOut = 9.0 # number of seconds for url request timeout
URLFetchTimeOut = 600.0 # number of seconds to wait while successful url request rate is 0, exit the program if time exceeded
Headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36'}

flog = open('log.txt', 'w')

if __name__ == '__main__':
    with open(NameInputFile, 'r') as file:
        print('Reading input!')
        readLines(file, skip_index)

        NumOfPMIDs = len(ListPMID) + skip_index
        ListCount = [None] * len(ListPMID)

        print("# of PMIDs:", NumOfPMIDs)
        try:
            parse_gp.initBrowser()
        except Exception as e:
            print(str(e) + '\nBrowser failed in initialize, exiting program!')
        else:
            print('Headless browser initialized')

            wt = WriteThread()
            pt = ProxyThread()
            ct = CollectThread()

            wt.start()
            pt.start()
            ct.start()

            StartTime = time.clock()
            dt = time.clock()
            dtFetchRate = time.clock()

            prevFetchRate = URLFetchCount

            while threading.activeCount() > 1:
                if time.clock() - dt > UpdateTimeInSec:
                    printStats()
                    dt = time.clock()

                    dFetchRate = URLFetchCount

                if URLFetchCount - prevFetchRate == 0:
                    if time.clock() - dtFetchRate > URLFetchTimeOut:
                        break
                else:
                    dtFetchRate = time.clock()
                    prevFetchRate = URLFetchCount

            flog.close()
            printStats()