# Chapter 278: Task Group

## The constraint

Running several coroutines concurrently in asyncio meant `asyncio.gather()`, and `gather` had a dangerous gap.
If one of the gathered tasks *failed*, the others were not automatically cleaned up - they kept running, orphaned, doing work whose result nobody would collect, potentially holding resources or making network calls long after the operation they belonged to had failed.
And error handling was awkward: `gather` either returned exceptions as results (easy to ignore) or raised the first one while leaving the rest unhandled.

This is the problem *structured concurrency* solves.
The core idea: concurrent tasks should live inside a *scope*, and the scope should not exit until every task in it has finished - and if any task fails, the rest should be cancelled and the errors reported together.
Tasks should nest in scopes the way blocks nest in code, so that a task cannot outlive the scope that spawned it.
This makes concurrent code reason about lifetimes as cleanly as sequential code: when the block ends, everything it started is done.

The constraint Python 3.11 (2022) answered: **give concurrent tasks a scope with a guaranteed lifetime and no orphans** - an `async with` block you spawn tasks in, that awaits them all and cancels the rest on failure.

This is a two-track chapter.
The asyncio model - the event loop, coroutines, tasks, cancellation - is Deep Volume H's subject, and exception groups are Chapter 21's.
What this chapter owns is the release: the day asyncio got structured concurrency.

## What shipped

`asyncio.TaskGroup` is an async context manager: inside the `async with` block you `create_task` coroutines, and the block does not exit until all of them complete.
If any task raises, the group cancels the siblings and raises an `ExceptionGroup`, caught with `except*`.
Listing 278.1 shows both paths on today's interpreters, using fixed work with no real delays so the output is deterministic.

Verified output (CPython 3.13.5):

```text
--- a TaskGroup runs tasks concurrently and awaits them all ---
  results after the `async with` block : ['a=1', 'b=2', 'c=3']
  create_task() schedules each coroutine in the group; the `async
  with` block does not exit until EVERY task has finished. so after
  the block, all results are guaranteed ready - no manual gather/await
--- the scope guarantees completion: no orphaned tasks ---
  unlike firing tasks and forgetting them, a TaskGroup task cannot
  outlive its block. the scope is the lifetime: enter, spawn, and on
  exit every task is done (or cancelled). that is 'structured
  concurrency' - tasks nest in scopes like blocks nest in code
--- on failure, siblings are cancelled and errors grouped ---
  caught 1 ValueError(s); siblings cancelled = 2
  when 'worker' raised, the TaskGroup CANCELLED the two siblings
  (which would have run for an hour) and raised an ExceptionGroup.
  no task is left running after a failure - the orphan problem gather
  had is gone
--- errors come as an ExceptionGroup, handled with except* ---
  a TaskGroup can fail with SEVERAL errors at once (multiple tasks),
  so it raises an ExceptionGroup and you catch by type with `except*`
  (Chapter 21). one worker failing gave one ValueError in the group;
  many failing would give many, each catchable by its type
--- the constraint answered ---
  gather() let a failed task orphan its siblings and made errors
  awkward. asyncio.TaskGroup (3.11) makes concurrent tasks a SCOPE:
  the `async with` block awaits them all, cancels siblings if one
  fails, and reports errors as an ExceptionGroup. concurrent tasks got
  the same lifetime discipline as a code block - structured concurrency
```

## Why each part answers the constraint

**The scope awaits all tasks.**
The first block shows the happy path: three `fetch` coroutines are scheduled with `create_task` inside the `async with asyncio.TaskGroup()` block, and after the block, all three results are ready (`['a=1', 'b=2', 'c=3']`).
The block does not exit until *every* task finishes, so there is no manual `gather`/`await` to collect results - the scope boundary *is* the "wait for everything" point.

**The scope is the lifetime.**
The second block states the structured-concurrency principle.
Unlike firing tasks and forgetting them, a `TaskGroup` task cannot outlive its block: you enter the scope, spawn tasks, and on exit every task is done or cancelled.
Tasks nest in scopes exactly as blocks nest in code, which is what makes concurrent lifetimes as predictable as sequential ones.

**Failure cancels siblings.**
The third block shows the critical improvement over `gather`.
When the `worker` task raised, the `TaskGroup` *cancelled* the two sibling tasks - which were sleeping for an hour and would otherwise have been orphaned - and the verified output confirms `siblings cancelled = 2`.
No task is left running after a failure.
The orphaned-task problem that `gather` had is structurally eliminated: a failure tears down the whole scope cleanly.

**Errors are grouped.**
The fourth block explains the error model.
Because multiple tasks in a group can fail *simultaneously*, a `TaskGroup` reports failures as an `ExceptionGroup` (Chapter 21), caught with `except*` by type.
One worker failing produced one `ValueError` in the group; many failing would produce many, each catchable by its type.
This is why exception groups and `TaskGroup` shipped in the same release - structured concurrency needs a way to represent several concurrent failures, and exception groups are it.

## The two-track note

The asyncio machinery - the event loop, how tasks are scheduled and cancelled, how `create_task` and `await` interact, how cancellation propagates - is Deep Volume H's to develop, and the `ExceptionGroup`/`except*` model is Chapter 21's.
`TaskGroup` composes those two pieces into structured concurrency.
What the timeline records is the release act: in 3.11, `asyncio.TaskGroup` gave concurrent tasks a scope with guaranteed completion and sibling cancellation, and exception groups gave it a way to report concurrent failures.
The modern consequence, verified above, is that `TaskGroup` is the recommended way to run concurrent asyncio tasks - superseding bare `gather` for the common case - because it cannot leak orphaned tasks and it surfaces every failure.

## Where this lands, and the close of The Specializing Interpreter

`asyncio.TaskGroup` brought structured concurrency - a discipline proven in other languages' "nurseries" - into Python's standard library.
Reach for it whenever you run multiple coroutines concurrently and want a guarantee that none outlives the block and that failures are not swallowed: spawn with `create_task` inside the `async with`, collect results after, and catch grouped failures with `except*`.
Prefer it to `gather` for concurrent work that shares a lifetime; `gather` remains for the narrow cases where you truly want independent, fire-and-collect semantics with explicit exception handling.
Deep Volume H explains the asyncio model; Chapter 21 explains exception groups; this chapter is the record of the release that gave concurrent tasks a scope with no orphans.

This closes Volume 15, The Specializing Interpreter.
The volume's headline was the Faster CPython project's specializing adaptive interpreter (Chapter 17) - the engine that made 3.11 dramatically faster - with exception groups and `except*` split out into their own chapter (Chapter 21).
Around those, 3.11 delivered a cluster of quality improvements that fit Part VI's thesis of trading interpreter complexity for value: fine-grained error locations, `add_note`, `tomllib`, and the structured concurrency of `TaskGroup` here.
Part VI continues with Volume 16, the scopes-and-observation changes of 3.12.
