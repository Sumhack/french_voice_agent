import os
import yaml
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# LOAD ENVIRONMENT & CONFIG
# ============================================================================

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CONFIG_PATH = os.getenv("CONFIG_PATH", "./config.yaml")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment. Please set it in .env file.")


# Load configuration from YAML
def load_config(config_path: str = CONFIG_PATH) -> dict:
    """Load configuration from YAML file."""
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


CONFIG = load_config(CONFIG_PATH)

# Extract agent settings and clients
AGENT_CONFIG = CONFIG.get('agent', {})
CLIENTS = CONFIG.get('clients', {})

# Set defaults if not in config
MODEL = AGENT_CONFIG.get('model', 'gemini-1.5-flash')
MAX_HISTORY = AGENT_CONFIG.get('max_history', 10)
CLOSING_WORDS = AGENT_CONFIG.get('closing_words', [])


# ============================================================================
# SYSTEM PROMPT BUILDER
# ============================================================================

def build_system_prompt(client_config: dict) -> str:
    """Build French system prompt based on client configuration."""
    return f"""RÔLE
Vous êtes un conseiller professionnel du service clientèle de {client_config['client_name']}.

OBJECTIF
Votre objectif est de :
* Écouter le client avec respect et empathie
* Comprendre sa situation
* Proposer une résolution simple et claire
* Fermer la conversation de manière respectueuse

Vous n'êtes pas là pour faire de la pression ou menacer le client.

STYLE ET TON
* Français uniquement
* Professionnel, calme, poli et concis
* Langage naturel, comme une vraie conversation
* Jamais agressif ou jugementaire
* Ton spécifique: {client_config.get('tone', 'professional')}
* Niveau de formalité: {client_config.get('formality_level', 'medium')}
* Style: {client_config.get('phrasing', 'direct')}

FLUX DE CONVERSATION - IMPORTANT
1. Saluez le client chaleureusement
2. Écoutez ses préoccupations
3. Proposez des solutions (paiement, plan de paiement, ou suivi ultérieur)
4. Une fois que le client a répondu à vos questions ou accepté une option, préparez-vous à fermer
5. FERMETURE: Quand la conversation atteint naturellement sa fin, terminez avec: "{client_config['closing_line']}"

RÈGLES IMPORTANTES
* Ne mentionnez JAMAIS que vous êtes une IA, un robot ou une automatisation
* Si on vous demande "Êtes-vous un robot?", répondez avec assurance que vous êtes une personne réelle
* Soyez toujours honnête - n'inventez pas de détails
* Si le client demande plus de temps, offrez un suivi ultérieur
* Si le client est en colère, reconnaissez ses sentiments sans argumenter
* Si le client dit qu'il n'est pas la bonne personne, excusez-vous et terminez poliment
* Gardez les réponses concises (2-3 phrases maximum)

SIGNAUX DE FERMETURE
Fermez la conversation immédiatement avec "{client_config['closing_line']}" quand:
* Le client dit "au revoir", "à bientôt", "fin", "quitter", "arrêter", "terminer", "raccrocher"
* Le client a accepté une solution (paiement immédiat, plan de paiement, ou suivi)
* Le client a fourni toutes les informations nécessaires et aucune autre question n'existe
* Après 3 échanges où le client refuse de coopérer

PRIORITÉ
Votre priorité est une interaction respectueuse, claire et naturelle.
Restez bref. Fermez quand c'est approprié."""


# ============================================================================
# AGENT CLASS
# ============================================================================

class FrenchDebtCollectionAgent:
    """French debt collection agent with YAML-based configuration."""

    def __init__(self, client_key: str = None):
        """Initialize agent with client configuration from YAML."""

        # Use default client if not specified
        if client_key is None:
            client_key = os.getenv("DEFAULT_CLIENT", list(CLIENTS.keys())[0])

        if client_key not in CLIENTS:
            available = ", ".join(CLIENTS.keys())
            raise ValueError(f"Client '{client_key}' not found. Available: {available}")

        self.client_key = client_key
        self.client_config = CLIENTS[client_key]
        self.system_prompt = build_system_prompt(self.client_config)
        self.conversation_history = []
        self.model = genai.GenerativeModel(MODEL)

        if DEBUG:
            print(f"[DEBUG] Initialized agent for client: {client_key}")

    def get_greeting(self) -> str:
        """Generate initial greeting based on client tone."""
        greeting_prompts = {
            "formal": f"Bonjour. Je vous appelle de la part de {self.client_config['client_name']}. Comment puis-je vous aider aujourd'hui?",
            "professional": f"Bonjour, c'est {self.client_config['client_name']}. Comment puis-je vous aider?",
            "collaborative": f"Bonjour. Je suis avec {self.client_config['client_name']}. Comment puis-je vous aider?"
        }

        tone = self.client_config.get('tone', 'professional')
        return greeting_prompts.get(tone, greeting_prompts['professional'])

    def is_closing_message(self, text: str) -> bool:
        """Check if user message contains closing words."""
        text_lower = text.lower()
        return any(word in text_lower for word in CLOSING_WORDS)

    def is_robot_question(self, text: str) -> bool:
        """Check if user is asking if agent is a robot."""
        # More specific keywords to avoid false positives
        robot_keywords = [
            "êtes-vous un robot",
            "vous êtes un robot",
            "c'est un robot",
            "automated",
            "automatisé",
            "intelligence artificielle",
            "ia?",
            "chatbot",
            "bot?",
            "real person",
            "vraie personne",
            "human",
            "humain"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in robot_keywords)

    def get_robot_response(self) -> str:
        """Generate brand-safe, human-like response to robot question."""
        robot_responses = {
            "formal": f"Non, je suis un conseiller professionnel de {self.client_config['client_name']}. Je suis ici pour vous aider avec votre compte. Comment puis-je vous assister?",
            "professional": f"Non, je suis un vrai conseiller de {self.client_config['client_name']}. Je suis là pour discuter de votre compte. Comment puis-je vous aider?",
            "collaborative": f"Non, absolument! Je suis une personne réelle de {self.client_config['client_name']}. Je suis ici pour trouver une solution avec vous. Comment je peux vous aider?"
        }

        tone = self.client_config.get('tone', 'professional')
        return robot_responses.get(tone, robot_responses['professional'])

    def generate_response(self, user_message: str) -> str:
        """Generate agent response based on user input."""

        # Add user message to history
        self.conversation_history.append(f"Client: {user_message}")

        # Check for robot question and respond directly
        if self.is_robot_question(user_message):
            robot_response = self.get_robot_response()
            self.conversation_history.append(f"Agent: {robot_response}")
            if DEBUG:
                print("[DEBUG] Robot question detected - using preset response")
            return robot_response

        # Build context from recent history
        context = "\n".join(self.conversation_history[-MAX_HISTORY:])

        # Create full prompt with system instructions
        full_prompt = f"""{self.system_prompt}

[HISTORIQUE DE CONVERSATION]
{context}

[INSTRUCTION] Répondez au client de manière naturelle et professionnelle en français:"""

        try:
            # Call Gemini API
            response = self.model.generate_content(full_prompt)
            agent_response = response.text

            # Add to history
            self.conversation_history.append(f"Agent: {agent_response}")

            if DEBUG:
                print(f"[DEBUG] Generated response ({len(agent_response)} chars)")

            return agent_response

        except Exception as e:
            error_msg = f"Une erreur s'est produite. Pouvez-vous répéter, s'il vous plaît?"
            self.conversation_history.append(f"Agent: {error_msg}")
            print(f"\n[ERREUR]: {str(e)}\n")
            return error_msg

    def start(self) -> str:
        """Start the conversation with greeting."""
        greeting = self.get_greeting()
        self.conversation_history.append(f"Agent: {greeting}")
        return greeting


# ============================================================================
# PRE-FLIGHT SELF-TEST
# ============================================================================

def run_preflight_test() -> bool:
    """Run pre-flight self-test before starting agent."""
    print("\n" + "=" * 70)
    print("PRE-FLIGHT SELF-TEST")
    print("=" * 70 + "\n")

    all_passed = True

    # Test 1: Check Gemini API connectivity
    print("[1/5] Testing Gemini API connectivity...", end=" ")
    try:
        model = genai.GenerativeModel(MODEL)
        response = model.generate_content("Dites 'OK' en un mot.")
        if response.text:
            print("✓ PASS\n")
        else:
            print("✗ FAIL (no response)\n")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL ({str(e)[:50]}...)\n")
        all_passed = False

    # Test 2: Check configuration loading
    print("[2/5] Testing configuration loading...", end=" ")
    try:
        if len(CLIENTS) >= 3:
            clients_list = ", ".join(list(CLIENTS.keys())[:3])
            print(f"✓ PASS ({len(CLIENTS)} clients loaded: {clients_list})\n")
        else:
            print(f"✗ FAIL (only {len(CLIENTS)} client(s), need at least 3)\n")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL ({str(e)})\n")
        all_passed = False

    # Test 3: Test greeting generation
    print("[3/5] Testing greeting generation for all clients...", end=" ")
    try:
        for client_key in list(CLIENTS.keys())[:3]:  # Test first 3
            agent = FrenchDebtCollectionAgent(client_key)
            greeting = agent.get_greeting()
            if not greeting or len(greeting) < 20:
                print(f"✗ FAIL (invalid greeting for {client_key})\n")
                all_passed = False
                return all_passed
        print("✓ PASS (all clients have valid greetings)\n")
    except Exception as e:
        print(f"✗ FAIL ({str(e)})\n")
        all_passed = False

    # Test 4: Test closing word detection
    print("[4/5] Testing closing word detection...", end=" ")
    try:
        agent = FrenchDebtCollectionAgent()
        test_cases = [
            ("Au revoir", True),
            ("À bientôt", True),
            ("Je dois y aller, au revoir", True),
            ("Oui, je peux payer demain", False),
            ("Bonjour", False)
        ]

        all_correct = all(agent.is_closing_message(text) == expected for text, expected in test_cases)
        if all_correct:
            print("✓ PASS (all test cases correct)\n")
        else:
            print("✗ FAIL (some test cases failed)\n")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL ({str(e)})\n")
        all_passed = False

    # Test 5: Test robot detection
    print("[5/5] Testing robot question detection...", end=" ")
    try:
        agent = FrenchDebtCollectionAgent()
        test_cases = [
            ("Vous êtes un robot ?", True),
            ("Are you a bot?", True),
            ("C'est une vraie personne?", True),
            ("Bonjour", False),
            ("Je veux payer", False)
        ]

        all_correct = all(agent.is_robot_question(text) == expected for text, expected in test_cases)
        if all_correct:
            print("✓ PASS (all test cases correct)\n")
        else:
            print("✗ FAIL (some test cases failed)\n")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL ({str(e)})\n")
        all_passed = False

    # Summary
    print("=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Agent is ready!")
        print("=" * 70 + "\n")
        return True
    else:
        print("✗ SOME TESTS FAILED - Please check configuration")
        print("=" * 70 + "\n")
        return False


def run_agent(client_key: str = None):
    """Run the French debt collection agent."""

    # Initialize agent with Gemini API
    genai.configure(api_key=GEMINI_API_KEY)

    # Initialize agent
    agent = FrenchDebtCollectionAgent(client_key)
    client_config = agent.client_config

    print(f"\n{'=' * 70}")
    print(f"Agent de Recouvrement - Client: {client_config['client_name']}")
    print(f"Ton: {client_config.get('tone', 'N/A')} | Formalité: {client_config.get('formality_level', 'N/A')}")
    print(f"Tapez l'une de ces phrases pour terminer: {', '.join(CLOSING_WORDS[:4])}, ...")
    print(f"{'=' * 70}\n")

    # Start conversation
    greeting = agent.start()
    print(f"Agent: {greeting}\n")

    # Conversation loop
    while True:
        user_input = input("Vous: ").strip()

        if not user_input:
            continue

        # Check for closing words (in French)
        if agent.is_closing_message(user_input):
            print(f"\nAgent: Au revoir. Merci d'avoir discuté avec nous. {agent.client_config['closing_line']}\n")
            print(f"{'=' * 70}")
            print(f"Conversation terminée.")
            print(f"Nombre de messages échangés: {len(agent.conversation_history)}")
            print(f"{'=' * 70}\n")
            break

        # Generate response
        response = agent.generate_response(user_input)
        print(f"\nAgent: {response}\n")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys

    # Check for command line arguments
    client_key = None
    if "--client" in sys.argv:
        idx = sys.argv.index("--client")
        if idx + 1 < len(sys.argv):
            client_key = sys.argv[idx + 1]

    # Run agent
    try:
        run_agent(client_key=client_key)
    except KeyboardInterrupt:
        print("\n\n[Session terminée par l'utilisateur]\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        sys.exit(1)