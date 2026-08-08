"""WhatsApp Webhook Handler."""
class WhatsAppWebhookHandler:
    def __init__(self, pat_repo, evo_service, adapter):
        self.pat_repo = pat_repo
        self.evo_service = evo_service
        self.adapter = adapter

    def process_incoming_payload(self, sender_phone, text_content, dia_contexto):
        patient = self.pat_repo.get_patient_by_phone(sender_phone)
        if not patient: return {"status": "patient_not_found"}

        self.evo_service.process_voice_report(
            patient_id=patient.id, protocol_id=patient.protocol_id, dia=dia_contexto,
            nivel_dor=4, relato_texto=text_content
        )
        return {"status": "success"}
