# ============================================================================
# DEMO SCENARIOS
# ============================================================================

DEMO_SCENARIOS = {
    "Scenario 1: Client Agrees to Pay": {
        "client": "amazon_business",
        "messages": [
            "Bonjour.",
            "Oui, c'est moi qui suis responsable.",
            "D'accord, je comprends.",
            "Je peux payer immédiatement.",
            "Au revoir."
        ]
    },
    "Scenario 2: Client Asks for Time": {
        "client": "dell",
        "messages": [
            "Bonjour.",
            "C'est moi.",
            "Je comprends, mais j'ai besoin de plus de temps.",
            "Je peux payer dans deux semaines.",
            "Merci, à bientôt."
        ]
    },
    "Scenario 3: Robot Question Detection": {
        "client": "microsoft",
        "messages": [
            "Bonjour.",
            "Vous êtes un robot?",
            "D'accord, je comprends.",
            "Je peux payer demain.",
            "À bientôt."
        ]
    }
}#!/usr/bin/env python3
"""
French Debt Collection Agent - Gradio Voice Interface

Text input + voice output interface for the French debt collection agent.
Uses gTTS (free, no credentials needed).
Deploy to HuggingFace Spaces or run locally.

Requirements:
    pip install gradio gtts python-dotenv pyyaml google-generativeai

Usage:
    python gradio_app.py

Then open: http://localhost:7860
"""

import os
import io
import gradio as gr
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
import yaml
from pathlib import Path

# Load environment
load_dotenv()

# Get API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Load config
CONFIG_PATH = os.getenv("CONFIG_PATH", "./config.yaml")
if not Path(CONFIG_PATH).exists():
    raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

CLIENTS = CONFIG.get('clients', {})
AGENT_CONFIG = CONFIG.get('agent', {})
MODEL = AGENT_CONFIG.get('model', 'gemini-1.5-flash')
MAX_HISTORY = AGENT_CONFIG.get('max_history', 10)
CLOSING_WORDS = AGENT_CONFIG.get('closing_words', [])

# ============================================================================
# AGENT CLASS (from agent.py)
# ============================================================================

def build_system_prompt(client_config: dict) -> str:
    """Build French system prompt based on client configuration."""
    return f"""RÔLE
Vous êtes un conseiller professionnel du service clientèle chargé de contacter les clients concernant un cas de facturation pour {client_config['client_name']}.

OBJECTIF
Votre objectif est de :
* Informer le client clairement et respectueusement
* Vérifier brièvement son identité
* Proposer une résolution simple :
   * un paiement,
   * un plan de paiement,
   * ou un suivi ultérieur

Vous n'êtes pas là pour faire de la pression, menacer ou forcer le client.

STYLE ET TON
* Français uniquement
* Professionnel, calme, poli, concis
* Langage naturel convenant à un appel téléphonique
* Jamais agressif ou jugementaire
* Évitez les longues explications
* Ton spécifique: {client_config.get('tone', 'professional')}
* Niveau de formalité: {client_config.get('formality_level', 'medium')}
* Style de formulation: {client_config.get('phrasing', 'direct')}

RÈGLES IMPORTANTES
* Ne mentionnez jamais l'intelligence artificielle, les robots ou l'automatisation
* Si on vous demande "Êtes-vous un robot?" ou quelque chose de similaire, répondez de manière rassurante et professionnelle, comme un humain
* Ne divulguez pas d'informations sensibles sans vérification minimale de l'identité
* Si la personne dit qu'elle n'est pas le bon interlocuteur, excusez-vous et terminez poliment l'appel
* Si la personne est confuse, contrariée ou refuse de continuer, restez calme et proposez un suivi

FLUX D'APPEL GÉNÉRAL
1. Saluez la personne et présentez-vous brièvement
2. Énoncez la raison générale de l'appel (facturation / cas en suspens)
3. Effectuez une vérification d'identité légère (nom ou confirmation qu'ils sont le bon interlocuteur)
4. Présentez l'option principale : {client_config['payment_label']} ou un suivi ultérieur
5. Terminez poliment avec : {client_config['closing_line']}

GESTION DES CAS EXCEPTIONNELS
* Si le client demande plus de temps → proposez un rappel ou un suivi
* Si le client est contrarié → reconnaissez ses sentiments sans argumenter
* Si la situation n'est pas claire → proposez une escalade vers un conseiller humain
* Si le client refuse de continuer → acceptez avec respect et proposez un suivi

PRIORITÉ
Votre priorité est une interaction respectueuse, claire et sûre qui correspond à l'image d'une grande entreprise.

INSTRUCTIONS SUPPLÉMENTAIRES
* Soyez concis et naturel - comme si vous parliez par téléphone
* N'inventez pas de faits sensibles (montants, dates précises, détails personnels)
* Écoutez et répondez aux préoccupations du client
* Proposez des solutions, pas des ultimatums"""

class VoiceAgent:
    """Agent with voice capabilities."""
    
    def __init__(self, client_key: str = None):
        """Initialize agent."""
        if client_key is None:
            client_key = list(CLIENTS.keys())[0]
        
        if client_key not in CLIENTS:
            raise ValueError(f"Client not found: {client_key}")
        
        self.client_key = client_key
        self.client_config = CLIENTS[client_key]
        self.system_prompt = build_system_prompt(self.client_config)
        self.conversation_history = []
        self.model = genai.GenerativeModel(MODEL)
    
    def get_greeting(self) -> str:
        """Get greeting for client."""
        greeting_prompts = {
            "formal": f"Bonjour. Je vous appelle de la part de {self.client_config['client_name']}. Comment puis-je vous aider aujourd'hui?",
            "professional": f"Bonjour, c'est {self.client_config['client_name']}. Comment puis-je vous aider?",
            "collaborative": f"Bonjour. Je suis avec {self.client_config['client_name']}. Comment puis-je vous aider?"
        }
        tone = self.client_config.get('tone', 'professional')
        return greeting_prompts.get(tone, greeting_prompts['professional'])
    
    def is_robot_question(self, text: str) -> bool:
        """Check if question is about being a robot."""
        robot_patterns = [
            "êtes-vous un robot",
            "vous êtes un robot",
            "c'est un robot",
            "vous êtes automat",
            "vous êtes une ia",
            "vous êtes une machine",
            "are you a robot",
            "are you a bot",
            "are you automated",
            "is this automated",
            "real person",
            "vraie personne",
            "real human"
        ]
        text_lower = text.lower().strip()
        return any(pattern in text_lower for pattern in robot_patterns)
    
    def get_robot_response(self) -> str:
        """Get robot question response."""
        robot_responses = {
            "formal": f"Non, je suis un conseiller professionnel de {self.client_config['client_name']}. Je suis ici pour vous aider avec votre compte. Comment puis-je vous assister?",
            "professional": f"Non, je suis un vrai conseiller de {self.client_config['client_name']}. Je suis là pour discuter de votre compte. Comment puis-je vous aider?",
            "collaborative": f"Non, absolument! Je suis une personne réelle de {self.client_config['client_name']}. Je suis ici pour trouver une solution avec vous. Comment je peux vous aider?"
        }
        tone = self.client_config.get('tone', 'professional')
        return robot_responses.get(tone, robot_responses['professional'])
    
    def generate_response(self, user_message: str) -> str:
        """Generate text response."""
        self.conversation_history.append(f"Client: {user_message}")
        
        if self.is_robot_question(user_message):
            response = self.get_robot_response()
            self.conversation_history.append(f"Agent: {response}")
            return response
        
        context = "\n".join(self.conversation_history[-MAX_HISTORY:])
        full_prompt = f"""{self.system_prompt}

[HISTORIQUE DE CONVERSATION]
{context}

[INSTRUCTION] Répondez au client de manière naturelle et professionnelle en français:"""
        
        try:
            response = self.model.generate_content(full_prompt)
            agent_response = response.text
            self.conversation_history.append(f"Agent: {agent_response}")
            return agent_response
        except Exception as e:
            error_response = "Une erreur s'est produite. Pouvez-vous répéter?"
            self.conversation_history.append(f"Agent: {error_response}")
            return error_response
    
    def text_to_speech(self, text: str) -> str:
        """Convert text to speech using gTTS (free) and save as file."""
        try:
            import tempfile
            import os
            
            # Create gTTS object
            tts = gTTS(text=text, lang='fr', slow=False)
            
            # Create a temporary directory in the current working directory
            # so Gradio can access it
            os.makedirs("./audio_cache", exist_ok=True)
            
            # Generate a unique filename
            import hashlib
            filename = hashlib.md5(text.encode()).hexdigest() + ".mp3"
            filepath = f"./audio_cache/{filename}"
            
            # Save only if not already cached
            if not os.path.exists(filepath):
                tts.save(filepath)
            
            # Return the file path
            return filepath
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return None

# ============================================================================
# GRADIO INTERFACE
# ============================================================================

# Global agent instance
current_agent = None

def initialize_agent(client_name: str):
    """Initialize agent with selected client."""
    global current_agent
    client_key = None
    for key, config in CLIENTS.items():
        if config['client_name'] == client_name:
            client_key = key
            break
    
    if not client_key:
        client_key = list(CLIENTS.keys())[0]
    
    current_agent = VoiceAgent(client_key)
    greeting = current_agent.get_greeting()
    current_agent.conversation_history.append(f"Agent: {greeting}")
    
    return greeting, ""

def process_message(user_message: str, conversation_history_text: str) -> tuple:
    """Process user message and generate voice response."""
    global current_agent
    
    if not current_agent or not user_message.strip():
        return conversation_history_text, None
    
    # Generate response
    agent_response = current_agent.generate_response(user_message)
    
    # Update conversation history display
    conversation_text = conversation_history_text + f"\n**Client:** {user_message}\n\n**Agent:** {agent_response}\n\n---\n"
    
    # Generate speech
    audio_data = current_agent.text_to_speech(agent_response)
    
    # Check for closing
    is_closing = any(word in user_message.lower() for word in CLOSING_WORDS)
    
    return conversation_text, audio_data

def reset_conversation(client_name: str):
    """Reset conversation."""
    greeting, _ = initialize_agent(client_name)
    return f"**Agent (Greeting):** {greeting}\n\n---\n", None

def run_demo_scenario(scenario_name: str) -> tuple:
    """Run a complete demo scenario end-to-end."""
    global current_agent
    
    if scenario_name not in DEMO_SCENARIOS:
        return "Invalid scenario"
    
    scenario = DEMO_SCENARIOS[scenario_name]
    client_key = scenario["client"]
    
    # Initialize agent for this scenario
    current_agent = VoiceAgent(client_key)
    
    # Start with greeting
    greeting = current_agent.get_greeting()
    conversation_text = f"**🤖 Agent (Greeting):** {greeting}\n\n---\n"
    current_agent.conversation_history.append(f"Agent: {greeting}")
    
    # Store all audios for playback
    audios_to_return = []
    
    # Generate audio for greeting
    try:
        greeting_audio = current_agent.text_to_speech(greeting)
        audios_to_return.append(greeting_audio)
    except Exception as e:
        print(f"Error generating greeting audio: {e}")
        audios_to_return.append(None)
    
    # Process each message in scenario
    for idx, client_msg in enumerate(scenario["messages"], 1):
        # Add client message
        conversation_text += f"\n**👤 Client:** {client_msg}\n"
        
        # Generate client audio
        try:
            client_audio = current_agent.text_to_speech(client_msg)
            audios_to_return.append(client_audio)
        except Exception as e:
            print(f"Error generating client audio: {e}")
            audios_to_return.append(None)
        
        # Generate agent response
        agent_response = current_agent.generate_response(client_msg)
        
        # Add agent response
        conversation_text += f"\n**🤖 Agent:** {agent_response}\n\n---\n"
        
        # Generate agent audio
        try:
            agent_audio = current_agent.text_to_speech(agent_response)
            audios_to_return.append(agent_audio)
        except Exception as e:
            print(f"Error generating agent audio: {e}")
            audios_to_return.append(None)
    
    # Return transcript and audios (up to 7 audio files)
    result = [conversation_text]
    result.extend(audios_to_return[:7])
    
    # Pad with None if fewer than 7 audios
    while len(result) < 8:
        result.append(None)
    
    return tuple(result)

# Build Gradio interface
def create_interface():
    """Create Gradio interface."""
    
    client_options = [config['client_name'] for config in CLIENTS.values()]
    scenario_options = list(DEMO_SCENARIOS.keys())
    
    with gr.Blocks(title="French Debt Collection Agent - Voice Demo") as demo:
        gr.Markdown("""
# 🇫🇷 French Debt Collection Agent - Voice Demo

Test the agent with **text input** and **voice output**, or run pre-scripted demo scenarios.

## Two Modes:

### 1️⃣ Interactive Mode (Type & Listen)
- Type your responses in French
- Listen to the agent respond
- Full conversation history

### 2️⃣ Demo Mode (Automated)
- Watch pre-scripted scenarios
- See full end-to-end call flow
- Perfect for recording videos

**Example French inputs:**
- `Bonjour.` (Hello)
- `Oui, c'est moi.` (Yes, it's me)
- `Je peux payer demain.` (I can pay tomorrow)
- `Au revoir.` (Goodbye)
        """)
        
        # ===== DEMO SCENARIOS TAB =====
        with gr.Tab("🎬 Demo Scenarios"):
            gr.Markdown("### Run Pre-Scripted End-to-End Call Demos")
            
            with gr.Row():
                scenario_selector = gr.Radio(
                    choices=scenario_options,
                    value=scenario_options[0],
                    label="Select Demo Scenario",
                    interactive=True
                )
                run_demo_btn = gr.Button("▶️ Run Demo", size="lg", variant="primary")
            
            with gr.Row():
                with gr.Column(scale=1.2):
                    demo_display = gr.Textbox(
                        label="📝 Conversation Transcript",
                        lines=16,
                        interactive=False,
                        value="Select a scenario and click 'Run Demo' to start..."
                    )
                
                with gr.Column(scale=0.8):
                    gr.Markdown("### 🔊 Audio")
                    
                    audio1 = gr.Audio(label="Greeting", interactive=False)
                    audio2 = gr.Audio(label="Client 1", interactive=False)
                    audio3 = gr.Audio(label="Agent 1", interactive=False)
                    audio4 = gr.Audio(label="Client 2", interactive=False)
                    audio5 = gr.Audio(label="Agent 2", interactive=False)
                    audio6 = gr.Audio(label="Client 3", interactive=False)
                    audio7 = gr.Audio(label="Agent 3", interactive=False)
            
            run_demo_btn.click(
                fn=run_demo_scenario,
                inputs=[scenario_selector],
                outputs=[demo_display, audio1, audio2, audio3, audio4, audio5, audio6, audio7]
            )
        
        # ===== INTERACTIVE MODE TAB =====
        with gr.Tab("💬 Interactive Mode"):
            gr.Markdown("### Have a Real-Time Conversation")
            
            with gr.Row():
                with gr.Column(scale=1):
                    client_selector = gr.Dropdown(
                        choices=client_options,
                        value=client_options[0],
                        label="Select Client",
                        interactive=True
                    )
                    
                    start_btn = gr.Button("🎙️ Start Conversation", size="lg", variant="primary")
                    reset_btn = gr.Button("🔄 Reset", size="lg")
                
                with gr.Column(scale=2):
                    gr.Markdown("### Conversation")
                    conversation_display = gr.Textbox(
                        label="Conversation History",
                        lines=10,
                        interactive=False,
                        value="Click 'Start Conversation' to begin..."
                    )
            
            with gr.Row():
                with gr.Column(scale=2):
                    user_input = gr.Textbox(
                        label="Your Message (in French)",
                        placeholder="Type in French, e.g., 'Bonjour. Oui, c'est moi.'",
                        lines=3
                    )
                
                with gr.Column(scale=1):
                    send_btn = gr.Button("📤 Send & Listen", size="lg", variant="primary")
                    audio_output = gr.Audio(
                        label="Agent Response (Listen)",
                        interactive=False
                    )
            
            # Event handlers
            start_btn.click(
                fn=initialize_agent,
                inputs=[client_selector],
                outputs=[conversation_display, user_input]
            )
            
            send_btn.click(
                fn=process_message,
                inputs=[user_input, conversation_display],
                outputs=[conversation_display, audio_output]
            ).then(
                fn=lambda: "",
                outputs=[user_input]
            )
            
            reset_btn.click(
                fn=reset_conversation,
                inputs=[client_selector],
                outputs=[conversation_display, audio_output]
            )
            
            user_input.submit(
                fn=process_message,
                inputs=[user_input, conversation_display],
                outputs=[conversation_display, audio_output]
            ).then(
                fn=lambda: "",
                outputs=[user_input]
            )
        
        # ===== INFO TAB =====
        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
### About This Agent

This agent conducts respectful, professional debt collection conversations in French.
It adapts tone and phrasing based on the selected client (Amazon, Dell, Microsoft).

**Features:**
- ✅ Text input, voice output
- ✅ Client-specific greetings and tone
- ✅ Handles robot/AI detection
- ✅ Proper conversation closing
- ✅ Real-time conversation history
- ✅ Free TTS using gTTS (no API keys!)
- ✅ Pre-scripted demo scenarios

**How It Works:**
1. **Interactive Mode:** Type French messages, listen to agent respond
2. **Demo Mode:** Watch automated end-to-end calls with pre-scripted conversations

**Use Cases:**
- Training and demonstration
- Testing conversation flows
- Recording videos for presentations
- Understanding agent behavior across scenarios

**Scenarios Included:**
1. Client agrees to pay
2. Client asks for more time
3. Robot question detection

---

Made with ❤️ using Gradio + French Debt Collection Agent
            """)
    
    return demo
    
    return demo

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        share=True,  # Create public link
        server_name="0.0.0.0",  # For HuggingFace Spaces
        server_port=7860
    )
