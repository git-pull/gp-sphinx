"""Demo module for sphinx-autodoc-layout live showcase.

Provides classes with varying parameter counts to demonstrate
region wrapping and parameter folding.
"""

from __future__ import annotations


def compact_function(name: str, value: int = 0) -> str:
    """Format a name-value pair.

    This should render without any fold -- just a narrative region
    followed by a fields region.

    Parameters
    ----------
    name : str
        The item name.
    value : int
        The item value.

    Returns
    -------
    str
        Formatted result.
    """
    return f"{name}={value}"


class LayoutDemo:
    """A class demonstrating all layout regions.

    The class docstring forms the **narrative** region.  The parameter
    field list below forms the **fields** region (folded if large
    enough).  Nested methods form the **members** region.

    Parameters
    ----------
    host : str
        Server hostname.
    port : int
        Server port number.
    username : str
        Authentication username.
    password : str
        Authentication password.
    database : str
        Database name.
    timeout : float
        Connection timeout in seconds.
    retries : int
        Number of connection retries.
    ssl : bool
        Enable SSL/TLS.
    pool_size : int
        Connection pool size.
    pool_timeout : float
        Pool checkout timeout.
    echo : bool
        Log all SQL statements.
    encoding : str
        Character encoding.
    isolation_level : str
        Transaction isolation level.
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        *,
        username: str = "admin",
        password: str = "",
        database: str = "default",
        timeout: float = 30.0,
        retries: int = 3,
        ssl: bool = True,
        pool_size: int = 5,
        pool_timeout: float = 10.0,
        echo: bool = False,
        encoding: str = "utf-8",
        isolation_level: str = "READ COMMITTED",
    ) -> None:
        self.host = host
        self.port = port

    def connect(self) -> bool:
        """Open a connection to the server.

        Returns
        -------
        bool
            True if connection succeeded.
        """
        return True

    def execute(
        self,
        query: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, str]]:
        """Execute a query and return results.

        Parameters
        ----------
        query : str
            SQL query string.
        params : dict[str, str] | None
            Query parameters.

        Returns
        -------
        list[dict[str, str]]
            Query result rows.
        """
        return []

    def close(self) -> None:
        """Close the connection."""
