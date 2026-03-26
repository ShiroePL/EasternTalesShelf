# Enhanced Logging System for EasternTalesShelf

## Overview
This document describes the enhanced logging system implemented for the MangaUpdates service, featuring comprehensive operation tracking and AI interaction logging.

## New Features

### 1. GPT-OSS-120B Integration
- **Model**: Updated from `meta-llama/llama-4-maverick-17b-128e-instruct` to `openai/gpt-oss-120b`
- **Reasoning**: Enabled with `reasoning_effort="medium"` for better analysis quality
- **Parameters**: 
  - Temperature: 1
  - Max completion tokens: 8192
  - Top-p: 1

### 2. Comprehensive Logging System

#### Groq API Interaction Logs
- **Location**: `logs/groq_interactions_YYYY-MM-DD.log`
- **Format**: JSON with structured data
- **Content**: 
  - Timestamp
  - Model used
  - Reasoning effort level
  - Token usage (prompt, completion, total)
  - Full messages sent
  - Complete responses received

#### Service Operation Logs
- **Location**: `logs/mangaupdates_operations_YYYY-MM-DD.log`
- **Format**: JSON with structured data
- **Tracked Operations**:
  - Update cycle start/completion
  - Manga list retrieval
  - Status update recording
  - Analysis phases
  - Notification saves

#### Service Activity Logs
- **Location**: `logs/mangaupdates_service_YYYY-MM-DD.log`
- **Format**: Standard logging format
- **Content**: General service activity and errors

### 3. Log File Structure

```
logs/
├── groq_interactions_2024-01-15.log     # AI API calls and responses
├── mangaupdates_operations_2024-01-15.log # Service operations tracking
└── mangaupdates_service_2024-01-15.log   # General service logs
```

### 4. Key Improvements

#### Enhanced AI Analysis
- **Reasoning Capability**: GPT-OSS-120B provides better reasoning for manga status analysis
- **Improved Accuracy**: Medium reasoning effort balances quality and performance
- **Better Filtering**: Enhanced notification filtering with reasoning

#### Comprehensive Tracking
- **Full Audit Trail**: Every operation is logged with timestamps and context
- **Performance Monitoring**: Token usage and processing times tracked
- **Error Tracking**: Detailed error logging with context
- **Data Flow**: Complete visibility into data processing pipeline

### 5. Usage Examples

#### Monitoring AI Performance
```bash
# View today's AI interactions
tail -f logs/groq_interactions_$(date +%Y-%m-%d).log

# Count API calls
grep -c "timestamp" logs/groq_interactions_$(date +%Y-%m-%d).log
```

#### Tracking Service Operations
```bash
# Monitor service operations
tail -f logs/mangaupdates_operations_$(date +%Y-%m-%d).log

# Check notification saves
grep "notification_saved" logs/mangaupdates_operations_$(date +%Y-%m-%d).log
```

### 6. Benefits

1. **Debugging**: Detailed logs make troubleshooting much easier
2. **Performance Analysis**: Track token usage and processing efficiency
3. **Quality Assurance**: Monitor AI response quality and accuracy
4. **Audit Trail**: Complete record of all operations for compliance
5. **Optimization**: Identify bottlenecks and optimization opportunities

### 7. Configuration

- Logs are automatically rotated daily
- UTF-8 encoding ensures proper handling of manga titles with special characters
- JSON format allows for easy parsing and analysis
- Git ignores log files to prevent repository bloat

### 8. Future Enhancements

- Log rotation and archiving
- Log analysis dashboard
- Performance metrics visualization
- Automated alerting for errors
- Log aggregation for multiple services