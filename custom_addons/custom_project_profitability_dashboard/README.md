# Custom Project Profitability Dashboard

## Overview

This module extends the official Odoo Project module by inheriting and enhancing the Project Updates feature.
It provides a comprehensive profitability dashboard for each project, integrating HR team cost calculation,
facilities costs, taxes, and other financial Key Performance Indicators(KPIs)directly into the project interface.

### Key Features

- Inherits and customizes the Project Updates functionality from the official Odoo Project module.
- Adds HR team cost calculation and reporting per project, based on timesheet data and employee cost rates.
- Integrates financial KPIs (costs, margin, taxes, facilities) into the project dashboard.
- Restricts access to sensitive financial data via custom security groups.
- Customizes project kanban and update views for improved usability and clarity.
- All enhancements are seamlessly integrated into the standard Project Updates workflow.

### Integration

All features are fully integrated with the standard Odoo Project Updates, ensuring a familiar user experience
with added value for project managers and financial controllers.

## Recent Improvements

### Version 1.2.0 - HR Cost Warning & Real-time Updates

####  Enhanced HR Cost Warning System
- **Professional Alert Display**: Redesigned warning messages with improved formatting and visual appeal
- **Better Spacing**: Added proper margins and separators around warning messages for better readability
- **Clear Employee Identification**: Warning messages now display affected employees in a bullet-point format
- **Actionable Guidance**: Added specific instructions for resolving zero timesheet cost issues

#### **Real-time Data Updates**
- **Dynamic Button Values**: Fixed issue where "Summary of HR Costs" and "Detailed HR Costs" buttons showed outdated values
- **Automatic Recomputation**: Implemented forced recalculation of profitability metrics when panel data is accessed
- **Accurate HR Cost Display**: Both summary and detailed cost buttons now reflect actual HR costs instead of generic values

#### **UI/UX Improvements**
- **Enhanced Warning Styling**: Added professional styling with background colors, borders, and proper spacing
- **Visual Separators**: Implemented separator lines before and after warning messages for better visual hierarchy
- **Improved Button Labels**: Renamed "Gross Margin" to "Detailed HR Costs" for better clarity

#### **Technical Enhancements**
- **Optimized Dependencies**: Ensured proper dependency tracking for computed fields
- **Performance Improvements**: Maintained stored computed fields while ensuring data freshness
- **Error Handling**: Improved robustness in handling edge cases and missing data

#### **Data Accuracy**
- **Consistent Calculations**: Ensured all HR cost calculations are synchronized across different views
- **Real-time Synchronization**: Fixed synchronization issues between timesheet cost changes and dashboard displays
- **Reliable Metrics**: Enhanced reliability of profitability metrics computation

---

**For installation and configuration, see the official Odoo documentation and follow standard module installation procedures.**