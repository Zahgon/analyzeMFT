"""
SQLite database writer for MFT analysis results
"""

import sqlite3
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from .mft_record import MftRecord
from .constants import FILE_RECORD_IN_USE, FILE_RECORD_IS_DIRECTORY


class SQLiteWriter:
    """SQLite database writer for MFT analysis results."""
    
    def __init__(self, database_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize SQLite writer.
        
        Args:
            database_path: Path to SQLite database file
            logger: Logger instance
        """
        self.database_path = Path(database_path)
        self.logger = logger or logging.getLogger('analyzeMFT.sqlite')
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def connect(self) -> None:
        """Connect to SQLite database and initialize schema."""
        try:
            # Create parent directories if needed
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(str(self.database_path))
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON")
            self._initialize_schema()
            
            self.logger.info(f"Connected to SQLite database: {self.database_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SQLite database: {e}")
            raise
            
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                self.conn.commit()
                self.conn.close()
                self.logger.info("SQLite database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
            
    def _initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist."""
        try:
            # Check if tables already exist
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mft_records'")
            if self.cursor.fetchone():
                self.logger.info("Database schema already exists, skipping initialization")
                return

            self.logger.info("Initializing new database schema")
            self._create_tables()
            self._populate_reference_tables()

            self.conn.commit()
            self.logger.info("Database schema initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing schema: {e}")
            if self.conn:
                self.conn.rollback()
            raise

    def _create_tables(self) -> None:
        """Create database tables and indexes."""
        # Create tables
        table_definitions = [
            """
            CREATE TABLE IF NOT EXISTS attribute_types (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS file_record_flags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mft_records (
                record_number INTEGER PRIMARY KEY,
                sequence_number INTEGER,
                flags INTEGER,
                used_size INTEGER,
                allocated_size INTEGER,
                base_record_number INTEGER,
                next_attribute_id INTEGER,
                filepath TEXT,
                filename TEXT,
                parent_record_number INTEGER,
                parent_sequence_number INTEGER,
                
                -- Standard Information timestamps
                si_creation_time TEXT,
                si_modification_time TEXT,
                si_access_time TEXT,
                si_entry_time TEXT,
                
                -- File Name timestamps
                fn_creation_time TEXT,
                fn_modification_time TEXT,
                fn_access_time TEXT,
                fn_entry_time TEXT,
                
                -- File attributes and sizes
                file_attributes INTEGER,
                allocated_file_size INTEGER,
                real_file_size INTEGER,
                
                -- Object ID information
                object_id TEXT,
                birth_volume_id TEXT,
                birth_object_id TEXT,
                birth_domain_id TEXT,
                
                -- Hash information (if computed)
                md5_hash TEXT,
                sha256_hash TEXT,
                sha512_hash TEXT,
                crc32_hash TEXT,
                
                -- Metadata
                is_active BOOLEAN,
                is_directory BOOLEAN,
                is_deleted BOOLEAN,
                has_ads BOOLEAN DEFAULT FALSE,
                
                -- Analysis timestamp
                analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mft_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_number INTEGER,
                attribute_type INTEGER,
                attribute_name TEXT,
                attribute_size INTEGER,
                resident BOOLEAN,
                data_size INTEGER,
                content_preview TEXT,
                FOREIGN KEY (record_number) REFERENCES mft_records(record_number),
                FOREIGN KEY (attribute_type) REFERENCES attribute_types(id)
            )
            """
        ]
        
        for table_sql in table_definitions:
            self.cursor.execute(table_sql)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_mft_records_filepath ON mft_records(filepath)",
            "CREATE INDEX IF NOT EXISTS idx_mft_records_filename ON mft_records(filename)",
            "CREATE INDEX IF NOT EXISTS idx_mft_records_parent ON mft_records(parent_record_number)",
            "CREATE INDEX IF NOT EXISTS idx_mft_records_flags ON mft_records(flags)",
            "CREATE INDEX IF NOT EXISTS idx_mft_records_creation_time ON mft_records(si_creation_time)",
            "CREATE INDEX IF NOT EXISTS idx_mft_records_modification_time ON mft_records(si_modification_time)",
            "CREATE INDEX IF NOT EXISTS idx_mft_attributes_record_type ON mft_attributes(record_number, attribute_type)"
        ]
        
        for index_sql in indexes:
            self.cursor.execute(index_sql)
        
        # Create views
        self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_files AS
            SELECT * FROM mft_records 
            WHERE is_active = 1 AND is_directory = 0
        """)
        
        self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_directories AS
            SELECT * FROM mft_records 
            WHERE is_active = 1 AND is_directory = 1
        """)
        
        self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS deleted_files AS
            SELECT * FROM mft_records 
            WHERE is_deleted = 1
        """)

    def _populate_reference_tables(self) -> None:
        """Populate reference tables with static data."""
        attribute_types = [
            (16, '$STANDARD_INFORMATION'),
            (32, '$ATTRIBUTE_LIST'),
            (48, '$FILE_NAME'),
            (64, '$OBJECT_ID'),
            (80, '$SECURITY_DESCRIPTOR'),
            (96, '$VOLUME_NAME'),
            (112, '$VOLUME_INFORMATION'),
            (128, '$DATA'),
            (144, '$INDEX_ROOT'),
            (160, '$INDEX_ALLOCATION'),
            (176, '$BITMAP'),
            (192, '$REPARSE_POINT'),
            (208, '$EA_INFORMATION'),
            (224, '$EA'),
            (256, '$LOGGED_UTILITY_STREAM')
        ]
        
        self.cursor.executemany(
            "INSERT OR IGNORE INTO attribute_types (id, name) VALUES (?, ?)",
            attribute_types
        )
        
        file_record_flags = [
            (1, 'FILE_RECORD_IN_USE'),
            (2, 'FILE_RECORD_IS_DIRECTORY'),
            (4, 'FILE_RECORD_IS_EXTENSION'),
            (8, 'FILE_RECORD_HAS_SPECIAL_INDEX')
        ]
        
        self.cursor.executemany(
            "INSERT OR IGNORE INTO file_record_flags (id, name) VALUES (?, ?)",
            file_record_flags
        )
        
    def write_record(self, record: MftRecord, filepath: str = "") -> None:
        """
        Write a single MFT record to the database.
        
        Args:
            record: MFT record to write
            filepath: Full file path
        """
        pass
            
    def write_records_batch(self, records: List[MftRecord], filepaths: Dict[int, str] = None) -> None:
        """
        Write a batch of MFT records to the database.
        
        Args:
            records: List of MFT records to write
            filepaths: Dictionary mapping record numbers to file paths
        """
        if filepaths is None:
            filepaths = {}
            
        try:
            self.logger.info(f"Writing batch of {len(records)} records to SQLite database")
            
            for record in records:
                try:
                    filepath = filepaths.get(getattr(record, 'recordnum', 0), "")
                    recordnum = getattr(record, 'recordnum', 0)
                    filename = getattr(record, 'filename', None)
                    flags = getattr(record, 'flags', 0)
                    
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO mft_records (
                            record_number, filepath, filename, flags, is_active, is_directory, is_deleted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        recordnum,
                        filepath,
                        filename, 
                        flags,
                        bool(flags & FILE_RECORD_IN_USE) if flags else False,
                        bool(flags & FILE_RECORD_IS_DIRECTORY) if flags else False,
                        not bool(flags & FILE_RECORD_IN_USE) if flags else True
                    ))
                    
                except Exception as e:
                    self.logger.warning(f"Error writing record {getattr(record, 'recordnum', 'unknown')}: {e}")
                    continue
                
            self.conn.commit()
            self.logger.info(f"Successfully wrote batch of {len(records)} records to database")
            
        except Exception as e:
            self.logger.error(f"Error writing record batch: {e}")
            if self.conn:
                self.conn.rollback()
            raise
            
    def _prepare_record_data(self, record: MftRecord, filepath: str) -> tuple:
        """
        Prepare record data for database insertion.
        
        Args:
            record: MFT record
            filepath: Full file path
            
        Returns:
            Tuple of record data
        """
        pass
        
    def _write_attributes(self, record: MftRecord) -> None:
        """
        Write record attributes to the database.
        
        Args:
            record: MFT record
        """
        # Implementation for writing attributes would go here
        pass
        
    def create_indexes(self) -> None:
        """Create additional indexes for performance."""
        pass
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary of statistics
        """
        pass
