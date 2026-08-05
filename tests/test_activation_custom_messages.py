import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from utils.locales import get_activation_message, get_confirmation_message, t


class TestActivationCustomMessages(unittest.TestCase):

    def test_get_activation_message_default_fallback(self):
        product = {"name": "Test Product", "delivery_type": "activation"}
        msg_fr = get_activation_message(product, "fr", order_id=123)
        self.assertIn("Paiement", msg_fr)
        self.assertIn("Test Product", msg_fr)

    def test_get_activation_message_custom_english(self):
        product = {
            "name": "Canva Pro",
            "delivery_type": "activation",
            "activation_message": "Please send your account ID or click https://example.com/join for order #{order_id}",
            "activation_message_fr": "Veuillez m'envoyer votre ID ou cliquer sur le lien https://example.com/join pour la commande #{order_id}"
        }
        msg_en = get_activation_message(product, "en", order_id=456)
        self.assertIn("Payment confirmed!", msg_en)
        self.assertIn("Please send your account ID or click https://example.com/join for order #456", msg_en)

        msg_fr = get_activation_message(product, "fr", order_id=456)
        self.assertIn("Paiement", msg_fr)
        self.assertIn("Veuillez m'envoyer votre ID ou cliquer sur le lien https://example.com/join pour la commande #456", msg_fr)


    def test_get_confirmation_message_custom(self):
        product = {
            "name": "Spotify Family",
            "delivery_type": "activation",
            "confirmation_message": "Your Spotify activation for {product} is completed! Order #{order_id}",
            "confirmation_message_fr": "Votre activation Spotify pour {product} est terminée ! Commande #{order_id}"
        }
        conf_fr = get_confirmation_message(product, "fr", order_id=789)
        self.assertEqual(conf_fr, "Votre activation Spotify pour Spotify Family est terminée ! Commande #789")


if __name__ == "__main__":
    unittest.main()
