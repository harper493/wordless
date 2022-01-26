#!/usr/bin/python3.8

import os
import sys
from dataclasses import dataclass
from typing import Callable
import random
import itertools
import math
import cmd
import readline
from default_words import default_words

DEFAULT_LENGTH = 5

alphabet = 'abcdefghijklmnopqrstuvwxyz'
the_words = None
the_index = None
the_cli = None

class trial(object):

    def __init__(self, key=None, text=None, compare=None):
        self.key = key
        if self.key:
            self.reset()
        elif text:
            self.parse(text)
        if compare:
            self.compare(compare)

    def reset(self):
        self.scores = [0] * len(self.key)

    def compare(self, test):
        self.reset()
        letters = set(test)
        for k,l,i in zip(self.key, test, range(len(self.key))):
            if k==l:
                self.scores[i] = 1
            elif k in letters:
                self.scores[i] = -1
        return self

    def match(self, test):
        letters = set(test)
        for k, l, v in zip(self.key, test, self.scores):
            if v>0 and k!=l:
                return False
            elif v==0 and k in letters:
                return False
            elif v<0 and (k not in letters or k==l):
                return False
        return True

    def find(self, idx):
        best_words = idx.find_best(self)
        return set([ w for w in best_words or the_words if self.match(w) ])

    def parse(self, text):
        self.key = ''
        self.scores = []
        hit = False
        for l in text:
            if l=='+':
                hit = True
            elif not l.isalpha():
                continue
            elif hit:
                hit = False
                self.key += l.lower()
                self.scores.append(1)
            elif l.islower():
                self.key += l
                self.scores.append(0)
            elif l.isupper():
                self.key += l.lower()
                self.scores.append(-1)

    def to_tuple(self):
        return tuple(self.scores)


    def __len__(self):
        return len(self.key)

    def __iter__(self):
        for k, i, s in zip(self.key, range(len(self)), self.scores):
            yield k, i, s

    def __str__(self):
        result = ''
        for l, s in zip(self.key, self.scores):
            if s>0:
                result += f'+{l}'
            elif s<0:
                result += l.upper()
            else:
                result += l
        return result

    def possible(self):
        for s in itertools.product((-1,0,1), repeat=len(self)):
            self.scores = s
            yield self

class trial_set(object):

    def __init__(self, text=None):
        self.trials = []
        if text:
            self.parse(text)

    def append(self, t):
        self.trials.append(t)

    def __iter__(self):
        for t in self.trails:
            yield t

    def __len__(self):
        return len(self.trails)

    def parse(self, text):
        self.trials = [trial(text=t) for t in text.split(',')]

    def match(self, idx):
        result = None
        if self.trials:
            result = self.trials[0].find(idx)
            for t in self.trials[1:]:
                result &= t.find(idx)
        return result

class words(object):

    def __init__(self, dict=None, length=0):
        self.length = length
        self.dict = []
        if dict:
            self.load(dict)

    def load(self, dict):
        words = [ w.lower() for w in (dict or []) if self.length==0 or len(w)==self.length ]
        words = sorted(words)
        self.dict = words

    def load_file(self, filename):
        with open(filename, 'r') as f:
            lines = [ line.strip() for line in f ]
            self.load(lines)

    def choose(self):
        return random.choice(self.dict)

    def __iter__(self):
        for w in self.dict:
            yield w

    def __getitem__(self, i):
        return self.dict[i]

    def __len__(self):
        return len(self.dict)

class index(object):

    def __init__(self, words=None):
        self.keys = {}
        if words:
            for w in words:
                self.load_one(w)

    def load_one(self, word):
        def _append(l, i):
            try:
                self.keys[(l, i)].append(word)
            except KeyError:
                self.keys[(l, i)] = [word]
        for i, l in enumerate(word):
            _append(l, i)
        for l in set(word):
            _append(l, -1)

    def find_best(self, t):
        best = None
        for k, i, v in t :
            if v>0:
                k1 = self.keys.get((k, i), None)
            elif v<0 :
                k1 = self.keys.get((k, -1), None)
            else:
                k1 = None
            if k1 and (not best or len(best) > len(k1)) :
                best = k1
        return best

class partition(object):

    def __init__(self, words, key):
        self.words = set(words)
        self.evaluate(key)

    def evaluate(self, key):
        self.results = {}
        for p in trial(key=key).possible():
            ww = [ w for w in p.find(the_index) if w in self.words ]
            tup = p.to_tuple()
            self.results[tup] = len(ww)
        total = sum(self.results.values())
        self.entropy = -sum([ x/total * math.log(x/total) for x in self.results.values() if x>0 ])

def old_stuff():
    length = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if length < 0:
        length = -length
        unique = False
    else:
        unique = True

    counts = {}
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        counts[letter] = 0

    with open(sys.argv[1]) as f:
        for line in f.readlines():
            line = line.strip()
            if len(line) == length or length == 0:
                letters = set()
                for letter in line:
                    letters.add(letter)
                for letter in letters if unique else line:
                    try:
                        counts[letter] += 1
                    except:
                        pass
    print(counts)
    total = sum(counts.values())
    keys = sorted(counts.keys())
    sorteds = sorted(counts.items(), key=lambda i: i[1], reverse=True)

    for i in range(len(counts)):
        print(f'{keys[i]} {100 * counts[keys[i]] / total:6.3f} {sorteds[i][0]} {100 * sorteds[i][1] / total:6.3f}')

class cli(cmd.Cmd):
    intro = ''
    prompt = 'wordless> '

    def __init__(self):
        super().__init__()
        self.new_word()
        self.trials = trial_set()
        self.match = the_words

    def do_try(self, arg):
        'try a word against the current word, showing result'
        t = trial(text=self.split_args(arg)[0])
        t.compare(self.word)
        self.trials.append(t)
        self.match = self.trials.match(the_index)
        if len(self.match) < 1000 :
            print(f"{t} {len(self.match)} possibilities: {', '.join(self.match)}")
        else:
            print(f"{t} {len(self.match)} possibilities")

    def do_test(self, arg):
        'evaluate one or more matches to find the remaining words'
        t = trial_set(text=self.split_args(arg)[0])
        m = t.match(the_index)
        print(f"{len(m)} possibilities: {', '.join(m)}")

    def do_new(self, arg):
        'select a new random word'
        self.new_word()

    def do_reveal(self, arg):
        'show the current word'
        print(self.word)

    def do_set(self, arg):
        'set the current word to a known value'
        self.new_word(self.split_args(arg)[0])

    def do_entropy(self, arg):
        'calculate the entropy for a given word in the current state'
        p = partition(self.match, self.split_args(arg)[0])
        print('\n'.join([f'{str(pk):30} {pl}' for pk,pl in p.results.items() if pl>0]))
        print(f'entropy = {p.entropy}')

    def do_best(self, arg):
        'find the best (highest entropy) word to use right now (takes a LONG time)'
        best = (None, 0)
        last_word = '!'
        for w in the_words:
            if w[0]!=last_word[0]:
                print(f"{w[0]}", end='')
                last_word = w
            p = partition(self.match, w)
            if p.entropy > best[1]:
                best = (w, p.entropy)
        print()
        print (f"Best word is '{best[0]}', entropy = {best[1]}")

    def new_word(self, word=None):
        self.word = word if word else the_words.choose()
        self.trials = trial_set()

    def split_args(self, arg):
        return arg.split()

def main():
    global the_words, the_index, the_cli
    random.seed()
    the_words = words(length=int(sys.argv[2]) if len(sys.argv) >= 2 else DEFAULT_LENGTH)
    if len(sys.argv) > 1:
        the_words.load_file(sys.argv[1])
    else:
        the_words.load(default_words.split('\n'))
    the_index = index(the_words)
    the_cli = cli()
    the_cli.cmdloop()

main()
