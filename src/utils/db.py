"""
UrbanHub - Database Utility
Smart City Data Platform
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from datetime import datetime
import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Boolean, Text, Numeric, MetaData, Table
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from loguru import logger


Base = declarative_base()
metadata = MetaData()


class Database:
    """Database manager for PostgreSQL."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database connection.
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._connect()
        
    def _connect(self) -> None:
        """Create database connection."""
        connection_string = (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['name']}"
        )
        
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=self.config.get("pool_size", 5),
            max_overflow=10,
            echo=self.config.get("echo", False)
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Connected to database: {self.config['host']}:{self.config['port']}/{self.config['name']}")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session context manager.
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result tuples
        """
        with self.get_session() as session:
            result = session.execute(query, params or {})
            return result.fetchall()
    
    def execute_many(
        self,
        query: str,
        params: List[Dict[str, Any]]
    ) -> None:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params: List of parameter dictionaries
        """
        with self.get_session() as session:
            session.execute(query, params)
    
    def read_sql(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Read SQL query into DataFrame.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            DataFrame with query results
        """
        return pd.read_sql(query, self.engine, params=params)
    
    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        index: bool = False
    ) -> None:
        """
        Write DataFrame to database table.
        
        Args:
            df: DataFrame to write
            table_name: Target table name
            if_exists: How to behave if table exists (fail, replace, append)
            index: Whether to write DataFrame index as a column
        """
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=index
        )
        logger.info(f"Wrote {len(df)} rows to table {table_name}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.
        
        Args:
            table_name: Table name
            
        Returns:
            True if table exists
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """
        result = self.execute_query(query, {"table_name": table_name})
        return result[0][0] if result else False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table.
        
        Args:
            table_name: Table name
            
        Returns:
            List of column names
        """
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """
        result = self.execute_query(query, {"table_name": table_name})
        return [row[0] for row in result]
    
    def create_table(
        self,
        table_name: str,
        columns: Dict[str, Any],
        if_not_exists: bool = True
    ) -> None:
        """
        Create a table.
        
        Args:
            table_name: Table name
            columns: Dictionary of column definitions
            if_not_exists: Whether to use IF NOT EXISTS
        """
        columns_def = ", ".join([
            f"{name} {dtype}" for name, dtype in columns.items()
        ])
        
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause}{table_name} ({columns_def})"
        
        with self.get_session() as session:
            session.execute(query)
        
        logger.info(f"Created table {table_name}")
    
    def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        Drop a table.
        
        Args:
            table_name: Table name
            if_exists: Whether to use IF EXISTS
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        query = f"DROP TABLE {exists_clause}{table_name}"
        
        with self.get_session() as session:
            session.execute(query)
        
        logger.info(f"Dropped table {table_name}")
    
    def vacuum_analyze(self, table_name: str) -> None:
        """
        Run VACUUM ANALYZE on a table.
        
        Args:
            table_name: Table name
        """
        query = f"VACUUM ANALYZE {table_name}"
        with self.get_session() as session:
            session.execute(query)
        
        logger.info(f"Vacuum analyzed table {table_name}")
    
    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """
    Get the global database instance.
    
    Returns:
        Database instance
    """
    global _db
    if _db is None:
        from .config import get_config
        config = get_config()
        db_config = config.get("database", {})
        _db = Database(db_config)
    return _db


# Metadata tables
class WeatherStation(Base):
    """Weather stations metadata table."""
    __tablename__ = "metadata.weather_stations"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(String(50), unique=True, nullable=False)
    station_name = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    country = Column(String(10))
    first_observation = Column(DateTime)
    last_observation = Column(DateTime)
    record_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BikesNetwork(Base):
    """Bike networks metadata table."""
    __tablename__ = "metadata.bikes_networks"
    
    id = Column(Integer, primary_key=True)
    network_id = Column(String(50), unique=True, nullable=False)
    network_name = Column(String(255))
    city = Column(String(255))
    country = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PollutionSensor(Base):
    """Pollution sensors metadata table."""
    __tablename__ = "metadata.pollution_sensors"
    
    id = Column(Integer, primary_key=True)
    sensor_id = Column(String(100), unique=True, nullable=False)
    sensor_name = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    city = Column(String(255))
    pollutant = Column(String(20))
    unit = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ETLRuns(Base):
    """ETL runs tracking table."""
    __tablename__ = "etl.runs"
    
    id = Column(Integer, primary_key=True)
    pipeline = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20))  # running, completed, failed
    records_processed = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
