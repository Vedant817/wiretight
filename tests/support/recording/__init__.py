"""Labelled demo mode (``DEMO_MODE=video``).

Everything here is simulated for the pitch recording: synthetic company, people,
emails, IBANs and amounts, and a :class:`MockAirwallexClient`
that returns documented-shape responses without opening a socket. Real core
modules (parsers, duplicates, vendor match, out-of-band callback rules, ledger)
compute the decisions shown on screen, so the demo shows what the code actually
enforces - against synthetic data.
"""
