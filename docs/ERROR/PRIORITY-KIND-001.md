# PRIORITY-KIND-001

Structural defect in the document.

## Meaning

The schema id, document id, version, or a field name is wrong, or a field is not recognised.

`unknownPolicy` is `reject`. An unrecognised field is far more often a typo or a private
extension than a deliberate addition, and silently ignoring it means the author believes
something is in force that is not.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Correct the field name, or remove it. If the field is a deliberate extension, propose it upstream rather than carrying it locally.
