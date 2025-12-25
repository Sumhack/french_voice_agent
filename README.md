# 🇫🇷 French Debt Collection Agent

A respectful, conversational AI agent that conducts professional debt collection conversations in French. Fully configurable for different client brands with varying tones and phrasing.

**Live Demo:** [HuggingFace Spaces](https://huggingface.co/spaces/sumhack/french_voice_agent) 

---

## ✨ Features

- 🇫🇷 **French-only conversations** - Fully conversational in French
- 🎯 **Configuration-driven** - Easy to adapt tone and phrasing per client
- 🤖 **Human-like responses** - Natural language, not robotic
- 🎙️ **Voice interface** - Text input + voice output (gTTS)
- ✅ **Pre-flight self-test** - Automated health checks
- 🧪 **Test harness** - Synthetic conversation testing with metrics
- 🔒 **Privacy-conscious** - No PII storage, environment-based secrets
- 📱 **Ready for voice input** - Architecture supports Whisper STT integration

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Sumhack/french_voice_agent.git
cd french-debt-collection-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment

```bash
# Copy the template
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_actual_key_here
```

Get your API key: [Google Gemini](https://makersuite.google.com/app/apikey)

### 4. Run Pre-flight Test

```bash
python preflight_test.py
```

Expected output:
```
======================================================================
PRE-FLIGHT SELF-TEST
======================================================================
[1/5] Testing Gemini API connectivity... ✓ PASS
[2/5] Testing configuration loading... ✓ PASS (3 clients)
[3/5] Testing greeting generation... ✓ PASS
[4/5] Testing closing word detection... ✓ PASS
[5/5] Testing robot question detection... ✓ PASS

======================================================================
✓ ALL TESTS PASSED - Agent is ready!
======================================================================
```

---

## 💬 Running the Agent

### Interactive Mode (Text Input)

```bash
# With default client (Amazon Business)
python run_agent.py

# With specific client
python run_agent.py --client dell
python run_agent.py --client microsoft

# List available clients
python run_agent.py --list

# Skip pre-flight test
python run_agent.py --skip-test --client dell
```

### Gradio Web Interface

```bash
python gradio_app.py
```

Then open: `http://localhost:7860`

**Features:**
- 🎬 Demo Scenarios tab - Watch pre-scripted end-to-end calls
- 💬 Interactive Mode tab - Have real conversations
- 🔊 Audio output - Listen to agent responses

---

## ⚙️ Configuration

### Changing Client Presets

Edit `config.yaml` to modify client behavior:

```yaml
clients:
  amazon_business:
    client_name: "Amazon Business"
    tone: "formal"                    # Options: formal, professional, collaborative
    formality_level: "high"           # Options: high, medium, low
    phrasing: "concise"               # Options: concise, direct, conversational
    payment_label: "règlement du solde impayé"
    closing_line: "Merci de votre compréhension et de votre collaboration."
```

### Adding a New Client

```yaml
acme_corp:
  client_name: "ACME Corporation"
  tone: "friendly"
  formality_level: "medium"
  phrasing: "conversational"
  payment_label: "résoudre votre facture"
  closing_line: "À bientôt et merci!"
```

Then run:
```bash
python run_agent.py --client acme_corp
```

### Available Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `tone` | formal, professional, collaborative | Communication style |
| `formality_level` | high, medium, low | Formality of language |
| `phrasing` | concise, direct, conversational | Word choice and structure |
| `client_name` | Any string | Company/brand name |
| `payment_label` | Any string | How to phrase payment resolution |
| `closing_line` | Any string | Professional closing message |

---

## 🔑 Environment Variables

Create a `.env` file (from `.env.example`):

```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
DEFAULT_CLIENT=amazon_business
CONFIG_PATH=./config.yaml
DEBUG=false
```

**Never commit `.env` to version control!**

---

## 🧪 Testing

### Run Pre-flight Test

```bash
python run_agent.py --test 
```

### Run Test Harness

```bash
python test_harness.py                      # Run all tests (18 API calls)
python test_harness.py --client dell        # Test specific client (6 calls)
python test_harness.py --iterations 3       # Run 3 times per scenario (54 calls)
python test_harness.py --verbose            # Show detailed output
```

**Output:** `test_report.md`

### Test Metrics

The test harness measures:
- ✅ **Success Rate** - % of tests passing
- ✅ **Response Time** - Average and P95
- ✅ **Failure Modes** - Why tests failed
- ✅ **Example Transcripts** - Sample conversations

---

## 📊 Test Results

### Latest Test Report

**Generated:** 2025-12-25

| Metric | Value |
|--------|-------|
| Total Tests | 6 |
| Passed | 6 |
| **Success Rate** | **100.0%** |
| Avg Response Time | 4.57s |
| P95 Response Time | 9.19s |

**Scenarios Tested:**
- ✅ Client agrees to pay immediately
- ✅ Client asks for time to pay
- ✅ Client requests payment plan
- ✅ Robot/AI detection question
- ✅ Upset/angry client behavior
- ✅ Multiple language switches

See full report: [test_report.md](https://github.com/Sumhack/french_voice_agent/blob/main/test_report.md)

---

## 🎙️ Voice Interface (Gradio)

### Text Input + Voice Output

```bash
python gradio_app.py
```

**Features:**
- Type in French, listen to agent respond
- Pre-scripted demo scenarios
- Real-time conversation history
- Client selector dropdown
- Audio playback for each exchange

### Deploy to HuggingFace Spaces

1. Create free account at [HuggingFace](https://huggingface.co)
2. Create new Space (Gradio)
3. Upload files:
   - `gradio_app.py`
   - `agent.py`
   - `config.yaml`
   - `requirements.txt`
   - `.env` (with your API key)
4. HuggingFace auto-runs it
5. Share public link

---

## 📁 Project Structure

```
french-debt-collection-agent/
├── agent.py                 # Core agent logic
├── gradio_app.py           # Gradio web interface
├── run_agent.py            # CLI entry point
├── test_harness.py         # Synthetic test suite
├── config.yaml             # Client configurations
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── README.md              # This file
└── test_report.md         # Latest test results
```

---

## 🔧 How It Works

### Architecture

```
User Input (French Text)
    ↓
Agent (agent.py)
    ├─ System Prompt (tone-specific)
    ├─ Robot Detection
    ├─ Conversation History
    └─ Gemini API (Response Generation)
    ↓
Response (French Text)
    ↓
gTTS (Text-to-Speech)
    ↓
Audio Output
```

### Conversation Flow

1. **Greeting** - Agent introduces itself based on client tone
2. **Listen** - Agent understands client concern
3. **Respond** - Agent generates natural response
4. **Iterate** - Conversation continues naturally
5. **End** - User can end anytime

### Agent Personality

- **Formal** - Professional, structured, high-formality
- **Professional** - Direct, medium-formality, concise
- **Collaborative** - Conversational, friendly, problem-solving

---

## 🚨 Troubleshooting

### "GEMINI_API_KEY not found"

```bash
# Check your .env file exists
ls -la .env

# Verify it has your key
cat .env  # (don't share output!)
```

### Pre-flight test fails

```bash
# Run with verbose output
python run_agent.py --test 

# Check:
# 1. Is GEMINI_API_KEY set?
# 2. Is config.yaml in current directory?
# 3. Is internet connection active?
```

### Agent responses are empty

1. Check API quota in Google Cloud Console
2. Verify API key is valid


### "Config file not found"

```bash
# Ensure config.yaml is in the same directory as scripts
pwd
ls -la config.yaml
```

---

## 📝 Example Conversation

```
Agent: Bonjour, c'est Dell. Comment puis-je vous aider?

Client: Bonjour. Oui, c'est moi.

Agent: Merci. Je suis là pour vous aider. Pourriez-vous me faire part 
de la raison de votre appel aujourd'hui?

Client: Je peux payer immédiatement.

Agent: C'est une excellente nouvelle. Nous apprécions votre attention 
à cette affaire.
```

---

## 🎥 Demo Video

Watch the agent in action:
- **Duration:** 60-90 seconds
- **Scenarios:** 2 different client interactions
- **Quality:** Shows conversation flow and audio responses

[View Demo Video](https://www.loom.com/share/423beece0ed6421592c9161907137043)

---

## 📚 Key Files

### agent.py
Core agent logic including:
- System prompt generation
- Robot detection
- Conversation management
- Gemini API integration

### gradio_app.py
Web interface with:
- Interactive conversation mode
- Pre-scripted demo scenarios
- Audio playback
- Client selector

### config.yaml
Client configurations:
- 3 default clients (Amazon, Dell, Microsoft)
- Easy to customize tone/phrasing
- Simple to add new clients

### test_harness.py
Automated testing:
- 6 synthetic scenarios
- Success rate tracking
- Response time metrics
- Detailed failure reporting

---


---

## 🎯 Quick Commands Reference

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env
# (edit .env with your API key)

# Testing
python run_agent.py --test 
python test_harness.py

# Running
python run_agent.py --client dell
python gradio_app.py



```

---

**Built with ❤️ using Gemini API, Gradio, and gTTS**

**Last Updated:** 2025-12-25
