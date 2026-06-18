"""Domain layer — pure business logic (Python standard library only).

No third-party imports are permitted anywhere under this package, so the domain
is importable and unit-testable with zero installed dependencies. The dependency
rule points inward: application -> domain, infrastructure -> application/domain.
"""
