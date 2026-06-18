"""Infrastructure layer: adapters, DI composition root, and inbound API.

This is the ONLY layer permitted to import third-party frameworks. All adapters
implement application-layer ports (``typing.Protocol``) and reference domain
value objects directly — never redefining them.
"""
