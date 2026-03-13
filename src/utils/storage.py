"""
UrbanHub - Storage Utility
Smart City Data Platform
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger


class Storage:
    """Storage manager for Parquet files."""
    
    def __init__(self, base_dir: Union[str, Path]):
        """
        Initialize storage manager.
        
        Args:
            base_dir: Base directory for data storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_partition_cols(self, partition_by: Optional[str] = None) -> Dict[str, Any]:
        """Get partition columns configuration."""
        if partition_by:
            if partition_by == "date":
                return {"date": datetime.now().strftime("%Y-%m-%d")}
            elif partition_by == "year":
                return {"year": datetime.now().year}
            elif partition_by == "year_month":
                now = datetime.now()
                return {"year": now.year, "month": f"{now.month:02d}"}
        return {}
    
    def write_parquet(
        self,
        df: pd.DataFrame,
        path: Union[str, Path],
        partition_by: Optional[str] = None,
        compression: str = "snappy",
        mode: str = "append"
    ) -> None:
        """
        Write DataFrame to Parquet file.
        
        Args:
            df: DataFrame to write
            path: Output path
            partition_by: Partition strategy (date, year, year_month)
            compression: Compression algorithm
            mode: Write mode (overwrite, append)
        """
        output_path = Path(path)
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get table from DataFrame
        table = pa.Table.from_pandas(df)
        
        # Write partitioned if requested
        if partition_by:
            partition_cols = self._get_partition_cols(partition_by)
            if partition_cols:
                pq.write_to_dataset(
                    table,
                    root_path=str(output_path.parent),
                    partition_cols=list(partition_cols.keys()),
                    compression=compression,
                    existing_data_behavior="overwrite_or_ignore"
                )
                logger.info(f"Wrote partitioned data to {output_path}")
                return
        
        # Regular write
        pq.write_table(
            table,
            str(output_path),
            compression=compression
        )
        logger.info(f"Wrote {len(df)} rows to {output_path}")
    
    def read_parquet(
        self,
        path: Union[str, Path],
        columns: Optional[List[str]] = None,
        filters: Optional[List[tuple]] = None
    ) -> pd.DataFrame:
        """
        Read Parquet file into DataFrame.
        
        Args:
            path: Path to Parquet file or directory
            columns: Columns to read (None for all)
            filters: PyArrow filters
            
        Returns:
            DataFrame
        """
        output_path = Path(path)
        
        if not output_path.exists():
            logger.warning(f"Path does not exist: {output_path}")
            return pd.DataFrame()
        
        # Read partitioned dataset or single file
        if output_path.is_dir():
            table = pq.read_table(
                str(output_path),
                columns=columns,
                filters=filters
            )
        else:
            table = pq.read_table(
                str(output_path),
                columns=columns
            )
        
        return table.to_pandas()
    
    def append_parquet(
        self,
        df: pd.DataFrame,
        path: Union[str, Path]
    ) -> None:
        """
        Append DataFrame to existing Parquet file.
        
        Args:
            df: DataFrame to append
            path: Output path
        """
        output_path = Path(path)
        
        # Read existing data if file exists
        if output_path.exists():
            existing_df = self.read_parquet(output_path)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df
        
        # Write combined data
        self.write_parquet(combined_df, output_path, compression="snappy")
    
    def get_latest_partition(
        self,
        path: Union[str, Path],
        partition_col: str = "year"
    ) -> Optional[str]:
        """
        Get the latest partition directory.
        
        Args:
            path: Path to partitioned dataset
            partition_col: Partition column name
            
        Returns:
            Latest partition value or None
        """
        output_path = Path(path)
        
        if not output_path.exists():
            return None
        
        # List partitions
        partitions = [d.name for d in output_path.iterdir() if d.is_dir()]
        
        if not partitions:
            return None
        
        # Sort and get latest
        partitions.sort(reverse=True)
        return partitions[0]
    
    def list_files(
        self,
        path: Union[str, Path],
        pattern: str = "*.parquet"
    ) -> List[Path]:
        """
        List files matching pattern.
        
        Args:
            path: Directory path
            pattern: File pattern
            
        Returns:
            List of file paths
        """
        output_path = Path(path)
        
        if not output_path.exists():
            return []
        
        return list(output_path.rglob(pattern))
    
    def get_file_info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about a Parquet file.
        
        Args:
            path: Path to Parquet file
            
        Returns:
            Dictionary with file information
        """
        output_path = Path(path)
        
        if not output_path.exists():
            return {"exists": False}
        
        # Read metadata
        pf = pq.ParquetFile(output_path)
        
        return {
            "exists": True,
            "path": str(output_path),
            "size_mb": output_path.stat().st_size / (1024 * 1024),
            "num_rows": pf.metadata.num_rows,
            "num_columns": pf.metadata.num_columns,
            "num_row_groups": pf.metadata.num_row_groups,
            "schema": pf.schema_arrow.names,
            "created": datetime.fromtimestamp(output_path.stat().st_ctime).isoformat()
        }


def get_storage(layer: str = "silver", category: str = "weather") -> Storage:
    """
    Get a storage instance for a specific layer and category.
    
    Args:
        layer: Data layer (raw, bronze, silver, gold)
        category: Data category
        
    Returns:
        Storage instance
    """
    from .config import get_config
    config = get_config()
    base_dir = config.get_data_dir(layer, category)
    return Storage(base_dir)
