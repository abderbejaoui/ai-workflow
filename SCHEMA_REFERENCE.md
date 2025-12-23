# Casino Database Schema Reference

## ⚠️ IMPORTANT: Correct Table and Column Names

### Tables (with actual database names)
- ✅ `marketing_casino.customer` (SINGULAR, not "customers")
- ✅ `marketing_casino.customer_behaviors`
- ✅ `finance_casino.transactions`
- ✅ `operations_casino.game_sessions`
- ✅ `operations_casino.gaming_equipment`
- ✅ `operations_casino.shifts`
- ✅ `hr_casino.employees`

### Key Column Locations

#### Risk-Related Columns
- ✅ `risk_score` → in `marketing_casino.customer` table (c.risk_score)
- ✅ `problem_gambling_score` → in `marketing_casino.customer_behaviors` table (cb.problem_gambling_score)
- ✅ `risk_level` → in `marketing_casino.customer_behaviors` table (cb.risk_level)

#### Common Join Pattern
```sql
FROM marketing_casino.customer c
JOIN finance_casino.transactions t ON c.customer_id = t.customer_id
JOIN operations_casino.game_sessions gs ON c.customer_id = gs.customer_id
JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
```

### Data Type Notes
- `transaction_amount` is TEXT → use `CAST(transaction_amount AS DECIMAL)`
- `total_deposits`, `total_withdrawals`, `net_balance` are TEXT → need casting
- `is_active` in employees is BIGINT (0/1), not BOOLEAN
- Boolean-like fields (`ever_bet_money`, `offline_gambling_participation`) are BIGINT (0/1)

## Example Queries

### High-Risk Customers with Losses
```sql
SELECT 
    c.customer_id, 
    c.risk_score,
    cb.problem_gambling_score,
    cb.risk_level,
    SUM(CAST(t.transaction_amount AS DECIMAL)) as total_transaction_amount
FROM marketing_casino.customer c
JOIN finance_casino.transactions t ON c.customer_id = t.customer_id
JOIN operations_casino.game_sessions gs ON c.customer_id = gs.customer_id
JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
WHERE gs.net_result < 0
GROUP BY c.customer_id, c.risk_score, cb.problem_gambling_score, cb.risk_level
ORDER BY total_transaction_amount DESC
LIMIT 5;
```

### Employee Revenue Performance
```sql
SELECT 
    e.employee_id, 
    e.first_name, 
    e.last_name, 
    AVG(s.total_revenue) AS avg_revenue_per_shift
FROM hr_casino.employees e
JOIN operations_casino.shifts s ON e.employee_id = s.employee_id
WHERE s.shift_start >= (CURRENT_DATE - INTERVAL '1 month')
GROUP BY e.employee_id, e.first_name, e.last_name
ORDER BY avg_revenue_per_shift DESC
LIMIT 10;
```
