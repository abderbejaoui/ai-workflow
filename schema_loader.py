"""
Schema Cache Loader.

Loads and caches database schema metadata at startup.
This avoids runtime schema discovery and improves performance.
"""
from typing import Dict, Any, List
from state import SchemaTable, SchemaCache
from casino_schema import get_casino_tables_for_schema_loader
import time
import json


class SchemaLoader:
    """
    Loads database schema metadata and maintains a cache.
    
    In production, this would:
    1. Query information_schema at startup
    2. Cache results in Redis/memory
    3. Refresh periodically
    
    For this implementation, we provide methods to load from various sources.
    """
    
    def __init__(self):
        self.cache: SchemaCache = None
    
    def load_from_databricks(self, connection_config: dict = None) -> SchemaCache:
        """
        Load schema directly from Databricks (one-time at startup).
        
        This is called once when the application starts, not on every request.
        
        Args:
            connection_config: Databricks connection parameters
        
        Returns:
            SchemaCache object
        """
        try:
            from databricks import sql
            from config import config
            
            conn = sql.connect(
                server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
                http_path=config.DATABRICKS_HTTP_PATH,
                access_token=config.DATABRICKS_ACCESS_TOKEN,
            )
            
            cursor = conn.cursor()
            
            # Query to get all tables and their columns
            # This is a simplified version - production would be more comprehensive
            query = """
            SELECT 
                table_catalog,
                table_schema,
                table_name,
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'sys')
            ORDER BY table_catalog, table_schema, table_name, ordinal_position
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Organize by table
            tables_dict = {}
            for row in rows:
                catalog, schema, table, column, dtype = row
                full_name = f"{catalog}.{schema}.{table}"
                
                if full_name not in tables_dict:
                    tables_dict[full_name] = {
                        "catalog": catalog,
                        "schema": schema,
                        "table": table,
                        "columns": [],
                        "column_types": {}
                    }
                
                tables_dict[full_name]["columns"].append(column)
                tables_dict[full_name]["column_types"][column] = dtype
            
            # Convert to SchemaTable objects
            tables = []
            for full_name, table_data in tables_dict.items():
                tables.append(SchemaTable(
                    catalog=table_data["catalog"],
                    schema=table_data["schema"],
                    table=table_data["table"],
                    columns=table_data["columns"],
                    column_types=table_data["column_types"],
                ))
            
            cursor.close()
            conn.close()
            
            self.cache = SchemaCache(
                tables=tables,
                last_updated=time.time()
            )
            
            return self.cache
            
        except Exception as e:
            print(f"Warning: Failed to load schema from Databricks: {e}")
            return self._create_empty_cache()
    
    def load_from_json(self, filepath: str) -> SchemaCache:
        """
        Load schema from a JSON file.
        
        Useful for testing or when schema is pre-exported.
        
        Expected format:
        {
            "tables": [
                {
                    "catalog": "main",
                    "schema": "default",
                    "table": "users",
                    "columns": ["id", "name", "email"],
                    "column_types": {"id": "bigint", "name": "string", ...}
                }
            ]
        }
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            tables = []
            for table_data in data.get("tables", []):
                tables.append(SchemaTable(
                    catalog=table_data.get("catalog", "main"),
                    schema=table_data.get("schema", "default"),
                    table=table_data["table"],
                    columns=table_data["columns"],
                    column_types=table_data["column_types"],
                    description=table_data.get("description"),
                ))
            
            self.cache = SchemaCache(
                tables=tables,
                last_updated=time.time()
            )
            
            return self.cache
            
        except Exception as e:
            print(f"Warning: Failed to load schema from JSON: {e}")
            return self._create_empty_cache()
    
    def load_casino_schema(self) -> SchemaCache:
        """
        Load the casino database schema.
        
        This loads the real casino schema with all 7 tables:
        - customers
        - customer_behaviors  
        - transactions
        - game_sessions
        - gaming_equipment
        - shifts
        - employees
        """
        try:
            tables_data = get_casino_tables_for_schema_loader()
            
            tables = []
            for table_data in tables_data:
                tables.append(SchemaTable(
                    catalog=table_data["catalog"],
                    schema=table_data["schema"],
                    table=table_data["table"],
                    columns=table_data["columns"],
                    column_types=table_data["column_types"],
                    description=table_data.get("description"),
                ))
            
            self.cache = SchemaCache(
                tables=tables,
                last_updated=time.time()
            )
            
            return self.cache
            
        except Exception as e:
            print(f"Warning: Failed to load casino schema: {e}")
            return self._create_empty_cache()
    
    def load_mock_schema(self) -> SchemaCache:
        """
        Load a mock schema for testing/demo purposes.
        """
        tables = [
            SchemaTable(
                catalog="main",
                schema="analytics",
                table="customers",
                columns=["customer_id", "name", "email", "signup_date", "country"],
                column_types={
                    "customer_id": "bigint",
                    "name": "string",
                    "email": "string",
                    "signup_date": "date",
                    "country": "string",
                },
                description="Customer master data"
            ),
            SchemaTable(
                catalog="main",
                schema="analytics",
                table="orders",
                columns=["order_id", "customer_id", "order_date", "total_amount", "status"],
                column_types={
                    "order_id": "bigint",
                    "customer_id": "bigint",
                    "order_date": "timestamp",
                    "total_amount": "decimal(10,2)",
                    "status": "string",
                },
                description="Order transactions"
            ),
            SchemaTable(
                catalog="main",
                schema="analytics",
                table="products",
                columns=["product_id", "name", "category", "price", "stock"],
                column_types={
                    "product_id": "bigint",
                    "name": "string",
                    "category": "string",
                    "price": "decimal(10,2)",
                    "stock": "integer",
                },
                description="Product catalog"
            ),
        ]
        
        self.cache = SchemaCache(
            tables=tables,
            last_updated=time.time()
        )
        
        return self.cache
    
    def _create_empty_cache(self) -> SchemaCache:
        """Create an empty schema cache."""
        return SchemaCache(tables=[], last_updated=time.time())
    
    def get_cache(self) -> SchemaCache:
        """Get the current cache."""
        return self.cache
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache to dictionary for state."""
        if not self.cache:
            return {"tables": []}
        
        return {
            "tables": [
                {
                    "catalog": t.catalog,
                    "schema": t.schema,
                    "table": t.table,
                    "full_name": t.full_name,
                    "columns": t.columns,
                    "column_types": t.column_types,
                    "description": t.description,
                }
                for t in self.cache.tables
            ],
            "last_updated": self.cache.last_updated
        }


# Global schema loader instance
_schema_loader = None


def get_schema_loader() -> SchemaLoader:
    """Get or create global schema loader instance."""
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader()
    return _schema_loader

