# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007-2008 Michael Abbott, Diamond Light Source Ltd.
#
# The Diamond cothread library is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# The Diamond cothread library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Contact:
#      Dr. Michael Abbott,
#      Diamond Light Source Ltd,
#      Diamond House,
#      Chilton,
#      Didcot,
#      Oxfordshire,
#      OX11 0DE
#      michael.abbott@diamond.ac.uk

'''Support for cooperative select functions.  Replaces the functionality of
the standard select module.'''

import select as _select
import ctypes
import cothread


__all__ = [
    'select',           # Non-blocking select function
    'poll',             # Non-blocking emulation of poll object
    'poll_list',        # Simpler interface to non-blocking polling
    'poll_block',       # Simpler interface to blocking polling

    'SelectError',      # Exception raised by select()
    
    # Poll constants
    'POLLIN',           # Data ready to read
    'POLLPRI',          # Urgent data ready to read
    'POLLOUT',          # Ready for writing
    'POLLERR',          # Error condition
    'POLLHUP',          # Hangup: socket has disconnected
    'POLLNVAL',         # Invalid request, not open.
    'POLLRDNORM',
    'POLLRDBAND',
    'POLLWRNORM',
    'POLLWRBAND',
    'POLLMSG',

    'POLLEXTRA',        # If any of these are set there is a socket problem
]


# A helpful routine to ensure that our select() behaves as much as possible
# like the real thing!
PyObject_AsFileDescriptor = ctypes.pythonapi.PyObject_AsFileDescriptor
PyObject_AsFileDescriptor.argtypes = [ctypes.py_object]

POLLIN     = _select.POLLIN
POLLPRI    = _select.POLLPRI
POLLOUT    = _select.POLLOUT
POLLERR    = _select.POLLERR
POLLHUP    = _select.POLLHUP
POLLNVAL   = _select.POLLNVAL
POLLRDNORM = _select.POLLRDNORM
POLLRDBAND = _select.POLLRDBAND
POLLWRNORM = _select.POLLWRNORM
POLLWRBAND = _select.POLLWRBAND
POLLMSG    = _select.POLLMSG

# These three flags are always treated as of interest and are never consumed.
POLLEXTRA = POLLERR | POLLHUP | POLLNVAL


def poll_block(poll_list, timeout = None):
    '''A simple wrapper for the poll method to provide actually directly
    useful functionality.  This will block non-cooperatively, so should only
    be used in a scheduler loop.
        Note that the timeout is in seconds.'''
    p = _select.poll()
    for file, events in poll_list:
        p.register(file, events)
    if timeout is not None:
        # Convert timeout into ms for calling poll() method.
        timeout *= 1000
    try:
        return p.poll(timeout)
    except _select.error:
        # Convert a select error into an empty list of events.  This will
        # occur if a signal is caught, for example if we're suspended and
        # then resumed!
        return []



class _Poller(object):
    '''Wrapper for handling poll wakeup.'''
    __slots__ = [
        'wakeup',           # Task wakeup object for scheduler
        '__events',         # The events we're actually watching
        '__ready_list',     # The events we now know to be ready
    ]
    
    def __init__(self, event_list):
        self.wakeup = cothread._Wakeup()
        self.__events = {}
        self.__ready_list = {}
        for file, events in event_list:
            file = PyObject_AsFileDescriptor(file)
            self.__events[file] = self.__events.get(file, 0) | events

    def notify_wakeup(self, file, events):
        '''This is called from the scheduler as each file becomes ready.  We
        add the file to our list of ready descriptors and wake ourself up.
        We return two masks: a mask of events that we've consumed, and a mask
        of events that we're still interested in.'''
        # Mask out only the events we're really interested in.
        events &= self.__events[file] | POLLEXTRA
        if events:
            # We're interested!  Record the event flag and wake our task.
            self.__ready_list[file] = self.__ready_list.get(file, 0) | events
            cothread._scheduler.wakeup([self.wakeup])
            return (events & ~POLLEXTRA, 0)
        elif self.wakeup.woken():
            # Doesn't matter, we're already awake!  Allegedly we're not
            # interested in any of the listed events...
            return (0, 0)
        else:
            # Tell the notifier to call us another time.
            return (0, self.__events[file])

    def event_list(self):
        return self.__events.items()

    def ready_list(self):
        return self.__ready_list.items()


def poll_list(event_list, timeout = None):
    '''event_list is a list of pairs, each consisting of a waitable
    descriptor and an event mask (generated by oring together POLL...
    constants).  This routine will cooperatively block until any descriptor
    signals a selected event (or any event from HUP, ERR, NVAL) or until
    the timeout (in seconds) occurs.'''
    until = cothread.Deadline(timeout)
    poller = _Poller(event_list)
    cothread._scheduler.poll_until(poller, until)
    return poller.ready_list()


class poll(object):
    '''Emulates select.poll(), but implements a cooperative non-blocking
    version for use with the cothread library.'''
    __slots__ = [
        '__watch_list'      # File selectors being watched and flags 
    ]
    
    def __init__(self):
        self.__watch_list = {}
        
    def register(self, file,
            events = _select.POLLIN | _select.POLLPRI | _select.POLLOUT):
        '''Adds file to the list of objects to be polled.  The default set
        of events is POLLIN|POLLPRI|POLLOUT.'''
        file = PyObject_AsFileDescriptor(file)
        self.__watch_list[file] = events
        
    def unregister(self, file):
        '''Removes file from the polling list.'''
        file = PyObject_AsFileDescriptor(file)
        del self.__watch_list[file]

    def poll(self, timeout = None):
        '''Blocks until any of the registered file events become ready.

        Beware: the timeout here is in milliseconds.  This is consistent
        with the select.poll().poll() function which this is emulating, 
        but inconsistent with all the other cothread routines!

        Consider using poll_list() instead for polling.'''
        return poll_list(self.__watch_list.items(), timeout / 1000.)


class SelectError(Exception):
    def __init__(self, flags):
        self.flags = flags
    def __str__(self):
        reasons = [
            (POLLERR,  'Error on file descriptor'),
            (POLLHUP,  'File descriptor disconnected'),
            (POLLNVAL, 'Invalid descriptor')]
        return 'Select error: ' + \
            ', '.join([reason
                for flag, reason in reasons
                if self.flags & flag])


def select(iwtd, owtd, ewtd, timeout = None):
    '''Non blocking select() function.  The interface should be as for the
    standard library select.select() function (though it raises different
    exceptions).'''

    inputs = (iwtd, owtd, ewtd)
    flag_mapping = (POLLIN, POLLOUT, POLLPRI)

    # First convert the descriptors into a format suitable for poll.
    interest = [(file, flag)
        for files, flag in zip(inputs, flag_mapping)
        for file in files]
    
    # Now wait until at least one of our interests occurs.
    poll_result = dict(poll_list(interest, timeout))

    # Now convert the results back.
    results = ([], [], [])
    for result, input, flag in zip(results, inputs, flag_mapping):
        for object in input:
            file = PyObject_AsFileDescriptor(object)
            events = poll_result.get(file, 0)
            if events & POLLEXTRA:
                # If any of the extra events come up, raise an exception.
                # This corresponds to errors raised by the os select().
                raise SelectError(events)
            elif events & flag:
                result.append(object)
    return results
