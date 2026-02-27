import unittest

from src.travel_ops.email_parser import EmailParseError, parse_email_content


class EmailParserTests(unittest.TestCase):
    def test_parse_email_content_success(self):
        content = """
Cliente: Cliente A
Viajante: Pessoa B
Data da viagem: 2026-03-10
Destino: Recife
Consultor: Ana
Status: Emitido
Data da compra: 2026-03-01
""".strip()

        record = parse_email_content(content, source_email="email_a.txt")

        self.assertEqual(record.client, "Cliente A")
        self.assertEqual(record.traveler, "Pessoa B")
        self.assertEqual(record.destination, "Recife")
        self.assertEqual(record.purchase_lead_days, 9)

    def test_parse_email_content_missing_fields(self):
        content = "Cliente: Cliente A\nStatus: Emitido"

        with self.assertRaises(EmailParseError) as ctx:
            parse_email_content(content, source_email="email_b.txt")

        self.assertIn("campos obrigatórios", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
