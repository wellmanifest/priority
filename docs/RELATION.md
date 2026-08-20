# RELATION

## Purpose

Declare how two priorities interact, overriding the measured complementarity score.

## Syntax

```
RELATION <a> <b> complementary|antagonistic|neutral [<strength>]
  BECAUSE "<why>"
```

## Inputs

Two distinct declared priority ids, a kind, and an optional strength in [-1, 1]. Omitting the strength uses +1, -1, or 0 for the three kinds.

## Outputs

A matrix entry marked `source: declared`. A human who has looked at two priorities outranks a similarity score, and the two are never conflated in the output.

## Errors

`PRIORITY-RELATION-001`.

## Examples

```
RELATION a b antagonistic -0.4
  BECAUSE "doing a moves b's signal the wrong way"
```

Antagonistic pairs are reported rather than optimized away: a standing negative score means two intents disagree, which is a question for a human.
