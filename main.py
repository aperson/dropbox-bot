#! /usr/bin/python

import json
import logging
import os
import time

import urlparse as up

import praw

from database import Database
from utils import delete_tmp_files
from dropbox import DropBox

def build_comment(imgur_url):
    head = '''Hi! I noticed that you posted an image from dropbox.com. I have
            rehosted your image to imgur because high traffic can break 
            dropbox.com links.\n\n'''

    body = '[Here is the rehosted image](' + imgur_url + ')\n\n'

    tail = '''This action was performed by a bot. If there is an issue or
            problem, please report it below.\n\n'''

    foot = '''[^[Bot&nbsp;FAQ]](http://www.reddit.com/r/DropBox_Bot/wiki/index)
        [^[Report&nbsp;Problem]](http://www.reddit.com/message/compose/?to=DropBox_Bot&subject=Problem%20to%20Report)
        [^[Feedback]](http://www.reddit.com/r/DropBox_Bot/submit) 
        [^[Source]](https://github.com/tzoch/dropbox-bot)''' 

    return head + body + tail + foot

def scrape_submissions(domain, blacklist, db, r):
    '''
    This is the main work horse function of the dropbox bot. The bot gets the
    latest submissions to the dropbox.com domain and checks for two conditions.
        1. If it has already processed the submission, the bot skips it
        2. If it is able to be rehosted, we processes it
            - currently, the bot only supports the rehosting of images, but
              if there is a demand for other formats, and if there are 
              convinient hosts to use, they will be implemented

    Currently, there is some basic logging to report the status of the bot.
    However, proper error handling should be added to make sure bad requests
    or 404'd dropbox pages are skipped and do not crash the bot.
    '''

    #submissions = r.get_domain_listing('dropbox.com', sort='new', limit=2)
    # switch the comment out when the bot goes live
    submissions = r.get_subreddit('DropBox_Bot').get_new(limit=10)

    for submission in submissions:
        name = submission.name # makes it easier to reassign this 
        drop = DropBox(submission.url)

        # ignore deleted comments
        if not submission.author:
            logging.info('Skipped! [' + name '] Submission has been deleted')
            continue

        if submission.subreddit.display_name in blacklist:
            logging.info('Skipped! [' + name + '] in a blacklisted subreddit')
            continue

        if db.is_processed(name):
            logging.info('Skipped! [' + name + '] has already been processed')
            continue

        if drop.is_rehostable:
            drop.download_file()
            imgur_url = drop.rehost_image()

            if imgur_url:
                comment = build_comment(imgur_url)
                submission.add_comment(comment)
                db.mark_as_processed(name)
                logging.info('Success! [' + name + '] rehosted')
            else:
                logging.error('Failure! [' + name + '] error while uploading')
        else:
            db.mark_as_processed(name)
            logging.info('Skipped! [' + name + '] is not rehostable')

def main():
    fmt = '[%(asctime)-15s] (%(module)-15s) %(levelname)-8s : %(message)s'
    logging.basicConfig(filename='dropbox-bot.log', 
                        format=fmt,
                        datefmt='%d-%b %H:%M:%S',
                        level=logging.INFO)

    logging.info('Bot Started')

    print '''DropBox Bot started...\n\tTo monitor the bots status check the log
             "dropbox-bot.log"\n\tTo stop the bot, use KeyboardInterrupt'''

    config = json.load(open('config.json'))
    blacklist = config['blacklist']

    db = Database(config['database'])

    r = praw.Reddit(config['user-agent'])
    r.login(config['username'], config['password'])

    while True:
        print 'Top of loop'
        try:
            print 'Scraping submissions'
            scrape_submissions('dropbox.com', blacklist, db, r)
            scrape_submissions('dl.dropboxusercontent.com', blacklist, db, r)
        except KeyboardInterrupt:
            import sys
            sys.exit(0)
        finally:
            delete_tmp_files()
            print 'Bot done scraping...sleeping for 5 minutes'
            logging.info('Sleeping! No new submissions to process')
            time.sleep(300)

if __name__ == '__main__':
    print '[INITIALIZED]'
    main()
