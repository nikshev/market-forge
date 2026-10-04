# Contract: GET /api/v1/volume-profile

Query: `venue`, `symbol`, `window` in `4h | 24h | 7d` (others 422), optional `at_ns` (default: the latest closed block).
200: `VolumeProfileOut` (see the data model). 404: no bins for the series, with a reason. Point-in-time: blocks closed after `at_ns` are never used.
