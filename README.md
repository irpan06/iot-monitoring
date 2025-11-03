# Hospital IoT Monitoring System

## Overview
This project demonstrates an end-to-end data monitoring and analytics pipeline designed for hospital IoT devices. It integrates real-time data ingestion, database management, automated incident handling, and an interactive visualization dashboard. The system simulates IoT devices transmitting their operational status to an API service, which stores and processes the information in a PostgreSQL database. A Streamlit dashboard provides real-time monitoring, alerting, and ticket management for maintenance and IT support teams.

---

## Objective
The primary objective of this project is to build a lightweight yet complete data-driven monitoring platform that reflects the essential components of an enterprise data system:
- Real-time data ingestion and validation from multiple IoT sources.
- Persistent data storage and historical tracking for analysis.
- Automated incident detection and ticket management.
- Data visualization for operational decision-making.

This project aims to emulate a scalable data architecture applicable to smart hospital environments and IoT-based asset management systems.

---

## Workflow and Architecture
The system operates in a continuous loop across three layers:

### 1. **Simulation Layer (Data Generation)**  
- `simulator.py` generates randomized status data (`online`, `error`, `offline`) for multiple virtual devices.  
- Each simulated device periodically sends its status and diagnostic message to the API endpoint.

### 2. **API & Database Layer (Data Processing)**  
- `api.py` receives check-in data through Flask endpoints.  
- Operations performed:
   - Update the `devices` table with the latest status and timestamp.  
   - Insert historical records into the `device_history` table.  
   - Automatically open or close tickets in the `tickets` table based on device conditions.  
   - Data is persisted in **PostgreSQL**, ensuring integrity and efficient querying.

### 3. **Visualization Layer (Data Presentation)**  
- `live_monitor.py` connects to the database and renders a real-time dashboard using **Streamlit**.  
- The dashboard includes:
   - **Monitoring Overview:** Device distribution and health metrics.  
  - **Active Tickets:** Ongoing incidents with technician assignments and notes.  
   - **Ticket History:** Historical overview of resolved and active issues.  
  - **Device History:** Device-specific performance timeline and CSV export options.  

### Data Flow Summary

![Data Workflow](assets/data%20workflow.png)

## Technology Stack

-  **Programming Language:** Python
-  **Data Collection:** Requests
-  **Data Processing:** Pandas
-  **Storage:** Local filesystem (for logs and cached data)
-  **Database:**  PostgreSQL
-  **Visualization:** Streamlit, Plotly (interactive dashboard)
