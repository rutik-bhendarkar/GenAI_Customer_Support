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