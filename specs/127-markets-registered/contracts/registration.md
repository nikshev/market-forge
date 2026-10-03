# Contract: market registration

1. Before an ingest process begins ingesting, it registers `(venue, symbol)` unless the key is present.
2. The row's market type is the registry's; its rules are empty.
3. Present means present: a key held with trading rules is not overwritten, and registering again adds nothing.
4. Any failure — catalog, commit, an unrecognised OKX instrument — is one WARNING naming venue and symbol,
   then ingest proceeds. No retry loop.
5. The market type is written only in `venue.py`.
