"""Notarizing final channel snapshots and decisions on a public chain (REQ-INFRA-007).

# @trace: REQ-INFRA-007

A record that became final is hashed together with the three things PRD §0.13 says a
result is reproducible from -- the config, the input dataset and the code commit -- and
the hash is committed through the `SignalNotary` contract ([[REQ-INFRA-006]]). The worker
registers records and holds no key; a separate service batches, signs and sends.
"""
