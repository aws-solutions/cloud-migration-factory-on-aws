# Lambda Import Data from S3

## Overview

This Lambda function processes entity import files uploaded to S3, creating and updating entities in the Migration Factory system. It handles entity relationships, cross-references, and provides detailed processing results.

## Trigger

- **Event Source**: S3 Object Creation
- **Prefix Filter**: `uploads/`
- **File Format**: JSON containing entity data validation results

## Processing Flow

### 1. **File Validation & Status Check**

- Retrieves upload metadata from S3 object
- Checks upload status in DynamoDB (prevents duplicate processing)
- Updates status: `pending` → `in-progress`

### 2. **Entity Processing**

- Generates ULIDs for new entities
- Validates entity existence and moves existing entities from CREATE to UPDATE
- Extracts cross-references from CREATE entities → moves to UPDATE phase
- Builds name-to-ID mappings (current file + database lookup)
- Adds bi-directional relationships between all entities
- Validates cross-references exist and resolves names to IDs

### 3. **CREATE Phase**

- POST entities without cross-references (clean creation)
- Processes in batches of 50
- Tracks successful creates and failures
- Failed CREATE entities are removed from subsequent UPDATE operations

### 4. **UPDATE Phase**

- PUT entities with cross-references and bidirectional relationships
- Processes in batches of 50
- Includes entities moved from CREATE phase and bidirectional references
- Tracks successful updates and failures
- Non-existent UPDATE entities are tracked as failures

### 5. **Results & Completion**

- Saves detailed results to S3
- Updates upload status in DynamoDB
- Provides complete audit trail

## Outputs

### DynamoDB Upload Status

**Location**: `{application}-{environment}-upload-entities-metadata` table

| Status | Description | When Set |
|--------|-------------|----------|
| `pending` | Initial upload state | File uploaded to S3 |
| `in-progress` | Currently processing | Lambda starts processing |
| `complete` | All entities processed successfully | No failures occurred |
| `failed` | Processing failed or entities failed | Any failures occurred |

**Upload Record Fields**:

```json
{
  "upload_id": "01234567890ABCDEFGHIJK",
  "status": "complete|failed",
  "results_location": "s3://bucket/results/path/file.json",
  "_history": {
    "lastModifiedBy": {"email": "[system]", "userRef": "[system]"},
    "lastModifiedTimestamp": "2024-01-01T12:00:00.000Z"
  }
}
```

### S3 Results File

**Location**: `s3://{bucket}/results/{original-path}`

- Original: `uploads/batch1/data.json`
- Results: `results/batch1/data.json`

**Results Structure**:

```json
{
  "upload_id": "01234567890ABCDEFGHIJK",
  "original_file": "uploads/batch1/data.json",
  "uploaded_by": "user@example.com",
  "created_items": {
    "app": [
      {"app_id": "01HGX...", "app_name": "MyApp1", "description": "Application 1"},
      {"app_id": "01HGY...", "app_name": "MyApp2", "description": "Application 2"}
    ],
    "server": [
      {"server_id": "01HGZ...", "server_name": "Server1", "server_os": "Linux"}
    ]
  },
  "updated_items": {
    "app": [
      {"app_id": "01HGX...", "server_ids": ["01HGZ..."]}
    ],
    "wave": [
      {"wave_id": "01HH0...", "wave_name": "Wave1", "app_ids": ["01HGX...", "01HGY..."]}
    ]
  },
  "create_failures": {
    "server": {
      "server-001": {
        "data": {"server_name": "server-001", "...": "..."},
        "error_message": "POST request failed: Validation error"
      }
    }
  },
  "update_failures": {
    "app": {
      "app-001": {
        "data": {"app_id": "01HGX...", "server_ids": ["invalid-ref"]},
        "error_message": "Cross-reference validation failed for attributes: server_ids"
      }
    }
  }
}
```

## Outcome Scenarios

### ✅ Complete Success

- **Upload Status**: `complete`
- **Results File**: Contains only `created_items` and `updated_items`
- **Failure Dictionaries**: Empty
- **Log**: "Upload {id} completed successfully. All entities processed without errors."

### ❌ API Failures

- **Upload Status**: `failed`
- **Results File**: Contains failures in `create_failures` or `update_failures`
- **Failure Reasons**:
  - HTTP 4xx/5xx from API Gateway
  - Network timeouts
  - Batch processing errors
- **Log**: "Upload {id} completed with failures. X creates failed, Y updates failed."

### ❌ Cross-Reference Failures

- **Upload Status**: `failed`
- **Results File**: Contains failures in `update_failures`
- **Failure Reasons**:
  - Referenced entity names not found in database
  - Invalid cross-reference format
  - UPDATE entities that don't exist in database
- **Entities**: Removed from processing to prevent broken references
- **Log**: "Cross-reference validation failed for attributes: {attrs}" or "Entity does not exist and cannot be updated"

### ❌ Cascade Failures

- **Upload Status**: `failed`
- **Results File**: Contains failures in both dictionaries
- **Scenario**: CREATE entities fail → UPDATE entities referencing them are removed
- **Behavior**: Prevents orphaned references in database

### ❌ System Failures

- **Upload Status**: `failed`
- **Results File**: May be empty if results saving fails
- **Failure Reasons**:
  - Lambda timeout
  - DynamoDB errors
  - S3 access issues
- **Fallback**: Status updated to `failed` even if results can't be saved

## Error Handling

### Idempotency

- Duplicate S3 events are ignored
- Upload status prevents reprocessing
- Returns early if already `in-progress`, `complete`, or `failed`

### Graceful Degradation

- Individual batch failures don't stop other batches
- Entity type failures don't stop other entity types
- Non-existent UPDATE entities are tracked as failures rather than causing processing to fail
- Always attempts to save results, even on catastrophic failure

### Retry Behavior

- **HTTP Level**: 2 retries for network issues (urllib3)
- **Application Level**: No retries - failures are permanent
- **Status Updates**: Always attempted, with fallback error handling

## Monitoring & Debugging

### Key Log Messages

```text
"Step 1: Reading data from S3 - {bucket}/{key}"
"Step 2: CREATE phase completed - X created, Y failed"
"Step 3: UPDATE phase completed - X updated, Y failed"
"Upload {id} completed successfully|with failures"
```

### Metrics to Monitor

- Upload processing duration
- CREATE/UPDATE success rates
- Cross-reference validation failures
- API Gateway error rates
- DynamoDB throttling

### Common Issues

1. **Cross-reference failures**: Check entity names in upload file vs database
2. **Non-existent UPDATE entities**: Verify entities exist before attempting updates
3. **Missing bidirectional relationships**: Check schema definitions for proper rel_entity attributes
4. **API timeouts**: Monitor API Gateway performance and Lambda timeout settings
5. **Stuck in-progress**: Check for Lambda errors or timeouts
6. **Missing results**: Check S3 permissions and bucket policies
