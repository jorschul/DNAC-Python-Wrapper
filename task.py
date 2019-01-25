#!/usr/bin/env python

from dnac import SUPPORTED_DNAC_VERSIONS, \
                 UNSUPPORTED_DNAC_VERSION
from dnacapi import DnacApi, \
                    DnacApiError, \
                    REQUEST_NOT_OK
from taskresults import TaskResults
import requests
import json

## module globals

# task states
TASK_EMPTY=""
TASK_CREATION="CLI Runner request creation"

## exceptions

class TaskError(DnacApiError):

    def __init__(self, msg):
        super(DnacApiError, self).__init__(msg)

## end exceptions

## end module globals

class Task(DnacApi):
    '''
    The Task class manages a task running on Cisco DNA Center.  Tasks run
    asynchronously on Cisco DNAC.  In other words, although a task is
    created, its results may not immediately be available.  Cisco DNA Center
    provides a task ID for checking a task's status, and this object stores
    it in its __taskId attribute.

    Task does not wait for a task running on Cisco DNAC to finish.  Instead,
    it returns the task's current state contained in the response's
    "progress" field.  Cisco DNAC provides two states: either the task is
    being created or it has finished.  During creation, Cisco DNAC sets
    progress to "CLI Runner request creation", and when it's done, progress
    is a string that can be converted to a dict that will look like:
    {fileId: <uuid>}.
    
    The task.py module defines a two constant that can be used for
    monitoring a task with checkTask().  Use TASK_EMPTY to see if a task
    has been created, and use TASK_CREATION to detect that Cisco DNA Center
    is preparing a task to run.  There is no constant for task completion.
    Instead, checkTask() returns the progress string Cisco DNAC furnished.

    When a task has completed, Cisco DNA Center stores the results in a file
    and provides the file's ID as the results of making an API call to
    the task.  Subsequently, when using this class' checkTask() method,
    if the task has completed, Task creates a TaskResults instance using
    the file ID returned.  Task then saves the TaskResults object as its
    __taskResults attribute.  This makes it easy for programmers to
    quickly and easily retrieve the actual results to be parsed.

    Usage:
        d = Dnac()
        task = Task(d, "aTask")
        task.checkTask()
        results = task.taskResults.getResults()
    '''

    def __init__(self,
                 dnac,
                 name,
                 taskId = "",
                 requestFilter="",
                 verify=False,
                 timeout=5):
        '''
        __init__ makes a new Task object.  An empty task object may be
        created by only passing a Dnac object and name for the task.  In
        this case, be certain to later set the taskId with the UUID of
        a task running on Cisco DNAC.
        
        The preferred method of creating a Task object is to pass the
        task's UUID to __init__ so that the Task instance sets its name
        and URL making it ready for use to monitor the task.  In this case,
        the name parameter is ignored and Task instead sets its name
        to the value "task_<id>".

        Parameters:
            dnac: A reference to the containing Dnac object.
                type: Dnac object
                default: None
                required: Yes
            name: A user friendly name for finding this object in a Dnac
                  instance.  If name is not included, __init__ sets
                  __name to "task__<id>", where <id> is the value of
                  the object's __id attribute..
                type: str
                default: None
                required: Yes
            taskId: The UUID of the task running on Cisco DNAC.  When
                    included, as part of calling __init__, the new object
                    sets its name and url based on id's value:
                    name = "task_<id>"
                    url = "dnac.url/self.respath/<id>"
                type: str
                default: None
                required: No
            requestFilter: An expression for filtering Cisco DNAC's
                           response.
                type: str
                default: None
                required: No
            verify: A flag used to check Cisco DNAC's certificate.
                type: boolean
                default: False
                required: No
            timeout: The number of seconds to wait for Cisco DNAC's
                     response.
                type: int
                default: 5
                required: No

        Return Values:
            Task object: a new Task object.

        Usage:
            d = Dnac()
            id = <task ID from Cisco DNAC>
            name = "task_" + id
            task = Task(d, name)
            task.taskId = id
            newId = <another task ID from Cisco DNAC>
            newTask = Task(d, "aNewName", newId)
        '''

        if dnac.version in SUPPORTED_DNAC_VERSIONS:
            self.__respath = "/api/v1/task"
        else:
            raise TaskError(
                "__init__: %s: %s" %
                (UNSUPPORTED_DNAC_VERSION, dnac.version)
                           )

        self.__id = taskId
        self.__url = ""
        self.__progress = TASK_EMPTY
        self.__taskResults = {}
        self.__taskResultsId = ""
        super(Task, self).__init__(dnac,
                                   name,
                                   resourcePath=self.__respath,
                                   requestFilter=requestFilter,
                                   verify=verify,
                                   timeout=timeout)
        if self.__id != "":
            self.name = "task_" + self.__id
            self.__url = self.respath + "/" + self.__id

## end __init__()

    @property
    def id(self):
        '''
        Get method id returns the value of __id, the task's UUID in Cisco
        DNAC.

        Parameters:
            None

        Return Values:
            str: The task's UUID.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", id=taskId)
            task.id
        '''
        return self.__id

## end id getter

    @id.setter
    def id(self, id):
        '''
        The id set method changes attribute __id to the task UUID passed,
        and it changes the name and url attributes to include the new id.
            task.name = "task_<id>"
            task.url = "respath/<id>"

        Parameters:
            id: str
            default: None
            required: Yes

        Return Values:
            None

        Usage:
            d = Dnac()
            id = aTaskId
            task = Task(d, "aTask")
            task.id = id
        '''
        self.__id = id
        self.name = "task_" + self.__id
        self.url = self.respath + "/" + self.__id

## end id setter

    @property
    def url(self):
        '''
        Get method url returns the value of __url, a resource path
        for accessing a task running on Cisco DNAC.

        Parameters:
            None

        Return Values:
            str: The task's resource path.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", id=taskId)
            task.url
        '''
        return self.__url

## end url getter

    @url.setter
    def url(self, url):
        '''
        Set method url changes attribute __url to the value passed.  In
        response to an API call that creates a task center such as running 
        a command, Cisco DNA Center responds with a task ID and a URL.  The
        URL is a resource path to the task with its ID pre-appended.
        Use the URL as this method's parameter.  __url is updated to the
        value passed, and the function extracts the task ID and updates
        the object's __id accordingly.

        Parameters:
            url: str
            default: None
            required: Yes

        Return Values:
            None

        Usage:
            d = Dnac()
            url = "/api/v1/task/<taskId>"
            task = Task(d, "aTask")
            task.url = url
        '''
        self.__url = url
        pathElts = url.split("/")
        self.__id = pathElts[ len(pathElts) - 1 ]
        self.name = "task_" + self.__id

## end url setter

    @property 
    def progress(self):
        '''
        Get method progress returns the value of __progress, which 
        indicates the current stat of the running task.

        Parameters:
            None

        Return Values:
            str: The task's current state:
                TASK_EMPTY: no task has been created in Cisco DNAC
                TASK_CREATION: Cisco DNAC is preparing the task to run
                <progress>: a string formatted as "{fileId: <id>}".
                            Use json.loads to convert it to a dict.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", id=taskId)
            task.progress
        '''
        return self.__progress

## end progress getter

    @progress.setter
    def progress(self, progress):
        '''
        Set method progress changes attribute __progress to the task's
        current state according to progress' current value.

        Parameters:
            progress: str (See progress' get method for valid values.
                           This method does not yet check the passed
                           value's bounds.)
            default: None
            required: Yes

        Return Values:
            None

        Usage:
            d = Dnac()
            task = Task(d, "aTask", "aTaskId")
            # checkTask already sets task.__progress but it also returns it
            task.progress = task.checkTask()
        '''
        self.__progress = progress

## end progress setter

    @property
    def taskResults(self):
        '''
        Get method taskResults returns the TaskResults object associated
        with the task referenced by this object.  If the task has not
        finished, None is returned.

        Rather than using this method, users are encouraged to directly
        access the TaskResults object and call its getResults method,
        which returns a list with the task's output.

        Parameters:
            None

        Return Values:
            str: The task's resource path.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", id=taskId)
            task.checkTask()
            results = task.results
        '''
        return self.__taskResults

## end taskResults getter

    @taskResults.setter
    def taskResults(self, taskResults):
        '''
        Set method taskResults sets the object's __taskResults to point
        to the new TaskResults object passed.

        Parameters:
            taskResults: TaskResults object
            default: None
            required: Yes

        Return Values:
            None

        Usage:
            d = Dnac()
            task = Task(d, "aTask", aTaskId)
            task.checkResults()
            # Not a realistic usage but here it is anyway
            newTask = Task(d, "aNewTask", aNewTaskId)
            newTask.taskResults = task.taskResults
        '''
        self.__taskResults = taskResults

## end taskResults setter

    @property
    def taskResultsId(self):
        '''
        The taskResultsId get method retrieves the object current value
        for __taskResultsId, which can be used to generate a new
        TaskResults object.

        Parameters:
            None

        Return Values:
            str: The UUID to the task's results, a file on Cisco DNAC.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", id=taskId)
            task.checkTask()
            results = TaskResults(d, "aName", task.taskResultsId)
        '''
        return self.__taskResultsId

## end taskResultsId getter

    @taskResultsId.setter
    def taskResultsId(self, taskResultsId):
        '''
        Set method taskResultsId sets the object's __taskResultsId to
        to a new UUID for a task's results, i.e. a file on Cisco DNAC.

        Parameters:
            taskResultsId: str
            default: None
            required: Yes

        Return Values:
            None

        Usage:
            d = Dnac()
            task = Task(d, "aTask", aTaskId)
            task.checkResults()
            # Not a realistic usage but here it is anyway
            newTask = Task(d, "aNewTask", aNewTaskId)
            newTask.taskResultsId = task.taskResultsId
        '''
        self.__taskResultsId = taskResultsId

## end taskResultsId setter

    def checkTask(self):
        '''
        Class method checkTask issues an API call to Cisco DNA Center and
        provides the task's results.  In its current form, this method
        assumes the task has completed and that Cisco DNAC provided a file
        ID for getting the task's results.  This will eventually be updated
        to handle situation in which this is not the case.

        If the task completed its work on Cisco DNAC, this function sets the
        __taskResultsId value to the file's UUID on Cisco DNAC, and it
        creates a new TaskResults object using the UUID to that the actual
        results may easily be queried from this object.  The results get
        save in __taskResults.

        Parameters:
            None

        Return Values:
            str: The task's results identifier, a file UUID on Cisco DNAC.

        Usage:
            d = Dnac()
            task = Task(d, "aTask", "aTaskId")
            task.checkTask()
        '''
        url = self.dnac.url + self.url + self.filter
        hdrs = self.dnac.hdrs
        resp = requests.request("GET",
                                url,
                                headers=hdrs,
                                verify=self.verify,
                                timeout=self.timeout)
        if resp.status_code != requests.codes.ok:
            raise TaskError(
                "checkTask: %s: %s: %s: expected %s" %
                (REQUEST_NOT_OK, url, str(resp.status_code),
                str(requests.codes.ok))
                           )
        else:
            self.__progress = json.loads(resp.text)['response']['progress']
            if self.__progress != TASK_CREATION:
                # task completed
                # get the fileId in the progress dict
                self.__taskResultsId = \
                    json.loads(self.__progress)['fileId']
                # create the task results
                self.__taskResults = TaskResults(self.dnac, \
                                                 "taskResults_", \
                                                 id=self.__taskResultsId)
                # retrieve the results, which are automatically saved in
                # the taskReaults' __results attribute
                self.__taskResults.getResults()
            return self.__progress
                  
## end checkTask()

## end class Task()

if  __name__ == '__main__':

    from dnac import Dnac
    import sys

    d = Dnac()

    t = Task(d, "task")

    print "Task:"
    print
    print "  dnac          = " + str(type(t.dnac))
    print "  name          = " + t.name
    print "  id            = " + t.id
    print "  url           = " + t.url
    print "  respath       = " + t.respath
    print "  filter        = " + t.filter
    print "  verify        = " + str(t.verify)
    print "  timeout       = " + str(t.timeout)
    print "  taskResultsId = " + t.taskResultsId
    print "  taskResults   = " + str(t.taskResults)
    print
    print "Checking task 6e9e1261-f088-4e9c-b2a0-8f006c682694..."
    print
    
    t.id = "6e9e1261-f088-4e9c-b2a0-8f006c682694"
    progress = t.checkTask()

    print "  name          = " + t.name
    print "  id            = " + t.id
    print "  url           = " + t.url
    print "  taskResultsId = " + t.taskResultsId
    print "  taskResultsUrl = " + t.taskResults.url
    print "  taskResults   = " + str(t.taskResults)
    print "  taskResults   = " + str(t.taskResults.getResults())
    print
    print "Checking task /api/v1/task/7d8cb348-c41e-4565-a733-5df4cb91805a"
    print

    t.url = "/api/v1/task/7d8cb348-c41e-4565-a733-5df4cb91805a"
    progress = t.checkTask()

    print "  name          = " + t.name
    print "  id            = " + t.id
    print "  url           = " + t.url
    print "  taskResultsId = " + t.taskResultsId
    print "  taskResultsUrl = " + t.taskResults.url
    print "  taskResults   = " + str(t.taskResults)
    print "  taskResults   = " + str(t.taskResults.getResults())
    print
    print "Testing exceptions..."
    print

    def raiseTaskError(msg):
        raise TaskError(msg)

    errors = (UNSUPPORTED_DNAC_VERSION,
              REQUEST_NOT_OK)

    for error in errors:
        try:
            raiseTaskError(error)
        except TaskError, error:
            print str(type(e)) + " = " + str(e)

    print
    print "Task: unit test complete."
    print

