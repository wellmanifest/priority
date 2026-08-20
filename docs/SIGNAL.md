# SIGNAL

## Purpose

Declare a named, typed measurement together with the thing that produces it, so that any rank can be traced back to something that was measured.

## Syntax

```
SIGNAL <name> metric|event|schedule "<producer>"
  UNIT "<string>"
  WINDOW <duration>
  ABSENT hold | zero
```

## Inputs

`producer` is an opaque command (metric), a path (event), or a cadence (schedule). Keeping it opaque is what keeps this pack abstract: the tools that produce quality numbers belong to their owners, and naming them here would couple the standard to a toolchain.

`WINDOW` is how long a reading stays valid, which lets a frequent control loop skip re-running slow producers.

`ABSENT` defaults to `hold`.

## Outputs

A reading, or no reading. With `ABSENT hold` a missing reading fires nothing at all.

## Errors

`PRIORITY-SIGNAL-001`, `PRIORITY-SIGNAL-002`, `PRIORITY-SIGNAL-003`.

## Examples

```
SIGNAL coverage metric "<command printing a number>"
  UNIT "percent"
  WINDOW 6h
  ABSENT hold
```
