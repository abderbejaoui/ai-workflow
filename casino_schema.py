"""
Casino Database Schema for the AI Workflow system.

This schema represents a comprehensive casino operations database
with tables for customers, transactions, gaming, and operations.
"""

CASINO_SCHEMA = {
    "customers": {
        "description": "Central customer profile repository containing unified customer data from survey and transaction sources.",
        "department": "CUSTOMER RELATIONS & MARKETING",
        "schema_name": "marketing_casino",
        "full_table_name": "marketing_casino.customers",
        "columns": {
            "customer_id": "VARCHAR(50) - Unique identifier for each customer",
            "gender": "VARCHAR(10) - Customer gender (Male/Female)",
            "age": "INTEGER - Customer age in years",
            "region": "VARCHAR(50) - Geographic region (North, Center, Lisbon, Alentejo, Algarve, Azores, Madeira)",
            "marital_status": "VARCHAR(30) - Marital status (Single, Married, Divorced, Widowed)",
            "employment_status": "VARCHAR(30) - Employment status (Employee, Self-employed, Unemployed, Student, Other)",
            "education_level": "VARCHAR(30) - Education level (Primary, Secondary, Bachelor, Master, PhD)",
            "risk_score": "INTEGER - Customer risk score 0-100"
        },
        "use_cases": "Customer segmentation, demographic analysis, customer lifetime value calculation, geographic market analysis, risk-based customer management",
        "record_count": "7,678"
    },
    
    "customer_behaviors": {
        "description": "Detailed behavioral profiles and gambling patterns from Portuguese survey data.",
        "department": "CUSTOMER RELATIONS & MARKETING",
        "schema_name": "marketing_casino",
        "full_table_name": "marketing_casino.customer_behaviors",
        "columns": {
            "behavior_id": "INTEGER - Unique behavior record identifier",
            "customer_id": "VARCHAR(50) - Links to customers table",
            "ever_bet_money": "BOOLEAN - Whether customer has ever bet money",
            "offline_gambling_participation": "BOOLEAN - Offline gambling participation",
            "online_gambling_participation": "BOOLEAN - Online gambling participation",
            "problem_gambling_score": "INTEGER - Problem gambling score",
            "risk_level": "VARCHAR(20) - Risk level (low/medium/high)"
        },
        "use_cases": "Problem gambling identification, behavioral segmentation, risk assessment, responsible gambling initiatives",
        "record_count": "1,993"
    },
    
    "transactions": {
        "description": "Complete payment transaction history for all customer financial activities.",
        "department": "FINANCE",
        "schema_name": "finance_casino",
        "full_table_name": "finance_casino.transactions",
        "columns": {
            "transaction_id": "INTEGER - Unique transaction identifier",
            "customer_id": "VARCHAR(50) - Links to customers table",
            "req_time_utc": "TIMESTAMP - Transaction timestamp in UTC",
            "transaction_type": "VARCHAR(30) - Type of transaction",
            "transaction_amount": "DECIMAL(10,2) - Transaction amount in USD",
            "status": "VARCHAR(20) - Transaction status (APPROVED/DECLINED)",
            "direction": "VARCHAR(10) - Transaction direction (IN/OUT)"
        },
        "use_cases": "Revenue tracking, fraud detection, payment method analysis, transaction approval rate monitoring, compliance reporting",
        "record_count": "586,781"
    },
    
    "game_sessions": {
        "description": "Gaming session summaries with financial performance metrics.",
        "department": "OPERATIONS",
        "schema_name": "operations_casino",
        "full_table_name": "operations_casino.game_sessions",
        "columns": {
            "session_id": "INTEGER - Unique session identifier",
            "game_id": "INTEGER - Game type identifier",
            "customer_id": "VARCHAR(50) - Links to customers table",
            "session_start_time": "TIMESTAMP - Session start timestamp",
            "total_bets": "DECIMAL(10,2) - Total bets placed during session",
            "total_wins": "DECIMAL(10,2) - Total wins earned during session",
            "net_result": "DECIMAL(10,2) - Net result (wins - bets)",
            "session_duration_minutes": "INTEGER - Session duration in minutes"
        },
        "use_cases": "Game performance analysis, session duration metrics, customer gaming behavior analysis, revenue per session calculations",
        "record_count": "3,000"
    },
    
    "gaming_equipment": {
        "description": "Casino equipment inventory and status tracking.",
        "department": "OPERATIONS",
        "schema_name": "operations_casino",
        "full_table_name": "operations_casino.gaming_equipment",
        "columns": {
            "equipment_id": "INTEGER - Unique equipment identifier",
            "equipment_name": "VARCHAR(100) - Equipment name",
            "equipment_type": "VARCHAR(30) - Equipment type (table/machine/terminal)",
            "status": "VARCHAR(20) - Equipment status (active/maintenance/inactive)",
            "hourly_revenue": "DECIMAL(8,2) - Average hourly revenue"
        },
        "use_cases": "Equipment utilization tracking, maintenance scheduling, revenue per equipment analysis, capacity planning",
        "record_count": "20"
    },
    
    "shifts": {
        "description": "Employee shift tracking and performance metrics.",
        "department": "OPERATIONS",
        "schema_name": "operations_casino",
        "full_table_name": "operations_casino.shifts",
        "columns": {
            "shift_id": "INTEGER - Unique shift identifier",
            "employee_id": "INTEGER - Links to employees table",
            "equipment_id": "INTEGER - Links to gaming_equipment table",
            "shift_start": "TIMESTAMP - Shift start timestamp",
            "total_revenue": "DECIMAL(10,2) - Total revenue during shift",
            "total_transactions": "INTEGER - Total transactions during shift"
        },
        "use_cases": "Employee productivity analysis, shift scheduling, performance-based compensation, workforce planning",
        "record_count": "100"
    },
    
    "employees": {
        "description": "Casino staff directory with department and compensation information.",
        "department": "HUMAN RESOURCES",
        "schema_name": "hr_casino",
        "full_table_name": "hr_casino.employees",
        "columns": {
            "employee_id": "INTEGER - Unique employee identifier",
            "first_name": "VARCHAR(50) - Employee first name",
            "last_name": "VARCHAR(50) - Employee last name",
            "department": "VARCHAR(30) - Department (finance/marketing/operations/security)",
            "position": "VARCHAR(50) - Job position",
            "hire_date": "DATE - Employee hire date",
            "salary": "DECIMAL(8,2) - Annual salary",
            "is_active": "BOOLEAN - Whether employee is active"
        },
        "use_cases": "Employee directory management, department staffing analysis, compensation planning, workforce development",
        "record_count": "50"
    }
}

def get_casino_schema_description() -> str:
    """
    Get a formatted description of the casino database schema
    for inclusion in prompts.
    """
    lines = ["CASINO DATABASE SCHEMA:"]
    lines.append("="*70)
    
    for table_name, table_info in CASINO_SCHEMA.items():
        full_name = table_info.get('full_table_name', table_name)
        lines.append(f"\n{full_name.upper()} ({table_info['record_count']} records)")
        lines.append(f"Department: {table_info['department']}")
        lines.append(f"Description: {table_info['description']}")
        lines.append("\nColumns:")
        for col_name, col_desc in table_info['columns'].items():
            lines.append(f"  - {col_name}: {col_desc}")
        lines.append(f"\nUse Cases: {table_info['use_cases']}")
        lines.append("-"*70)
    
    return "\n".join(lines)


def get_casino_tables_for_schema_loader():
    """
    Convert casino schema to format compatible with schema loader.
    
    Uses the proper schema prefixes for each table group:
    - hr_casino for employees
    - marketing_casino for customers, customer_behaviors  
    - operations_casino for game_sessions, gaming_equipment, shifts
    - finance_casino for transactions
    """
    tables = []
    
    for table_name, table_info in CASINO_SCHEMA.items():
        # Extract column names and types
        columns = list(table_info['columns'].keys())
        column_types = {}
        
        for col_name, col_desc in table_info['columns'].items():
            # Extract type from description (before the dash)
            col_type = col_desc.split(' - ')[0] if ' - ' in col_desc else 'VARCHAR'
            column_types[col_name] = col_type
        
        # Get schema name and full table name
        schema_name = table_info.get('schema_name', 'public')
        full_table_name = table_info.get('full_table_name', table_name)
        
        tables.append({
            "catalog": schema_name,  # Use the schema as catalog
            "schema": schema_name,
            "table": table_name,
            "full_name": full_table_name,  # This is what will be used in queries
            "columns": columns,
            "column_types": column_types,
            "description": table_info['description']
        })
    
    return tables

