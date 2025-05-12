<!--
Instructions:  Fill in the placeholders below to create the System Manifest.
This document provides a high-level overview of the entire system.
*Do NOT include these comments in the created file.*
-->

# System: {SystemName}

## Purpose
{1-2 sentences describing system purpose}

## Architecture
{ASCII diagram of system Modules}

## Module Registry
- [{ModuleName1} (`{path/to/ModuleName1_module.md}`)]: {brief description}
- [{module_dir}/{module_dir2}]: {brief description}
...

## Development Workflow
1. {First step}
2. {Second step}
...

## Version: {version} | Status: {status}

---

Here's a minimalist example for a hypothetical inventory management system:

**System Manifest:**

# System: Inventory Management System

## Purpose
Tracks product inventory, orders, and shipments for e-commerce platform.

## Architecture
[frontend] <-> [api_gateway] <-> [services] <-> [database]
  |                |             |            |
  |                |             |            +-- [Data Models]
  |                |             +-- [Order Service]
  |                |             +-- [Inventory Service] 
  |                |             +-- [Shipping Service]
  |                +-- [Auth]
  +-- [Admin UI]
  +-- [Customer UI]

## Module Registry
- [frontend (`src/frontend/frontend_module.md`)]: User interfaces
- [src/frontend/api_gateway]: Request routing
- [src/frontend/api_gateway/services]: Business logic
- [src/frontend/api_gateway/services/database]: Data storage

## Development Workflow
1. Update documentation
2. Create task instructions
3. Implement features
4. Test and validate
5. Document changes

## Version: 0.2 | Status: Development