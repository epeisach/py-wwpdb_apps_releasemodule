##
# File:  SearchMP.py
# Date:  23-Jul-2013
# Updates:
##
"""
Run NCBI pubmed fetch utility with multiprocessing option.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os,sys,multiprocessing,traceback

from wwpdb.apps.releasemodule.citation.SearchUtil  import SearchUtil
from wwpdb.apps.releasemodule.utils.MultiProcLimit import MultiProcLimit
from wwpdb.utils.config.ConfigInfo                   import ConfigInfo

class SearchWorker(multiprocessing.Process):
    """
    """
    def __init__(self, path='.', processLabel='', siteId = None, taskQueue=None, resultQueue=None, \
                 mpl = None, log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__processLabel = processLabel
        self.__taskQueue=taskQueue
        self.__resultQueue=resultQueue
        self.__lfh=log
        self.__verbose=verbose
        self.__mpl = mpl
        self.__siteId = siteId

    def fetchEntryList(self,term):
        search = SearchUtil(path=self.__sessionPath, processLabel=self.__processLabel, \
                          term=term, siteId = self.__siteId, log=self.__lfh, verbose=self.__verbose)
        # Speed limit
        if self.__mpl:
            self.__mpl.waitnext()
        search.doSearch()
        return search.getPubmedIdList()

    def run(self):
        processName=self.name
        while True:
            nextList=self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            resultList = []
            for term in nextList:
                list = self.fetchEntryList(term)
                if not list:
                    continue
                #
                dir = {}
                dir['term'] = term
                dir['id'] = list
                resultList.append(dir)
            #
            self.__resultQueue.put(resultList)
        #

class SearchMP(object):
    """
    """
    def __init__(self, path='.', termList=None, siteId = None, log=sys.stderr, verbose=False):
        """
        """
        self.__siteId = siteId
        self.__sessionPath = path
        self.__termList = termList
        self.__lfh = log
        self.__verbose = verbose
        self.__termMap = {}
        self.__cI = ConfigInfo(self.__siteId)
        self.__apikey = self.__cI.get('NCBI_API_KEY')

    def run(self):
        numProc = multiprocessing.cpu_count() * 2
        # Leave room for other processes
        if self.__apikey:
            rate = 8
        else:
            rate = 1
        # Extra in case processing from previous result still going on
        numProc = min(numProc, rate + 1)
        mpl = MultiProcLimit(rate)
        #
        subLists = [self.__termList[i::numProc] for i in xrange(numProc)]
        #
        taskQueue = multiprocessing.Queue()
        resultQueue = multiprocessing.Queue()
        #
        workers = [ SearchWorker(path=self.__sessionPath, processLabel=str(i+1), taskQueue=taskQueue, \
                       resultQueue=resultQueue, log=self.__lfh, verbose=self.__verbose, \
                       siteId = self.__siteId, mpl = mpl) \
                       for i in xrange(numProc) ]
        #
        for w in workers:
            w.start()
        #
        for subList in subLists:
            taskQueue.put(subList)
        #
        for i in xrange(numProc):
            taskQueue.put(None)
        #
        for i in xrange(len(subLists)):
            list = resultQueue.get()
            if not list:
                continue
            #
            for dir in list:
                self.__termMap[dir['term']] = dir['id']
            #
        #
        try:
            for w in workers:
                w.terminate()
                w.join(1)
            #
        except:
            if self.__verbose:
                traceback.print_exc(file=self.__lfh)
            #
        #

    def getTermMap(self):
        return self.__termMap

if __name__ == '__main__':
    f = file(sys.argv[1], 'r')
    data = f.read()
    f.close()
    #
    termlist = data.split('\n')
    termlist.remove('')
    print 'termlist=' + str(len(termlist)) 
    cf = SearchMP(termList=termlist,log=sys.stderr, verbose=False)
    cf.run()
    dir = cf.getTermMap()
    print 'dir=' + str(len(dir))
    print dir
    #
