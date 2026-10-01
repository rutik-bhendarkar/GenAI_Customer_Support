## Task 6 – Multilingual Customer Support

Implemented multilingual conversation handling for customer support interactions.

### Supported Languages

- English
- Hindi
- Marathi

### Features Implemented

- Automatic language detection
- Language confidence scoring
- Language clarification detection
- Mixed-language message handling
- Multilingual conversation context
- Conversation history management
- Context window of up to 10 messages
- Customer session isolation
- Session creation and activity tracking
- 30-minute inactivity detection
- Session restoration within 24 hours
- Session expiry after 24 hours
- Order ID normalization
- Protection of order IDs and other structured entities
- Preservation of order IDs during normalization
- Integration with existing ticket workflow
- Integration with sentiment analysis
- Integration with RAG knowledge retrieval
- FastAPI `/chat` integration
- Swagger API testing

### Multilingual Processing Flow

```text
Customer Message
       |
       v
Language Detection
       |
       v
Confidence Check
       |
       +------------------+
       |                  |
   Sufficient          Low Confidence
       |                  |
       v                  v
Normalization       Clarification
       |              Required
       v
Entity Protection
       |
       v
Conversation Context
       |
       v
Session Management
       |
       v
Sentiment Analysis
       |
       v
Ticket Processing
       |
       v
Knowledge Base / RAG
       |
       v
Customer Response

## Task 5 – Multimodal Evidence Upload

Handles customer evidence uploads (invoice, screenshot, order image, PDF)
through `POST /upload`.

### Supported Formats

- PDF (text is extracted with `pypdf`, no external tool required)
- PNG (OCR)
- JPG / JPEG (OCR)

### OCR Requirement (images only)

Image OCR uses `pytesseract`, which needs the **Tesseract OCR executable**.

The executable is resolved in this order:

1. `TESSERACT_CMD` or `TESSERACT_PATH` environment variable
2. `tesseract` available on `PATH`
3. Common Windows install locations, for example
   `C:\Program Files\Tesseract-OCR\tesseract.exe`

If Tesseract is installed in a custom location, set the environment
variable before starting the backend:

```powershell
$env:TESSERACT_CMD = "D:\Tools\Tesseract-OCR\tesseract.exe"
python -m uvicorn backend.main:app --reload
```

Verify the engine is detected:

```powershell
python -c "from backend.multimodal.ocr import get_ocr_engine_diagnostics; print(get_ocr_engine_diagnostics())"
```

If Tesseract is missing, image uploads return HTTP 200 with
`success: false`, `stage: "text_extraction"` and an `ocr_engine`
diagnostics block. PDF uploads keep working.

### Processing Pipeline

```text
Uploaded File
       |
       v
File Validation (extension, size, filename)
       |
       v
Text Extraction (pypdf for PDF, Tesseract OCR for images)
       |
       v
Content Security (prompt-injection patterns)
       |
       v
Structured Extraction
(order IDs, dates, amounts, products, error codes)
       |
       v
Message vs File Comparison (conflict detection)
       |
       v
Processed / Rejected File Handling
```

### API Response

```json
{
    "success": true,
    "filename": "test_order.png",
    "message": "File processed successfully.",
    "extracted_text": "Order ID: ORD12345",
    "extracted_information": {
        "order_ids": ["ORD12345"],
        "dates": [],
        "amounts": [],
        "product_names": [],
        "error_codes": [],
        "comparison": {
            "status": "MATCH",
            "conflict": false,
            "conflicts": [],
            "message_order_ids": ["ORD12345"],
            "file_order_ids": ["ORD12345"]
        }
    },
    "processed_file": "data\\uploads\\processed\\test_order.png"
}
```

Failures return `success: false` together with the failing `stage`
(`file_validation`, `text_extraction`, `content_security`,
`conflict_detection`) and a short `error` / `error_type` description.
Full diagnostics (including tracebacks) are written to the backend log.

### Tests

```powershell
python -m backend.multimodal.test_final
python -m pytest tests -q
```
