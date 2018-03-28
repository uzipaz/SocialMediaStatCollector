# SocialMediaStatCollector

### Summary
I wrote this program for a research project conducted by researchers at University of Iowa. They wanted to find how scientific/medical journal articles on the internet are communicated on popular Social Media websites such as FaceBook and Twitter. My program attempts to accomplish the first part of the research that was to collect Social Media statistics such as number of shares, likes, comments on each article.

### Intention
The researchers identified PubMed (http://www.ncbi.nlm.nih.gov/pubmed) as a good resource to collect statistics on given that there was prior similar research done on this topic (link-here). In this script, I make the use of Facebook/Twitter/Linkedin web APIs to retrieve social media statistics about a given article. But, there is a drawback in using these web APIs because we need to send an HTTP request to get a response and when you need a lot of requests to send, probably in millions, which can overload the server and possibly cause it crash or slow down considerably. Hence, these Facebook/Twitter/Linkedin web APIs have implemented a concept of call rate limitation which blocks incoming requests from an IP address if the number of requests per given time exceed a given threshold. 

### Justification
Such limitation seems reasonable to avoid issues such as DDoS attacks, fair treatment towards each request but slows down our task considerably. For example, if we are to collect statistics of all published PubMed articles in year 2015, the website will loosely return about a million articles. For each, we will extract related/relevent links that point to more detailed sources at sister websites, let the average number of these links be 3 and we are collecting stats for 3 social networks sites, Hence, we will need to make (1,000,000 * 3 * 3 = 9,000,000) HTTP requests to get all the data. Given, the call rate of Facebook 1 per second, it will take us approximately 41 days to collect data in a serial threaded program that accounts for the rate limit.

### Solution
To speed up the process, we could have multiple computers/hosts running the same program in parallel but this solution seems expensive to implement. Instead, we can have multiple threads in the same program running parallel, but the fundamental issue still remains, all the HTTP requests will be sent from the same IP address and will get our program blocked. As a workaround, we can send our HTTP requests through a proxy server. There are alot of resources online for publicly available proxy servers and some provide a list of available servers. Though, most servers do not stay up for use all the time, are quite slow and lose connection quite often. Hence, websites such as (http://gatherproxy.com) provide reguarly updated proxy servers with their performance metrics (such as Response time in ms and UptimeVsDowntime) from all over the world. The website offers all these servers in a .txt file if we pay a premium fee ajd Hence, I wrote a crawler program running in a seperate thread that crawls through the website and maintains a list best proxy servers according to their performance metrics.

In order to begin the program, we need to provide a list of PubMed articles IDs (PIDs) that we are to collect statistics about. These can be downloaded from the PubMed website (http://www.ncbi.nlm.nih.gov/pubmed) as .txt file, after reading the IDs into memory. We initiate threads such as ProxyThread which is reponsible for crawling the proxy website and download and update fresh lists of proxy servers, WriteThread waits goes linearly through the PIDs list and waits until stats for a PID has been collected and then writes them to an output file in a specific format, StatThread is the main component of the program, it firsts calls prepData which crawls through the PubMed Article webpage and extracts links to sister websites and then launch worker PMIDThread threads that will independently request/receive JSON objects from social media web APIs parse, store them to a list that will be read by the WriteThread. By doing this, the above mentioned 9,000,000 HTTP requests can processed in approximately 4 days instead of 40 days.

### Required libraries/tools
 - Python Requests API (http://docs.python-requests.org/en/master/)
 - Selenium WebDriver (http://www.seleniumhq.org/projects/webdriver/)
 - geckodriver (https://github.com/mozilla/geckodriver/releases)
 - Beautiful Soup (https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-beautiful-soup)
 - TwitterSearch (https://github.com/ckoepp/TwitterSearch)

### Needed Improvements
Some refactoring is needed to be done because I gradually put new features into the program such as website crawling, custom PriorityQueue). Program Parameters in the beginning of the program need to be programmed to be initialized by command line instead directly specifying in the source code. Maybe add a GUI interface instead of command line interface that shows the progress of the program.

