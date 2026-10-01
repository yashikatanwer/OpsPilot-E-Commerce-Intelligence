# OpsPilot — E-Commerce Intelligence

OpsPilot is a local Flask-based web application that helps analyze e-commerce sales and order data from Excel and CSV files.

The main idea is to upload an e-commerce dataset and get useful business information such as revenue, orders, customers, products, trends, cancellations and other available metrics without having to manually clean and analyze the file first.

## What OpsPilot Does

OpsPilot takes an uploaded spreadsheet, checks its structure, identifies the available e-commerce fields and then performs the analysis based on those fields.

The application does not assume that every dataset has the same columns. For example, one file may have `Order ID` while another may use `Invoice`, and one file may contain `Revenue` while another only has `Quantity` and `Unit Price`.

The system tries to identify these common variations and uses the data that is actually available.

If a metric cannot be calculated because the required information is missing, OpsPilot does not create a value for it.

## Features

### 1. File Upload

Supports:

- `.xlsx` Excel files
- `.xls` Excel files
- `.csv` files
- Multiple compatible e-commerce sheets in the same Excel workbook

### 2. Automatic Column Detection

OpsPilot identifies common e-commerce fields, including:

- Order ID
- Transaction ID
- Invoice
- Order Date
- Product
- Product ID / SKU
- Category
- Quantity
- Unit Price
- Revenue / Sales
- Customer ID
- Customer Name
- Order Status
- Payment Method
- Referral Source
- Sales Channel
- Location
- Discount
- Cost
- Profit

Different column names can represent the same type of information. For example, `Order ID`, `OrderID`, `Transaction ID`, or `Invoice` can be detected as order or transaction identifiers depending on the dataset.

### 3. Data Validation

Before performing the analysis, OpsPilot checks the uploaded data for:

- Missing values
- Duplicate records
- Invalid or unusable columns
- Missing required information
- Negative quantities
- Cancellation and return records

### 4. Revenue Calculation

If the dataset contains a revenue or sales column, OpsPilot uses it directly.

If revenue is not available but quantity and unit price are present, revenue can be calculated as:

```text
Revenue = Quantity × Unit Price
```

### 5. Business Metrics

Depending on the available data, OpsPilot can calculate:

- Total Revenue
- Total Orders
- Total Customers
- Average Order Value
- Total Quantity Sold
- Total Cost
- Total Profit
- Profit Margin
- Cancellation Rate
- Return / Refund Value
- Data Completeness
- Duplicate Records

Only metrics that can actually be calculated from the uploaded dataset are displayed.

### 6. Product Analysis

When product information is available, OpsPilot can show:

- Top-selling products
- Revenue by product
- Product-level sales
- Product performance

### 7. Category Analysis

If category information is available, the application can show sales and revenue across different product categories.

### 8. Customer Analysis

Customer analysis is performed when the dataset contains an actual customer identifier such as:

```text
Customer ID
Customer Name
```

Fields such as customer ratings or review scores are not treated as customer identifiers.

### 9. Sales Trends

If a usable date column is available, OpsPilot can analyze sales over time, including:

- Daily sales
- Monthly sales
- Revenue trends
- Order trends

### 10. Cancellation and Return Detection

OpsPilot checks for records that may indicate cancellations or returns using information such as:

- Negative quantities
- Cancellation statuses
- Return statuses
- Refund-related values

These records are shown separately from normal sales.

### 11. Business Insights

The Insights section provides observations based on the uploaded data.

Depending on the dataset, it can identify things such as:

- Cancellation and return patterns
- Revenue patterns
- Product-level observations
- Category-level observations
- Other supported business patterns

The insights are generated from the uploaded data rather than fixed sample results.

### 12. Reports

OpsPilot can generate a report containing the analyzed information.

The report uses the same calculations as the dashboard and analytics sections so that the displayed results remain consistent.

### 13. Login and Signup

The application includes a basic authentication system where users can:

- Create an account
- Log in
- Log out
- Access the application after authentication

Passwords are stored using hashing rather than plain text.

---

## How It Works

The basic workflow is:

```text
Upload File
     ↓
Read Dataset
     ↓
Inspect Columns
     ↓
Detect E-Commerce Fields
     ↓
Validate Data
     ↓
Normalize Data
     ↓
Calculate Metrics
     ↓
Generate Analytics
     ↓
Generate Insights
     ↓
Create Report
```

## Flexible Dataset Handling

OpsPilot is not built around one fixed spreadsheet format.

For example, one dataset may contain:

```text
OrderID
Product
Quantity
Price
TotalPrice
```

while another may contain:

```text
Invoice
Description
Quantity
UnitPrice
Sales
```

OpsPilot attempts to identify the corresponding fields and use them for analysis.

At the same time, the application is focused on e-commerce order and sales data. Unrelated datasets such as SaaS subscriptions, restaurant sales, or inventory-only workbooks are not forced into the e-commerce analysis when the required e-commerce structure is missing.

## Application Sections

### Dashboard

Provides an overview of the uploaded dataset and displays the main available business metrics.

### Upload Data

Allows users to upload an Excel or CSV file and inspect the detected structure.

### Analytics

Provides detailed charts and breakdowns based on the available data, such as product, category, revenue, order, and time-based analysis.

### Insights

Shows automatically generated observations based on patterns found in the uploaded dataset.

### Reports

Provides a downloadable report containing the verified metrics and analysis.

## Data Handling

OpsPilot does not assume that every dataset contains the same fields.

For example:

```text
No Order ID
→ Order-level metrics may not be available

No Customer ID
→ Customer analysis is not available

No Cost
→ Profit cannot be calculated

No Date
→ Time-based trends cannot be generated
```

This prevents the application from creating or displaying unsupported metrics.

## Tech Stack

### Backend

- Python
- Flask
- Pandas
- NumPy

### Data Processing

- Pandas
- OpenPyXL

### Frontend

- HTML
- CSS
- JavaScript
- Jinja2

### Reporting

- PDF report generation

## Project Structure

```text
OpsPilot/
│
├── app.py
├── requirements.txt
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── analytics.html
│   ├── insights.html
│   └── reports.html
│
├── static/
│   └── css/
│
└── users.json
```

`users.json` is created when users register in the local application.

## Running the Project

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the Flask application:

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

Create an account or log in and upload an e-commerce dataset.

## Supported Scope

OpsPilot is designed for common e-commerce order and sales datasets.

It supports:

- Common order IDs / transaction IDs / invoices
- Product names and descriptions
- Product IDs / SKUs
- Quantity and unit price
- Explicit revenue or sales fields
- Optional customer, category, date, status, payment, referral, channel, and location fields
- Optional discount, cost, and profit fields
- Multiple compatible e-commerce sheets in one workbook

The application only displays metrics supported by the uploaded data and does not create fake values when information is missing.