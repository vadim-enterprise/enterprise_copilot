# Example CRM Dataset

This directory contains example CSV files that simulate CRM and transaction data for 12 companies. These files are designed to be used with the websearch upload functionality in the pred_genai application.

## Files Included

1. **example_crm_data.csv** - Primary CRM data with company information and transactions
2. **example_company_metrics.csv** - Company-level metrics and performance indicators
3. **example_transaction_metrics.csv** - Detailed metrics for each transaction

## Usage

Upload these files through the websearch bar data upload feature to populate the PostgreSQL database with sample data for testing and demonstration purposes.

### File Relationships

- Files are related through common keys:
  - `company_id` links company_metrics to crm_data
  - `transaction_id` links transaction_metrics to crm_data

## Data Analysis Examples

Once uploaded, you can perform various types of analysis such as:

### SQL Query Examples

1. **Revenue by industry:**
```sql
SELECT industry, SUM(transaction_amount) as total_revenue
FROM example_crm_data
GROUP BY industry
ORDER BY total_revenue DESC;
```

2. **Transaction status breakdown:**
```sql
SELECT status, COUNT(*) as transaction_count, 
       SUM(transaction_amount) as total_amount
FROM example_crm_data
GROUP BY status
ORDER BY transaction_count DESC;
```

3. **Joining tables for deeper analysis:**
```sql
SELECT c.name, c.industry, 
       SUM(c.transaction_amount) as revenue,
       m.growth_rate, m.customer_segment
FROM example_crm_data c
JOIN example_company_metrics m ON c.company_id = m.company_id
GROUP BY c.name, c.industry, m.growth_rate, m.customer_segment
ORDER BY revenue DESC;
```

### Python Analysis Examples

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the data
crm_data = pd.read_csv('example_crm_data.csv')
company_metrics = pd.read_csv('example_company_metrics.csv')
transaction_metrics = pd.read_csv('example_transaction_metrics.csv')

# Merge datasets
merged_data = pd.merge(crm_data, company_metrics, on='company_id')
merged_data = pd.merge(merged_data, transaction_metrics, on='transaction_id')

# Analyze relationship between company growth rate and transaction amounts
plt.figure(figsize=(10, 6))
plt.scatter(merged_data['growth_rate'], merged_data['transaction_amount'])
plt.xlabel('Company Growth Rate (%)')
plt.ylabel('Transaction Amount ($)')
plt.title('Relationship Between Growth Rate and Transaction Size')
plt.tight_layout()
plt.show()

# Analyze revenue by industry
industry_revenue = crm_data.groupby('industry')['transaction_amount'].sum().sort_values(ascending=False)
plt.figure(figsize=(12, 6))
industry_revenue.plot(kind='bar')
plt.xlabel('Industry')
plt.ylabel('Total Revenue ($)')
plt.title('Revenue by Industry')
plt.tight_layout()
plt.show()
```

## Schema Details

### example_crm_data.csv
- company_id: Unique identifier for each company
- name: Name of the company
- industry: Industry sector
- location: Company headquarters
- contact_person: Primary contact name
- contact_email: Email address
- contact_phone: Phone number
- transaction_id: Unique identifier for each transaction
- transaction_date: Date of transaction
- transaction_amount: Value in USD
- product_type: Type of product or service
- status: Current status (Completed/In Progress)
- revenue_impact: Impact level on revenue
- satisfaction_score: Customer satisfaction (1-5 scale)
- follow_up_date: Scheduled follow-up
- notes: Additional transaction notes

### example_company_metrics.csv
- company_id: Unique identifier for each company (links to crm_data)
- name: Name of the company
- annual_revenue: Revenue in USD
- employee_count: Number of employees
- founded_year: Year the company was founded
- market_cap: Market capitalization (for public companies)
- growth_rate: Annual growth percentage
- churn_rate: Customer churn percentage
- acquisition_cost: Customer acquisition cost
- lifetime_value: Customer lifetime value
- repeat_purchase_rate: Percentage of repeat purchases
- nps_score: Net Promoter Score
- industry_ranking: Ranking within their industry
- public_company: Whether the company is publicly traded
- headquarters: Company headquarters location
- website: Company website domain

### example_transaction_metrics.csv
- transaction_id: Unique identifier for each transaction (links to crm_data)
- days_to_close: Number of days to close the deal
- sales_rep_id: ID of sales representative
- sales_rep_name: Name of sales representative
- discount_percentage: Discount given
- profit_margin: Profit margin percentage
- customer_segment: Market segment
- marketing_channel: Channel that generated the lead
- lead_source: Source of the lead
- region: Geographic region
- quarter: Fiscal quarter
- fiscal_year: Fiscal year
- deal_complexity: Complexity level
- upsell_opportunity: Potential for upselling
- cross_sell_related: Whether cross-selling was related
- customer_tenure_months: Customer relationship duration in months 