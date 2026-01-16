"""Database connection and base model"""
import os
import logging
from mysql.connector import Error, pooling
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling"""
    
    _pool = None
    
    @classmethod
    def init_pool(cls):
        """Initialize connection pool"""
        if cls._pool is None:
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    pool_name="mypool",
                    pool_size=5,
                    pool_reset_session=True,
                    host=os.getenv('DB_HOST', 'db'),
                    user=os.getenv('DB_USER', 'root'),
                    password=os.getenv('DB_PASSWORD', ''),
                    database=os.getenv('DB_NAME', 'agents'),
                    autocommit=False  # Manual transaction control for safety
                )
                logger.info("Database connection pool initialized")
            except Error as e:
                logger.error(f"Error creating connection pool: {e}")
                raise
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Context manager for database connections"""
        if cls._pool is None:
            raise RuntimeError("Database connection pool is not initialized.")
        
        connection = None
        try:
            connection = cls._pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    @classmethod
    def execute_query(cls, query, params=None, fetch_one=False, fetch_all=False, commit=True):
        """Execute a query with automatic connection management
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row (SELECT)
            fetch_all: Return all rows (SELECT)
            commit: Auto-commit transaction after execution (default: True for convenience)
                    Set to False for multi-statement transactions
        
        Design Rationale:
            The connection pool is configured with autocommit=False to enforce explicit 
            transaction control and prevent accidental auto-commits. However, this method
            defaults to commit=True for developer convenience in the common case of 
            single-operation queries (e.g., simple INSERT, UPDATE, DELETE).
            
            This design provides:
            - Safety: Pool-level autocommit=False prevents silent data corruption
            - Convenience: Method-level commit=True avoids boilerplate for simple queries
            - Flexibility: Set commit=False to manually control multi-statement transactions
            
            For complex transactions spanning multiple queries, call execute_query with
            commit=False for each operation, then manually commit via get_connection().
        """
        with cls.get_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            try:
                # Force params to be a tuple to handle single-value parameters correctly
                if params is None:
                    params_tuple = ()
                elif isinstance(params, tuple):
                    params_tuple = params
                else:
                    # Convert non-tuple params (like single values) to tuple
                    params_tuple = (params,) if not hasattr(params, '__iter__') or isinstance(params, str) else tuple(params)
                
                cursor.execute(query, params_tuple)
                
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    # For INSERT/UPDATE/DELETE, consume any results
                    if cursor.description:
                        # If there are results, fetch them to avoid "unread result" error
                        result = cursor.fetchall()
                    else:
                        result = cursor.lastrowid
                    
                    if commit:
                        connection.commit()
                
                return result
            except Error as e:
                connection.rollback()
                logger.error(f"Query execution error: {e}")
                raise
            finally:
                cursor.close()
    
    @classmethod
    def execute_many(cls, query, params_list):
        """Execute multiple queries with same structure"""
        with cls.get_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.executemany(query, params_list)
                connection.commit()
                return cursor.rowcount
            except Error as e:
                connection.rollback()
                logger.error(f"Batch execution error: {e}")
                raise
            finally:
                cursor.close()