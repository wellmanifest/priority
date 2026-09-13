# `DOCUMENT PRIORITY` — grammar

Line-oriented, two-space indented, comments start with `#`. The text form and the
JSON AST are equivalent: parsing then rendering is lossless.

```
DOCUMENT PRIORITY
SCHEMA wellmanifest.priority/v1
ID <identifier>
VERSION <semver>
EFFECT propose-only

SIGNAL <name> <kind> <producer>          # kind: metric | event | schedule
  UNIT <string>                          # metric only
  WINDOW <duration>                      # how long an observation stays fresh
  ABSENT <hold|zero>                     # what a missing reading means (default hold)

PRIORITY <identifier>
  TIER floor | standard | opportunistic
  INTENT "<one sentence>"
  BECAUSE "<evidence, ideally a path:line>"
  BASE <number>
  TOUCHES <glob>                         # repeatable; the surface this work edits
  SATISFIED_WHEN <signal> <op> <number>  # when this priority is done
  ON <signal> <op> <number> RAISE|LOWER <factor> BECAUSE "<why>"
  ESCALATE <factor> PER <duration>       # floor only
  DECAY <factor> PER <duration>          # opportunistic only
  STARVATION <points> PER <duration> CAP <points>
  AMEND WHEN <signal> <op> <number> [FOR <duration>]
    REWRITE INTENT "<new sentence>"
    SET TIER <tier>
    SET BASE <number>
    RETIRE
    BECAUSE "<why the intent itself changes>"

RELATION <a> <b> complementary|antagonistic|neutral [<strength>]
  BECAUSE "<why>"
```

## Operators

`>` `>=` `<` `<=` `==` `!=` for metrics; `changed` and `stale` for events;
`elapsed` for schedules.

## Why `AMEND` is separate from `ON`

`ON` changes the *weight* of an intent. `AMEND` changes the *intent*.

The distinction matters because it is the difference between "this got more
urgent" and "this is no longer the thing we want". Collapsing them produces
documents where a priority quietly becomes a different priority while keeping its
identity and its history, which is exactly the drift a standing document is
supposed to prevent.

## Duration

`<n>s`, `<n>m`, `<n>h`, `<n>d`, `<n>w`.
