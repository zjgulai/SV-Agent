class ProductDomainError(Exception):
    """Base error for product domain rules."""


class LockedFactError(ProductDomainError):
    """A locked fact cannot be changed in place."""
