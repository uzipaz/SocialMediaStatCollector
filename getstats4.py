import threading, time, requests, os, decimal, ast, heapq, copy, sys, re
from HTMLParser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

skip_index = 835469
ListPMID = []
ListJournal = []
ListCount = []
PMIDReadCount = skip_index
URLFetchCount = 0
HTMLLock = threading.Lock()

NameInputFile = 'pubmed_2013.txt'
NameOutputFile = 'pubmed_2013_stats.txt'

DelayInSec = 1.0
UpdateTimeInSec = 10.0
ProxyUpdateTime = 360
RequestTimeOut = 9.0
URLFetchTimeOut = 720.0
Headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36'}
PhantomJSPath = 'C:\Python27\misc\PhantomJS\phantomjs.exe'

flog = open('log.txt', 'w')
#htmlfile1 = open('html1.html', 'w')
#htmlfile2 = open('html2.html', 'w')

#----------------------------------------------------------------------------------------------------------------------------

class PriorityQueue:
	def __init__(self):
		self._queue = []
	def push(self, item):
		heapq.heappush(self._queue, item)
	def pop(self):
		return heapq.heappop(self._queue)
	def empty(self):
		return len(self._queue) == 0
	def contains(self, item):
		if item in [i[1] for i in self._queue]:
			return True
		return False
	def extend(self, pq):
		for item in pq._queue:
			self.push(item)
	def len(self):
		return len(self._queue)

#----------------------------------------------------------------------------------------------------------------------------

class ProxyFetcher:
	FreeProxyList = PriorityQueue()
	BusyProxyList = []
	browser = webdriver.PhantomJS(executable_path=PhantomJSPath, service_log_path=os.path.devnull)
	lock = threading.Lock()
	def gatherproxy_req(self):
		gatherproxy_pq = PriorityQueue()
		URLs = []
		URLs.append('http://www.gatherproxy.com/proxylist/country/?c=United%20States')
		URLs.append('http://www.gatherproxy.com/proxylist/country/?c=Netherlands')
		URLs.append('http://www.gatherproxy.com/proxylist/country/?c=France')
		URLs.append('http://gatherproxy.com/proxylist/country/?c=United%20Kingdom')
		URLs.append('http://gatherproxy.com/proxylist/country/?c=Germany')
		for url in URLs:
			ProxyFetcher.browser.get(url)
			button = ProxyFetcher.browser.find_element_by_class_name("button")
			button.click()
			WebDriverWait(ProxyFetcher.browser, timeout = 10)
			gatherproxy_pq.extend(self.parse_gp(ProxyFetcher.browser.page_source.splitlines()))
			index = 2
			while True:
				try:
					link = ProxyFetcher.browser.find_element_by_link_text(str(index))
					link.click()
					WebDriverWait(ProxyFetcher.browser, timeout = 10)
					gatherproxy_pq.extend(self.parse_gp(ProxyFetcher.browser.page_source.splitlines()))
				except Exception, e:
					break
				else:
					index = index + 1
		return gatherproxy_pq
	def parse_gp(self, lines):
		''' Parse the raw scraped data '''
		gatherproxy_pq = PriorityQueue()
		i = 0
		while (i < len(lines) - 6):
			ip = re.compile('\d+\.\d+\.\d+\.\d+').search(lines[i])
			i = i + 1
			if ip != None:
				port = re.compile('>\d+<').search(lines[i])
				i = i + 5
				speed = re.compile('\d+ms').search(lines[i])
				i = i + 1
				proxy = ip.group() + ':' + (port.group())[1:len(port.group())-1]
				#gatherproxy_pq.push((int(speed.group()[:len(speed.group())-2]), proxy.encode('ascii', errors='ignore')))
				gatherproxy_pq.push((0, proxy.encode('ascii', errors='ignore')))
		return gatherproxy_pq
	def updateProxyList(self):
		try:
			ProxyFetcher.NewProxyList = self.gatherproxy_req()
		except Exception, e:
			raise e
		else:
			with ProxyFetcher.lock:
				#flog.write('At ' + str(round(time.clock(), 2)) + ' sec: ' + 'New Number of proxies: ' + str(ProxyFetcher.NewProxyList.len()) + '\n')
				while not ProxyFetcher.NewProxyList.empty():
					proxy = ProxyFetcher.NewProxyList.pop()
					if proxy[1] not in ProxyFetcher.BusyProxyList and not ProxyFetcher.FreeProxyList.contains(proxy[1]):
						ProxyFetcher.FreeProxyList.push(proxy)
	def getProxy(self):
		with ProxyFetcher.lock:
			try:
				proxy = ProxyFetcher.FreeProxyList.pop()
			except Exception, e:
				return None
			else:
				ProxyFetcher.BusyProxyList.append(proxy[1])
				return proxy
	def releaseProxy(self, proxy):
		with ProxyFetcher.lock:
			if proxy[1] in ProxyFetcher.BusyProxyList:
				ProxyFetcher.BusyProxyList.remove(proxy[1])
				ProxyFetcher.FreeProxyList.push(proxy)
	def removeProxy(self, proxy):
		with ProxyFetcher.lock:
			if proxy[1] in ProxyFetcher.BusyProxyList:
				ProxyFetcher.BusyProxyList.remove(proxy[1])
	def isProxyAvailable(self):
		return (not ProxyFetcher.FreeProxyList.empty())

#----------------------------------------------------------------------------------------------------------------------------

class PubmedParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isCorrect = False
	def handle_starttag(self, tag, attrs):
		if tag == 'meta':
			if attrs[0][1] == 'ncbi_app' and attrs[1][1] == 'entrez':
				self.isCorrect = True

class LinksParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.ListLinks = []
	def handle_starttag(self, tag, attrs):
		if tag == 'a':
			for ats in attrs:
				if ats[0] == u'href':
					self.ListLinks.append(ats[1].encode('ascii', errors='ignore'))
					break
													
def prepData(pmid):
	url = 'http://www.ncbi.nlm.nih.gov/pubmed/' + pmid
	ExceptionURL = []
	ExceptionURL.append('&')
	ExceptionURL.append('=')
	ExceptionURL.append('#')
	ExceptionURL.append("'")
	ListURL = []
	proxy = ProxyFetcher().getProxy()
	while proxy == None:
		proxy = ProxyFetcher().getProxy()
	proxies = {"http" :"http://%s" % proxy[1]}
	while True:
		try:
			t0 = time.clock()
			response = requests.get(url, proxies = proxies, headers = Headers, timeout = RequestTimeOut)
			if response.url != url or response.status_code != 200:
				flog.write('Wrong url received on ' + pmid + '\n')
				raise Exception('wrong url')
			page = response.text
			parser = PubmedParser()
			parser.feed(page)
			if not parser.isCorrect:
				flog.write('Wrong url received on ' + pmid + '\n')
				raise Exception('wrong url')
			html = page.splitlines()
		except Exception, e:
			#pass
			#flog.write(str(e) + ' on prepData, url: ' + str(url) + pmid + '\n')
			ProxyFetcher().releaseProxy((proxy[0] + 1, proxy[1]))
			proxy = ProxyFetcher().getProxy()
			while proxy == None:
				proxy = ProxyFetcher().getProxy()
			proxies = {"http" :"http://%s" % proxy[1]}
		else:
			parser = LinksParser()
			for line in html:
				StartPos = line.find('Full Text Sources')
				if StartPos != -1:
					StartPos = StartPos + 30
					EndPos = line[StartPos:].find('</ul>')
					parser.feed(line[StartPos:StartPos+EndPos-5])
					
					for exp in ExceptionURL:
						for u in parser.ListLinks[:]:
							if exp in u:
								parser.ListLinks.remove(u)
					
					#for u in parser.ListLinks[:]:
					#	if requests.get(u, headers = Headers, timeout = RequestTimeOut).url != u:
					#		parser.ListLinks.remove(u)
						
					ListURL.extend(parser.ListLinks)
					break
			break
	#flog.write('At ' + str(round(time.clock(), 2)) + ' sec: ' + pmid + ' URLs: ' + str(len(ListURL) - 1) + '\n')
	rank = proxy[0]
	if rank > 0:
		rank -= 1
	ProxyFetcher().releaseProxy((rank, proxy[1]))
	ListURL.append(url)
	#dt = time.clock() - t0
	#if dt < 1.0:
	#	time.sleep(1.0-dt) 
	return ListURL

#----------------------------------------------------------------------------------------------------------------------------

class Stat:
	def getStats():
		return 0
		
class FacebookStat(Stat):
	BlackListedProxies = []
	def getStats(self, url, proxy, headers, timeout):
		if proxy in FacebookStat.BlackListedProxies:
			raise Exception('IP blocked by FaceBook')
		try:
			response = requests.get('http://graph.facebook.com/fql?q=SELECT total_count FROM link_stat WHERE url = \"%s\"' % url, proxies = {'http' : 'http://%s' % proxy}, headers = headers, timeout = timeout)
			JsonObj = response.json()
			stats = JsonObj[u'data'][0]
			count = stats[u'total_count']
		except KeyError, e:
			error = JsonObj[u'error'][u'code']
			if error == 4 or error == 5: # Application request limit reached, BlackList this proxy
				FacebookStat.BlackListedProxies.append(proxy)
			raise Exception(str(e) + ' on Facebook\nJSON: ' + response.text)
		except Exception, e:
			#flog.write(str(e) + ' on Facebook, url: ' + str(url) + ' JSON: ' + response.text + '\n')
			raise Exception(str(e) + ' on Facebook')
		else:
			return count
			
class TwitterStat(Stat):
	def getStats(self, url, proxy, headers, timeout):
		try:
			response = requests.get('http://cdn.api.twitter.com/1/urls/count.json?url=%s' % url, proxies = {'http' : 'http://%s' % proxy}, headers = headers, timeout = timeout)
			JsonObj = response.json()
			count = JsonObj[u'count']
		except Exception, e:
			#flog.write(str(e) + ' on Twitter, url: ' + str(url) + '\n')
			raise Exception(str(e) + ' on Twitter')
		else:
			return count
			
class LinkedinStat(Stat):
	def getStats(self, url, proxy, headers, timeout):
		try:
			response = requests.get('http://www.linkedin.com/countserv/count/share?url=%s&format=json' % url, proxies = {'http' : 'http://%s' % proxy}, headers = headers, timeout = timeout)
			JsonObj = response.json()
			count = JsonObj[u'count']
		except Exception, e:
			#flog.write(str(e) + ' on Linkedin, url: ' + str(url) + '\n')
			raise Exception(str(e) + ' on LinkedinStat')
		else:
			return count

class StatCollectThread(threading.Thread):
	def __init__(self, ListURL, statObj):
		threading.Thread.__init__(self)
		self.daemon = True
		self.ListURL = ListURL
		self.TotalCount = 0
		self.event = threading.Event()
		self.statObj = statObj
	def run(self):
		proxy = ProxyFetcher().getProxy()
		while proxy == None:
			proxy = ProxyFetcher().getProxy()
		i = 0
		while (i < len(self.ListURL)):
			try:
				t0 = time.clock()
				count = self.statObj.getStats(self.ListURL[i], proxy[1], Headers, RequestTimeOut)
			except Exception, e:
				ProxyFetcher().releaseProxy((proxy[0] + 1, proxy[1]))
				proxy = ProxyFetcher().getProxy()
				while proxy == None:
					proxy = ProxyFetcher().getProxy()	
				#flog.write(str(e) + ' on url: ' + str(self.ListURL[i]) + '\n')
			else:
				global URLFetchCount
				URLFetchCount += 1
				self.TotalCount += count
				i += 1
				dt = time.clock() - t0
				if dt < 1.0:
					time.sleep(1.0-dt)
		rank = proxy[0]
		if rank > 0:
			rank -= 1
		ProxyFetcher().releaseProxy((rank, proxy[1]))
		self.event.set()
				
class PMIDThread(threading.Thread):
	NumOfThreads = 0
	lock = threading.Lock()
	def __init__(self, pmid, index):
		threading.Thread.__init__(self)
		self.daemon = True
		self.pmid = pmid
		self.index = index
	def run(self):
		with PMIDThread.lock:
			PMIDThread.NumOfThreads = PMIDThread.NumOfThreads + 1
		try:
			ListURL = prepData(self.pmid)
		except Exception, e:
			pass
			#flog.write('At ' + str(round(time.clock(), 2)) + ' sec: ' + 'Failed to fetch data on ' + self.pmid + '\n')
		else:
			ft = StatCollectThread(ListURL, FacebookStat())
			tt = StatCollectThread(ListURL, TwitterStat())
			lt = StatCollectThread(ListURL, LinkedinStat())
			ft.start()
			tt.start()
			lt.start()
			ft.event.wait()
			tt.event.wait()
			lt.event.wait()
			global PMIDReadCount
			#with PMIDThread.lock:
			PMIDReadCount = PMIDReadCount + 1
			#ListCount[self.index] = '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(self.pmid, ft.TotalCount, tt.TotalCount, lt.TotalCount, str(len(ReturnValue[0])), ReturnValue[1], ReturnValue[2], ReturnValue[3])
			ListCount[self.index] = '{}|{}|{}\n'.format(ft.TotalCount, tt.TotalCount, lt.TotalCount)
		with PMIDThread.lock:
			PMIDThread.NumOfThreads = PMIDThread.NumOfThreads - 1
			
class StatThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
	def run(self):
		i = 0
		while (i < len(ListPMID)):
			#with PMIDThread.lock:
			if PMIDThread.NumOfThreads < 30:
				PMIDThread(ListPMID[i], i).start()
				i += 1
		
class WriteThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
		self.file = open(NameOutputFile, 'a')
	def run(self):
		i = 0
		while (i < len(ListPMID)):
			if ListCount[i] != None:
				self.file.write(ListPMID[i] + '|' + ListJournal[i] + '|' + ListCount[i])
				i += 1
		self.file.close()
				
#----------------------------------------------------------------------------------------------------------------------------
		
class ProxyThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
	def run(self):
		dProxyTime = time.clock() - ProxyUpdateTime
		while (threading.activeCount() > 2):
			if time.clock() - dProxyTime > ProxyUpdateTime:
				ProxyFetcher().updateProxyList()
				dProxyTime = time.clock()
	
def readLines(file, skip_index):
	count = 0
	for line in file:
		if count >= skip_index:
			str = line[:len(line)-1].split('|') # discard the newline character read from the file at each line
			ListPMID.append(str[0]) # Append PMID to list
			ListJournal.append(str[1]) # Append Journal to list
			count += 1
		else:
			count += 1
			continue
        
	   
def printStats():
	os.system('cls')
	print str(round(((time.clock() - StartTime)/60.0), 2)), 'minutes elapsed'
	print str(PMIDReadCount) ,'results fetched,', str(round(((PMIDReadCount/float(NumOfPMIDs)) * 100.0), 2)), '% done'
	print 'URL Fetch rate', str(URLFetchCount - dFetchRate), 'per', str(UpdateTimeInSec), 'sec,', str(URLFetchCount), 'total URLs fetched'
	print '# of Proxies:', str(len(ProxyFetcher().BusyProxyList))
	print 'Total Proxies:', str(ProxyFetcher().FreeProxyList.len() + len(ProxyFetcher().BusyProxyList))

file = open(NameInputFile, 'r')
readLines(file, skip_index)
NumOfPMIDs = len(ListPMID) + skip_index
ListCount = [None] * len(ListPMID)

print "# of PMIDs:", NumOfPMIDs

WriteThread().start()
StatThread().start()
ProxyThread().start()

StartTime = time.clock()
dt = time.clock()
dtFetchRate = time.clock()
dFetchRate = URLFetchCount
prevFetchRate = URLFetchCount
while threading.activeCount() > 1:
	if time.clock() - dt > UpdateTimeInSec:
		printStats()
		dt = time.clock()
		dFetchRate = URLFetchCount
	if URLFetchCount - prevFetchRate is 0:
		if time.clock() - dtFetchRate > URLFetchTimeOut:
			break
	else:
		dtFetchRate = time.clock()
		prevFetchRate = URLFetchCount
		
file.close()
flog.close()
printStats()