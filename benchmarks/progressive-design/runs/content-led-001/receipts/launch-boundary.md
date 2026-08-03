# Coordinator launch boundary

The four sealed packets are prepared and the source directories were empty at initialization. This coordinator session did not execute any condition implementation. Independent workers or isolated contexts were not available in the current environment, and sequential implementation in this context would violate the isolation contract.

A second hard gate remains: the approved image metadata and official resource URLs are frozen, but binary image bytes could not be retrieved by this environment. Before launching any worker, materialize the four declared image files once, record SHA-256 values in `receipts/hashes.json`, set each `binary_present` field to `true`, and expose identical byte-for-byte fixtures to all four workers. No implementation may begin before that gate is closed.

When independent execution is available, launch the four packets in separate workspaces or contexts with only the assigned prompt, `FROZEN_BRIEF.md`, immutable fixtures, the route contract, and the shared evidence budget.
