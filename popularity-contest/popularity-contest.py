# Let's see what other users are up to :-)
# This scripts uses the Github, Gitlab and protohackers API to fetch
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
except:
    pass

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)
GITHUB_HEADERS = {'Authorization': f'Bearer {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

def fetch_github(user, repo):
    r = requests.get(f'https://api.github.com/repos/{user}/{repo}/languages', headers=GITHUB_HEADERS)
    if not r:
        return None
    m = max(r.json().items(), key=lambda u: u[1])
    return m[0]


def fetch_gitlab(user, repo):
    r = requests.get(f'https://gitlab.com/api/v4/projects/{user}%2f{repo}/languages')
    if not r:
        return None
    m = max(r.json().items(), key=lambda u: u[1])
    return m[0]


def get_lang(user, url):
    if url.startswith('https://github.com/'):
        url_cut = url[len('https://github.com/'):]
        a = url_cut.split('/')
        if len(a) == 2 and a[1]:
            return fetch_github(a[0], a[1])
        if len(a) == 1 or not a[1]:
            return (
                fetch_github(a[0], 'protohackers') or
                fetch_github(a[0], 'protohacker') or
                fetch_github(a[0], 'protohack')
            )
    elif url.startswith('https://gitlab.com/'):
        url_cut = url[len('https://gitlab.com/'):]
        a = url_cut.split('/')
        if len(a) == 2 and a[1]:
            return fetch_gitlab(a[0], a[1])
        if len(a) == 1 or not a[1]:
            return (
                fetch_gitlab(a[0], 'protohackers') or
                fetch_gitlab(a[0], 'protohacker') or
                fetch_gitlab(a[0], 'protohack')
            )


def main():
    d = [
        requests.get(f'https://api.protohackers.com/leaderboard/{n}').json()
        for n in range(3)
    ]

    x = reduce(operator.or_, ({
            v['displayname']: v['repo_url']
            for v in n['leaderboard']
            if v['repo_url']
        } for n in d), {}
    )

    L = Counter(filter(None, (get_lang(u, v) for u, v in x.items())))

    plt.pie(L.values(), labels=[u + ": " + str(v) for u, v in L.items()])
    plt.savefig('pie.png')


if __name__ == '__main__':
    main()