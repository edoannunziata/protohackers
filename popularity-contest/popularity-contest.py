# Let's see what other users are up to :-)
# This script uses the Github, Gitlab and protohackers APIs to fetch
# how many users used each language.

import requests
import operator
import os
from functools import reduce
from collections import Counter
from matplotlib import pyplot as plt


try:
    with open('.env') as f:
        for line in f:
            try:
                k, v = line.split('=')
                os.environ[k.strip()] = v.strip()
            except ValueError:
                pass
except IOError:
    pass

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)

BASE_HEADERS = {
    "User-Agent": "edoannunziata/protohackers - popularity-contest generating pie graph script"
}

if GITHUB_TOKEN is None:
    GITHUB_HEADERS = BASE_HEADERS
else:
    GITHUB_HEADERS = BASE_HEADERS | {'Authorization': f'Bearer {GITHUB_TOKEN}'}


def fetch_github(user, repo):
    r = requests.get(f'https://api.github.com/repos/{user}/{repo}/languages', headers=GITHUB_HEADERS)
    if not r:
        return None
    m = max(r.json().items(), key=lambda u: u[1])
    return m[0]


def fetch_gitlab(user, repo):
    r = requests.get(f'https://gitlab.com/api/v4/projects/{user}%2f{repo}/languages', headers=BASE_HEADERS)
    if not r:
        return None
    m = max(r.json().items(), key=lambda u: u[1])
    return m[0]


def get_lang(url):
    to_attempt = ['protohackers', 'protohacker', 'protohack']
    if url.startswith('https://github.com/'):
        a = url[len('https://github.com/'):].split('/')
        if len(a) == 2 and a[1]:
            to_attempt = [a[1], *to_attempt]
        return next((u for u in (
            fetch_github(a[0], w) for w in to_attempt
        ) if u), None)
    elif url.startswith('https://gitlab.com/'):
        a = url[len('https://gitlab.com/'):].split('/')
        if len(a) == 2 and a[1]:
            to_attempt = [a[1], *to_attempt]
        return next((u for u in (
            fetch_gitlab(a[0], w) for w in to_attempt
        ) if u), None)


def get_problem_ids():
    j = requests.get('https://api.protohackers.com/problems', headers=BASE_HEADERS).json()
    return (p['id'] for p in j['problems'])


def main():
    d = [
        requests.get(f'https://api.protohackers.com/leaderboard/{n}', headers=BASE_HEADERS).json()
        for n in get_problem_ids()
    ]

    x = reduce(operator.or_, ({
            v['displayname']: v['repo_url']
            for v in n['leaderboard']
            if v['repo_url']
        } for n in d), {}
    )

    L = Counter(filter(None, (get_lang(u) for u in x.values())))

    plt.pie(L.values(), labels=[u + ": " + str(v) for u, v in L.items()])
    plt.savefig('pie.png')


if __name__ == '__main__':
    main()
