# INVALID: a signal with no producer. A number nobody can point at cannot justify
# a rank, so PRIORITY-SIGNAL-002 rejects it.
DOCUMENT PRIORITY
SCHEMA wellmanifest.priority/v1
ID broken.example
VERSION 0.1.0
EFFECT propose-only

SIGNAL vibes metric ""

PRIORITY guesswork
  TIER standard
  INTENT "Do the thing that feels most urgent."
  BECAUSE "someone mentioned it"
  BASE 10
  SATISFIED_WHEN vibes > 5
