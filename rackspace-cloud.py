#!/usr/bin/env python
# -*- coding: utf-8 -*-

# usage

# chmod +x rackspace-files.py
# then:
#
# ./rackspace-files.py store --path=directory

# fetching the newest object
# ./rackspace-files.py fetch-newest-object --to=~/backup.sql

## there is help if you just type:
# ./rackspace-files.py --help

#######################################################
#      CONFIGURATION AREA, SET YOUR API KEY HERE      #
# --------------------------------------------------- #
RACKSPACE_USERNAME = 'xxxxxxxx'
RACKSPACE_API_KEY  = 'zzzzzzzzzzzzzzzzzzzzzz'
DEFAULT_CONTAINER_NAME = 'testing'
DEFAULT_SUBDIR_OPTION = 'no'
DEFAULT_TTL_OPTION = '295200'
OUR_EMAIL = 'tech@acme.com'
#######################################################

from datetime import datetime
from os.path import abspath, split
from os.path import exists, isfile, expanduser
from ssl import SSLError
from cloudfiles.errors import NoSuchObject
from cloudfiles.errors import ResponseError
from cloudfiles.errors import ContainerNotEmpty
import commands
import time

def ensure_the_library_is_installed(name):
    print 'You have to install the python library "%s" in order to use ' \
          'this script' % name
    print
    print 'Just type: sudo pip install %s and you should be fine :)' % name
    raise SystemExit(1)

try:
    from argh import *
except ImportError:
    ensure_the_library_is_installed('argh')

try:
    import cloudfiles
    from cloudfiles.errors import NoSuchObject
except ImportError:
    ensure_the_library_is_installed('python-cloudfiles')


def convert_bytes(bytes):
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2f bytes' % bytes
    return size


def progress_for(action):
    def progress_callback(transferred, size, up=True):
        transferred, size = map(convert_bytes, (transferred, size))
        print '{2}-> {3} {0} of {1}'.format(
            transferred,
            size,
            up and '\033[A' or '',
            action,
        )
    return progress_callback


@arg('--container', default=DEFAULT_CONTAINER_NAME,
    help='The name of the cloudfiles container that will hold your file',
)

def delete_container(args):
    "Deletes a container on Rackspace Cloud Files"
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )
    
    container = connection.get_container(args.container)
    for obj in container.list_objects():
            for w in range(1,10):
                if w != 1:
                    connection = cloudfiles.get_connection(  RACKSPACE_USERNAME, RACKSPACE_API_KEY, )
                    try:
                         container.get_object(obj)
                         print 'Trying again to delete..'
                         container.delete_object(obj)
                         break
                    except NoSuchObject:
                         print 'Not existing anymore'
                         break
                    except ResponseError:
                         break
                    except SSLError:
                         break
                try:
                    print 'Object to delete "%s"' % obj
                    container.delete_object(obj)
                    print 'Object "%s" deleted!' % obj
                    break
                except SSLError:
                    print "Rackspace SSL error.. retrying"
                except ResponseError:
                    break       
                time.sleep(5)
                if w > 10:
                    print "Giving up trying to delete file.. too many error attempts!"
                    raise SystemExit(1)
    print "Finished deleting files.. confirming.." 
    time.sleep(5)    
    getobj=container.list_objects()
    if getobj:
        print "Container not empty!... Deleting remaining files.."
        for obj in container.list_objects():
             try:
                 container.delete_object(obj)
             except ResponseError:
                 print "File not in container anymore" 
        connection.delete_container(args.container)
        print 'Container "%s" deleted' % args.container
    else:
        try:
            connection.delete_container(args.container)
            print 'Container "%s" deleted' % args.container
        except ContainerNotEmpty:
            connection = cloudfiles.get_connection(  RACKSPACE_USERNAME, RACKSPACE_API_KEY, )
            container = connection.get_container(args.container)
            for obj in container.list_objects():
                 try:
                     container.delete_object(obj)
                 except ResponseError:
                     print "File not in container anymore"
            connection.delete_container(args.container)
            print 'Container "%s" deletedNE' % args.container

@arg('--path',
    help='The local path to the file you wanna store there',
)
@arg('--container', default=DEFAULT_CONTAINER_NAME,
    help='The name of the cloudfiles container that will hold your file',
)
@arg('--subdironly', default=DEFAULT_SUBDIR_OPTION,
    help='Only uploads subdirectories to the container',
)
@arg('--ttl', default=DEFAULT_TTL_OPTION,
    help='TTL to use for CDN',
)

def store(args):
    "Stores a local file in a given container on Rackspace Cloud Files"
    fullpath = expanduser(args.path)
    print 'the directory is "%s"' % fullpath
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )

    container = connection.create_container(args.container)

    if not exists(fullpath):
        print 'The directory "%s" does not exist!' % fullpath
        raise SystemExit(1)
    
    if not isfile(fullpath):
        cmd = 'find "%s" -type d' % fullpath
        result = commands.getoutput(cmd)
        array = result.split()
        print "creating structure of nested directories.."
        cmd='curl -D - -H "X-Auth-Key: 11cd1fca407e058c9d6cd3eaeba72ec6" -H "X-Auth-User: masman84" https://auth.api.rackspacecloud.com/v1.0'
        result = commands.getoutput(cmd)
        cmdarray = result.split()
        authtoken=cmdarray[66]
        storageurl=cmdarray[53]
        storageurl=storageurl+'/'+container.name+'/'
        print storageurl
        print authtoken

        for i in array:
            print i
            print fullpath
            if args.subdironly == "yes":
                if i == fullpath:
                    continue
                i = i[ len(fullpath)+1:]
  	
            url=storageurl+i
            print url
            if args.subdironly == "yes":
                cmd='cd "%s"; curl -X PUT -T "%s" -D - -H "Content-Type: application/directory" -H "X-Auth-Token: "%s"" "%s" ' % (fullpath,i,authtoken, url)
            else:
                cmd='curl -X PUT -T "%s" -D - -H "Content-Type: application/directory" -H "X-Auth-Token: "%s"" "%s" ' % (i,authtoken, url)
            print 'Directory "%s" ..created' % i
            result = commands.getoutput(cmd)
    #        print result
        
        print "structure of nested directories..created!\n"
    
    cmd = 'find "%s" -type f' % fullpath
    result = commands.getoutput(cmd) 
    array = result.split()
    for i in array:
        started_at = datetime.now()
        x=i
        if args.subdironly == "yes":
                i = i[ len(fullpath)+1:]
        print "sending %r to %s@rackspace:%s \n" % (
        i, RACKSPACE_USERNAME, container.name)

        #progress_callback = progress_for('saving backup')
    	#progress_callback(0, 0, False)

        destination = container.create_object(i)
        if args.subdironly == "yes":
    	    for w in range(1,10): 
                if w != 1:
                     connection = cloudfiles.get_connection(  RACKSPACE_USERNAME, RACKSPACE_API_KEY, )
                     # progress_callback(0, 0, False)
                     destination=container.create_object(i)
                try:
               #     destination.load_from_filename(x, True, progress_callback)
                    destination.load_from_filename(x, True)
                    break
                except SSLError:
                    print "Rackspace SSL error.. retrying"
                time.sleep(5)
            if w > 10:
                print "Giving up trying to store file.. too many error attempts!"
                raise SystemExit(1)               
        else:
            for w in range(1,10):
                if w != 1:
                     connection = cloudfiles.get_connection(  RACKSPACE_USERNAME, RACKSPACE_API_KEY, )
                    # progress_callback(0, 0, False)
                     destination=container.create_object(i)
                try:
                #    destination.load_from_filename(i, True, progress_callback)
                    destination.load_from_filename(i, True)
                    break
                except SSLError:
                    print "Rackspace SSL error.. retrying"
                time.sleep(5)
            if w > 10:
                print "Giving up trying to store file.. too many error attempts!"
                raise SystemExit(1)

    	print "saved %r to %s@rackspace:%s succesfully!" % (
        i, RACKSPACE_USERNAME, container.name)

    	print "it took like %s seconds" % (datetime.now() - started_at).seconds 
    
    val = int(args.ttl) * 3600
    if val == 252900 :
       container.make_public(259200)
    else :
       container.make_public(val)
    resulturi=container.public_uri()
    print 'Container  "%s" ..CDN enabled' % container.name
    print 'CDN URL: "%s" ' % resulturi
    cont = connection.get_container(args.container)
    resultssl=cont.public_ssl_uri()
    print 'CDN SSL URL: "%s" ' % resultssl

@alias('fetch-newest-object')
@arg('--from-container',
    help='The container name to look for the newest object',
    default=DEFAULT_CONTAINER_NAME,
)
@arg('--to',
    help='a path to save a new file to',
)
def fetch_newest_object(args):
    "retrieves the most recent backup file"
    fullpath = abspath(expanduser(args.to or '.'))
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )
    container = connection.create_container(args.from_container)

    remote_backup_items = container.list_objects_info()
    remote_backup_items.sort(key=lambda x: x['last_modified'])
    print "found %d items in the container '%s'" % (
        len(remote_backup_items),
        args.from_container,
    )
    # now we have the newest being the latest

    newest = remote_backup_items[-1]
    backup = container.get_object(newest['name'])
    print "the latest object is %s" % newest['name']
    save_to = args.to and fullpath or newest['name']
    print "saving to %s" % save_to

    progress_callback = progress_for('downloading')
    progress_callback(0, 0, False)
    backup.save_to_filename(save_to, progress_callback)


@alias('list')
@arg('--from-container',
    help='The container name to list backups',
    default=DEFAULT_CONTAINER_NAME,
)
@arg('--limit',
    help='the limit of objects to fetch',
    default=3,
)
def list_backups(args):
    "list the remote files"
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )
    container = connection.create_container(args.from_container)

    remote_backup_items = container.list_objects_info()
    remote_backup_items.sort(key=lambda x: x['last_modified'])
    remote_backup_items = list(reversed(
        sorted(remote_backup_items, key=lambda x: x['bytes'])))

    limited_list = remote_backup_items[:int(args.limit)]

    def header():
        print 'Showing %d of %d items in the container "%s"' % (
            len(limited_list),
            len(remote_backup_items),
            args.from_container,
        )

    header()
    for item in limited_list:
        if int(item['bytes']) == 0:
            continue

        print "    name: %s (%.0fMB)" % (
            item['name'],
            float(item['bytes']) / 1024 / 1024,
        )

        for k, v in item.items():
            if k != 'name':
                print "        %s: %s" % (k, v)

        print

    header()


@arg('--from-container',
    help='The container name to look for the newest object',
    default=DEFAULT_CONTAINER_NAME,
)
@arg('--imsure',
    help='if should just delete with no questions',
    default=False,
)
@arg('--object',
    help='the object name, you can retrieve names with the "list" sub-command',
)
def erase(args):
    "erase a remote file from a container"
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )
    m = '\033[1;31mAre you \033[1;37m100%\033[1;31m ' \
        'sure you wanna delete \033[1;32m"{0} ?"\033[0m (y/n)'

    container = connection.create_container(args.from_container)
    try:
        obj = container.get_object(args.object)
        question = m.format('%s (%s)' % (
            obj.name, convert_bytes(obj.size)))

        agreed = decided = bool(args.imsure)
        while not decided and not agreed:
            i = raw_input(question).strip().lower()
            decided = i in ['y', 'n']
            agreed = i == 'y'

        if agreed:
            obj.purge_from_cdn(email=OUR_EMAIL)
            container.delete_object(obj.name)
        else:
            print
            print "Ok then, never mind"

    except NoSuchObject:
        print 'There is no such object "{0}" in the container "{1}"'.format(
            args.object,
            args.from_container,
        )

def contlistall(args):
    "Lists all available containers"
    connection = cloudfiles.get_connection(
        RACKSPACE_USERNAME,
        RACKSPACE_API_KEY,
    )
    containers = connection.get_all_containers()
    for container in containers:
        print container.name


if __name__ == '__main__':
    p = ArghParser()
    p.add_commands([store, delete_container, fetch_newest_object, list_backups, erase, contlistall])
    p.dispatch()
