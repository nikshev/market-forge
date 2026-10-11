"""HyperEVM's public JSON-RPC node (REQ-WP-099).

# @trace: REQ-WP-099

Here and not in `channelflow.chain`: that package defines the provider protocol and may not open
a socket (ADR-012; `test_the_chain_package_cannot_consult_a_clock_or_open_a_socket`), so the thing
that talks to a node lives with the other connectors.
"""
