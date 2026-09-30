# Algorithms and data structures

| Implemented algorithm | Input → output | Important invariant |
|---|---|---|
| Parameter validation | scaffold request → validated values | Names are DNS-safe; ports and dependencies are valid |
| Template rendering | approved template + parameters → file map | Request service/owner identity appears in output metadata |
| Artifact packaging | file map → deterministic ZIP/manifest | Paths cannot escape; stable order/timestamp yields reproducible checksum |
| Atomic registration | artifact + metadata → catalog record | A catalog record is not created if artifact storage fails |
| Dependency projection | services → nodes/edges | Edges reference registered service IDs |

The local registry uses dictionaries keyed by template/service IDs and a bounded artifact map. Rendering is O(number of files), packaging is O(total artifact bytes), and graph projection is O(services + dependencies). Tests cover five generators, quality defaults, archive contents/checksums, governance roles, graph output, and invalid input.
