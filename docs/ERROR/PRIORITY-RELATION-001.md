# PRIORITY-RELATION-001

Malformed relation.

## Meaning

The relation kind is unknown, it names a priority that does not exist, it relates a
priority to itself, or the declared strength lies outside [-1, 1].

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Name two distinct declared priorities, a kind from `complementary|antagonistic|neutral`, and a strength within [-1, 1].
