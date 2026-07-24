"""Listing 5.4 - a generator is a suspendable, resumable frame: the seed of
async/await.

PEP 342 (Python 2.5) turned generators from one-way producers into two-way
coroutines. send(value) resumes the generator and makes the paused yield
expression evaluate to value; throw injects an exception at the yield point;
close raises GeneratorExit so the generator can release resources. A fresh
generator must be primed with next() before a real send().
"""


def averager():
    total, count, avg = 0.0, 0, None
    while True:
        try:
            x = yield avg                 # value arrives via .send(x)
        except GeneratorExit:
            print("  averager closing")
            return
        total += x
        count += 1
        avg = total / count


g = averager()
next(g)                                   # prime to the first yield
print("--- driving a coroutine with send() ---")
print("  avg after 10:       ", g.send(10))
print("  avg after 10,20:    ", g.send(20))
print("  avg after 10,20,30: ", g.send(30))
g.close()

print()
print("--- priming is mandatory: send() on a just-started generator raises ---")


def gen():
    x = yield
    print("  got", x)


fresh = gen()
try:
    fresh.send(10)
except TypeError as exc:
    print("  send(10) before priming ->", type(exc).__name__ + ":", exc)

print()
print("The suspended frame stays alive on the heap between resumptions, with its")
print("resume point (f_lasti) and stack recorded. That suspendable frame is what")
print("yield from and native async/await generalize.")
