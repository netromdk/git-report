#!/usr/bin/env python
import os
import re
import sys
import subprocess
from datetime import datetime

SEP = ',|,'
LOG_CMD = 'git log --pretty=format:"%an{}%ae{}%at"  --shortstat --no-color'.format(SEP, SEP)
FILES_CHANGED_REGEX = re.compile(r'(\d+)\s+files\s+changed')
INSERTIONS_REGEX = re.compile(r'(\d+)\s+insertions')
DELETIONS_REGEX = re.compile(r'(\d+)\s+deletions')

def create_cmd():
  return filter(None, LOG_CMD.split(' '))

def get_commit_info(repo):
  print('Running git log..')
  res = subprocess.run(create_cmd(), stdout = subprocess.PIPE, cwd = repo)
  print('Sanitizing output..')
  return res.stdout.decode('utf-8').replace('\"', '').splitlines()

def format_timestamp(timestamp):
  utc_time = datetime.utcfromtimestamp(float(timestamp))
  return utc_time.strftime("%Y-%m-%d %H:%M:%S (UTC)")

def process(info):
  author_email = {} # author -> email
  author_timestamp = {} # author -> [timestamps]
  author_changes = {} # author -> (#files changed, #insertions, #deletions)
  total_commits = 0
  total_files_changed = 0
  total_insertions = 0
  total_deletions = 0
  oldest_timestamp = -1
  latest_timestamp = -1
  previous_author = None

  for line in info:
    if SEP in line:
      total_commits += 1
      (author, email, timestamp) = line.split(SEP)
      previous_author = author
      author_email[author] = email
      if not author in author_timestamp:
        author_timestamp[author] = []
      author_timestamp[author].append(timestamp)
      if oldest_timestamp == -1:
        oldest_timestamp = timestamp
      oldest_timestamp = min(oldest_timestamp, timestamp)
      if latest_timestamp == -1:
        latest_timestamp = timestamp
      latest_timestamp = max(latest_timestamp, timestamp)
    elif previous_author:
      author = previous_author
      files_changed = 0
      m = FILES_CHANGED_REGEX.search(line)
      if m:
        files_changed = int(m.group(1))
        total_files_changed += files_changed
      insertions = 0
      m = INSERTIONS_REGEX.search(line)
      if m:
        insertions = int(m.group(1))
        total_insertions += insertions
      deletions = 0
      m = DELETIONS_REGEX.search(line)
      if m:
        deletions = int(m.group(1))
        total_deletions += deletions
      if not author in author_changes:
        author_changes[author] = (0, 0, 0)
      changes = author_changes[author]
      author_changes[author] = (changes[0] + files_changed, changes[1] + insertions,
                                changes[2] + deletions)

  print('Total commits: {}'.format(total_commits))
  print('Total files changed: {}'.format(total_files_changed))
  print('Total insertions: {}'.format(total_insertions))
  print('Total deletions: {}'.format(total_deletions))
  print('Oldest/latest timestamps: {} / {}'.format(format_timestamp(oldest_timestamp),
                                                   format_timestamp(latest_timestamp)))

  # Sort authors for most commits first.
  authors = []
  for author in author_email.keys():
    authors.append((author, len(author_timestamp[author])))
  authors.sort(key = lambda x: x[1], reverse = True)

  print('Authors:')
  for elm in authors:
    author = elm[0]
    email = author_email[author]
    timestamps = author_timestamp[author]
    commits = len(timestamps)
    commit_perc = float(commits) / float(total_commits) * 100
    oldest_timestamp = -1
    latest_timestamp = -1
    for timestamp in timestamps:
      if oldest_timestamp == -1:
        oldest_timestamp = timestamp
      oldest_timestamp = min(oldest_timestamp, timestamp)
      if latest_timestamp == -1:
        latest_timestamp = timestamp
      latest_timestamp = max(latest_timestamp, timestamp)
    changes = author_changes[author]
    print('  {} ({}): {} commits ({:.1f}%), {} files changed, {} insertions, {} deletions'.
          format(author, email, commits, commit_perc, changes[0], changes[1], changes[2]))

def main():
  repo = os.path.abspath(sys.argv[1])
  print('Git repo: {}'.format(repo))

  if not os.path.exists(repo):
    print('Repo doesn\'t exist!')
    return

  print('Retrieving commits..')
  info = get_commit_info(repo)

  print('Processing commits..')
  process(info)

if __name__ == '__main__':
  if len(sys.argv) != 2:
    print('usage: {} <path to git repo>'.format(sys.argv[0]))
    sys.exit(-1)

  main()