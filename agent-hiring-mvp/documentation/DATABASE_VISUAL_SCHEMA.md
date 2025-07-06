# AgentHub Database Visual Schema

This document provides a visual representation of the AgentHub database schema using ASCII diagrams and detailed field descriptions.

## ASCII Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    AGENTHUB DATABASE                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    USERS TABLE                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  id (PK) │ created_at │ updated_at │ username │ email │ full_name │ is_active      │
│  INTEGER │ TIMESTAMP  │ TIMESTAMP  │ VARCHAR  │VARCHAR│ VARCHAR   │ BOOLEAN        │
│          │            │            │ (50)     │(255)  │ (255)     │ DEFAULT TRUE   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ hashed_password │ is_verified │ avatar_url │ bio │ website │ preferences │ last_login │
│ VARCHAR(255)    │ BOOLEAN     │ VARCHAR    │TEXT │VARCHAR  │ JSON        │ TIMESTAMP  │
│                 │ DEFAULT F   │ (500)      │     │(500)    │             │            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   AGENTS TABLE                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  id (PK) │ created_at │ updated_at │ name │ description │ version │ author │ email  │
│  INTEGER │ TIMESTAMP  │ TIMESTAMP  │VARCHAR│ TEXT        │VARCHAR  │VARCHAR │VARCHAR │
│          │            │            │(255)  │             │ (50)    │(255)   │(255)   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ entry_point │ requirements │ config_schema │ code_zip_url │ code_hash │ docker_image │
│ VARCHAR(255) │ JSON         │ JSON          │ VARCHAR(500) │VARCHAR(64)│ VARCHAR(255) │
│              │              │               │              │           │              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ code │ file_path │ tags │ category │ pricing_model │ price_per_use │ monthly_price │
│ TEXT │ VARCHAR   │ JSON │VARCHAR   │ VARCHAR(50)   │ FLOAT         │ FLOAT         │
│      │ (500)     │      │(100)     │               │               │               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ status │ is_public │ validation_errors │ total_hires │ total_executions │ avg_rating │
│VARCHAR │ BOOLEAN   │ JSON              │ INTEGER     │ INTEGER          │ FLOAT      │
│ (20)   │ DEFAULT F │                   │ DEFAULT 0   │ DEFAULT 0        │ DEFAULT 0  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   HIRINGS TABLE                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  id (PK) │ created_at │ updated_at │ agent_id (FK) │ user_id (FK) │ status │ hired_at │
│  INTEGER │ TIMESTAMP  │ TIMESTAMP  │ INTEGER       │ INTEGER      │VARCHAR │ TIMESTAMP │
│          │            │            │ NOT NULL      │              │ (20)   │ NOT NULL  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ expires_at │ config │ acp_endpoint │ total_executions │ last_executed_at │ billing_cycle │
│ TIMESTAMP  │ JSON   │ VARCHAR(500) │ INTEGER         │ TIMESTAMP        │ VARCHAR(20)   │
│            │        │              │ DEFAULT 0       │                  │              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ next_billing_date │
│ TIMESTAMP         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  EXECUTIONS TABLE                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  id (PK) │ created_at │ updated_at │ agent_id (FK) │ hiring_id (FK) │ user_id (FK) │
│  INTEGER │ TIMESTAMP  │ TIMESTAMP  │ INTEGER       │ INTEGER        │ INTEGER      │
│          │            │            │ NOT NULL      │                │              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ status │ started_at │ completed_at │ duration_ms │ input_data │ output_data │ error_msg │
│VARCHAR │ TIMESTAMP  │ TIMESTAMP    │ INTEGER     │ JSON        │ JSON        │ TEXT      │
│ (20)   │            │              │             │             │             │           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ cpu_usage │ memory_usage │ disk_usage │ execution_id │ acp_session_id │
│ FLOAT     │ FLOAT        │ FLOAT      │ VARCHAR(64)  │ VARCHAR(64)    │
│           │              │            │ UNIQUE       │                │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Entity Relationship Diagram

```
                    ┌─────────────┐
                    │    USERS    │
                    ├─────────────┤
                    │ id (PK)     │
                    │ username    │
                    │ email       │
                    │ is_active   │
                    │ ...         │
                    └─────────────┘
                           │
                           │ 1:N
                           │
                    ┌─────────────┐
                    │   HIRINGS   │
                    ├─────────────┤
                    │ id (PK)     │
                    │ agent_id(FK)│
                    │ user_id(FK) │
                    │ status      │
                    │ config      │
                    │ ...         │
                    └─────────────┘
                           │
                           │ 1:N
                           │
                    ┌─────────────┐
                    │ EXECUTIONS  │
                    ├─────────────┤
                    │ id (PK)     │
                    │ agent_id(FK)│
                    │ hiring_id(FK)│
                    │ user_id(FK) │
                    │ status      │
                    │ input_data  │
                    │ output_data │
                    │ ...         │
                    └─────────────┘
                           │
                           │ N:1
                           │
                    ┌─────────────┐
                    │   AGENTS    │
                    ├─────────────┤
                    │ id (PK)     │
                    │ name        │
                    │ description │
                    │ status      │
                    │ code        │
                    │ ...         │
                    └─────────────┘
```

## Detailed Field Descriptions

### 🔵 USERS Table
**Purpose:** Store user account information and profiles

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Primary key | AUTO_INCREMENT |
| `username` | VARCHAR(50) | Unique username | UNIQUE, NOT NULL |
| `email` | VARCHAR(255) | User email address | UNIQUE, NOT NULL |
| `full_name` | VARCHAR(255) | User's full name | NULLABLE |
| `is_active` | BOOLEAN | Account active status | DEFAULT TRUE |
| `is_verified` | BOOLEAN | Email verification status | DEFAULT FALSE |
| `hashed_password` | VARCHAR(255) | Password hash | NULLABLE (OAuth) |
| `avatar_url` | VARCHAR(500) | Profile picture URL | NULLABLE |
| `bio` | TEXT | User biography | NULLABLE |
| `preferences` | JSON | User preferences | NULLABLE |

### 🟢 AGENTS Table
**Purpose:** Store agent definitions, metadata, and code

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Primary key | AUTO_INCREMENT |
| `name` | VARCHAR(255) | Agent name | NOT NULL, INDEX |
| `description` | TEXT | Agent description | NOT NULL |
| `version` | VARCHAR(50) | Version string | DEFAULT "1.0.0" |
| `author` | VARCHAR(255) | Agent author | NOT NULL |
| `email` | VARCHAR(255) | Author email | NOT NULL |
| `entry_point` | VARCHAR(255) | Main function/file | NOT NULL |
| `requirements` | JSON | Python dependencies | NULLABLE |
| `config_schema` | JSON | Configuration schema | NULLABLE |
| `code` | TEXT | Agent source code | NULLABLE |
| `tags` | JSON | Search tags | NULLABLE |
| `category` | VARCHAR(100) | Agent category | NULLABLE |
| `status` | VARCHAR(20) | Agent status | DEFAULT "draft" |
| `is_public` | BOOLEAN | Public visibility | DEFAULT FALSE |
| `pricing_model` | VARCHAR(50) | Pricing type | NULLABLE |
| `price_per_use` | FLOAT | Per-use price | NULLABLE |
| `total_hires` | INTEGER | Total hiring count | DEFAULT 0 |
| `total_executions` | INTEGER | Total execution count | DEFAULT 0 |

### 🟡 HIRINGS Table
**Purpose:** Track agent hiring records and configurations

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Primary key | AUTO_INCREMENT |
| `agent_id` | INTEGER | Agent reference | FK → agents.id |
| `user_id` | INTEGER | User reference | FK → users.id, NULLABLE |
| `status` | VARCHAR(20) | Hiring status | DEFAULT "active" |
| `hired_at` | TIMESTAMP | Hiring timestamp | NOT NULL |
| `expires_at` | TIMESTAMP | Expiration date | NULLABLE |
| `config` | JSON | Agent configuration | NULLABLE |
| `acp_endpoint` | VARCHAR(500) | ACP endpoint | NULLABLE |
| `total_executions` | INTEGER | Execution count | DEFAULT 0 |
| `billing_cycle` | VARCHAR(20) | Billing frequency | NULLABLE |

### 🔴 EXECUTIONS Table
**Purpose:** Track agent execution logs and results

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Primary key | AUTO_INCREMENT |
| `agent_id` | INTEGER | Agent reference | FK → agents.id |
| `hiring_id` | INTEGER | Hiring reference | FK → hirings.id, NULLABLE |
| `user_id` | INTEGER | User reference | FK → users.id, NULLABLE |
| `status` | VARCHAR(20) | Execution status | DEFAULT "pending" |
| `started_at` | TIMESTAMP | Start timestamp | NULLABLE |
| `completed_at` | TIMESTAMP | Completion timestamp | NULLABLE |
| `duration_ms` | INTEGER | Execution duration | NULLABLE |
| `input_data` | JSON | Input parameters | NULLABLE |
| `output_data` | JSON | Output results | NULLABLE |
| `error_message` | TEXT | Error details | NULLABLE |
| `execution_id` | VARCHAR(64) | Unique execution ID | UNIQUE, INDEX |
| `cpu_usage` | FLOAT | CPU usage % | NULLABLE |
| `memory_usage` | FLOAT | Memory usage MB | NULLABLE |

## Status Enumerations

### Agent Status Values
```
draft      → submitted → approved → active
   ↓           ↓           ↓         ↓
rejected   → inactive
```

### Hiring Status Values
```
active → expired
   ↓       ↓
cancelled  suspended
```

### Execution Status Values
```
pending → running → completed
   ↓        ↓         ↓
failed   timeout   cancelled
```

## Sample Data Visualization

### Current Database State
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                CURRENT SAMPLE DATA                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ USERS (2 records):                                                                  │
│ ┌─────┬──────────┬─────────────────────┬─────────────┬──────────┐                  │
│ │ ID  │ username │ email               │ full_name   │ is_active│                  │
│ ├─────┼──────────┼─────────────────────┼─────────────┼──────────┤                  │
│ │  1  │ admin    │ admin@agenthub.com  │ System Admin│   true   │                  │
│ │  2  │ creator1 │ creator1@example.com│ Agent Creator│  true   │                  │
│ └─────┴──────────┴─────────────────────┴─────────────┴──────────┘                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ AGENTS (3 records):                                                                 │
│ ┌─────┬────────────────┬─────────────────────┬─────────┬─────────┬─────────┐       │
│ │ ID  │ name           │ description         │ author  │ status  │ is_public│       │
│ ├─────┼────────────────┼─────────────────────┼─────────┼─────────┼─────────┤       │
│ │  1  │ Echo Agent     │ Simple echo agent   │ creator1│approved │  true   │       │
│ │  2  │ Calculator     │ Math operations     │ creator1│approved │  true   │       │
│ │  3  │ Text Processor │ Text analysis       │ creator1│approved │  true   │       │
│ └─────┴────────────────┴─────────────────────┴─────────┴─────────┴─────────┘       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ HIRINGS (0 records) - Created on-demand during testing                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ EXECUTIONS (0 records) - Created on-demand during testing                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Relationships Summary

1. **User → Hiring** (1:N): One user can hire multiple agents
2. **Agent → Hiring** (1:N): One agent can be hired multiple times
3. **Hiring → Execution** (1:N): One hiring can have multiple executions
4. **User → Execution** (1:N): One user can have multiple executions
5. **Agent → Execution** (1:N): One agent can have multiple executions

## Database Growth Patterns

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              EXPECTED DATA GROWTH                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ USERS: Low growth (user accounts)                                                  │
│ AGENTS: Medium growth (agent submissions)                                          │
│ HIRINGS: Medium growth (agent usage)                                               │
│ EXECUTIONS: High growth (execution logs) - Consider archiving old records          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

This visual schema provides a clear understanding of the database structure, relationships, and data flow in the AgentHub system. 