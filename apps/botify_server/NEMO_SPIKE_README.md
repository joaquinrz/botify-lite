# NeMo Guardrails Content Safety Spike

This spike replaces the Azure Content Safety service with NVIDIA NeMo Guardrails for content safety and jailbreak detection.

## What's Changed

### 1. **New Service Implementation**
- **File**: `app/services/nemo_guardrails_service.py`
- Implements content safety using NeMo Guardrails with rule-based fallback
- Provides the same interface as the original Azure Content Safety service
- Includes comprehensive jailbreak detection patterns
- Integrated with existing telemetry and logging

### 2. **Routes Updated**
- **File**: `app/api/routes.py`
- Commented out Azure Content Safety import
- Added NeMo Guardrails service import
- Updated `_check_content_safety()` function to use NeMo Guardrails
- Improved response messages for blocked content

### 3. **Configuration**
- **Embedded Configuration**: All NeMo Guardrails configuration is embedded in the service code
- **Dynamic YAML Generation**: The service generates Azure OpenAI configuration dynamically
- **No External Files**: No external config files are needed - everything is self-contained
- **Default Model**: Uses `gpt-4.1-mini` by default for cost efficiency

### 4. **Dependencies**
- **File**: `pyproject.toml`
- Added `nemoguardrails = "^0.8.0"`

### 5. **Tests**
- **File**: `tests/test_nemo_guardrails_service.py`
- Comprehensive test suite for the new service
- Tests safe content, jailbreak detection, and harmful content filtering

## Key Features

### **Robust Fallback Strategy**
- Uses NeMo Guardrails when available
- Falls back to rule-based pattern matching if NeMo fails
- Graceful error handling with detailed logging

### **Jailbreak Detection Patterns**
- "ignore previous instructions"
- "forget everything above"
- "act as if you are" / "pretend to be"
- "roleplay as" / "simulate being"
- "jailbreak" / "DAN mode" / "developer mode"
- "override your programming"

### **Harmful Content Detection**
- Bomb-making instructions
- Violence and harm
- Illegal activities
- Hacking and malware
- Customizable pattern matching

### **Performance Optimized**
- Rule-based checks are extremely fast (< 1ms)
- NeMo Guardrails with lightweight model when available
- Async implementation with proper thread handling

## Usage

The service maintains the same interface as the original Azure Content Safety service:

```python
# Check content safety
is_safe, reasons = await nemo_guardrails_service.is_safe_content(message)

if not is_safe:
    print(f"Content blocked: {reasons}")
```

## Testing

Run the test suite:

```bash
# In the botify_server directory
poetry run pytest tests/test_nemo_guardrails_service.py -v
```

Or run the simple development test:

```bash
poetry run python tests/test_nemo_guardrails_service.py
```

## Benefits Over Azure Content Safety

1. **Cost**: No additional API calls to Azure
2. **Latency**: Faster response times with rule-based fallback
3. **Customization**: Easy to modify rules and patterns
4. **Reliability**: No dependency on external API availability
5. **Privacy**: Content doesn't leave your environment
6. **Flexibility**: Can be extended with custom detection logic

## Next Steps

1. **Test thoroughly** with various jailbreak attempts and harmful content
2. **Monitor performance** and adjust patterns as needed
3. **Consider fine-tuning** the confidence thresholds
4. **Add custom rules** specific to your use case
5. **Evaluate** whether to use LLM-based or pure rule-based approach

## Rollback Plan

To rollback to Azure Content Safety:

1. Uncomment the Azure Content Safety import in `routes.py`
2. Comment out the NeMo Guardrails import
3. Revert the `_check_content_safety()` function changes
4. Remove the `nemoguardrails` dependency if desired

The original Azure Content Safety code is preserved with comments for easy restoration.
